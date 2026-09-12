import time
import uuid
import joblib
import logging
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models import RouteStop, InferenceLog
from src.api.schemas import PredictionRequest, PredictionResponse, MonotonicQuantilesSchema
from src.services.weather import WeatherService
from src.services.decision_optimizer import optimize_commute_decision

logger = logging.getLogger(__name__)

router = APIRouter()

# Instantiate external services
weather_service = WeatherService()

# ── Weather condition presets ───────────────────────────────────────────────────
# Maps user-friendly condition labels to the 3 weather features the model was
# trained on. Values are representative historical medians from the DB training
# data so predictions stay well within the model's learned feature space.
WEATHER_PRESETS: dict[str, dict[str, float]] = {
    "clear":   {"precipitation_mm": 0.0,  "apparent_temperature_c": 20.0, "wind_speed_kmh": 8.0},
    "cloudy":  {"precipitation_mm": 0.2,  "apparent_temperature_c": 15.0, "wind_speed_kmh": 14.0},
    "rainy":   {"precipitation_mm": 4.5,  "apparent_temperature_c": 11.0, "wind_speed_kmh": 22.0},
    "snowy":   {"precipitation_mm": 2.0,  "apparent_temperature_c": -2.0, "wind_speed_kmh": 18.0},
    "stormy":  {"precipitation_mm": 12.0, "apparent_temperature_c": 8.0,  "wind_speed_kmh": 45.0},
}

# Global Model Loading Strategy
# Caching ML models in global state avoids the severe latency hit of 
# reading heavily serialized joblib files from disk on every API request.
try:
    preprocessor = joblib.load("artifacts/feature_pipeline.joblib")
    model_q10 = joblib.load("artifacts/model_q10.joblib")
    model_q50 = joblib.load("artifacts/model_q50.joblib")
    model_q90 = joblib.load("artifacts/model_q90.joblib")
    logger.info("Successfully loaded ML feature pipeline and LightGBM models.")
except FileNotFoundError:
    preprocessor = None
    model_q10 = None
    model_q50 = None
    model_q90 = None
    logger.warning("ML models not found in artifacts/. Please run training pipeline before using the predict endpoint.")

@router.post("/predict", response_model=PredictionResponse)
async def predict_route(request: PredictionRequest, db: Session = Depends(get_db)):
    """
    Main RouteTrust predictive inference endpoint.
    Retrieves static route data, pulls async weather conditions, engineers features, 
    evaluates through quantile ML models, optimizes the leave-by decision, and logs everything to SQLite.
    """
    start_time = time.perf_counter()
    request_uuid = str(uuid.uuid4())
    
    if not preprocessor or not model_q10:
        raise HTTPException(
            status_code=500, 
            detail="Machine learning models are not initialized. Please run the training pipeline."
        )
        
    # 1. Lookup Route Stop
    route_stop = db.query(RouteStop).filter(RouteStop.id == request.route_stop_id).first()
    if not route_stop:
        raise HTTPException(
            status_code=404, 
            detail=f"Route stop ID {request.route_stop_id} not found in database."
        )
        
    # 2. Fetch Live or Fallback Weather (Async), then optionally override with user preset
    weather_data = await weather_service.get_weather_data(route_stop_id=route_stop.id, db_session=db)

    condition_key = (request.weather_condition or "current").strip().lower()
    if condition_key in WEATHER_PRESETS:
        preset = WEATHER_PRESETS[condition_key]
        # Override only the 3 weather features; keep source tag for UI display
        weather_data["precipitation_mm"]      = preset["precipitation_mm"]
        weather_data["apparent_temperature_c"] = preset["apparent_temperature_c"]
        weather_data["wind_speed_kmh"]         = preset["wind_speed_kmh"]
        weather_data["source"] = f"preset:{condition_key}"
    
    # 3. Construct the Feature Vector
    target_time = request.target_arrival_time
    hour_of_day = target_time.hour
    day_of_week = target_time.weekday()
    
    num_features = [
        'scheduled_travel_time_sec', 
        'hour_of_day', 
        'day_of_week', 
        'precipitation_mm', 
        'apparent_temperature_c', 
        'wind_speed_kmh'
    ]
    
    # Create single-row pandas DataFrame matching the ML pipeline input schema
    input_df = pd.DataFrame([{
        'scheduled_travel_time_sec': route_stop.scheduled_travel_time_sec,
        'hour_of_day': hour_of_day,
        'day_of_week': day_of_week,
        'precipitation_mm': weather_data['precipitation_mm'],
        'apparent_temperature_c': weather_data['apparent_temperature_c'],
        'wind_speed_kmh': weather_data['wind_speed_kmh']
    }])
    
    # 4. Transform features using serialized StandardScaler/ColumnTransformer
    X_num = preprocessor.transform(input_df)
    
    if isinstance(X_num, pd.DataFrame):
        X_num = X_num.values
        
    X_pred = pd.DataFrame(X_num, columns=num_features)
    
    # Route_stop_id is handled natively by lightgbm as a 'category' type
    X_pred['route_stop_id'] = pd.Categorical([route_stop.id])
    
    # 5. Run ML Inference 
    raw_q10 = float(model_q10.predict(X_pred)[0])
    raw_q50 = float(model_q50.predict(X_pred)[0])
    raw_q90 = float(model_q90.predict(X_pred)[0])
    
    # 6. Postprocess & Optimize Decision
    decision = optimize_commute_decision(
        target_arrival=target_time,
        scheduled_travel_sec=route_stop.scheduled_travel_time_sec,
        raw_q10=raw_q10,
        raw_q50=raw_q50,
        raw_q90=raw_q90,
        alpha=request.alpha
    )
    
    # Grab the low confidence flag directly from DB schema
    low_confidence = route_stop.is_low_sample
    
    # Calculate end-to-end latency
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    # 7. Audit Logging (Write to DB)
    inference_log = InferenceLog(
        request_uuid=request_uuid,
        route_stop_id=route_stop.id,
        required_arrival_time=target_time,
        alpha=request.alpha,
        raw_q10_delay_sec=raw_q10,
        raw_q50_delay_sec=raw_q50,
        raw_q90_delay_sec=raw_q90,
        adjusted_q_delay_sec=decision.risk_delay_sec,
        recommended_leave_by=decision.recommended_leave_by,
        reliability_grade=decision.reliability_grade,
        weather_source=weather_data['source'],
        guard_triggered=decision.guard_triggered,
        low_confidence_flag=low_confidence,
        latency_ms=latency_ms
    )
    db.add(inference_log)
    db.commit()
    
    # 8. Return structured JSON response
    return PredictionResponse(
        request_uuid=request_uuid,
        recommended_leave_by=decision.recommended_leave_by,
        scheduled_departure=decision.scheduled_departure,
        risk_delay_sec=decision.risk_delay_sec,
        reliability_grade=decision.reliability_grade,
        interquantile_spread=decision.interquantile_spread,
        weather_source=weather_data['source'],
        weather_condition=request.weather_condition,
        guard_triggered=decision.guard_triggered,
        low_confidence_flag=low_confidence,
        monotonic_quantiles=MonotonicQuantilesSchema(
            q10=decision.monotonic_quantiles['q10'],
            q50=decision.monotonic_quantiles['q50'],
            q90=decision.monotonic_quantiles['q90']
        ),
        latency_ms=latency_ms
    )
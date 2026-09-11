from pydantic import BaseModel, Field
from datetime import datetime

class PredictionRequest(BaseModel):
    route_stop_id: int = Field(
        ..., 
        description="The unique identifier for the Route/Stop combination in the database (e.g., 1 to 4)."
    )
    target_arrival_time: datetime = Field(
        ..., 
        description="The user's desired arrival time at the destination stop."
    )
    alpha: float = Field(
        default=0.20, 
        ge=0.01, 
        le=0.99, 
        description="Risk tolerance factor for the prediction. Lower means less tolerance for being late (more conservative)."
    )


class MonotonicQuantilesSchema(BaseModel):
    q10: float = Field(
        ..., 
        description="The 10th percentile predicted delay in seconds (optimistic)."
    )
    q50: float = Field(
        ..., 
        description="The 50th percentile predicted delay in seconds (median expectation)."
    )
    q90: float = Field(
        ..., 
        description="The 90th percentile predicted delay in seconds (pessimistic)."
    )


class PredictionResponse(BaseModel):
    request_uuid: str = Field(
        ..., 
        description="A unique UUID dynamically generated to track this specific request."
    )
    recommended_leave_by: datetime = Field(
        ..., 
        description="The optimized, recommended time the user needs to leave for the stop."
    )
    scheduled_departure: datetime = Field(
        ..., 
        description="The standard scheduled departure time based purely on GTFS transit timetables."
    )
    risk_delay_sec: float = Field(
        ..., 
        description="The calculated delay buffer in seconds added based on the user's alpha."
    )
    reliability_grade: str = Field(
        ..., 
        description="The reliability grade of the prediction interval spread (A, B, C, D, or F)."
    )
    interquantile_spread: float = Field(
        ..., 
        description="The relative spread between the pessimistic and optimistic quantiles."
    )
    weather_source: str = Field(
        ..., 
        description="The source of the weather data injected into the model ('live' or 'sqlite_fallback')."
    )
    guard_triggered: bool = Field(
        ..., 
        description="True if the ML model predicted leaving later than scheduled and was clamped by the Early Departure Guard."
    )
    low_confidence_flag: bool = Field(
        ..., 
        description="True if the RouteStop lacks sufficient historical sample data in the database."
    )
    monotonic_quantiles: MonotonicQuantilesSchema = Field(
        ..., 
        description="The raw machine learning quantile outputs, enforced to be strictly non-decreasing."
    )
    latency_ms: float = Field(
        ..., 
        description="The total latency of the entire prediction processing pipeline in milliseconds."
    )

import logging
import httpx
from datetime import datetime
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from src.db.models import WeatherFallback

logger = logging.getLogger(__name__)

class WeatherData(BaseModel):
    precipitation_mm: float
    apparent_temperature_c: float
    wind_speed_kmh: float
    source: str

class WeatherService:
    def __init__(self, timeout: float = 3.0):
        self.timeout = timeout
        # Using Open-Meteo public API as specified
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    async def fetch_live_weather(self, lat: float, lon: float) -> dict | None:
        """
        Fetches live weather from Open-Meteo with a strict timeout.
        Returns a dictionary of relevant metrics if successful, otherwise None.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "precipitation,apparent_temperature,wind_speed_10m"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                current = data.get("current", {})
                
                if not current:
                    logger.warning("Live weather API returned an unexpected or empty payload.")
                    return None
                    
                return {
                    "precipitation_mm": float(current.get("precipitation", 0.0)),
                    "apparent_temperature_c": float(current.get("apparent_temperature", 0.0)),
                    "wind_speed_kmh": float(current.get("wind_speed_10m", 0.0)),
                }
                
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"Live weather fetch failed (network or HTTP error): {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching live weather: {str(e)}")
            return None

    async def get_weather_data(self, route_stop_id: int, db_session: Session, lat: float = 40.7128, lon: float = -74.0060) -> dict:
        """
        Attempts to fetch live weather first (using defaulted NYC coordinates since they aren't stored in RouteStop).
        If the fetch fails or times out, safely falls back to querying the SQLite weather_fallbacks table.
        """
        logger.info(f"Attempting to fetch live weather for coordinates ({lat}, {lon})")
        live_data = await self.fetch_live_weather(lat, lon)
        
        if live_data:
            try:
                # Validate and structure the live data using Pydantic
                weather = WeatherData(
                    precipitation_mm=live_data["precipitation_mm"],
                    apparent_temperature_c=live_data["apparent_temperature_c"],
                    wind_speed_kmh=live_data["wind_speed_kmh"],
                    source="live"
                )
                logger.info("Successfully retrieved live weather data.")
                return weather.model_dump()
            except ValidationError as e:
                logger.error(f"Validation error on live weather data payload: {e}")
                # Fall through to the database fallback
        
        logger.warning(f"Falling back to SQLite weather database for route_stop_id={route_stop_id}...")
        
        now = datetime.now()
        month = now.month
        hour = now.hour
        
        # Query the SQLite fallback table
        fallback = db_session.query(WeatherFallback).filter(
            WeatherFallback.route_stop_id == route_stop_id,
            WeatherFallback.month == month,
            WeatherFallback.hour == hour
        ).first()
        
        if fallback:
            # Validate and structure the fallback data
            weather = WeatherData(
                precipitation_mm=fallback.median_precipitation_mm,
                apparent_temperature_c=fallback.median_apparent_temperature_c,
                wind_speed_kmh=fallback.median_wind_speed_kmh,
                source="sqlite_fallback"
            )
            logger.info("Successfully retrieved fallback weather data from SQLite.")
            return weather.model_dump()
            
        logger.error(f"CRITICAL: No fallback weather data found for route_stop_id={route_stop_id}, month={month}, hour={hour}.")
        
        # Absolute last-resort default
        emergency_weather = WeatherData(
            precipitation_mm=0.0,
            apparent_temperature_c=15.0,
            wind_speed_kmh=10.0,
            source="emergency_default"
        )
        return emergency_weather.model_dump()

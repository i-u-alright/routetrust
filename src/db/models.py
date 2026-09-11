from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, DateTime, ForeignKey, SmallInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base

class RouteStop(Base):
    __tablename__ = "routes_stops"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    stop_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    route_short_name: Mapped[str] = mapped_column(String(128), nullable=False)
    stop_name: Mapped[str] = mapped_column(String(256), nullable=False)
    scheduled_travel_time_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_low_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    weather_fallbacks: Mapped[list["WeatherFallback"]] = relationship(back_populates="route_stop", cascade="all, delete-orphan")
    inference_logs: Mapped[list["InferenceLog"]] = relationship(back_populates="route_stop", cascade="all, delete-orphan")


class WeatherFallback(Base):
    __tablename__ = "weather_fallbacks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    route_stop_id: Mapped[int] = mapped_column(ForeignKey("routes_stops.id"), index=True, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hour: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    median_precipitation_mm: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    median_apparent_temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    median_wind_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    route_stop: Mapped["RouteStop"] = relationship(back_populates="weather_fallbacks")


class InferenceLog(Base):
    __tablename__ = "inference_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    route_stop_id: Mapped[int] = mapped_column(ForeignKey("routes_stops.id"), nullable=False)
    required_arrival_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    alpha: Mapped[float] = mapped_column(Float, nullable=False)
    raw_q10_delay_sec: Mapped[float] = mapped_column(Float, nullable=False)
    raw_q50_delay_sec: Mapped[float] = mapped_column(Float, nullable=False)
    raw_q90_delay_sec: Mapped[float] = mapped_column(Float, nullable=False)
    adjusted_q_delay_sec: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_leave_by: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reliability_grade: Mapped[str] = mapped_column(String(2), nullable=False)
    weather_source: Mapped[str] = mapped_column(String(32), nullable=False)
    guard_triggered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    low_confidence_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    route_stop: Mapped["RouteStop"] = relationship(back_populates="inference_logs")

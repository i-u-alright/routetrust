from src.db.session import engine, SessionLocal, Base
from src.db.models import RouteStop, WeatherFallback, InferenceLog

def init_db():
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    print("Initializing database session...")
    with SessionLocal() as db:
        existing_stops = db.query(RouteStop).count()
        if existing_stops > 0:
            print("Database already seeded. Skipping.")
            return
            
        print("Seeding RouteStop data...")
        stops_data = [
            RouteStop(
                route_id="M15-SBS", stop_id="401923", route_short_name="M15-SBS Southbound",
                stop_name="2nd Ave & E 34th St", scheduled_travel_time_sec=1380,
                sample_count=1420, is_low_sample=False
            ),
            RouteStop(
                route_id="B63", stop_id="308211", route_short_name="B63 Westbound",
                stop_name="5th Ave & 9th St", scheduled_travel_time_sec=960,
                sample_count=22, is_low_sample=True
            ),
            RouteStop(
                route_id="Q32", stop_id="502188", route_short_name="Q32 Queens Blvd",
                stop_name="Queens Blvd & 48th St", scheduled_travel_time_sec=1800,
                sample_count=850, is_low_sample=False
            ),
            RouteStop(
                route_id="BX12-SBS", stop_id="102944", route_short_name="BX12-SBS Crosstown",
                stop_name="Pelham Pkwy & White Plains Rd", scheduled_travel_time_sec=1140,
                sample_count=1600, is_low_sample=False
            )
        ]
        
        # We need to add and commit the stops first so they get primary keys (stop.id)
        db.add_all(stops_data)
        db.commit()
        
        print("Seeding WeatherFallback data...")
        for stop in stops_data:
            weather_fallbacks = []
            for h in range(24):
                weather_fallbacks.append(
                    WeatherFallback(
                        route_stop_id=stop.id,
                        month=9,
                        hour=h,
                        median_precipitation_mm=0.0,
                        median_apparent_temperature_c=round(18.0 + (h * 0.4), 2),
                        median_wind_speed_kmh=round(10.0 + (h * 0.2), 2)
                    )
                )
            db.add_all(weather_fallbacks)
            
        db.commit()
        print("Database seeding completed successfully.")

if __name__ == "__main__":
    init_db()

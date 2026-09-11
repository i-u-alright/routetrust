import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler

def generate_synthetic_data(num_samples: int = 5000) -> pd.DataFrame:
    np.random.seed(42)
    
    # Generate dates over the last few weeks in chronological order
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    timestamps = [start_date + timedelta(seconds=int(x)) for x in np.random.uniform(0, 30*24*3600, num_samples)]
    timestamps.sort()
    
    route_stop_ids = np.random.choice([1, 2, 3, 4], size=num_samples)
    
    # Simple mapping for scheduled_travel_time_sec based on init_db definitions
    travel_times = {1: 1380, 2: 960, 3: 1800, 4: 1140}
    scheduled_travel_time_sec = np.array([travel_times[rs] for rs in route_stop_ids])
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'route_stop_id': route_stop_ids,
        'scheduled_travel_time_sec': scheduled_travel_time_sec
    })
    
    df['hour_of_day'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    
    # Weather feature generation
    # Zero-inflated exponential for precipitation
    is_raining = np.random.choice([0, 1], p=[0.8, 0.2], size=num_samples)
    precipitation_mm = is_raining * np.random.exponential(scale=2.0, size=num_samples)
    
    apparent_temperature_c = np.random.uniform(15.0, 30.0, size=num_samples)
    wind_speed_kmh = np.random.uniform(5.0, 25.0, size=num_samples)
    
    df['precipitation_mm'] = precipitation_mm
    df['apparent_temperature_c'] = apparent_temperature_c
    df['wind_speed_kmh'] = wind_speed_kmh
    
    # Delay logic
    # Base delay with positive skew (lognormal)
    base_delay = np.random.lognormal(mean=3.0, sigma=1.0, size=num_samples)
    
    # Weather interaction: rain increases variance and mean
    weather_impact = precipitation_mm * np.random.uniform(10, 50, size=num_samples)
    
    # Random early arrivals
    early_arrivals = np.random.uniform(-60, 0, size=num_samples)
    is_early = np.random.choice([0, 1], p=[0.9, 0.1], size=num_samples)
    
    delay_sec = (base_delay + weather_impact) * (1 - is_early) + early_arrivals * is_early
    df['delay_sec'] = delay_sec
    
    return df

def main():
    print("Starting ML data pipeline...")
    
    # Ensure directories exist
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("artifacts", exist_ok=True)
    
    raw_path = "data/raw/gtfs_rt_archive.parquet"
    
    # 1. Synthetic Data Generation
    if not os.path.exists(raw_path):
        print(f"Generating synthetic dataset of 5,000 observations at {raw_path}...")
        df = generate_synthetic_data(5000)
        df.to_parquet(raw_path, index=False)
    else:
        print(f"Loading existing raw dataset from {raw_path}...")
        df = pd.read_parquet(raw_path)
    
    print(f"Total raw rows loaded: {len(df)}")
    
    # 3. Chronological Holdout Split
    # Sort strictly by timestamp to prevent temporal leakage
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    holdout_df = df.iloc[split_idx:].copy()
    
    # Assert temporal integrity
    assert train_df['timestamp'].max() <= holdout_df['timestamp'].min(), "Temporal data leakage detected!"
    
    print(f"Train set: {len(train_df)} rows.")
    print(f"  --> Train window: {train_df['timestamp'].min()} to {train_df['timestamp'].max()}")
    print(f"Holdout set: {len(holdout_df)} rows.")
    print(f"  --> Holdout window: {holdout_df['timestamp'].min()} to {holdout_df['timestamp'].max()}")
    
    # 2. Feature Preprocessing & Transformation
    num_features = [
        'scheduled_travel_time_sec', 
        'hour_of_day', 
        'day_of_week', 
        'precipitation_mm', 
        'apparent_temperature_c', 
        'wind_speed_kmh'
    ]
    
    print("Fitting feature ColumnTransformer pipeline on training data...")
    preprocessor = ColumnTransformer(
        transformers=[
            ('num_scaler', StandardScaler(), num_features)
        ],
        remainder='passthrough',
        verbose_feature_names_out=False
    )
    
    # Use pandas output to preserve feature names if supported (sklearn >= 1.2)
    try:
        preprocessor.set_output(transform='pandas')
    except AttributeError:
        pass # Fallback for older scikit-learn versions
        
    preprocessor.fit(train_df[num_features])
    
    # Save clean datasets
    train_path = "data/processed/train.parquet"
    holdout_path = "data/processed/holdout.parquet"
    train_df.to_parquet(train_path, index=False)
    holdout_df.to_parquet(holdout_path, index=False)
    print(f"Saved split datasets to {train_path} and {holdout_path}")
    
    # Save fitted transformer
    joblib_path = "artifacts/feature_pipeline.joblib"
    joblib.dump(preprocessor, joblib_path)
    print(f"Serialized fitted feature pipeline to {joblib_path}")
    
    print("Pipeline execution completed successfully.")

if __name__ == "__main__":
    main()

import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
import lightgbm as lgb

def pinball_loss(y_true, y_pred, tau):
    return np.mean(np.maximum(tau * (y_true - y_pred), (1 - tau) * (y_pred - y_true)))

def main():
    print("Loading data and preprocessing pipeline...")
    train_df = pd.read_parquet("data/processed/train.parquet")
    holdout_df = pd.read_parquet("data/processed/holdout.parquet")
    preprocessor = joblib.load("artifacts/feature_pipeline.joblib")
    
    num_features = [
        'scheduled_travel_time_sec', 
        'hour_of_day', 
        'day_of_week', 
        'precipitation_mm', 
        'apparent_temperature_c', 
        'wind_speed_kmh'
    ]
    
    target = 'delay_sec'
    y_train = train_df[target].values
    y_holdout = holdout_df[target].values
    
    print("Transforming features...")
    # Transform numerical features
    X_train_num = preprocessor.transform(train_df[num_features])
    X_holdout_num = preprocessor.transform(holdout_df[num_features])
    
    # Ensure it's a numpy array for consistent DataFrame creation
    if isinstance(X_train_num, pd.DataFrame):
        X_train_num = X_train_num.values
        X_holdout_num = X_holdout_num.values
        
    # Reconstruct DataFrames with features and categorical route_stop_id
    X_train = pd.DataFrame(X_train_num, columns=num_features)
    X_train['route_stop_id'] = pd.Categorical(train_df['route_stop_id'])
    
    X_holdout = pd.DataFrame(X_holdout_num, columns=num_features)
    X_holdout['route_stop_id'] = pd.Categorical(holdout_df['route_stop_id'])
    
    print("Training Quantile Regression Models...")
    params = {
        'objective': 'quantile',
        'n_estimators': 150,
        'learning_rate': 0.05,
        'max_depth': 6,
        'random_state': 42
    }
    
    models = {}
    quantiles = [0.10, 0.50, 0.90]
    
    for tau in quantiles:
        print(f"Training LightGBM Model for tau={tau}...")
        model = lgb.LGBMRegressor(**params, alpha=tau)
        model.fit(X_train, y_train)
        models[tau] = model
        
        joblib_path = f"artifacts/model_q{int(tau*100)}.joblib"
        joblib.dump(model, joblib_path)
    
    print("Evaluating Groupby-Median Baseline...")
    # Compute baseline
    baseline_group = train_df.groupby(['route_stop_id', 'hour_of_day'])['delay_sec'].median().reset_index()
    baseline_group.rename(columns={'delay_sec': 'baseline_pred'}, inplace=True)
    
    # Merge on holdout
    holdout_baseline = pd.merge(holdout_df, baseline_group, on=['route_stop_id', 'hour_of_day'], how='left')
    overall_median = train_df['delay_sec'].median()
    holdout_baseline['baseline_pred'] = holdout_baseline['baseline_pred'].fillna(overall_median)
    
    y_baseline = holdout_baseline['baseline_pred'].values
    
    losses_lgb = {}
    losses_base = {}
    coverages = {}
    
    for tau in quantiles:
        y_pred = models[tau].predict(X_holdout)
        
        loss_lgb = pinball_loss(y_holdout, y_pred, tau)
        loss_base = pinball_loss(y_holdout, y_baseline, tau)
        
        losses_lgb[f"q{int(tau*100)}"] = float(loss_lgb)
        losses_base[f"q{int(tau*100)}"] = float(loss_base)
        
        coverage = np.mean(y_holdout <= y_pred)
        coverages[f"q{int(tau*100)}"] = float(coverage)
        
        print(f"\nTau={tau}:")
        print(f"  LGBM Pinball Loss:     {loss_lgb:.4f}")
        print(f"  Baseline Pinball Loss: {loss_base:.4f}")
        print(f"  Empirical Coverage:    {coverage:.4f}")
        
    avg_loss_lgb = np.mean(list(losses_lgb.values()))
    avg_loss_base = np.mean(list(losses_base.values()))
    
    print(f"\nAverage Pinball Loss (LGBM):     {avg_loss_lgb:.4f}")
    print(f"Average Pinball Loss (Baseline): {avg_loss_base:.4f}")
    
    improvement = (avg_loss_base - avg_loss_lgb) / avg_loss_base
    print(f"LGBM Improvement over Baseline:  {improvement * 100:.2f}%")
    
    if improvement < 0.10:
        print("Warning: LightGBM did not achieve >= 10% loss reduction over baseline.")
    
    # Extract Feature importances using the median (q50) model
    feature_names = num_features + ['route_stop_id']
    importance_values = models[0.50].feature_importances_
    feature_importances = {name: float(val) for name, val in zip(feature_names, importance_values)}
    feature_importances = dict(sorted(feature_importances.items(), key=lambda item: item[1], reverse=True))
    
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "pinball_loss_lgbm": losses_lgb,
            "pinball_loss_baseline": losses_base,
            "average_pinball_loss_lgbm": float(avg_loss_lgb),
            "average_pinball_loss_baseline": float(avg_loss_base),
            "improvement_pct": float(improvement * 100),
            "coverage": coverages
        },
        "feature_importances_q50": feature_importances,
        "provenance": {
            "train_size": len(train_df),
            "holdout_size": len(holdout_df)
        }
    }
    
    with open("artifacts/metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)
        
    print("\nTraining completed successfully and artifacts saved.")

if __name__ == "__main__":
    main()

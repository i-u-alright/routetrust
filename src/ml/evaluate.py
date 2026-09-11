import os
import json

def main():
    metadata_path = "artifacts/metadata.json"
    
    if not os.path.exists(metadata_path):
        print("Error: Could not find artifacts/metadata.json.")
        print("Please run the training pipeline first using: python -m src.ml.train")
        return
        
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
        
    metrics = metadata.get("metrics", {})
    coverage = metrics.get("coverage", {})
    
    print("=" * 65)
    print(" " * 18 + "ROUTETRUST ML AUDIT REPORT")
    print("=" * 65)
    
    print("\n1. Quantile Calibration (Empirical Coverage)")
    print("-" * 65)
    print(f"{'Quantile (tau)':<16} | {'Target Coverage':<18} | {'Empirical Holdout Coverage':<25}")
    print("-" * 65)
    
    targets = {"q10": "10% (0.10)", "q50": "50% (0.50)", "q90": "90% (0.90)"}
    for q, emp_cov in coverage.items():
        target = targets.get(q, "N/A")
        print(f"{q:<16} | {target:<18} | {emp_cov:.4f} ({(emp_cov*100):.1f}%)")
        
    print("\n2. Pinball Loss Comparison")
    print("-" * 65)
    
    loss_lgb = metrics.get("average_pinball_loss_lgbm", 0)
    loss_base = metrics.get("average_pinball_loss_baseline", 0)
    improvement = metrics.get("improvement_pct", 0)
    
    print(f"{'Groupby-Median Baseline Avg Loss':<35}: {loss_base:.4f}")
    print(f"{'LightGBM Average Loss':<35}: {loss_lgb:.4f}")
    print(f"{'LightGBM Improvement':<35}: {improvement:.2f}%")
    
    print("\n3. Top 5 Most Important Features (by Gain for q50)")
    print("-" * 65)
    features = metadata.get("feature_importances_q50", {})
    
    for i, (feat, importance) in enumerate(list(features.items())[:5], 1):
        print(f"  {i}. {feat:<28} : {importance:.2f}")
        
    print("\n" + "=" * 65)

if __name__ == "__main__":
    main()

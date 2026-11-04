import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from .models import ModelVersion
FEATURES = ["deposits_last_5_minutes", "deposit_amount_ratio_to_baseline", "bets_last_60_seconds", "bonus_claims_last_24_hours", "distinct_accounts_per_device", "failed_actions_last_10_minutes"]
MODEL_DIR = os.getenv("MODEL_DIR", "/tmp/risk-models")
def train_demo_model():
    os.makedirs(MODEL_DIR, exist_ok=True)
    rng = np.random.default_rng(42)
    normal = rng.normal(loc=[1, 1, 2, 0.2, 1, 0.1], scale=[1, .5, 2, .5, .3, .5], size=(1500, 6))
    model = IsolationForest(n_estimators=200, contamination=0.02, random_state=42)
    model.fit(normal)
    version = "iforest-demo-v1"
    path = os.path.join(MODEL_DIR, version + ".joblib")
    joblib.dump({"model": model, "features": FEATURES, "version": version}, path)
    ModelVersion.objects.update(active=False)
    ModelVersion.objects.update_or_create(name="isolation_forest", defaults={"version": version, "artifact_path": path, "active": True, "metrics": {"training_rows": 1500, "data": "synthetic"}})
    return path, version
def score_features(values):
    active = ModelVersion.objects.filter(name="isolation_forest", active=True).first()
    if not active or not active.artifact_path or not os.path.exists(active.artifact_path):
        raise ValueError("No trained model found. Run the demo training endpoint first.")
    bundle = joblib.load(active.artifact_path)
    row = np.array([[float(values.get(k, 0)) for k in bundle["features"]]])
    model = bundle["model"]
    return {"prediction": int(model.predict(row)[0]), "anomaly_score": float(-model.decision_function(row)[0]), "model_version": bundle["version"]}

import sys
import time
import requests
import numpy as np
from pathlib import Path

# Add ai_engine to path
base_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(base_dir / "ai_engine"))

from data_generator import _daily_from_monthly, _mutate  # type: ignore

BACKEND_URL = "http://localhost:8000/api/internal/ingest"

# 5 specific bad actors for the demo
BAD_ACTORS = [
    {"meter_id": "MTR-00142", "zone_id": "z1", "type": "Ghost Load"},
    {"meter_id": "MTR-00387", "zone_id": "z3", "type": "Phase Bypass"},
    {"meter_id": "MTR-00521", "zone_id": "z2", "type": "Billing Freeze"},
    {"meter_id": "MTR-00899", "zone_id": "z4", "type": "Meter Tamper"},
    {"meter_id": "MTR-00999", "zone_id": "z5", "type": "Slow Bleed"},
]

rng = np.random.default_rng()

def generate_curve(anomaly_type="Normal"):
    # Generate base shapes similar to our mocked training data
    monthly = rng.uniform(100, 300, size=12)
    daily_template = np.sin(np.linspace(0, np.pi * 2, 96)) * 50 + 100 + rng.normal(0, 5, size=96)
    
    # Scale daily to match monthly using the exact training logic
    daily = _daily_from_monthly(monthly, daily_template, rng)
    
    # Apply the exact same anomaly mutations used during training
    mutated_monthly, mutated_daily, peer = _mutate(anomaly_type, monthly, daily, rng)
    
    return list(mutated_daily), list(mutated_monthly), list(peer)

def main():
    print("Starting Live Simulator...")
    while True:
        payload = []
        # Add a few normal meters
        for i in range(10):
            d, m, p = generate_curve("Normal")
            payload.append({
                "meter_id": f"MTR-NORM-{i:03d}",
                "zone_id": f"z{(i % 6) + 1}",
                "daily_curve": d,
                "monthly_history": m,
                "peer_average": p
            })
            
        # Add the bad actors
        for actor in BAD_ACTORS:
            d, m, p = generate_curve(actor["type"])
            payload.append({
                "meter_id": actor["meter_id"],
                "zone_id": actor["zone_id"],
                "daily_curve": d,
                "monthly_history": m,
                "peer_average": p
            })
            
        try:
            resp = requests.post(BACKEND_URL, json=payload)
            print(f"Sent {len(payload)} readings to backend. Status: {resp.status_code}")
        except Exception as e:
            print(f"Failed to connect to backend: {e}")
            
        time.sleep(30)

if __name__ == "__main__":
    main()

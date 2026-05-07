import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from pydantic import BaseModel  # type: ignore

# Add ai_engine to path
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(base_dir / "ai_engine"))

from inference import predict_fingerprint  # type: ignore
from api.forecast_engine import generate_zone_forecast_and_risk

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory mock database
zones_config = [
    {"zone_id": "z1", "zone_name": "Indiranagar", "rated_capacity_kw": 10000, "base_load": 5000},
    {"zone_id": "z2", "zone_name": "Whitefield", "rated_capacity_kw": 12000, "base_load": 6000},
    {"zone_id": "z3", "zone_name": "Koramangala", "rated_capacity_kw": 9000, "base_load": 4500},
    {"zone_id": "z4", "zone_name": "HSR Layout", "rated_capacity_kw": 11000, "base_load": 5500},
    {"zone_id": "z5", "zone_name": "Jayanagar", "rated_capacity_kw": 8000, "base_load": 4000},
    {"zone_id": "z6", "zone_name": "Malleswaram", "rated_capacity_kw": 7000, "base_load": 3500},
]

system_state = {
    "last_updated": datetime.now().isoformat(),
    "flagged_meters": {},
    "zones": {},
    "zone_forecasts": {}
}

def initialize_forecasts():
    for z in zones_config:
        forecast, risk_level = generate_zone_forecast_and_risk(z["zone_id"], z["base_load"], z["rated_capacity_kw"])
        
        # Calculate peak
        peak_forecast = max(forecast, key=lambda x: x["predicted_kw"]) if forecast else None
        
        system_state["zones"][z["zone_id"]] = {
            "zone_id": z["zone_id"],
            "zone_name": z["zone_name"],
            "current_load_kw": z["base_load"],
            "rated_capacity_kw": z["rated_capacity_kw"],
            "load_percent": (z["base_load"] / z["rated_capacity_kw"]) * 100,
            "risk_level": risk_level,
            "risk_label": risk_level,
            "peak_forecast_kw": peak_forecast["predicted_kw"] if peak_forecast else 0,
            "peak_forecast_time": peak_forecast["time"] if peak_forecast else datetime.now().isoformat()
        }
        system_state["zone_forecasts"][z["zone_id"]] = forecast

initialize_forecasts()

class MeterReading(BaseModel):
    meter_id: str
    zone_id: str
    daily_curve: List[float]
    monthly_history: Optional[List[float]] = None
    peer_average: Optional[List[float]] = None

@app.post("/api/internal/ingest")
def ingest_data(readings: List[MeterReading]):
    model_path = str(base_dir / "ai_engine" / "artifacts" / "fingerprint_model.joblib")
    
    for reading in readings:
        result = predict_fingerprint(
            timeseries_array=reading.daily_curve,
            monthly_history=reading.monthly_history,
            peer_average=reading.peer_average,
            model_path=model_path
        )
        
        if result["fingerprint"] != "Normal" and result["confidence"] >= 0.70:
            # Add or update flagged meter
            system_state["flagged_meters"][reading.meter_id] = {
                "meter_id": reading.meter_id,
                "zone_id": reading.zone_id,
                "zone_name": system_state["zones"][reading.zone_id]["zone_name"],
                "fingerprint_type": result["fingerprint"],
                "confidence": result["confidence"],
                "flagged_at": datetime.now().isoformat(),
                "status": "unreviewed",
                "features": result["features"],
                "timeseries": [
                    {"time": (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=15*i)).isoformat(), "kwh": val}
                    for i, val in enumerate(reading.daily_curve)
                ],
                "peer_average": [
                    {"time": (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=15*i)).isoformat(), "kwh": val}
                    for i, val in enumerate(reading.peer_average or [0.5]*96)
                ]
            }
        elif reading.meter_id in system_state["flagged_meters"]:
            # If it returned to normal, remove it from the flagged list
            del system_state["flagged_meters"][reading.meter_id]
            
    system_state["last_updated"] = datetime.now().isoformat()
    return {"status": "success", "processed": len(readings)}

@app.post("/api/forecast/refresh")
def refresh_forecasts():
    initialize_forecasts()
    system_state["last_updated"] = datetime.now().isoformat()
    return {"status": "success", "message": "Forecasts regenerated and models reloaded if available"}

@app.get("/api/forecast/summary")
def get_forecast_summary():
    return {
        "last_updated": system_state["last_updated"],
        "zones": list(system_state["zones"].values())
    }

@app.get("/api/forecast/zones/{zone_id}")
def get_zone_forecast(zone_id: str):
    if zone_id not in system_state["zones"]:
        return {"error": "Zone not found"}
    zone_info = system_state["zones"][zone_id]
    return {
        "zone_id": zone_info["zone_id"],
        "zone_name": zone_info["zone_name"],
        "rated_capacity_kw": zone_info["rated_capacity_kw"],
        "risk_level": zone_info["risk_level"],
        "forecast": system_state["zone_forecasts"][zone_id]
    }

@app.get("/api/fingerprints/meters")
def get_flagged_meters():
    meters = list(system_state["flagged_meters"].values())
    # Return brief info
    brief_meters = []
    for m in meters:
        brief_meters.append({
            "meter_id": m["meter_id"],
            "zone_id": m["zone_id"],
            "zone_name": m["zone_name"],
            "fingerprint_type": m["fingerprint_type"],
            "confidence": m["confidence"],
            "flagged_at": m["flagged_at"],
            "status": m["status"]
        })
    return {
        "last_updated": system_state["last_updated"],
        "total_flagged": len(brief_meters),
        "meters": brief_meters
    }

@app.get("/api/fingerprints/meters/{meter_id}")
def get_meter_detail(meter_id: str):
    if meter_id not in system_state["flagged_meters"]:
        return {"error": "Meter not found"}
    return system_state["flagged_meters"][meter_id]

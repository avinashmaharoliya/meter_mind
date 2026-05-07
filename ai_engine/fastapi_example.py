from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from inference import predict_fingerprint


app = FastAPI(title="BESCOM Loss Fingerprinting MVP")


class FingerprintRequest(BaseModel):
    daily_curve: list[float] = Field(..., min_length=48, description="48 half-hourly or 96 fifteen-minute readings")
    monthly_history: Optional[list[float]] = Field(None, description="Optional 12 monthly consumption values")
    peer_average: Optional[list[float]] = Field(None, description="Optional 12 peer-group average values")


@app.post("/predict-fingerprint")
def predict(request: FingerprintRequest):
    return predict_fingerprint(
        timeseries_array=request.daily_curve,
        monthly_history=request.monthly_history,
        peer_average=request.peer_average,
        model_path="artifacts/fingerprint_model.joblib",
    )

import math
from datetime import datetime, timedelta
from pathlib import Path
import os
import joblib  # type: ignore

# The folder where the Prophet models will be dropped later
MODELS_DIR = Path(__file__).resolve().parent.parent / "artifacts"
MODELS_DIR.mkdir(exist_ok=True)

def generate_mock_forecast(base_load: float) -> list:
    """Fallback mock generator if Prophet models are not yet available."""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    forecast = []
    for i in range(24):
        time_point = now + timedelta(hours=i)
        # Simple diurnal curve simulation
        hour_factor = math.sin(math.pi * (time_point.hour - 6) / 12) * 0.3 + 1.0
        val = base_load * hour_factor
        forecast.append({
            "time": time_point.isoformat(),
            "predicted_kw": val,
            "upper_bound_kw": val * 1.1,
            "lower_bound_kw": val * 0.9
        })
    return forecast

def get_prophet_forecast(zone_id: str, periods: int = 24) -> list:
    """Attempt to load and use the real Prophet model."""
    model_path = MODELS_DIR / f"prophet_{zone_id}.joblib"
    if not model_path.exists():
        return None
        
    try:
        import pandas as pd
        # The forecasting person might use prophet or fbprophet depending on version
        try:
            # pyrefly: ignore [missing-import]
            from prophet import Prophet
        except ImportError:
            # pyrefly: ignore [missing-import]
            from fbprophet import Prophet
            
        model = joblib.load(model_path)
        
        # Create future dataframe starting from current hour
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        future_dates = [now + timedelta(hours=i) for i in range(periods)]
        future_df = pd.DataFrame({'ds': future_dates})
        
        # Inject the custom regressors that the backend team added to the Prophet model
        future_df['temperature'] = 33.0
        future_df['summer_flag'] = 1
        
        forecast_df = model.predict(future_df)
        
        forecast = []
        for _, row in forecast_df.iterrows():
            forecast.append({
                "time": row['ds'].isoformat(),
                "predicted_kw": float(row['yhat']),
                "upper_bound_kw": float(row['yhat_upper']),
                "lower_bound_kw": float(row['yhat_lower'])
            })
        return forecast
    except Exception as e:
        print(f"Failed to run Prophet model for {zone_id}: {e}")
        return None

def calculate_risk_level(forecast: list, rated_capacity_kw: float) -> str:
    """Calculate the risk level based on the max upper bound over the next 24 hours."""
    if not forecast:
        return "Normal"
        
    max_upper_bound = max(f["upper_bound_kw"] for f in forecast)
    
    if max_upper_bound > 0.90 * rated_capacity_kw:
        return "High Risk"
    elif max_upper_bound > 0.75 * rated_capacity_kw:
        return "Medium Risk"
    else:
        return "Normal"

def generate_zone_forecast_and_risk(zone_id: str, base_load: float, rated_capacity_kw: float):
    """
    Main entrypoint for the API. It tries to use the Prophet model if the file 
    exists, otherwise falls back to the mock data. It then calculates the risk level.
    """
    forecast = get_prophet_forecast(zone_id)
    
    # Fallback if model missing or failed to run
    if not forecast:
        forecast = generate_mock_forecast(base_load)
        
    risk_level = calculate_risk_level(forecast, rated_capacity_kw)
    
    return forecast, risk_level

# BESCOM Loss Fingerprinting MVP Training

This folder trains the MVP model requested in the Siya report.

## Files

- `features.py` - backend handoff file with `extract_features(timeseries_array, monthly_history=None, peer_average=None)`.
- `data_generator.py` - reads SGCC and London ZIPs, synthesizes the five theft fingerprints plus Normal, and writes `artifacts/training_data.csv`.
- `train_rf.py` - trains the Random Forest and writes `artifacts/fingerprint_model.joblib`.
- `inference.py` - backend-friendly prediction wrapper.

## Local Run

```bash
python data_generator.py --samples-per-class 1500
python train_rf.py
```

## Kaggle Run

Attach the SGCC and London Smart Meter datasets, upload these scripts, then run:

```python
!python data_generator.py \
  --sgcc-zip "/kaggle/input/<sgcc-folder>/archive (2).zip" \
  --london-zip "/kaggle/input/<london-folder>/archive (3).zip" \
  --output-dir "/kaggle/working/artifacts" \
  --samples-per-class 3000

!python train_rf.py \
  --training-csv "/kaggle/working/artifacts/training_data.csv" \
  --output-dir "/kaggle/working/artifacts"
```

Download these for backend integration:

- `/kaggle/working/artifacts/fingerprint_model.joblib`
- `features.py`
- `inference.py`

## Backend Input Options

Report-compatible input:

```json
{
  "daily_curve": [96 numbers]
}
```

Stronger input:

```json
{
  "daily_curve": [96 numbers],
  "monthly_history": [12 numbers],
  "peer_average": [12 numbers]
}
```

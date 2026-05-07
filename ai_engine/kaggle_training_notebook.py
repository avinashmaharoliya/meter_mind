# %% [markdown]
# # BESCOM Loss Fingerprinting MVP
#
# Upload these project files to Kaggle:
#
# - `features.py`
# - `data_generator.py`
# - `train_rf.py`
# - `inference.py`
#
# Attach the SGCC and London Smart Meter datasets in the Kaggle notebook sidebar.

# %%
from pathlib import Path
import subprocess

INPUT = Path("/kaggle/input")
WORKING = Path("/kaggle/working")

for path in INPUT.iterdir():
    print(path)

# %% [markdown]
# Find the ZIP files. If Kaggle has already extracted your datasets, update these paths manually.

# %%
zip_files = list(INPUT.glob("**/*.zip"))
for z in zip_files:
    print(z)

sgcc_zip = next(z for z in zip_files if "archive (2)" in z.name.lower() or "sgcc" in str(z).lower())
london_zip = next(z for z in zip_files if "archive (3)" in z.name.lower() or "london" in str(z).lower() or "smart" in str(z).lower())

print("SGCC:", sgcc_zip)
print("London:", london_zip)
sgcc_zip_str = str(sgcc_zip)
london_zip_str = str(london_zip)

# %% [markdown]
# Generate the synthetic fingerprint training data. Use `3000` per class on Kaggle for a stronger run.

# %%
subprocess.run(
    [
        "python",
        "data_generator.py",
        "--sgcc-zip",
        sgcc_zip_str,
        "--london-zip",
        london_zip_str,
        "--output-dir",
        "/kaggle/working/artifacts",
        "--samples-per-class",
        "3000",
    ],
    check=True,
)

# %% [markdown]
# Train the Random Forest model.

# %%
subprocess.run(
    [
        "python",
        "train_rf.py",
        "--training-csv",
        "/kaggle/working/artifacts/training_data.csv",
        "--output-dir",
        "/kaggle/working/artifacts",
    ],
    check=True,
)

# %% [markdown]
# Check the metrics.

# %%
print(Path("/kaggle/working/artifacts/classification_report.txt").read_text())

# %% [markdown]
# Test backend-style inference with only 96 numbers.

# %%
from inference import predict_fingerprint

sample_ghost_load = [0.05] * 24 + [0.001] * 64 + [0.7] * 8
predict_fingerprint(sample_ghost_load, model_path="/kaggle/working/artifacts/fingerprint_model.joblib")

# %% [markdown]
# Download these files from Kaggle output:
#
# - `/kaggle/working/artifacts/fingerprint_model.joblib`
# - `/kaggle/working/artifacts/training_data.csv`
# - `/kaggle/working/artifacts/classification_report.txt`
# - `features.py`
# - `inference.py`

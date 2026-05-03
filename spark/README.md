# Spark — Data Preprocessing Pipeline

PySpark preprocessing pipeline that runs on AWS EMR to transform raw instruction-tuning datasets into clean, deduplicated Parquet splits ready for fine-tuning.

## Scripts

| Script | Purpose |
|--------|---------|
| `download_datasets.py` | Downloads 3 datasets from HuggingFace Hub to local `raw_data/` |
| `preprocess.py` | **Main PySpark pipeline** — runs on EMR as a Spark step |
| `scripts/fix_data.py` | Post-Spark deduplication and train↔val leakage removal |
| `scripts/verify_data.py` | Data quality verification (row counts, nulls, duplicates, leakage) |
| `scripts/generate_plots.py` | EDA visualisation generator for split distributions |

## Pipeline Steps (preprocess.py)

1. **Load** — Read 3 JSONL files from `s3://25nsfb-cisc886-project-v4/raw-data/`
2. **Auto-detect schema** — Handles both `conversations` array (OpenHermes) and flat format (Airoboros)
3. **Normalise** — Unify all sources to `{instruction, output, source}` columns
4. **Hold out test set** — 5% from OpenHermes-2.5 (pre-merge, no leakage)
5. **Union** — Combine all training sources
6. **Deduplicate** — `dropDuplicates(["instruction"])`
7. **Filter** — Output word count ∈ [10, ~2048 tokens], instruction ≥ 3 words
8. **Split** — 90/10 train/val via `randomSplit(seed=42)`
9. **Write** — Parquet to `s3://25nsfb-cisc886-project-v4/processed/`

## Post-Processing (fix_data.py)

After the EMR step completed, verification revealed:
- **523 duplicate rows** (near-duplicates differing in whitespace)
- **91 instruction strings** leaked between train ↔ val splits

The `scripts/fix_data.py` script resolved both issues. Clean splits were re-uploaded as `processed_clean/`.

## Usage

```bash
# All commands should be run from the repository root

# Step 1: Download datasets locally
pip install datasets huggingface_hub pandas
python spark/download_datasets.py

# Step 2: Upload to S3
aws s3 cp raw_data/ s3://25nsfb-cisc886-project-v4/raw-data/ --recursive

# Step 3: Upload PySpark script and submit EMR step
aws s3 cp spark/preprocess.py s3://25nsfb-cisc886-project-v4/scripts/preprocess.py
aws emr add-steps --cluster-id <EMR_ID> \
  --steps '[{
    "Type": "Spark",
    "Name": "CISC886-Preprocess",
    "ActionOnFailure": "CONTINUE",
    "Args": ["s3://25nsfb-cisc886-project-v4/scripts/preprocess.py"]
  }]'

# Step 4: Download processed data and run quality fix
aws s3 sync s3://25nsfb-cisc886-project-v4/processed/ processed_data/
pip install pyarrow
python scripts/verify_data.py
python scripts/fix_data.py

# Step 5: Upload clean data back to S3
aws s3 sync processed_data_clean/ s3://25nsfb-cisc886-project-v4/processed_clean/
```

## Datasets

| Dataset | Rows | Format | License |
|---------|------|--------|---------|
| OpenHermes-2.5 | ~1.0M | conversations array | MIT |
| OpenHermes-2.0 | ~240K | conversations array | MIT |
| Airoboros-3.2 | ~70K | flat instruction/output | CC-BY-4.0 |

**Final output:** 100,000 samples total (Train: 70K · Val: 15K · Test: 15K)

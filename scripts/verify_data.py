"""
CISC 886 — Data Verification Script
Run this LOCALLY before terminating the EMR cluster.
Checks row counts, schema, nulls, duplicates, and sample rows.

Usage:
    pip install pandas pyarrow
    python verify_data.py
"""

import os
import pandas as pd
import pyarrow.parquet as pq

SPLITS = {
    "train": "processed_data/train",
    "val":   "processed_data/val",
    "test":  "processed_data/test",
}

EXPECTED_COLUMNS = {"instruction", "output", "source"}

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def load_split(folder):
    """Load all parquet part-files in a folder into one DataFrame."""
    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.endswith(".parquet")
    ]
    if not files:
        raise FileNotFoundError(f"No parquet files found in: {folder}")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

def separator(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)

# ─── MAIN ────────────────────────────────────────────────────────────────────

dfs = {}
for split, folder in SPLITS.items():
    separator(f"[{split.upper()}] Loading from {folder}")
    df = load_split(folder)
    dfs[split] = df

    # 1. Row count
    print(f"  Rows         : {len(df):,}")

    # 2. Columns
    print(f"  Columns      : {list(df.columns)}")
    missing_cols = EXPECTED_COLUMNS - set(df.columns)
    if missing_cols:
        print(f"  *** MISSING COLUMNS: {missing_cols} ***")
    else:
        print(f"  Columns OK   : all expected columns present")

    # 3. Null check
    null_counts = df[list(EXPECTED_COLUMNS & set(df.columns))].isnull().sum()
    print(f"  Null counts  :\n{null_counts.to_string()}")
    if null_counts.any():
        print("  *** WARNING: nulls found ***")

    # 4. Duplicate instructions
    dup_count = df["instruction"].duplicated().sum()
    print(f"  Dup instruct : {dup_count:,}")
    if dup_count > 0:
        print("  *** WARNING: duplicate instructions found ***")

    # 5. Source distribution
    if "source" in df.columns:
        print(f"  Source dist  :\n{df['source'].value_counts().to_string()}")

    # 6. Output word count stats
    df["_wc"] = df["output"].str.split().str.len()
    print(f"  Output words : min={df['_wc'].min()}  "
          f"median={df['_wc'].median():.0f}  "
          f"max={df['_wc'].max()}  "
          f"mean={df['_wc'].mean():.0f}")
    df.drop(columns=["_wc"], inplace=True)

    # 7. Sample rows
    print(f"\n  --- Sample row ---")
    sample = df.sample(1).iloc[0]
    print(f"  [source]      {sample['source']}")
    print(f"  [instruction] {str(sample['instruction'])[:120]}...")
    print(f"  [output]      {str(sample['output'])[:120]}...")

# ─── CROSS-SPLIT SUMMARY ─────────────────────────────────────────────────────
separator("CROSS-SPLIT SUMMARY")

total = sum(len(d) for d in dfs.values())
for split, df in dfs.items():
    pct = len(df) / total * 100
    print(f"  {split:<6}: {len(df):>8,} rows  ({pct:.1f}%)")
print(f"  {'TOTAL':<6}: {total:>8,} rows")

# Check for leakage between train and test
separator("LEAKAGE CHECK (train instruction vs test instruction)")
train_instrs = set(dfs["train"]["instruction"].dropna())
test_instrs  = set(dfs["test"]["instruction"].dropna())
overlap = train_instrs & test_instrs
if overlap:
    print(f"  *** WARNING: {len(overlap):,} instructions appear in BOTH train and test! ***")
else:
    print(f"  No leakage detected between train and test.")

separator("VERIFICATION COMPLETE")
print("  If no warnings above — data looks good. Safe to terminate cluster.")

"""
CISC 886 — Data Fix Script
Fixes two issues found during verification:
  1. 222 duplicate instructions in the test set
  2. 4,686 instructions that appear in both train and test (leakage)

Saves clean splits to: processed_data_clean/train | val | test

Usage:
    python fix_data.py
"""

import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

RAW_DIR   = "processed_data"
CLEAN_DIR = "processed_data_clean"
SPLITS    = ["train", "val", "test"]

# ─── LOAD ────────────────────────────────────────────────────────────────────

def load_split(split):
    folder = os.path.join(RAW_DIR, split)
    files  = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".parquet")]
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)

def save_split(df, split):
    folder = os.path.join(CLEAN_DIR, split)
    os.makedirs(folder, exist_ok=True)
    out_path = os.path.join(folder, "part-00000.parquet")
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out_path)
    print(f"  Saved {len(df):,} rows → {out_path}")

print("=" * 60)
print("  Loading splits...")
print("=" * 60)

train = load_split("train")
val   = load_split("val")
test  = load_split("test")

print(f"  Before fix — train: {len(train):,}  val: {len(val):,}  test: {len(test):,}")

# ─── FIX 1: Deduplicate test set ─────────────────────────────────────────────
print("\n[Fix 1] Deduplicating test set on instruction...")
before = len(test)
test = test.drop_duplicates(subset=["instruction"])
print(f"  Removed {before - len(test):,} duplicate rows from test. Now: {len(test):,}")

# ─── FIX 2: Remove test instructions from train and val ──────────────────────
print("\n[Fix 2] Removing test instructions from train and val (leakage fix)...")
test_instrs = set(test["instruction"].dropna())

before_train = len(train)
train = train[~train["instruction"].isin(test_instrs)]
print(f"  Removed {before_train - len(train):,} leaking rows from train. Now: {len(train):,}")

before_val = len(val)
val = val[~val["instruction"].isin(test_instrs)]
print(f"  Removed {before_val - len(val):,} leaking rows from val.   Now: {len(val):,}")

# ─── FINAL SANITY CHECK ──────────────────────────────────────────────────────
print("\n[Sanity check] Verifying no remaining leakage...")
overlap_train = set(train["instruction"]) & test_instrs
overlap_val   = set(val["instruction"])   & test_instrs
dup_test      = test["instruction"].duplicated().sum()

assert len(overlap_train) == 0, f"Still {len(overlap_train)} train/test overlaps!"
assert len(overlap_val)   == 0, f"Still {len(overlap_val)} val/test overlaps!"
assert dup_test == 0,           f"Still {dup_test} duplicate instructions in test!"
print("  All checks passed.")

# ─── SAVE ────────────────────────────────────────────────────────────────────
print(f"\n[Saving] Writing clean splits to ./{CLEAN_DIR}/...")
save_split(train, "train")
save_split(val,   "val")
save_split(test,  "test")

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
total = len(train) + len(val) + len(test)
print("\n" + "=" * 60)
print("  CLEAN SPLIT SUMMARY")
print("=" * 60)
for name, df in [("train", train), ("val", val), ("test", test)]:
    print(f"  {name:<6}: {len(df):>8,} rows  ({len(df)/total*100:.1f}%)")
print(f"  {'TOTAL':<6}: {total:>8,} rows")

print("\n  Source distribution (train):")
print(train["source"].value_counts().to_string())

print("\n" + "=" * 60)
print("  DONE — safe to upload clean splits to S3, then terminate cluster.")
print("=" * 60)
print(f"""
Next steps:
  aws s3 sync processed_data_clean/ s3://25nsfb-cisc886-project-v4/processed_clean/
  aws emr terminate-clusters --cluster-ids j-3PODFNQEY7USO --region ca-central-1
""")
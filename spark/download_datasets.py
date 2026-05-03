"""
CISC 886 — Cloud Computing Project
Dataset Download Script

Downloads three instruction-tuning datasets from HuggingFace Hub to local disk
before uploading to S3 for PySpark preprocessing.

Datasets:
  1. teknium/OpenHermes-2.5  (~1.0M rows)
  2. teknium/openhermes       (~240K rows, OpenHermes-2.0)
  3. jondurbin/airoboros-3.2  (~70K rows)

Output: raw_data/ directory containing three .jsonl files.

Usage:
  pip install datasets huggingface_hub pandas
  python spark/download_datasets.py

Author: Ahmed Hussain | NetID: 25nsfb | Queen's University
Course: CISC 886 Cloud Computing
"""

from datasets import load_dataset
import pandas as pd
import json
import os

os.makedirs("raw_data", exist_ok=True)

# ── 1. OpenHermes-2.5 ─────────────────────────────────────────────────────────
if not os.path.exists("raw_data/openhermes25.jsonl"):
    print("Downloading OpenHermes-2.5 (~1M rows)...")
    ds1 = load_dataset("teknium/OpenHermes-2.5", split="train")
    ds1.to_json("raw_data/openhermes25.jsonl", lines=True)
    print(f"  Saved {len(ds1):,} rows → raw_data/openhermes25.jsonl")
else:
    print("OpenHermes-2.5 already exists locally — skipping download.")

# ── 2. OpenHermes-2.0 ─────────────────────────────────────────────────────────
print("Downloading OpenHermes-2.0...")
try:
    ds2 = load_dataset("teknium/openhermes", split="train")
    ds2.to_json("raw_data/openhermes20.jsonl", lines=True)
    print(f"  Saved {len(ds2):,} rows → raw_data/openhermes20.jsonl")
except Exception as e:
    print(f"  Error downloading OpenHermes-2.0: {e}")

# ── 3. Airoboros-3.2 ──────────────────────────────────────────────────────────
# Airoboros stores conversations as a list of {from, value} dicts.
# We extract the first human turn (instruction) and first gpt turn (output).
print("Downloading Airoboros-3.2...")
try:
    ds3 = load_dataset("jondurbin/airoboros-3.2", split="train")

    def extract_chat(example):
        """Extract first human/gpt turn pair from conversations list."""
        convs = example.get("conversations", [])
        instruction, output = "", ""
        for msg in convs:
            role = msg.get("from", "")
            if role == "human" and not instruction:
                instruction = msg.get("value", "")
            if role == "gpt" and not output:
                output = msg.get("value", "")
            if instruction and output:
                break
        return {"instruction": instruction, "output": output}

    ds3_processed = ds3.map(extract_chat)
    ds3_processed = ds3_processed.filter(
        lambda x: len(x["instruction"]) > 0 and len(x["output"]) > 0
    )
    ds3_processed.to_json("raw_data/airoboros32.jsonl", lines=True)
    print(f"  Saved {len(ds3_processed):,} rows → raw_data/airoboros32.jsonl")

except Exception as e:
    print(f"  Error downloading Airoboros-3.2: {e}")

print("\nAll downloads complete. Upload to S3 with:")
print("  aws s3 cp raw_data/ s3://25nsfb-cisc886-project-v4/raw-data/ --recursive")
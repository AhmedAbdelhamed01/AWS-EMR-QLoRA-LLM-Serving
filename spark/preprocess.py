"""
CISC 886 — Cloud Computing Project
PySpark Preprocessing Pipeline
Model: Gemma-2 2B | Datasets: OpenHermes-2.5 + OpenHermes-2.0 + Airoboros-3.2
Author: Ahmed | Queen's University
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType

# ─── CONFIG ──────────────────────────────────────────────────────────────────
BUCKET = "25nsfb-cisc886-project-v4"
INPUT  = f"s3://{BUCKET}/raw-data/"
OUTPUT = f"s3://{BUCKET}/processed/"
SEED   = 42

# ─── 1. SPARK SESSION ────────────────────────────────────────────────────────
spark = SparkSession.builder \
    .appName(f"CISC886-Preprocessing-{BUCKET}") \
    .config("spark.sql.shuffle.partitions", "100") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("=" * 60)
print("CISC 886 Preprocessing Pipeline Starting")
print(f"Spark version: {spark.version}")
print("=" * 60)

# ─── 2. LOAD ALL THREE DATASETS ──────────────────────────────────────────────
print("\n[Step 2] Loading datasets from S3...")

df1 = spark.read.json(f"{INPUT}openhermes25.jsonl")
df2 = spark.read.json(f"{INPUT}openhermes20.jsonl")
df3 = spark.read.json(f"{INPUT}airoboros32.jsonl")

# Print schemas so stderr/stdout logs always reveal the actual structure
print("\n[DEBUG] df1 (OpenHermes-2.5) columns:", df1.columns)
df1.printSchema()
print("\n[DEBUG] df2 (OpenHermes-2.0) columns:", df2.columns)
df2.printSchema()
print("\n[DEBUG] df3 (Airoboros-3.2) columns:", df3.columns)
df3.printSchema()

# ─── 3. NORMALIZE COLUMNS ────────────────────────────────────────────────────
# OpenHermes 2.5 and 2.0: conversations array of {from, value} structs.
#   → Use SQL filter expression (works on ALL Spark versions, no lambda needed)
# Airoboros 3.2: already flat instruction + output from download_datasets.py.
print("\n[Step 3] Normalizing column names...")


def normalize_conversations(df, source_name):
    """
    Parses OpenHermes-style conversations array:
      [ {from: "human", value: "..."}, {from: "gpt", value: "..."} ]
    Uses F.expr SQL syntax so it works on Spark 2.4+ (no Python lambda required).
    """
    print(f"  [{source_name}] Parsing conversations array...")

    # SQL filter expression: grab first human turn and first gpt turn
    df = df.withColumn(
        "instruction",
        F.expr("filter(conversations, x -> x.from = 'human')[0].value")
    ).withColumn(
        "output",
        F.expr("filter(conversations, x -> x.from = 'gpt')[0].value")
    )

    # Drop rows where extraction produced nulls (malformed records)
    df = df.filter(
        F.col("instruction").isNotNull() & F.col("output").isNotNull()
    )

    return df.select(
        F.col("instruction").cast("string"),
        F.col("output").cast("string"),
        F.lit(source_name).alias("source")
    )


def normalize_flat(df, source_name):
    """
    Handles flat format with direct instruction + output columns.
    Falls back through common alternative column names.
    """
    print(f"  [{source_name}] Detected flat format, scanning columns: {df.columns}")

    cols = df.columns
    instr_col  = next((c for c in cols if c in ["instruction", "prompt", "input"]),  None)
    output_col = next((c for c in cols if c in ["output", "response", "completion"]), None)

    if not instr_col or not output_col:
        raise ValueError(
            f"[{source_name}] Could not find instruction/output columns.\n"
            f"Available columns: {cols}\n"
            f"Expected one of: instruction/prompt/input  AND  output/response/completion"
        )

    print(f"  [{source_name}] Using '{instr_col}' as instruction, '{output_col}' as output")

    return df.select(
        F.col(instr_col).cast("string").alias("instruction"),
        F.col(output_col).cast("string").alias("output"),
        F.lit(source_name).alias("source")
    )


def normalize_auto(df, source_name):
    """
    Auto-detects whether the dataframe uses conversations or flat format
    and routes to the correct normalizer. Handles both schemas safely.
    """
    if "conversations" in df.columns:
        print(f"  [{source_name}] Detected conversations format.")
        return normalize_conversations(df, source_name)
    else:
        print(f"  [{source_name}] Detected flat format.")
        return normalize_flat(df, source_name)


df1 = normalize_auto(df1, "openhermes25")
df2 = normalize_auto(df2, "openhermes20")
df3 = normalize_auto(df3, "airoboros32")

print(f"\n  [INFO] df1 row count after normalize: {df1.count()}")
print(f"  [INFO] df2 row count after normalize: {df2.count()}")
print(f"  [INFO] df3 row count after normalize: {df3.count()}")

# ─── 4. HOLD OUT TEST SET BEFORE MERGING ─────────────────────────────────────
print("\n[Step 4] Extracting test set from OpenHermes-2.5...")
df1_main, df1_test = df1.randomSplit([0.95, 0.05], seed=SEED)

# ─── 5. UNION ALL TRAINING SOURCES ───────────────────────────────────────────
# All three DataFrames now have identical columns: instruction, output, source
# so union is safe.
print("\n[Step 5] Unioning all training sources...")
combined = df1_main.union(df2).union(df3)

# ─── 6. REMOVE DUPLICATES ────────────────────────────────────────────────────
print("\n[Step 6] Removing duplicates on instruction text...")
before_dedup = combined.count()
combined = combined.dropDuplicates(["instruction"])
after_dedup = combined.count()
print(f"  Removed {before_dedup - after_dedup} duplicate rows.")

# ─── 7. FILTER BY OUTPUT LENGTH ──────────────────────────────────────────────
print("\n[Step 7] Filtering by output length (10-2048 approx tokens)...")
combined = combined.withColumn(
    "output_word_count",
    F.size(F.split(F.col("output"), " ")).cast(IntegerType())
).withColumn(
    "approx_tokens",
    (F.col("output_word_count") / 0.75).cast(IntegerType())
)

combined = combined.filter(
    (F.col("output_word_count") >= 10) &
    (F.col("approx_tokens")     <= 2048)
)

# ─── 8. FILTER INSTRUCTIONS ──────────────────────────────────────────────────
print("\n[Step 8] Filtering instructions (non-null, >= 3 words)...")
combined = combined.filter(
    F.col("instruction").isNotNull() &
    F.col("output").isNotNull() &
    (F.length(F.col("instruction")) > 0) &
    (F.length(F.col("output")) > 0) &
    (F.size(F.split(F.col("instruction"), " ")) >= 3)
)

# Drop helper columns before saving
combined = combined.drop("output_word_count", "approx_tokens")

# ─── 9. TRAIN / VALIDATION SPLIT ─────────────────────────────────────────────
print("\n[Step 9] Splitting into train / val / test...")
train_df, val_df = combined.randomSplit([0.9, 0.1], seed=SEED)
test_df = df1_test

train_count = train_df.count()
val_count   = val_df.count()
test_count  = test_df.count()

print(f"\n  [INFO] train : {train_count:,} rows")
print(f"  [INFO] val   : {val_count:,} rows")
print(f"  [INFO] test  : {test_count:,} rows")
print(f"  [INFO] total : {train_count + val_count + test_count:,} rows")

# ─── 10. SAVE TO S3 AS PARQUET ───────────────────────────────────────────────
print("\n[Step 10] Writing Parquet files to S3...")

train_df.write.mode("overwrite").parquet(f"{OUTPUT}train/")
print(f"  Saved train to {OUTPUT}train/")

val_df.write.mode("overwrite").parquet(f"{OUTPUT}val/")
print(f"  Saved val   to {OUTPUT}val/")

test_df.write.mode("overwrite").parquet(f"{OUTPUT}test/")
print(f"  Saved test  to {OUTPUT}test/")

spark.stop()
print("\n" + "=" * 60)
print("PREPROCESSING COMPLETE")
print("=" * 60)
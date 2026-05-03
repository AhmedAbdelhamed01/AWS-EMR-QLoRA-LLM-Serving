import pandas as pd
import matplotlib.pyplot as plt
import os

# Create folder for images
os.makedirs("eda_plots", exist_ok=True)

# Load the local data you just downloaded
train_df = pd.read_parquet("processed_data/train")
val_df   = pd.read_parquet("processed_data/val")
test_df  = pd.read_parquet("processed_data/test")

# Sample for plotting
sample_pd = train_df.sample(frac=0.05, random_state=42)

# Figure 1: Split Counts
fig, ax = plt.subplots(figsize=(8, 5))
splits = ["Train", "Validation", "Test"]
counts = [len(train_df), len(val_df), len(test_df)]
ax.bar(splits, counts, color=['#4285F4', '#FBBC04', '#34A853'])
ax.set_title("Final Dataset Splits")
for i, v in enumerate(counts):
    ax.text(i, v + 500, f"{v:,}", ha='center')
plt.savefig("eda_plots/dataset_splits.png")

print("Plots generated in the 'eda_plots' folder!")
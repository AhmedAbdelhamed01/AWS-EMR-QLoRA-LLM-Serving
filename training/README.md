# Training — QLoRA Fine-Tuning

Fine-tuning of **Qwen-2.5-3B-Instruct** using QLoRA (4-bit NF4) on a local workstation with an NVIDIA RTX 5000 Ada GPU (32 GB VRAM).

## Notebook

| Notebook | Description |
|----------|-------------|
| `qwen25_qlora_finetuning.ipynb` | **Primary notebook** — QLoRA fine-tuning with Unsloth, full training pipeline |

## Hyperparameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Base model | `unsloth/Qwen2.5-3B-Instruct-bnb-4bit` | 4-bit quantised, ~2.2 GB VRAM base |
| LoRA rank (r) | 32 | Strong learning signal for short training |
| LoRA alpha | 64 | Scaling factor: α/r = 2 |
| Learning rate | 2e-4 | Standard for LoRA (Unsloth recommended) |
| Batch size | 2 | Safe for 3B model @ seq=1024 on 32 GB VRAM |
| Gradient accumulation | 8 | Effective batch size = 16 |
| Epochs | 2 | 2 full passes over 20,000 training samples |
| Max sequence length | 1024 | Covers > 95% of all examples |
| Quantisation | 4-bit NF4 (QLoRA) | Memory-efficient fine-tuning |
| Optimizer | AdamW 8-bit | Reduced memory vs. standard AdamW |
| Chat template | ChatML | `<\|im_start\|>user` / `<\|im_start\|>assistant` |

## Training Results

- **Training samples used:** 20,000 (random sub-sample from 70K train split)
- **Validation samples:** 1,000 (trimmed for VRAM efficiency)
- **Total steps:** 2,478
- **Duration:** ~6 hours
- **Final training loss:** < 0.7
- **GGUF export:** Q4_K_M quantisation → **1.8 GB** file

## Hardware

| Component | Specification |
|-----------|--------------|
| GPU | NVIDIA RTX 5000 Ada (32 GB VRAM) |
| OS | Windows 11 |
| CUDA | 12.1 |
| Framework | Unsloth + Hugging Face Transformers |
| Peak VRAM | < 12 GB |

## Why Not Gemma-2 2B?

The original plan used Gemma-2 2B Instruct. Training was abandoned after:
1. Cross-entropy loss failed to descend below 4.98 (vs. < 0.7 for Qwen)
2. Gemma-specific chat template incompatible with Unsloth on Windows
3. LoRA → GGUF merge export failed reproducibly

Switching to Qwen-2.5-3B-Instruct resolved all three issues immediately.

## Usage

1. Install dependencies: `pip install unsloth transformers datasets trl`
2. Open `qwen25_qlora_finetuning.ipynb` in Jupyter
3. Configure AWS credentials for S3 data access
4. Run all cells (~6 hours on RTX 5000 Ada)
5. GGUF model will be exported to `models/` directory

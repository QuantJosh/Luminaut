# Phase 2: Embedding Research & Development

**Timeline:** Week 3-5  
**Status:** In Progress  
**Last Updated:** 2026-03-13

---

## Overview

Phase 2 focuses on developing deep learning models to learn low-dimensional embeddings of market states. These embeddings capture essential information from high-dimensional order book and trade data, enabling prediction of short-term price movements.

### Goals

1. **Baseline Model**: Implement and train a simple autoencoder
2. **Advanced Architecture**: Develop multi-branch encoder with cross-attention
3. **Multi-task Learning**: Combine reconstruction, contrastive, and prediction losses
4. **Model Export**: Export trained models to ONNX format for production deployment

---

## Implementation Status

### ✅ Completed Components

#### 1. Baseline Autoencoder (`luminaut/phase2_embedding_research/models/autoencoder.py`)

```python
Autoencoder(
    input_dim=50,      # Feature dimension from Phase 1
    latent_dim=16,     # Embedding dimension
    hidden_dims=(64, 32),
    dropout=0.1,
    use_batch_norm=True
)
```

**Features:**
- Configurable architecture via dataclass
- Batch normalization and dropout for regularization
- ReLU activation functions
- MSE reconstruction loss

#### 2. Data Loading Pipeline (`luminaut/phase2_embedding_research/data/dataset.py`)

**MarketDataset:**
- Loads data from Parquet/CSV files
- Automatic feature detection
- Z-score normalization
- Sequence support for temporal models

**MarketDataModule:**
- Train/val/test splits (80/10/10)
- PyTorch DataLoader integration
- GPU-optimized data loading

#### 3. Training Pipeline (`luminaut/phase2_embedding_research/trainers/trainer.py`)

**TrainingPipeline:**
- Full training loop with early stopping
- Learning rate scheduling (ReduceLROnPlateau)
- Gradient clipping
- Model checkpointing
- Optional W&B experiment tracking

**Features:**
```python
pipeline = TrainingPipeline(
    model=model,
    train_loader=train_loader,
    val_loader=val_loader,
    learning_rate=1e-3,
    weight_decay=1e-5,
    use_wandb=True,
)

history = pipeline.train(
    num_epochs=100,
    patience=15,
    checkpoint_dir="checkpoints/autoencoder",
)
```

#### 4. Training Script (`scripts/train_autoencoder.py`)

**Usage:**
```bash
python scripts/train_autoencoder.py \
    --data-dir data/catalog \
    --latent-dim 16 \
    --epochs 100 \
    --batch-size 256 \
    --lr 1e-3 \
    --use-wandb
```

#### 5. Evaluation Script (`scripts/evaluate_embeddings.py`)

**Metrics:**
- Reconstruction MSE/MAE
- Clustering quality (Silhouette score)
- Visualization (PCA, t-SNE)

**Usage:**
```bash
python scripts/evaluate_embeddings.py \
    --checkpoint checkpoints/autoencoder/best_model.pt \
    --data-dir data/catalog \
    --output-dir results/embedding_analysis
```

---

## 🚧 Next Steps

### 1. Advanced Model Architecture

Implement `LuminautEmbedder` with:

- **LOB Encoder**: CNN for spatial order book features
- **Trade Flow Encoder**: MLP for trade dynamics
- **Cross-Attention Fusion**: Combine multiple modalities
- **Temporal Encoder**: Transformer for time-series patterns

### 2. Multi-task Learning

Implement combined loss function:
```python
total_loss = (
    1.0 * reconstruction_loss +    # MSE
    0.5 * contrastive_loss +       # InfoNCE
    0.3 * direction_loss           # CrossEntropy
)
```

### 3. Data Augmentation

- Temporal jittering
- Gaussian noise injection
- Mixup for regularization

### 4. Hyperparameter Optimization

- Grid search for latent dimensions (16, 32, 64, 128)
- Learning rate tuning (1e-4 to 1e-2)
- Architecture search (number of layers, hidden dims)

---

## File Structure

```
luminaut/phase2_embedding_research/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── autoencoder.py          # ✅ Baseline model
│   └── luminaut_embedder.py    # 🚧 Advanced model
├── data/
│   ├── __init__.py
│   └── dataset.py              # ✅ Data loading
├── trainers/
│   ├── __init__.py
│   └── trainer.py              # ✅ Training pipeline
├── experiments/                # 🚧 Experiment configs
└── notebooks/                  # 🚧 Analysis notebooks
```

---

## Usage Guide

### Step 1: Prepare Data

Ensure you have collected sufficient data in Phase 1:

```bash
# Collect 1+ hour of data
python scripts/quick_data_test.py --duration-minutes 60
```

### Step 2: Train Baseline Model

```bash
python scripts/train_autoencoder.py \
    --data-dir data/catalog \
    --latent-dim 32 \
    --epochs 100 \
    --batch-size 256 \
    --lr 1e-3
```

### Step 3: Evaluate Embeddings

```bash
python scripts/evaluate_embeddings.py \
    --checkpoint checkpoints/autoencoder/best_model.pt \
    --output-dir results/autoencoder_analysis
```

### Step 4: Visualize Results

Check the generated visualizations:
- `results/autoencoder_analysis/embeddings_pca.png`
- `results/autoencoder_analysis/embeddings_tsne.png`
- `results/autoencoder_analysis/evaluation_results.json`

---

## Success Criteria

### Baseline Autoencoder

| Metric | Target | Status |
|--------|--------|--------|
| Reconstruction MSE | < 0.01 | ⏳ TBD |
| Training Time | < 1 hour | ⏳ TBD |
| Embedding Dim | 16-32 | ✅ Configurable |

### Advanced Embedder (Next Steps)

| Metric | Target | Status |
|--------|--------|--------|
| Direction Accuracy | > 55% | 🚧 Not implemented |
| Silhouette Score | > 0.4 | 🚧 Not implemented |
| Inference Latency | < 20ms | 🚧 Not implemented |

---

## Experiment Tracking

### Weights & Biases Setup

```bash
# Login to W&B
wandb login

# Train with W&B logging
python scripts/train_autoencoder.py \
    --data-dir data/catalog \
    --use-wandb \
    --wandb-project luminaut-embeddings
```

### Metrics to Track

- Training/Validation loss curves
- Reconstruction error distribution
- Embedding statistics (mean, std, sparsity)
- Learning rate schedule

---

## Troubleshooting

### Issue: No data files found

**Solution:** Run Phase 1 data collection first:
```bash
python scripts/quick_data_test.py --duration-minutes 60
```

### Issue: CUDA out of memory

**Solution:** Reduce batch size:
```bash
python scripts/train_autoencoder.py --batch-size 64
```

### Issue: Poor reconstruction quality

**Solutions:**
1. Increase model capacity (larger hidden dims)
2. Train for more epochs
3. Check data normalization
4. Verify no data leakage in train/val split

---

## References

1. **Autoencoders**: Hinton & Salakhutdinov (2006) - "Reducing the Dimensionality of Data with Neural Networks"
2. **Contrastive Learning**: Chen et al. (2020) - "A Simple Framework for Contrastive Learning of Visual Representations"
3. **Transformers**: Vaswani et al. (2017) - "Attention Is All You Need"

---

## Next Milestones

- [ ] **Week 3**: Complete baseline model training and evaluation
- [ ] **Week 4**: Implement advanced LuminautEmbedder architecture
- [ ] **Week 5**: Multi-task training and ONNX export

---

**Contact:** For questions or issues, please open a GitHub issue or contact the development team.

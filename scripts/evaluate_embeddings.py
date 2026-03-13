"""
Phase 2: Evaluate Embedding Quality

This script evaluates the quality of learned embeddings by:
1. Measuring reconstruction error
2. Visualizing embedding space (t-SNE/PCA)
3. Analyzing clustering quality
"""

import argparse
import sys
from pathlib import Path
import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_model(checkpoint_path: str):
    """Load trained model from checkpoint."""
    from luminaut.phase2_embedding_research.models.autoencoder import AutoencoderConfig
    
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    config = checkpoint.get("config", {})
    
    if not config:
        # Try to infer config from model state
        state = checkpoint["model_state_dict"]
        input_dim = state["encoder.0.weight"].shape[1]
        latent_dim = state["encoder.-2.weight"].shape[0]
        
        config = {
            "input_dim": input_dim,
            "latent_dim": latent_dim,
            "hidden_dims": (64, 32),
        }
    
    from luminaut.phase2_embedding_research.models.autoencoder import (
        Autoencoder,
        AutoencoderConfig,
    )
    
    model_config = AutoencoderConfig(**config) if isinstance(config, dict) else config
    model = Autoencoder(model_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    
    return model, checkpoint


def evaluate_reconstruction(model, test_loader, device):
    """Evaluate reconstruction quality."""
    model.eval()
    total_mse = 0.0
    total_mae = 0.0
    num_batches = 0
    
    with torch.no_grad():
        for batch_x, _ in test_loader:
            batch_x = batch_x.to(device)
            
            latent, reconstruction = model(batch_x)
            
            mse = ((reconstruction - batch_x) ** 2).mean().item()
            mae = torch.abs(reconstruction - batch_x).mean().item()
            
            total_mse += mse
            total_mae += mae
            num_batches += 1
    
    return {
        "mse": total_mse / num_batches,
        "mae": total_mae / num_batches,
    }


def extract_embeddings(model, data_loader, device):
    """Extract embeddings for all samples."""
    model.eval()
    embeddings = []
    original_features = []
    
    with torch.no_grad():
        for batch_x, _ in data_loader:
            batch_x = batch_x.to(device)
            latent = model.encode(batch_x)
            
            embeddings.append(latent.cpu().numpy())
            original_features.append(batch_x.cpu().numpy())
    
    return np.vstack(embeddings), np.vstack(original_features)


def visualize_embeddings(embeddings, original_features, save_dir: str):
    """Create visualization of embedding space."""
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    
    # Subsample for visualization (max 5000 points)
    n_samples = min(5000, len(embeddings))
    indices = np.random.choice(len(embeddings), n_samples, replace=False)
    
    emb_sub = embeddings[indices]
    feat_sub = original_features[indices]
    
    # PCA to 2D
    print("Computing PCA...")
    pca = PCA(n_components=2)
    emb_2d = pca.fit_transform(emb_sub)
    
    plt.figure(figsize=(10, 8))
    plt.scatter(emb_2d[:, 0], emb_2d[:, 1], alpha=0.5, s=1)
    plt.title(f"PCA Visualization (Explained Var: {pca.explained_variance_ratio_.sum():.2%})")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.grid(True, alpha=0.3)
    plt.savefig(save_path / "embeddings_pca.png", dpi=150)
    plt.close()
    print(f"Saved PCA plot to {save_path / 'embeddings_pca.png'}")
    
    # t-SNE to 2D
    print("Computing t-SNE...")
    tsne = TSNE(n_components=2, perplexity=30, n_iter=1000, random_state=42)
    emb_2d_tsne = tsne.fit_transform(emb_sub)
    
    plt.figure(figsize=(10, 8))
    plt.scatter(emb_2d_tsne[:, 0], emb_2d_tsne[:, 1], alpha=0.5, s=1)
    plt.title("t-SNE Visualization")
    plt.xlabel("t-SNE 1")
    plt.ylabel("t-SNE 2")
    plt.grid(True, alpha=0.3)
    plt.savefig(save_path / "embeddings_tsne.png", dpi=150)
    plt.close()
    print(f"Saved t-SNE plot to {save_path / 'embeddings_tsne.png'}")


def analyze_clustering(embeddings):
    """Analyze clustering quality of embeddings."""
    # Use K-Means to find clusters
    from sklearn.cluster import KMeans
    
    # Try different numbers of clusters
    results = []
    for k in range(3, 10):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        # Calculate silhouette score
        if len(np.unique(labels)) > 1:
            sil_score = silhouette_score(embeddings, labels)
            results.append({
                "k": k,
                "silhouette_score": sil_score,
                "inertia": kmeans.inertia_,
            })
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate embedding quality"
    )
    
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to trained model checkpoint"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/catalog",
        help="Directory containing test data"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Batch size for evaluation"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/embedding_analysis",
        help="Directory to save results"
    )
    
    args = parser.parse_args()
    
    # Check checkpoint exists
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        print(f"Error: Checkpoint not found: {checkpoint_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Luminaut Phase 2: Embedding Quality Evaluation")
    print("=" * 60)
    
    # Load model
    print(f"\nLoading model from {checkpoint_path}...")
    model, checkpoint = load_model(str(checkpoint_path))
    
    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    model.to(device)
    
    # Load data
    print(f"\nLoading data from {args.data_dir}...")
    from luminaut.phase2_embedding_research.data.dataset import MarketDataModule
    
    data_module = MarketDataModule(
        data_dir=args.data_dir,
        batch_size=args.batch_size,
    )
    data_module.setup()
    
    test_loader = data_module.test_dataloader()
    print(f"Test set size: {len(data_module.test_dataset)}")
    
    # Evaluate reconstruction
    print("\nEvaluating reconstruction quality...")
    recon_metrics = evaluate_reconstruction(model, test_loader, device)
    
    print(f"\nReconstruction Metrics:")
    print(f"  MSE: {recon_metrics['mse']:.6f}")
    print(f"  MAE: {recon_metrics['mae']:.6f}")
    
    # Extract embeddings
    print("\nExtracting embeddings...")
    embeddings, original_features = extract_embeddings(model, test_loader, device)
    
    print(f"Embedding shape: {embeddings.shape}")
    
    # Analyze clustering
    print("\nAnalyzing clustering quality...")
    clustering_results = analyze_clustering(embeddings)
    
    print("\nClustering Analysis:")
    print("  k\tSilhouette Score")
    print("  " + "-" * 30)
    for result in clustering_results:
        print(f"  {result['k']}\t{result['silhouette_score']:.4f}")
    
    # Visualize
    print("\nGenerating visualizations...")
    visualize_embeddings(embeddings, original_features, args.output_dir)
    
    # Save results
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = {
        "reconstruction": recon_metrics,
        "clustering": clustering_results,
        "embedding_stats": {
            "mean": embeddings.mean().item(),
            "std": embeddings.std().item(),
            "min": embeddings.min().item(),
            "max": embeddings.max().item(),
        },
    }
    
    import json
    with open(output_path / "evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_path / 'evaluation_results.json'}")
    
    # Quality assessment
    print("\n" + "=" * 60)
    print("Quality Assessment")
    print("=" * 60)
    
    if recon_metrics["mse"] < 0.01:
        print("✓ Reconstruction MSE < 0.01 (Excellent)")
    elif recon_metrics["mse"] < 0.1:
        print("✓ Reconstruction MSE < 0.1 (Good)")
    else:
        print("✗ Reconstruction MSE > 0.1 (Needs improvement)")
    
    best_silhouette = max(r["silhouette_score"] for r in clustering_results)
    if best_silhouette > 0.5:
        print(f"✓ Best silhouette score > 0.5 ({best_silhouette:.3f}) - Strong clustering")
    elif best_silhouette > 0.3:
        print(f"✓ Best silhouette score > 0.3 ({best_silhouette:.3f}) - Moderate clustering")
    else:
        print(f"✗ Best silhouette score < 0.3 ({best_silhouette:.3f}) - Weak clustering")


if __name__ == "__main__":
    main()

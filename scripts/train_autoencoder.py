"""
Phase 2: Train Baseline Autoencoder

This script trains a baseline autoencoder on market data collected in Phase 1.

Usage:
    python scripts/train_autoencoder.py --data-dir data/catalog --latent-dim 16 --epochs 100
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from luminaut.phase2_embedding_research.trainers.trainer import train_autoencoder


def main():
    parser = argparse.ArgumentParser(
        description="Train baseline autoencoder on market data"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/catalog",
        help="Directory containing training data (CSV or Parquet files)"
    )
    
    parser.add_argument(
        "--latent-dim",
        type=int,
        default=16,
        help="Dimension of latent embedding space"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Training batch size"
    )
    
    parser.add_argument(
        "--epochs",
        type=int,
        default=100,
        help="Maximum number of training epochs"
    )
    
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Learning rate"
    )
    
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="checkpoints/autoencoder",
        help="Directory to save model checkpoints"
    )
    
    parser.add_argument(
        "--use-wandb",
        action="store_true",
        help="Enable Weights & Biases experiment tracking"
    )
    
    parser.add_argument(
        "--wandb-project",
        type=str,
        default="luminaut-embeddings",
        help="W&B project name"
    )
    
    args = parser.parse_args()
    
    # Validate data directory
    data_path = Path(args.data_dir)
    if not data_path.exists():
        print(f"Error: Data directory not found: {data_path}")
        print("\nPlease run Phase 1 data collection first:")
        print("  python scripts/quick_data_test.py --duration-minutes 60")
        sys.exit(1)
    
    # Check if data files exist
    csv_files = list(data_path.glob("features_*.csv"))
    parquet_files = list(data_path.glob("*.parquet"))
    
    if not csv_files and not parquet_files:
        print(f"Error: No feature files found in {data_path}")
        print("\nExpected files: features_*.csv or *.parquet")
        sys.exit(1)
    
    print("=" * 60)
    print("Luminaut Phase 2: Baseline Autoencoder Training")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Data directory: {args.data_dir}")
    print(f"  Latent dimension: {args.latent_dim}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Learning rate: {args.lr}")
    print(f"  Checkpoint directory: {args.checkpoint_dir}")
    print(f"  W&B logging: {args.use_wandb}")
    print(f"\nFound {len(csv_files) + len(parquet_files)} data files")
    print("=" * 60)
    
    # Train model
    try:
        model, history = train_autoencoder(
            data_dir=args.data_dir,
            latent_dim=args.latent_dim,
            batch_size=args.batch_size,
            num_epochs=args.epochs,
            learning_rate=args.lr,
            use_wandb=args.use_wandb,
            checkpoint_dir=args.checkpoint_dir,
        )
        
        print("\n" + "=" * 60)
        print("Training completed successfully!")
        print("=" * 60)
        print(f"\nResults:")
        print(f"  Best validation loss: {min(history['val_loss']):.6f}")
        print(f"  Final training loss: {history['train_loss'][-1]:.6f}")
        print(f"\nModel saved to: {Path(args.checkpoint_dir) / 'best_model.pt'}")
        print(f"Training history: {Path(args.checkpoint_dir) / 'training_history.json'}")
        
        # Next steps
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Evaluate embedding quality:")
        print("   python scripts/evaluate_embeddings.py --checkpoint checkpoints/autoencoder/best_model.pt")
        print("\n2. Visualize embeddings:")
        print("   python scripts/visualize_embeddings.py --checkpoint checkpoints/autoencoder/best_model.pt")
        print("\n3. Export to ONNX:")
        print("   python scripts/export_model_onnx.py --checkpoint checkpoints/autoencoder/best_model.pt")
        
    except Exception as e:
        print(f"\nError during training: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

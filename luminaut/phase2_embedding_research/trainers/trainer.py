"""
Training pipeline for Phase 2 embedding models.

This module provides training loops, validation, and model saving
functionality for embedding models.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import numpy as np
from datetime import datetime
import json

# Optional imports
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False
    print("Warning: wandb not installed. Install with: pip install wandb")


class TrainingPipeline:
    """
    Training pipeline for embedding models.
    
    Supports:
    - Multi-task learning (reconstruction + contrastive + direction)
    - Early stopping
    - Learning rate scheduling
    - Checkpoint saving
    - Experiment tracking (W&B)
    """
    
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-5,
        device: Optional[str] = None,
        use_wandb: bool = False,
        wandb_project: str = "luminaut-embeddings",
    ):
        """
        Initialize training pipeline.
        
        Args:
            model: PyTorch model to train
            train_loader: Training data loader
            val_loader: Validation data loader
            learning_rate: Initial learning rate
            weight_decay: L2 regularization strength
            device: Device to train on (cuda/cpu)
            use_wandb: Whether to use Weights & Biases tracking
            wandb_project: W&B project name
        """
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        
        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        self.model.to(self.device)
        
        # Optimizer
        self.optimizer = optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True,
        )
        
        # Training state
        self.current_epoch = 0
        self.best_val_loss = float('inf')
        self.best_model_state = None
        
        # W&B setup
        self.use_wandb = use_wandb and WANDB_AVAILABLE
        if self.use_wandb:
            wandb.init(project=wandb_project, config={
                "learning_rate": learning_rate,
                "weight_decay": weight_decay,
                "model": model.__class__.__name__,
            })
        
        # Training history
        self.history = {
            "train_loss": [],
            "val_loss": [],
            "learning_rate": [],
        }
    
    def train_epoch(self) -> float:
        """
        Train for one epoch.
        
        Returns:
            Average training loss
        """
        self.model.train()
        total_loss = 0.0
        num_batches = 0
        
        for batch_x, batch_y in self.train_loader:
            batch_x = batch_x.to(self.device)
            batch_y = batch_y.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            
            # For autoencoder: (latent, reconstruction)
            outputs = self.model(batch_x)
            
            if isinstance(outputs, tuple):
                latent, reconstruction = outputs
                loss = self.model.reconstruction_loss(batch_x, reconstruction)
            else:
                # If model only returns reconstruction
                loss = self.model.reconstruction_loss(batch_x, outputs)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
        
        avg_loss = total_loss / num_batches
        return avg_loss
    
    @torch.no_grad()
    def validate(self) -> float:
        """
        Validate the model.
        
        Returns:
            Average validation loss
        """
        self.model.eval()
        total_loss = 0.0
        num_batches = 0
        
        for batch_x, batch_y in self.val_loader:
            batch_x = batch_x.to(self.device)
            batch_y = batch_y.to(self.device)
            
            # Forward pass
            outputs = self.model(batch_x)
            
            if isinstance(outputs, tuple):
                latent, reconstruction = outputs
                loss = self.model.reconstruction_loss(batch_x, reconstruction)
            else:
                loss = self.model.reconstruction_loss(batch_x, outputs)
            
            total_loss += loss.item()
            num_batches += 1
        
        avg_loss = total_loss / num_batches
        return avg_loss
    
    def train(
        self,
        num_epochs: int = 100,
        patience: int = 10,
        checkpoint_dir: str = "checkpoints",
        save_every: int = 10,
    ) -> Dict[str, List[float]]:
        """
        Full training loop with early stopping.
        
        Args:
            num_epochs: Maximum number of epochs
            patience: Early stopping patience
            checkpoint_dir: Directory to save checkpoints
            save_every: Save checkpoint every N epochs
        
        Returns:
            Training history
        """
        checkpoint_path = Path(checkpoint_dir)
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Starting training for {num_epochs} epochs...")
        print(f"Device: {self.device}")
        print(f"Using W&B logging: {self.use_wandb}")
        
        epochs_without_improvement = 0
        
        for epoch in range(num_epochs):
            self.current_epoch = epoch + 1
            
            # Train
            train_loss = self.train_epoch()
            
            # Validate
            val_loss = self.validate()
            
            # Update scheduler
            self.scheduler.step(val_loss)
            
            # Record history
            self.history["train_loss"].append(train_loss)
            self.history["val_loss"].append(val_loss)
            self.history["learning_rate"].append(self.optimizer.param_groups[0]["lr"])
            
            # Logging
            log_msg = (
                f"Epoch {self.current_epoch:3d}/{num_epochs}: "
                f"train_loss={train_loss:.6f}, val_loss={val_loss:.6f}, "
                f"lr={self.optimizer.param_groups[0]['lr']:.2e}"
            )
            print(log_msg)
            
            # W&B logging
            if self.use_wandb:
                wandb.log({
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "learning_rate": self.optimizer.param_groups[0]["lr"],
                    "epoch": self.current_epoch,
                })
            
            # Check for improvement
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.best_model_state = self.model.state_dict().copy()
                epochs_without_improvement = 0
                
                # Save best model
                torch.save({
                    "epoch": self.current_epoch,
                    "model_state_dict": self.best_model_state,
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "val_loss": val_loss,
                    "config": self.model.config if hasattr(self.model, "config") else {},
                }, checkpoint_path / "best_model.pt")
                
                print(f"  ✓ New best model! Saved to {checkpoint_path / 'best_model.pt'}")
            else:
                epochs_without_improvement += 1
            
            # Save periodic checkpoint
            if (epoch + 1) % save_every == 0:
                torch.save({
                    "epoch": self.current_epoch,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "val_loss": val_loss,
                }, checkpoint_path / f"checkpoint_epoch_{self.current_epoch}.pt")
            
            # Early stopping
            if epochs_without_improvement >= patience:
                print(f"\nEarly stopping triggered after {self.current_epoch} epochs")
                break
        
        # Load best model
        if self.best_model_state is not None:
            self.model.load_state_dict(self.best_model_state)
            print(f"Loaded best model with val_loss={self.best_val_loss:.6f}")
        
        # Save training history
        with open(checkpoint_path / "training_history.json", "w") as f:
            json.dump(self.history, f, indent=2)
        
        print(f"\nTraining completed!")
        print(f"Best validation loss: {self.best_val_loss:.6f}")
        
        return self.history
    
    def cleanup(self):
        """Clean up resources (e.g., close W&B)."""
        if self.use_wandb:
            wandb.finish()


def train_autoencoder(
    data_dir: str,
    latent_dim: int = 16,
    batch_size: int = 256,
    num_epochs: int = 100,
    learning_rate: float = 1e-3,
    use_wandb: bool = False,
    checkpoint_dir: str = "checkpoints/autoencoder",
) -> Tuple[nn.Module, Dict]:
    """
    Convenience function to train an autoencoder.
    
    Args:
        data_dir: Directory containing training data
        latent_dim: Dimension of latent embedding
        batch_size: Training batch size
        num_epochs: Number of epochs
        learning_rate: Learning rate
        use_wandb: Whether to use W&B logging
        checkpoint_dir: Directory to save checkpoints
    
    Returns:
        Tuple of (trained_model, training_history)
    """
    from luminaut.phase2_embedding_research.models.autoencoder import (
        create_baseline_autoencoder,
    )
    from luminaut.phase2_embedding_research.data.dataset import MarketDataModule
    
    # Setup data
    print("Loading data...")
    data_module = MarketDataModule(
        data_dir=data_dir,
        batch_size=batch_size,
    )
    data_module.setup()
    
    feature_dim = data_module.get_feature_dim()
    print(f"Feature dimension: {feature_dim}")
    
    # Create model
    model = create_baseline_autoencoder(
        input_dim=feature_dim,
        latent_dim=latent_dim,
    )
    
    # Setup training
    pipeline = TrainingPipeline(
        model=model,
        train_loader=data_module.train_dataloader(),
        val_loader=data_module.val_dataloader(),
        learning_rate=learning_rate,
        use_wandb=use_wandb,
    )
    
    # Train
    history = pipeline.train(
        num_epochs=num_epochs,
        patience=15,
        checkpoint_dir=checkpoint_dir,
    )
    
    pipeline.cleanup()
    
    return model, history


if __name__ == "__main__":
    # Example usage
    print("Training Pipeline Test")
    print("=" * 50)
    
    # This would be run with actual data:
    # model, history = train_autoencoder(
    #     data_dir="data/catalog",
    #     latent_dim=16,
    #     num_epochs=50,
    # )
    
    print("To train a model, run:")
    print('  python -m luminaut.phase2_embedding_research.trainers.trainer')

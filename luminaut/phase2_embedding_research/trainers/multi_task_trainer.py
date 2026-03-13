"""
Multi-task Training Pipeline for Luminaut Embedder

Supports combined training with:
- Reconstruction loss (MSE)
- Contrastive loss (InfoNCE)
- Direction prediction loss (CrossEntropy)
- Volatility prediction loss (MSE)
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


class MultiTaskTrainingPipeline:
    """
    Multi-task training pipeline for LuminautEmbedder.
    
    Combines multiple loss functions with configurable weights:
        total_loss = (
            w1 * reconstruction_loss +
            w2 * contrastive_loss +
            w3 * direction_loss +
            w4 * volatility_loss
        )
    """
    
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-5,
        device: Optional[str] = None,
        # Loss weights
        w_reconstruct: float = 1.0,
        w_contrastive: float = 0.5,
        w_direction: float = 0.3,
        w_volatility: float = 0.2,
        # Other
        use_wandb: bool = False,
        wandb_project: str = "luminaut-embeddings",
    ):
        """Initialize multi-task training pipeline."""
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
        self.scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer,
            T_0=10,
            T_mult=2,
            eta_min=1e-6,
        )
        
        # Loss weights
        self.loss_weights = {
            "reconstruct": w_reconstruct,
            "contrastive": w_contrastive,
            "direction": w_direction,
            "volatility": w_volatility,
        }
        
        # Training state
        self.current_epoch = 0
        self.best_val_loss = float('inf')
        self.best_model_state = None
        
        # W&B setup
        self.use_wandb = use_wandb and WANDB_AVAILABLE
        if self.use_wandb:
            wandb.init(
                project=wandb_project,
                config={
                    "learning_rate": learning_rate,
                    "weight_decay": weight_decay,
                    "model": model.__class__.__name__,
                    "loss_weights": self.loss_weights,
                }
            )
        
        # Training history
        self.history = {
            "train_loss": [],
            "val_loss": [],
            "train_losses_component": [],
            "val_losses_component": [],
            "learning_rate": [],
        }
    
    def compute_total_loss(
        self,
        outputs: Dict[str, torch.Tensor],
        targets: Dict[str, torch.Tensor],
        batch_size: int,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute weighted sum of all losses.
        
        Returns:
            Tuple of (total_loss, loss_components)
        """
        losses = {}
        
        # Reconstruction loss
        losses["reconstruct"] = self.model.reconstruction_loss(outputs, targets)
        
        # Contrastive loss
        losses["contrastive"] = self.model.contrastive_loss(outputs["embedding"])
        
        # Direction prediction loss
        losses["direction"] = self.model.direction_loss(outputs, targets)
        
        # Volatility prediction loss
        losses["volatility"] = self.model.volatility_loss(outputs, targets)
        
        # Weighted sum
        total_loss = sum(
            self.loss_weights[k] * losses[k]
            for k in losses.keys()
        )
        
        # Convert to dict of floats for logging
        loss_components = {k: v.item() for k, v in losses.items()}
        loss_components["total"] = total_loss.item()
        
        return total_loss, loss_components
    
    def train_epoch(self) -> Dict[str, float]:
        """Train for one epoch. Returns average losses."""
        self.model.train()
        
        total_losses = {"total": 0.0}
        for key in self.loss_weights.keys():
            total_losses[key] = 0.0
        
        num_batches = 0
        
        for batch in self.train_loader:
            # Unpack batch
            lob_data = batch["lob"].to(self.device)
            trade_data = batch["trade"].to(self.device)
            targets = {
                "reconstruction": batch["reconstruction_target"].to(self.device),
                "direction": batch["direction"].to(self.device),
                "volatility": batch["volatility"].to(self.device),
            }
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(lob_data, trade_data)
            
            # Compute loss
            total_loss, loss_components = self.compute_total_loss(
                outputs, targets, lob_data.shape[0]
            )
            
            # Backward pass
            total_loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            # Accumulate losses
            for key in total_losses.keys():
                total_losses[key] += loss_components.get(key, 0.0)
            
            num_batches += 1
        
        # Average losses
        avg_losses = {k: v / num_batches for k, v in total_losses.items()}
        return avg_losses
    
    @torch.no_grad()
    def validate(self) -> Dict[str, float]:
        """Validate the model. Returns average losses."""
        self.model.eval()
        
        total_losses = {"total": 0.0}
        for key in self.loss_weights.keys():
            total_losses[key] = 0.0
        
        num_batches = 0
        
        for batch in self.val_loader:
            # Unpack batch
            lob_data = batch["lob"].to(self.device)
            trade_data = batch["trade"].to(self.device)
            targets = {
                "reconstruction": batch["reconstruction_target"].to(self.device),
                "direction": batch["direction"].to(self.device),
                "volatility": batch["volatility"].to(self.device),
            }
            
            # Forward pass
            outputs = self.model(lob_data, trade_data)
            
            # Compute loss
            _, loss_components = self.compute_total_loss(
                outputs, targets, lob_data.shape[0]
            )
            
            # Accumulate losses
            for key in total_losses.keys():
                total_losses[key] += loss_components.get(key, 0.0)
            
            num_batches += 1
        
        # Average losses
        avg_losses = {k: v / num_batches for k, v in total_losses.items()}
        return avg_losses
    
    def train(
        self,
        num_epochs: int = 100,
        patience: int = 15,
        checkpoint_dir: str = "checkpoints/luminaut_embedder",
        save_every: int = 10,
    ) -> Dict[str, List[float]]:
        """Full training loop with early stopping."""
        checkpoint_path = Path(checkpoint_dir)
        checkpoint_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Starting multi-task training for {num_epochs} epochs...")
        print(f"Device: {self.device}")
        print(f"Loss weights: {self.loss_weights}")
        
        epochs_without_improvement = 0
        
        for epoch in range(num_epochs):
            self.current_epoch = epoch + 1
            
            # Train
            train_losses = self.train_epoch()
            
            # Validate
            val_losses = self.validate()
            
            # Update scheduler
            self.scheduler.step()
            
            # Record history
            self.history["train_loss"].append(train_losses["total"])
            self.history["val_loss"].append(val_losses["total"])
            self.history["train_losses_component"].append(train_losses)
            self.history["val_losses_component"].append(val_losses)
            self.history["learning_rate"].append(self.optimizer.param_groups[0]["lr"])
            
            # Logging
            log_msg = (
                f"Epoch {self.current_epoch:3d}/{num_epochs}: "
                f"train={train_losses['total']:.4f}, val={val_losses['total']:.4f}, "
                f"lr={self.optimizer.param_groups[0]['lr']:.2e}"
            )
            print(log_msg)
            
            # Detailed loss breakdown (every 10 epochs)
            if (epoch + 1) % 10 == 0:
                print("  Loss breakdown:")
                for key in ["reconstruct", "contrastive", "direction", "volatility"]:
                    print(f"    {key}: train={train_losses[key]:.4f}, val={val_losses[key]:.4f}")
            
            # W&B logging
            if self.use_wandb:
                wandb.log({
                    "train_loss": train_losses["total"],
                    "val_loss": val_losses["total"],
                    "learning_rate": self.optimizer.param_groups[0]["lr"],
                    "epoch": self.current_epoch,
                    **{f"train_{k}": v for k, v in train_losses.items()},
                    **{f"val_{k}": v for k, v in val_losses.items()},
                })
            
            # Check for improvement
            if val_losses["total"] < self.best_val_loss:
                self.best_val_loss = val_losses["total"]
                self.best_model_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
                epochs_without_improvement = 0
                
                # Save best model
                torch.save({
                    "epoch": self.current_epoch,
                    "model_state_dict": self.best_model_state,
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "val_loss": val_losses["total"],
                    "config": self.model.config if hasattr(self.model, "config") else {},
                }, checkpoint_path / "best_model.pt")
                
                print(f"  ✓ New best model! val_loss={val_losses['total']:.4f}")
            else:
                epochs_without_improvement += 1
            
            # Save periodic checkpoint
            if (epoch + 1) % save_every == 0:
                torch.save({
                    "epoch": self.current_epoch,
                    "model_state_dict": self.model.state_dict(),
                    "optimizer_state_dict": self.optimizer.state_dict(),
                    "val_loss": val_losses["total"],
                }, checkpoint_path / f"checkpoint_epoch_{self.current_epoch}.pt")
            
            # Early stopping
            if epochs_without_improvement >= patience:
                print(f"\nEarly stopping triggered after {self.current_epoch} epochs")
                break
        
        # Load best model
        if self.best_model_state is not None:
            self.model.load_state_dict(self.best_model_state)
            print(f"\nLoaded best model with val_loss={self.best_val_loss:.4f}")
        
        # Save training history
        with open(checkpoint_path / "training_history.json", "w") as f:
            json.dump(self.history, f, indent=2)
        
        print(f"\nTraining completed!")
        print(f"Best validation loss: {self.best_val_loss:.4f}")
        
        return self.history
    
    def cleanup(self):
        """Clean up resources."""
        if self.use_wandb:
            wandb.finish()


def train_luminaut_embedder(
    train_loader: DataLoader,
    val_loader: DataLoader,
    embedding_dim: int = 64,
    sequence_length: int = 10,
    num_epochs: int = 100,
    learning_rate: float = 1e-3,
    checkpoint_dir: str = "checkpoints/luminaut_embedder",
    use_wandb: bool = False,
) -> Tuple[nn.Module, Dict]:
    """
    Convenience function to train LuminautEmbedder.
    
    Returns:
        Tuple of (trained_model, training_history)
    """
    from luminaut.phase2_embedding_research.models.luminaut_embedder import (
        create_luminaut_embedder,
    )
    
    # Create model
    model = create_luminaut_embedder(
        embedding_dim=embedding_dim,
        sequence_length=sequence_length,
    )
    
    # Setup training
    pipeline = MultiTaskTrainingPipeline(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
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
    print("Multi-task Training Pipeline Test")
    print("=" * 50)
    print("To train LuminautEmbedder, run:")
    print("  python scripts/train_luminaut_embedder.py")

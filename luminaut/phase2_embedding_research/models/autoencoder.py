"""
Baseline Autoencoder for Market State Embedding

This module implements a simple autoencoder as a baseline for
learning low-dimensional embeddings of market states.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np


@dataclass
class AutoencoderConfig:
    """Configuration for the baseline autoencoder."""
    
    # Input dimension (feature vector size)
    input_dim: int = 50
    
    # Latent dimension (embedding size)
    latent_dim: int = 16
    
    # Hidden layer dimensions
    hidden_dims: Tuple[int, ...] = (64, 32)
    
    # Dropout rate
    dropout: float = 0.1
    
    # Activation function
    activation: str = "relu"
    
    # Batch normalization
    use_batch_norm: bool = True


class Autoencoder(nn.Module):
    """
    Baseline Autoencoder for market state embedding.
    
    Architecture:
        Encoder: input_dim -> hidden_dims -> latent_dim
        Decoder: latent_dim -> hidden_dims (reversed) -> input_dim
    
    The model learns to compress market state features into a low-dimensional
    embedding while preserving reconstruction ability.
    """
    
    def __init__(self, config: AutoencoderConfig):
        super().__init__()
        self.config = config
        
        # Build encoder
        encoder_layers = []
        prev_dim = config.input_dim
        
        for hidden_dim in config.hidden_dims:
            encoder_layers.append(nn.Linear(prev_dim, hidden_dim))
            if config.use_batch_norm:
                encoder_layers.append(nn.BatchNorm1d(hidden_dim))
            encoder_layers.append(self._get_activation(config.activation))
            encoder_layers.append(nn.Dropout(config.dropout))
            prev_dim = hidden_dim
        
        # Final layer to latent space
        encoder_layers.append(nn.Linear(prev_dim, config.latent_dim))
        self.encoder = nn.Sequential(*encoder_layers)
        
        # Build decoder (reverse of encoder)
        decoder_layers = []
        prev_dim = config.latent_dim
        
        for hidden_dim in reversed(config.hidden_dims):
            decoder_layers.append(nn.Linear(prev_dim, hidden_dim))
            if config.use_batch_norm:
                decoder_layers.append(nn.BatchNorm1d(hidden_dim))
            decoder_layers.append(self._get_activation(config.activation))
            decoder_layers.append(nn.Dropout(config.dropout))
            prev_dim = hidden_dim
        
        # Final layer to output (reconstruction)
        decoder_layers.append(nn.Linear(prev_dim, config.input_dim))
        self.decoder = nn.Sequential(*decoder_layers)
    
    def _get_activation(self, name: str) -> nn.Module:
        """Get activation function by name."""
        activations = {
            "relu": nn.ReLU(),
            "gelu": nn.GELU(),
            "tanh": nn.Tanh(),
            "sigmoid": nn.Sigmoid(),
        }
        if name not in activations:
            raise ValueError(f"Unknown activation: {name}")
        return activations[name]
    
    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """
        Encode input to latent representation.
        
        Args:
            x: Input tensor of shape (batch_size, input_dim)
        
        Returns:
            Latent representation of shape (batch_size, latent_dim)
        """
        return self.encoder(x)
    
    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """
        Decode latent representation to reconstruction.
        
        Args:
            z: Latent tensor of shape (batch_size, latent_dim)
        
        Returns:
            Reconstruction of shape (batch_size, input_dim)
        """
        return self.decoder(z)
    
    def forward(
        self, x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass through encoder and decoder.
        
        Args:
            x: Input tensor of shape (batch_size, input_dim)
        
        Returns:
            Tuple of (latent, reconstruction)
        """
        latent = self.encode(x)
        reconstruction = self.decode(latent)
        return latent, reconstruction
    
    def reconstruction_loss(
        self, x: torch.Tensor, x_reconstructed: torch.Tensor
    ) -> torch.Tensor:
        """
        Calculate reconstruction loss (MSE).
        
        Args:
            x: Original input
            x_reconstructed: Reconstructed input
        
        Returns:
            Mean squared error loss
        """
        return F.mse_loss(x_reconstructed, x)
    
    def get_embedding_dim(self) -> int:
        """Get the dimension of the latent embedding."""
        return self.config.latent_dim


def create_baseline_autoencoder(
    input_dim: int = 50,
    latent_dim: int = 16,
) -> Autoencoder:
    """
    Create a baseline autoencoder with default configuration.
    
    Args:
        input_dim: Dimension of input features
        latent_dim: Dimension of latent embedding
    
    Returns:
        Configured Autoencoder model
    """
    config = AutoencoderConfig(
        input_dim=input_dim,
        latent_dim=latent_dim,
        hidden_dims=(64, 32),
        dropout=0.1,
        activation="relu",
        use_batch_norm=True,
    )
    return Autoencoder(config)


if __name__ == "__main__":
    # Test the model
    model = create_baseline_autoencoder(input_dim=50, latent_dim=16)
    
    # Create dummy input
    batch_size = 32
    x = torch.randn(batch_size, 50)
    
    # Forward pass
    latent, reconstruction = model(x)
    
    print(f"Input shape: {x.shape}")
    print(f"Latent shape: {latent.shape}")
    print(f"Reconstruction shape: {reconstruction.shape}")
    
    # Calculate loss
    loss = model.reconstruction_loss(x, reconstruction)
    print(f"Reconstruction loss: {loss.item():.4f}")

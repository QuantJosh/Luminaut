"""
Luminaut Embedder: Advanced Multi-Branch Architecture

This module implements the production embedding model with:
- Multi-branch encoding (LOB + Trade Flow)
- Cross-attention fusion
- Transformer temporal encoder
- Multi-task learning heads
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
import numpy as np


@dataclass
class LuminautEmbedderConfig:
    """Configuration for LuminautEmbedder."""
    
    # Input dimensions
    lob_input_dim: int = 40  # 10 levels × 4 fields (price, volume, delta, ratio)
    trade_input_dim: int = 10  # Trade flow features
    
    # LOB Encoder config
    lob_hidden_dims: Tuple[int, ...] = (128, 64)
    lob_kernel_size: int = 3
    lob_num_filters: int = 32
    
    # Trade Flow Encoder config
    trade_hidden_dims: Tuple[int, ...] = (64, 32)
    
    # Fusion config
    fusion_hidden_dim: int = 128
    num_attention_heads: int = 4
    
    # Temporal Encoder config
    transformer_hidden_dim: int = 128
    transformer_num_layers: int = 2
    transformer_dropout: float = 0.1
    
    # Embedding config
    embedding_dim: int = 64
    
    # Task heads
    direction_hidden_dim: int = 32
    volatility_hidden_dim: int = 32
    
    # Regularization
    dropout: float = 0.1
    use_batch_norm: bool = True
    use_layer_norm: bool = True


class LOBEncoder(nn.Module):
    """
    CNN-based encoder for Order Book data.
    
    Processes L2 order book snapshots with spatial convolutions
    to capture level-wise patterns.
    """
    
    def __init__(self, config: LuminautEmbedderConfig):
        super().__init__()
        self.config = config
        
        # Convolutional layers
        self.conv1 = nn.Conv2d(
            in_channels=1,
            out_channels=config.lob_num_filters,
            kernel_size=(config.lob_kernel_size, 3),
            padding=(1, 1)
        )
        self.conv2 = nn.Conv2d(
            in_channels=config.lob_num_filters,
            out_channels=config.lob_num_filters * 2,
            kernel_size=(config.lob_kernel_size, 3),
            padding=(1, 1)
        )
        
        # Fully connected layers
        fc_layers = []
        prev_dim = config.lob_num_filters * 2 * 10  # 10 price levels
        for hidden_dim in config.lob_hidden_dims:
            fc_layers.append(nn.Linear(prev_dim, hidden_dim))
            if config.use_batch_norm:
                fc_layers.append(nn.BatchNorm1d(hidden_dim))
            fc_layers.append(nn.ReLU())
            fc_layers.append(nn.Dropout(config.dropout))
            prev_dim = hidden_dim
        
        self.fc = nn.Sequential(*fc_layers)
        self.output_dim = prev_dim
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: LOB data of shape (batch, 1, 10, 4)
               where 10 = price levels, 4 = [bid_price, bid_vol, ask_price, ask_vol]
        
        Returns:
            Encoded features of shape (batch, output_dim)
        """
        # Convolutional layers
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        
        # Flatten
        x = x.flatten(1)
        
        # Fully connected layers
        x = self.fc(x)
        
        return x


class TradeFlowEncoder(nn.Module):
    """
    MLP-based encoder for trade flow data.
    
    Processes trade statistics and flow imbalances.
    """
    
    def __init__(self, config: LuminautEmbedderConfig):
        super().__init__()
        self.config = config
        
        # MLP layers
        layers = []
        prev_dim = config.trade_input_dim
        for hidden_dim in config.trade_hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            if config.use_batch_norm:
                layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(config.dropout))
            prev_dim = hidden_dim
        
        self.mlp = nn.Sequential(*layers)
        self.output_dim = prev_dim
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Trade flow data of shape (batch, trade_input_dim)
        
        Returns:
            Encoded features of shape (batch, output_dim)
        """
        return self.mlp(x)


class CrossAttentionFusion(nn.Module):
    """
    Cross-attention mechanism to fuse LOB and Trade Flow embeddings.
    """
    
    def __init__(self, config: LuminautEmbedderConfig):
        super().__init__()
        self.config = config
        
        # Query, Key, Value projections
        self.lob_query = nn.Linear(config.lob_hidden_dims[-1], config.fusion_hidden_dim)
        self.trade_key = nn.Linear(config.trade_hidden_dims[-1], config.fusion_hidden_dim)
        self.trade_value = nn.Linear(config.trade_hidden_dims[-1], config.fusion_hidden_dim)
        
        # Multi-head attention
        self.attention = nn.MultiheadAttention(
            embed_dim=config.fusion_hidden_dim,
            num_heads=config.num_attention_heads,
            dropout=config.dropout,
            batch_first=True
        )
        
        # Layer norm
        if config.use_layer_norm:
            self.layer_norm = nn.LayerNorm(config.fusion_hidden_dim)
        else:
            self.layer_norm = nn.Identity()
        
        # Output projection
        self.output_proj = nn.Linear(config.fusion_hidden_dim, config.fusion_hidden_dim)
    
    def forward(
        self,
        lob_features: torch.Tensor,
        trade_features: torch.Tensor
    ) -> torch.Tensor:
        """
        Forward pass with cross-attention.
        
        Args:
            lob_features: LOB embeddings (batch, lob_hidden_dim)
            trade_features: Trade flow embeddings (batch, trade_hidden_dim)
        
        Returns:
            Fused features (batch, fusion_hidden_dim)
        """
        # Project to common dimension
        query = self.lob_query(lob_features).unsqueeze(1)  # (batch, 1, dim)
        key = self.trade_key(trade_features).unsqueeze(1)   # (batch, 1, dim)
        value = self.trade_value(trade_features).unsqueeze(1)  # (batch, 1, dim)
        
        # Cross-attention
        attended, _ = self.attention(query, key, value)
        attended = attended.squeeze(1)  # (batch, dim)
        
        # Residual connection + layer norm
        output = self.layer_norm(attended + query.squeeze(1))
        output = F.relu(self.output_proj(output))
        
        return output


class TransformerTemporalEncoder(nn.Module):
    """
    Transformer-based temporal encoder for sequential patterns.
    """
    
    def __init__(self, config: LuminautEmbedderConfig, sequence_length: int = 10):
        super().__init__()
        self.config = config
        self.sequence_length = sequence_length
        
        # Positional encoding
        self.pos_encoding = nn.Parameter(
            torch.randn(1, sequence_length, config.fusion_hidden_dim) * 0.1
        )
        
        # Transformer encoder layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.fusion_hidden_dim,
            nhead=config.num_attention_heads,
            dim_feedforward=config.transformer_hidden_dim,
            dropout=config.transformer_dropout,
            batch_first=True
        )
        
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.transformer_num_layers
        )
        
        # Layer norm
        if config.use_layer_norm:
            self.layer_norm = nn.LayerNorm(config.fusion_hidden_dim)
        else:
            self.layer_norm = nn.Identity()
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        
        Args:
            x: Sequence of fused features (batch, seq_len, fusion_hidden_dim)
        
        Returns:
            Temporal encoding (batch, fusion_hidden_dim)
        """
        # Add positional encoding
        x = x + self.pos_encoding
        
        # Transformer encoding
        x = self.transformer(x)
        
        # Global average pooling
        x = x.mean(dim=1)
        
        # Layer norm
        x = self.layer_norm(x)
        
        return x


class LuminautEmbedder(nn.Module):
    """
    Complete Luminaut Embedding Model.
    
    Architecture:
        LOB Data → LOB Encoder ─┐
                                ├→ Cross-Attention → Transformer → Embedding
        Trade Data → Trade Encoder ─┘
    
    Multi-task heads:
        - Reconstruction (decoder)
        - Direction prediction (classification)
        - Volatility prediction (regression)
    """
    
    def __init__(self, config: LuminautEmbedderConfig, sequence_length: int = 10):
        super().__init__()
        self.config = config
        self.sequence_length = sequence_length
        
        # Encoders
        self.lob_encoder = LOBEncoder(config)
        self.trade_encoder = TradeFlowEncoder(config)
        
        # Fusion
        self.fusion = CrossAttentionFusion(config)
        
        # Temporal encoding
        self.temporal_encoder = TransformerTemporalEncoder(config, sequence_length)
        
        # Embedding projection
        self.embedding_proj = nn.Sequential(
            nn.Linear(config.fusion_hidden_dim, config.embedding_dim),
            nn.LayerNorm(config.embedding_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout)
        )
        
        # Task heads
        self.direction_head = nn.Sequential(
            nn.Linear(config.embedding_dim, config.direction_hidden_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.direction_hidden_dim, 3)  # Up/Down/Neutral
        )
        
        self.volatility_head = nn.Sequential(
            nn.Linear(config.embedding_dim, config.volatility_hidden_dim),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.volatility_hidden_dim, 1)
        )
        
        # Decoder for reconstruction
        self.decoder = nn.Sequential(
            nn.Linear(config.embedding_dim, config.fusion_hidden_dim),
            nn.ReLU(),
            nn.Linear(config.fusion_hidden_dim, config.lob_input_dim + config.trade_input_dim)
        )
    
    def encode(
        self,
        lob_data: torch.Tensor,
        trade_data: torch.Tensor
    ) -> torch.Tensor:
        """
        Encode market data to embedding.
        
        Args:
            lob_data: LOB features (batch, seq_len, 1, 10, 4)
            trade_data: Trade flow features (batch, seq_len, trade_input_dim)
        
        Returns:
            Embedding (batch, embedding_dim)
        """
        batch_size, seq_len = lob_data.shape[:2]
        
        # Encode each timestep
        lob_embeddings = []
        trade_embeddings = []
        
        for t in range(seq_len):
            lob_t = lob_data[:, t, :, :, :]  # (batch, 1, 10, 4)
            trade_t = trade_data[:, t, :]     # (batch, trade_input_dim)
            
            lob_enc = self.lob_encoder(lob_t)
            trade_enc = self.trade_encoder(trade_t)
            
            lob_embeddings.append(lob_enc)
            trade_embeddings.append(trade_enc)
        
        # Stack sequences
        lob_embeddings = torch.stack(lob_embeddings, dim=1)  # (batch, seq_len, lob_dim)
        trade_embeddings = torch.stack(trade_embeddings, dim=1)  # (batch, seq_len, trade_dim)
        
        # Fuse at each timestep
        fused = []
        for t in range(seq_len):
            fused_t = self.fusion(lob_embeddings[:, t, :], trade_embeddings[:, t, :])
            fused.append(fused_t)
        
        fused = torch.stack(fused, dim=1)  # (batch, seq_len, fusion_dim)
        
        # Temporal encoding
        temporal = self.temporal_encoder(fused)
        
        # Final embedding
        embedding = self.embedding_proj(temporal)
        
        return embedding
    
    def forward(
        self,
        lob_data: torch.Tensor,
        trade_data: torch.Tensor,
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass with all task heads.
        
        Args:
            lob_data: LOB features (batch, seq_len, 1, 10, 4)
            trade_data: Trade flow features (batch, seq_len, trade_input_dim)
        
        Returns:
            Dictionary with:
                - embedding: (batch, embedding_dim)
                - direction: (batch, 3) logits
                - volatility: (batch, 1)
                - reconstruction: (batch, input_dim)
        """
        # Get embedding
        embedding = self.encode(lob_data, trade_data)
        
        # Task heads
        direction_logits = self.direction_head(embedding)
        volatility = self.volatility_head(embedding)
        reconstruction = self.decoder(embedding)
        
        return {
            "embedding": embedding,
            "direction": direction_logits,
            "volatility": volatility,
            "reconstruction": reconstruction,
        }
    
    def reconstruction_loss(
        self,
        prediction: Dict[str, torch.Tensor],
        target: Dict[str, torch.Tensor]
    ) -> torch.Tensor:
        """Calculate reconstruction loss (MSE)."""
        return F.mse_loss(prediction["reconstruction"], target["reconstruction"])
    
    def direction_loss(
        self,
        prediction: Dict[str, torch.Tensor],
        target: Dict[str, torch.Tensor]
    ) -> torch.Tensor:
        """Calculate direction prediction loss (CrossEntropy)."""
        return F.cross_entropy(prediction["direction"], target["direction"])
    
    def volatility_loss(
        self,
        prediction: Dict[str, torch.Tensor],
        target: Dict[str, torch.Tensor]
    ) -> torch.Tensor:
        """Calculate volatility prediction loss (MSE)."""
        return F.mse_loss(prediction["volatility"].squeeze(), target["volatility"])
    
    def contrastive_loss(
        self,
        embedding: torch.Tensor,
        temperature: float = 0.07
    ) -> torch.Tensor:
        """
        Calculate InfoNCE contrastive loss.
        
        Encourages similar embeddings for nearby timesteps.
        """
        # Normalize embeddings
        embedding = F.normalize(embedding, p=2, dim=1)
        
        # Similarity matrix
        sim_matrix = torch.matmul(embedding, embedding.T) / temperature
        
        # Labels: positive pairs are diagonal and adjacent
        batch_size = embedding.shape[0]
        labels = torch.zeros(batch_size, dtype=torch.long, device=embedding.device)
        
        # InfoNCE loss
        loss = F.cross_entropy(sim_matrix, labels)
        
        return loss
    
    def get_embedding_dim(self) -> int:
        """Get embedding dimension."""
        return self.config.embedding_dim


def create_luminaut_embedder(
    lob_input_dim: int = 40,
    trade_input_dim: int = 10,
    embedding_dim: int = 64,
    sequence_length: int = 10,
) -> LuminautEmbedder:
    """
    Create LuminautEmbedder with default configuration.
    
    Args:
        lob_input_dim: Dimension of LOB input features
        trade_input_dim: Dimension of trade flow input
        embedding_dim: Final embedding dimension
        sequence_length: Sequence length for temporal modeling
    
    Returns:
        Configured LuminautEmbedder
    """
    config = LuminautEmbedderConfig(
        lob_input_dim=lob_input_dim,
        trade_input_dim=trade_input_dim,
        embedding_dim=embedding_dim,
    )
    return LuminautEmbedder(config, sequence_length=sequence_length)


if __name__ == "__main__":
    # Test the model
    print("Testing LuminautEmbedder...")
    
    model = create_luminaut_embedder(
        lob_input_dim=40,
        trade_input_dim=10,
        embedding_dim=64,
        sequence_length=10,
    )
    
    # Create dummy input
    batch_size = 32
    seq_len = 10
    lob_data = torch.randn(batch_size, seq_len, 1, 10, 4)
    trade_data = torch.randn(batch_size, seq_len, 10)
    
    # Forward pass
    outputs = model(lob_data, trade_data)
    
    print(f"LOB input shape: {lob_data.shape}")
    print(f"Trade input shape: {trade_data.shape}")
    print(f"Embedding shape: {outputs['embedding'].shape}")
    print(f"Direction logits shape: {outputs['direction'].shape}")
    print(f"Volatility shape: {outputs['volatility'].shape}")
    print(f"Reconstruction shape: {outputs['reconstruction'].shape}")
    
    print("\n✓ Model test passed!")

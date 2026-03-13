"""
Luminaut Phase 2: Embedding Research Module

This module contains deep learning models and training pipelines for
learning market state embeddings from high-frequency trading data.
"""

from luminaut.phase2_embedding_research.models.autoencoder import (
    Autoencoder,
    AutoencoderConfig,
)
from luminaut.phase2_embedding_research.models.luminaut_embedder import (
    LuminautEmbedder,
    LuminautEmbedderConfig,
)
from luminaut.phase2_embedding_research.data.dataset import (
    MarketDataset,
    MarketDataModule,
)
from luminaut.phase2_embedding_research.trainers.trainer import TrainingPipeline

__all__ = [
    "Autoencoder",
    "AutoencoderConfig",
    "LuminautEmbedder",
    "LuminautEmbedderConfig",
    "MarketDataset",
    "MarketDataModule",
    "TrainingPipeline",
]

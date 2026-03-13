"""
Models package for Phase 2 embedding research.
"""

from luminaut.phase2_embedding_research.models.autoencoder import (
    Autoencoder,
    AutoencoderConfig,
    create_baseline_autoencoder,
)

__all__ = [
    "Autoencoder",
    "AutoencoderConfig",
    "create_baseline_autoencoder",
]

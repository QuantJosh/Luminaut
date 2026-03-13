"""
Trainers package for Phase 2 embedding research.
"""

from luminaut.phase2_embedding_research.trainers.trainer import (
    TrainingPipeline,
    train_autoencoder,
)
from luminaut.phase2_embedding_research.trainers.multi_task_trainer import (
    MultiTaskTrainingPipeline,
    train_luminaut_embedder,
)

__all__ = [
    "TrainingPipeline",
    "train_autoencoder",
    "MultiTaskTrainingPipeline",
    "train_luminaut_embedder",
]

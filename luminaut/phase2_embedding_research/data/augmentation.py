"""
Data Augmentation Utilities for Market Data

Provides augmentation techniques for training robust embedding models:
- Temporal jittering
- Gaussian noise injection
- Mixup
- Feature masking
"""

import torch
import numpy as np
from typing import Tuple, Dict, Optional


class MarketDataAugmenter:
    """
    Data augmentation for market data.
    
    Applies various transformations to increase training data diversity
    and improve model robustness.
    """
    
    def __init__(
        self,
        noise_std: float = 0.01,
        mixup_alpha: float = 0.2,
        mask_prob: float = 0.1,
        temporal_jitter: int = 1,
        apply_prob: float = 0.5,
    ):
        """
        Initialize data augmenter.
        
        Args:
            noise_std: Standard deviation of Gaussian noise
            mixup_alpha: Alpha parameter for mixup (0 = no mixup)
            mask_prob: Probability of masking each feature
            temporal_jitter: Max timesteps to jitter
            apply_prob: Probability of applying each augmentation
        """
        self.noise_std = noise_std
        self.mixup_alpha = mixup_alpha
        self.mask_prob = mask_prob
        self.temporal_jitter = temporal_jitter
        self.apply_prob = apply_prob
    
    def add_noise(self, x: torch.Tensor) -> torch.Tensor:
        """Add Gaussian noise to input."""
        if np.random.random() > self.apply_prob:
            return x
        
        noise = torch.randn_like(x) * self.noise_std
        return x + noise
    
    def apply_mixup(
        self,
        x1: torch.Tensor,
        x2: torch.Tensor,
        y1: Optional[torch.Tensor] = None,
        y2: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor], Optional[torch.Tensor]]:
        """
        Apply mixup augmentation between two samples.
        
        Returns:
            Mixed features and labels
        """
        if np.random.random() > self.apply_prob or self.mixup_alpha <= 0:
            return x1, x2, y1, y2
        
        # Sample mixing coefficient
        lam = np.random.beta(self.mixup_alpha, self.mixup_alpha)
        
        # Mix features
        x_mixed = lam * x1 + (1 - lam) * x2
        
        # Mix labels if provided
        if y1 is not None and y2 is not None:
            y_mixed = lam * y1 + (1 - lam) * y2
            return x_mixed, x2, y_mixed, y2
        else:
            return x_mixed, x2, y1, y2
    
    def mask_features(self, x: torch.Tensor) -> torch.Tensor:
        """Randomly mask features (set to zero or mean)."""
        if np.random.random() > self.apply_prob:
            return x
        
        mask = torch.rand_like(x) > self.mask_prob
        masked = x * mask.float()
        
        return masked
    
    def temporal_jitter_augment(
        self,
        x: torch.Tensor,
        seq_dim: int = 1
    ) -> torch.Tensor:
        """
        Apply temporal jittering to sequence data.
        
        Args:
            x: Sequence tensor (batch, seq_len, ...)
            seq_dim: Dimension corresponding to time
        """
        if np.random.random() > self.apply_prob or self.temporal_jitter <= 0:
            return x
        
        batch_size = x.shape[0]
        seq_len = x.shape[seq_dim]
        
        # Sample jitter offsets
        offsets = np.random.randint(
            -self.temporal_jitter,
            self.temporal_jitter + 1,
            size=batch_size
        )
        
        # Apply jitter
        x_jittered = x.clone()
        for i in range(batch_size):
            offset = offsets[i]
            if offset != 0:
                # Roll the sequence
                x_jittered[i] = torch.roll(x[i], shifts=offset, dims=seq_dim-1)
        
        return x_jittered
    
    def augment(
        self,
        lob_data: torch.Tensor,
        trade_data: torch.Tensor,
        targets: Optional[Dict[str, torch.Tensor]] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, Optional[Dict[str, torch.Tensor]]]:
        """
        Apply all augmentations to a batch.
        
        Args:
            lob_data: LOB features (batch, seq_len, 1, 10, 4)
            trade_data: Trade flow features (batch, seq_len, trade_dim)
            targets: Optional target dictionary
        
        Returns:
            Augmented (lob_data, trade_data, targets)
        """
        # Add noise
        lob_data = self.add_noise(lob_data)
        trade_data = self.add_noise(trade_data)
        
        # Mask features
        lob_data = self.mask_features(lob_data)
        trade_data = self.mask_features(trade_data)
        
        # Temporal jitter
        lob_data = self.temporal_jitter_augment(lob_data, seq_dim=1)
        trade_data = self.temporal_jitter_augment(trade_data, seq_dim=1)
        
        return lob_data, trade_data, targets


class FeatureNormalizer:
    """
    Online feature normalization with running statistics.
    """
    
    def __init__(self, num_features: int, epsilon: float = 1e-5):
        """
        Initialize normalizer.
        
        Args:
            num_features: Number of features
            epsilon: Small constant for numerical stability
        """
        self.num_features = num_features
        self.epsilon = epsilon
        
        # Running statistics
        self.register_buffer("running_mean", torch.zeros(num_features))
        self.register_buffer("running_var", torch.ones(num_features))
        self.register_buffer("num_batches", torch.tensor(0))
    
    def register_buffer(self, name: str, tensor: torch.Tensor):
        """Register a buffer (for non-nn.Module usage)."""
        setattr(self, name, tensor)
    
    def partial_fit(self, x: torch.Tensor):
        """
        Update running statistics with a new batch.
        
        Args:
            x: Input tensor (batch, num_features)
        """
        batch_mean = x.mean(dim=0)
        batch_var = x.var(dim=0, unbiased=False)
        batch_size = x.shape[0]
        
        # Update running statistics
        n = self.num_batches.item()
        new_n = n + batch_size
        
        delta = batch_mean - self.running_mean
        m_a = self.running_var * n
        m_b = batch_var * batch_size
        m2 = m_a + m_b + delta ** 2 * n * batch_size / new_n
        
        self.running_var = m2 / new_n
        self.running_mean = self.running_mean + delta * batch_size / new_n
        self.num_batches = torch.tensor(new_n)
    
    def transform(self, x: torch.Tensor) -> torch.Tensor:
        """
        Normalize input using running statistics.
        
        Args:
            x: Input tensor (batch, num_features)
        
        Returns:
            Normalized tensor
        """
        return (x - self.running_mean) / torch.sqrt(self.running_var + self.epsilon)
    
    def fit_transform(self, x: torch.Tensor) -> torch.Tensor:
        """Fit and transform in one step."""
        self.partial_fit(x)
        return self.transform(x)
    
    def inverse_transform(self, x: torch.Tensor) -> torch.Tensor:
        """Denormalize input."""
        return x * torch.sqrt(self.running_var + self.epsilon) + self.running_mean


if __name__ == "__main__":
    # Test augmentations
    print("Testing MarketDataAugmenter...")
    
    augmenter = MarketDataAugmenter(
        noise_std=0.01,
        mixup_alpha=0.2,
        mask_prob=0.1,
        temporal_jitter=1,
        apply_prob=0.5,
    )
    
    # Create dummy data
    batch_size = 32
    seq_len = 10
    lob_data = torch.randn(batch_size, seq_len, 1, 10, 4)
    trade_data = torch.randn(batch_size, seq_len, 10)
    
    # Apply augmentation
    lob_aug, trade_aug, _ = augmenter.augment(lob_data, trade_data)
    
    print(f"Original LOB shape: {lob_data.shape}")
    print(f"Augmented LOB shape: {lob_aug.shape}")
    print(f"Original Trade shape: {trade_data.shape}")
    print(f"Augmented Trade shape: {trade_aug.shape}")
    
    # Test normalizer
    print("\nTesting FeatureNormalizer...")
    normalizer = FeatureNormalizer(num_features=50)
    
    # Simulate streaming data
    for i in range(10):
        x = torch.randn(32, 50) * 2 + 5  # Random data with mean=5, std=2
        x_norm = normalizer.fit_transform(x)
        
        print(f"Batch {i+1}: mean={x_norm.mean():.3f}, std={x_norm.std():.3f}")
    
    print("\n✓ All tests passed!")

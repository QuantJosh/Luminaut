"""
Data loading utilities for Phase 2 embedding training.

This module provides dataset and dataloader classes for loading
market data from Parquet files generated in Phase 1.
"""

import torch
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import pyarrow.parquet as pq


class MarketDataset(Dataset):
    """
    PyTorch Dataset for loading market data from Parquet files.
    
    This dataset loads feature vectors from Phase 1 data collection
    and provides them for training embedding models.
    """
    
    def __init__(
        self,
        data_dir: str,
        feature_columns: Optional[List[str]] = None,
        normalize: bool = True,
        sequence_length: int = 1,
    ):
        """
        Initialize the dataset.
        
        Args:
            data_dir: Directory containing Parquet files
            feature_columns: List of feature columns to use. If None, auto-detect.
            normalize: Whether to normalize features
            sequence_length: Length of sequences for temporal models
        """
        self.data_dir = Path(data_dir)
        self.feature_columns = feature_columns
        self.normalize = normalize
        self.sequence_length = sequence_length
        
        # Load and preprocess data
        self.data = self._load_data()
        self.feature_stats = self._compute_stats()
        
        if self.normalize:
            self.data = self._normalize_data()
    
    def _load_data(self) -> pd.DataFrame:
        """Load all Parquet files from the data directory."""
        parquet_files = list(self.data_dir.glob("*.parquet"))
        csv_files = list(self.data_dir.glob("features_*.csv"))
        
        if not parquet_files and not csv_files:
            raise FileNotFoundError(
                f"No Parquet or CSV files found in {self.data_dir}"
            )
        
        dfs = []
        
        # Load Parquet files
        for file in parquet_files:
            try:
                df = pd.read_parquet(file)
                dfs.append(df)
            except Exception as e:
                print(f"Warning: Could not read {file}: {e}")
        
        # Load CSV files
        for file in csv_files:
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except Exception as e:
                print(f"Warning: Could not read {file}: {e}")
        
        if not dfs:
            raise ValueError("No valid data files found")
        
        combined = pd.concat(dfs, ignore_index=True)
        print(f"Loaded {len(combined)} samples from {len(parquet_files) + len(csv_files)} files")
        
        return combined
    
    def _compute_stats(self) -> Dict[str, Tuple[float, float]]:
        """Compute normalization statistics."""
        stats = {}
        
        if self.feature_columns:
            columns = self.feature_columns
        else:
            # Auto-detect numeric columns
            columns = self.data.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            mean = self.data[col].mean()
            std = self.data[col].std()
            if std == 0:
                std = 1.0
            stats[col] = (mean, std)
        
        return stats
    
    def _normalize_data(self) -> pd.DataFrame:
        """Normalize features using z-score normalization."""
        data = self.data.copy()
        
        for col, (mean, std) in self.feature_stats.items():
            if col in data.columns:
                data[col] = (data[col] - mean) / std
        
        return data
    
    def __len__(self) -> int:
        """Return the number of samples."""
        return len(self.data) - self.sequence_length + 1
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Get a sample from the dataset.
        
        Args:
            idx: Index of the sample
        
        Returns:
            Tuple of (features, target)
            For autoencoder: target is the same as input (reconstruction)
        """
        if self.sequence_length == 1:
            # Single sample
            sample = self.data.iloc[idx]
            
            if self.feature_columns:
                features = sample[self.feature_columns].values.astype(np.float32)
            else:
                features = sample.select_dtypes(include=[np.number]).values.astype(np.float32)
            
            # Handle NaN values
            features = np.nan_to_num(features, nan=0.0)
            
            return torch.tensor(features), torch.tensor(features)
        else:
            # Sequence of samples
            indices = range(idx, idx + self.sequence_length)
            sequence = self.data.iloc[indices]
            
            if self.feature_columns:
                features = sequence[self.feature_columns].values.astype(np.float32)
            else:
                features = sequence.select_dtypes(include=[np.number]).values.astype(np.float32)
            
            features = np.nan_to_num(features, nan=0.0)
            
            return torch.tensor(features), torch.tensor(features)
    
    def get_feature_dim(self) -> int:
        """Get the dimension of feature vectors."""
        if self.feature_columns:
            return len(self.feature_columns)
        else:
            return self.data.select_dtypes(include=[np.number]).shape[1]
    
    def get_stats(self) -> Dict[str, Tuple[float, float]]:
        """Get normalization statistics."""
        return self.feature_stats


class MarketDataModule:
    """
    PyTorch Lightning-style data module for market data.
    
    Provides train/val/test splits and dataloaders.
    """
    
    def __init__(
        self,
        data_dir: str,
        feature_columns: Optional[List[str]] = None,
        batch_size: int = 256,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        num_workers: int = 0,
    ):
        """
        Initialize the data module.
        
        Args:
            data_dir: Directory containing data files
            feature_columns: List of feature columns to use
            batch_size: Batch size for training
            train_ratio: Ratio of data for training
            val_ratio: Ratio of data for validation
            num_workers: Number of workers for data loading
        """
        self.data_dir = data_dir
        self.feature_columns = feature_columns
        self.batch_size = batch_size
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.num_workers = num_workers
        
        self.train_dataset: Optional[MarketDataset] = None
        self.val_dataset: Optional[MarketDataset] = None
        self.test_dataset: Optional[MarketDataset] = None
    
    def setup(self, stage: Optional[str] = None):
        """
        Set up datasets.
        
        Args:
            stage: Fit, validate, or test
        """
        # Load full dataset
        full_dataset = MarketDataset(
            self.data_dir,
            self.feature_columns,
            normalize=True,
        )
        
        # Calculate split indices
        total_size = len(full_dataset)
        train_size = int(self.train_ratio * total_size)
        val_size = int(self.val_ratio * total_size)
        test_size = total_size - train_size - val_size
        
        # Split datasets
        self.train_dataset, self.val_dataset, self.test_dataset = (
            torch.utils.data.random_split(
                full_dataset,
                [train_size, val_size, test_size],
                generator=torch.Generator().manual_seed(42)
            )
        )
        
        print(f"Dataset splits:")
        print(f"  Train: {len(self.train_dataset)} samples")
        print(f"  Val: {len(self.val_dataset)} samples")
        print(f"  Test: {len(self.test_dataset)} samples")
    
    def train_dataloader(self) -> DataLoader:
        """Get training dataloader."""
        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            pin_memory=True,
        )
    
    def val_dataloader(self) -> DataLoader:
        """Get validation dataloader."""
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True,
        )
    
    def test_dataloader(self) -> DataLoader:
        """Get test dataloader."""
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=True,
        )
    
    def get_feature_dim(self) -> int:
        """Get feature dimension."""
        if self.train_dataset:
            return self.train_dataset.dataset.get_feature_dim()
        else:
            # Create temporary dataset to get dimension
            temp = MarketDataset(self.data_dir, self.feature_columns)
            return temp.get_feature_dim()


if __name__ == "__main__":
    # Test the dataset
    print("Testing MarketDataset...")
    
    # Create dummy data for testing
    test_dir = Path("data/test_features")
    test_dir.mkdir(exist_ok=True)
    
    # Generate sample data
    n_samples = 1000
    n_features = 50
    data = pd.DataFrame(np.random.randn(n_samples, n_features))
    data.columns = [f"feature_{i}" for i in range(n_features)]
    data.to_csv(test_dir / "features_test.csv", index=False)
    
    # Load dataset
    dataset = MarketDataset(str(test_dir))
    print(f"Dataset size: {len(dataset)}")
    print(f"Feature dimension: {dataset.get_feature_dim()}")
    
    # Get a sample
    x, y = dataset[0]
    print(f"Sample shape: {x.shape}")
    
    # Test data module
    print("\nTesting MarketDataModule...")
    data_module = MarketDataModule(str(test_dir), batch_size=32)
    data_module.setup()
    
    train_loader = data_module.train_dataloader()
    for batch_x, batch_y in train_loader:
        print(f"Batch shape: {batch_x.shape}")
        break
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    print("\nTest completed successfully!")

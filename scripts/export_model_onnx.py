"""
Phase 2: Export Model to ONNX

This script exports trained PyTorch models to ONNX format for
production deployment with onnxruntime.

Usage:
    python scripts/export_model_onnx.py --checkpoint checkpoints/luminaut_embedder/best_model.pt --output models/production_embedder.onnx
"""

import argparse
import sys
import torch
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_checkpoint(checkpoint_path: str):
    """Load model from checkpoint."""
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    
    # Determine model type from config or state dict
    config = checkpoint.get("config", {})
    state_dict = checkpoint["model_state_dict"]
    
    # Try to infer model type
    if "lob_encoder.conv1.weight" in state_dict:
        # LuminautEmbedder
        from luminaut.phase2_embedding_research.models.luminaut_embedder import (
            LuminautEmbedder,
            LuminautEmbedderConfig,
        )
        
        model_config = LuminautEmbedderConfig(**config) if config else LuminautEmbedderConfig()
        model = LuminautEmbedder(model_config)
        print("Loaded LuminautEmbedder")
    else:
        # Baseline Autoencoder
        from luminaut.phase2_embedding_research.models.autoencoder import (
            Autoencoder,
            AutoencoderConfig,
        )
        
        if not config:
            # Infer from state dict
            input_dim = state_dict["encoder.0.weight"].shape[1]
            latent_dim = state_dict["encoder.-2.weight"].shape[0]
            config = AutoencoderConfig(input_dim=input_dim, latent_dim=latent_dim)
        else:
            config = AutoencoderConfig(**config)
        
        model = Autoencoder(config)
        print("Loaded Autoencoder")
    
    model.load_state_dict(state_dict)
    model.eval()
    
    return model, checkpoint


def export_autoencoder_onnx(
    model,
    output_path: str,
    input_dim: int,
    opset_version: int = 11,
):
    """Export autoencoder to ONNX."""
    from luminaut.phase2_embedding_research.models.autoencoder import Autoencoder
    
    model.eval()
    
    # Create dummy input
    dummy_input = torch.randn(1, input_dim)
    
    # Export
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["latent", "reconstruction"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "latent": {0: "batch_size"},
            "reconstruction": {0: "batch_size"},
        },
    )
    
    print(f"Exported autoencoder to {output_path}")


def export_luminaut_embedder_onnx(
    model,
    output_path: str,
    sequence_length: int = 10,
    opset_version: int = 11,
):
    """Export LuminautEmbedder to ONNX."""
    from luminaut.phase2_embedding_research.models.luminaut_embedder import LuminautEmbedder
    
    model.eval()
    
    # Create dummy input
    batch_size = 1
    lob_input = torch.randn(batch_size, sequence_length, 1, 10, 4)
    trade_input = torch.randn(batch_size, sequence_length, 10)
    
    # Export
    torch.onnx.export(
        model,
        (lob_input, trade_input),
        output_path,
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["lob_input", "trade_input"],
        output_names=["embedding", "direction", "volatility", "reconstruction"],
        dynamic_axes={
            "lob_input": {0: "batch_size", 1: "sequence_length"},
            "trade_input": {0: "batch_size", 1: "sequence_length"},
            "embedding": {0: "batch_size"},
            "direction": {0: "batch_size"},
            "volatility": {0: "batch_size"},
            "reconstruction": {0: "batch_size"},
        },
    )
    
    print(f"Exported LuminautEmbedder to {output_path}")


def verify_onnx_model(onnx_path: str):
    """Verify ONNX model can be loaded and run."""
    try:
        import onnx
        import onnxruntime as ort
        
        # Load and check model
        onnx_model = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model)
        print("✓ ONNX model validation passed")
        
        # Create inference session
        session = ort.InferenceSession(onnx_path)
        
        # Get input/output info
        print(f"\nModel inputs:")
        for inp in session.get_inputs():
            print(f"  {inp.name}: {inp.shape} ({inp.type})")
        
        print(f"\nModel outputs:")
        for out in session.get_outputs():
            print(f"  {out.name}: {out.shape} ({out.type})")
        
        # Test inference
        if len(session.get_inputs()) == 1:
            # Autoencoder
            input_name = session.get_inputs()[0].name
            test_input = torch.randn(1, 50).numpy()
            outputs = session.run(None, {input_name: test_input})
            print(f"\n✓ Test inference successful")
            print(f"  Output shapes: {[o.shape for o in outputs]}")
        else:
            # LuminautEmbedder
            input_names = [inp.name for inp in session.get_inputs()]
            test_lob = torch.randn(1, 10, 1, 10, 4).numpy()
            test_trade = torch.randn(1, 10, 10).numpy()
            outputs = session.run(None, dict(zip(input_names, [test_lob, test_trade])))
            print(f"\n✓ Test inference successful")
            print(f"  Output shapes: {[o.shape for o in outputs]}")
        
        return True
        
    except ImportError:
        print("Warning: onnx or onnxruntime not installed. Skipping verification.")
        print("Install with: pip install onnx onnxruntime")
        return False
    except Exception as e:
        print(f"Warning: ONNX verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Export trained model to ONNX format"
    )
    
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to model checkpoint (.pt file)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="models/production_embedder.onnx",
        help="Output path for ONNX model"
    )
    
    parser.add_argument(
        "--opset",
        type=int,
        default=11,
        help="ONNX opset version"
    )
    
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify exported model"
    )
    
    args = parser.parse_args()
    
    # Check checkpoint exists
    checkpoint_path = Path(args.checkpoint)
    if not checkpoint_path.exists():
        print(f"Error: Checkpoint not found: {checkpoint_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Luminaut Phase 2: ONNX Model Export")
    print("=" * 60)
    
    # Load model
    print(f"\nLoading model from {checkpoint_path}...")
    model, checkpoint = load_checkpoint(str(checkpoint_path))
    
    # Create output directory
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Export model
    print(f"\nExporting to ONNX (opset {args.opset})...")
    
    from luminaut.phase2_embedding_research.models.autoencoder import Autoencoder
    from luminaut.phase2_embedding_research.models.luminaut_embedder import LuminautEmbedder
    
    if isinstance(model, Autoencoder):
        input_dim = model.config.input_dim
        export_autoencoder_onnx(model, str(output_path), input_dim, args.opset)
    elif isinstance(model, LuminautEmbedder):
        export_luminaut_embedder_onnx(model, str(output_path), opset_version=args.opset)
    else:
        print(f"Error: Unknown model type: {type(model)}")
        sys.exit(1)
    
    # Verify
    if args.verify:
        print("\n" + "=" * 60)
        print("Verifying ONNX model...")
        print("=" * 60)
        verify_onnx_model(str(output_path))
    
    # Save model info
    info_path = output_path.with_suffix(".json")
    import json
    model_info = {
        "checkpoint": str(checkpoint_path),
        "onnx_path": str(output_path),
        "model_type": model.__class__.__name__,
        "embedding_dim": model.get_embedding_dim() if hasattr(model, "get_embedding_dim") else "N/A",
        "export_timestamp": str(Path.cwd()),
    }
    
    with open(info_path, "w") as f:
        json.dump(model_info, f, indent=2)
    
    print(f"\nModel info saved to {info_path}")
    
    print("\n" + "=" * 60)
    print("Export completed successfully!")
    print("=" * 60)
    print(f"\nONNX model: {output_path}")
    print(f"Model info: {info_path}")
    
    # Usage example
    print("\n" + "=" * 60)
    print("Usage in production:")
    print("=" * 60)
    print("""
import onnxruntime as ort
import numpy as np

# Load model
session = ort.InferenceSession("models/production_embedder.onnx")

# Prepare input
lob_input = np.random.randn(1, 10, 1, 10, 4).astype(np.float32)
trade_input = np.random.randn(1, 10, 10).astype(np.float32)

# Run inference
outputs = session.run(None, {
    "lob_input": lob_input,
    "trade_input": trade_input
})

embedding = outputs[0]
print(f"Embedding shape: {embedding.shape}")
    """)


if __name__ == "__main__":
    main()

"""
Luminaut环境验证脚本
检查所有必要的依赖是否已正确安装
"""

import sys

def check_imports():
    """检查关键依赖的导入"""
    print("=" * 60)
    print("🔍 Luminaut 环境验证")
    print("=" * 60)
    
    checks = []
    
    # 检查NautilusTrader
    try:
        import nautilus_trader
        version = nautilus_trader.__version__
        print(f"✅ NautilusTrader: {version}")
        checks.append(True)
    except ImportError as e:
        print(f"❌ NautilusTrader 导入失败: {e}")
        checks.append(False)
    
    # 检查Pandas
    try:
        import pandas
        version = pandas.__version__
        print(f"✅ Pandas: {version}")
        checks.append(True)
    except ImportError as e:
        print(f"❌ Pandas 导入失败: {e}")
        checks.append(False)
    
    # 检查NumPy
    try:
        import numpy
        version = numpy.__version__
        print(f"✅ NumPy: {version}")
        checks.append(True)
    except ImportError as e:
        print(f"❌ NumPy 导入失败: {e}")
        checks.append(False)
    
    # 检查PyTorch
    try:
        import torch
        version = torch.__version__
        print(f"✅ PyTorch: {version}")
        checks.append(True)
    except ImportError as e:
        print(f"❌ PyTorch 导入失败: {e}")
        checks.append(False)
    
    # 检查ONNX
    try:
        import onnx
        import onnxruntime as ort
        print(f"✅ ONNX: {onnx.__version__}")
        print(f"✅ ONNXRuntime: {ort.__version__}")
        checks.append(True)
    except ImportError as e:
        print(f"❌ ONNX/ONNXRuntime 导入失败: {e}")
        checks.append(False)
    
    # 检查Plotly
    try:
        import plotly
        version = plotly.__version__
        print(f"✅ Plotly: {version}")
        checks.append(True)
    except ImportError as e:
        print(f"❌ Plotly 导入失败: {e}")
        checks.append(False)
    
    # 检查Weights & Biases
    try:
        import wandb
        version = wandb.__version__
        print(f"✅ Weights & Biases: {version}")
        checks.append(True)
    except ImportError as e:
        print(f"⚠️  Weights & Biases 导入失败 (可选): {e}")
        # W&B是可选的，不算失败
    
    print("=" * 60)
    
    if all(checks):
        print("🎉 所有关键依赖已正确安装！")
        print("✅ 环境验证通过 - 可以开始数据采集测试")
        return 0
    else:
        print("❌ 部分依赖安装失败，请检查错误信息")
        return 1


def check_project_structure():
    """检查项目目录结构"""
    import os
    from pathlib import Path
    
    print("\n" + "=" * 60)
    print("📁 项目结构检查")
    print("=" * 60)
    
    required_dirs = [
        "luminaut/phase1_data_collection/actors",
        "luminaut/phase2_embedding_research",
        "luminaut/phase3_trading_deployment",
        "data/catalog",
        "scripts",
        "tests",
        "logs",
        "docs",
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        full_path = Path(dir_path)
        if full_path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} (缺失)")
            all_exist = False
    
    print("=" * 60)
    return all_exist


def check_code_files():
    """检查关键代码文件"""
    from pathlib import Path
    
    print("\n" + "=" * 60)
    print("📝 核心代码文件检查")
    print("=" * 60)
    
    required_files = [
        "luminaut/phase1_data_collection/actors/feature_builder.py",
        "scripts/run_phase1_collection.py",
        "requirements.txt",
        "README.md",
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists():
            size = full_path.stat().st_size
            print(f"✅ {file_path} ({size:,} bytes)")
        else:
            print(f"❌ {file_path} (缺失)")
            all_exist = False
    
    print("=" * 60)
    return all_exist


if __name__ == "__main__":
    print("\n")
    
    # 检查依赖导入
    deps_ok = check_imports() == 0
    
    # 检查项目结构
    struct_ok = check_project_structure()
    
    # 检查代码文件
    files_ok = check_code_files()
    
    print("\n" + "=" * 60)
    print("📊 验证总结")
    print("=" * 60)
    print(f"依赖安装: {'✅ 通过' if deps_ok else '❌ 失败'}")
    print(f"项目结构: {'✅ 完整' if struct_ok else '❌ 不完整'}")
    print(f"核心文件: {'✅ 存在' if files_ok else '❌ 缺失'}")
    print("=" * 60)
    
    if deps_ok and struct_ok and files_ok:
        print("\n🚀 环境验证完成！可以运行:")
        print("   python scripts/run_phase1_collection.py --duration-minutes 5")
        print("\n")
        sys.exit(0)
    else:
        print("\n⚠️  环境验证未通过，请解决上述问题")
        sys.exit(1)

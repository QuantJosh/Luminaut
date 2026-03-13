# Luminaut环境激活脚本
# 用法: .\activate_env.ps1

Write-Host "🚀 激活Luminaut虚拟环境..." -ForegroundColor Green
.\.venv\Scripts\Activate.ps1

Write-Host "✅ 虚拟环境已激活" -ForegroundColor Green
Write-Host ""
Write-Host "可用命令:" -ForegroundColor Yellow
Write-Host "  python scripts/run_phase1_collection.py --duration-minutes 5" -ForegroundColor Cyan
Write-Host "  pytest tests/ -v" -ForegroundColor Cyan
Write-Host ""

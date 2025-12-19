# Git setup script for PowerShell

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Git Repository Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: SHL Assessment Recommendation System

- Complete RAG-based recommendation system
- 389 assessments crawled from SHL catalog
- XGBoost re-ranking (56.89% Mean Recall@10)
- FastAPI backend and Streamlit frontend
- All evaluation scripts and experiments"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "1. Add your GitHub remote:" -ForegroundColor Yellow
Write-Host "   git remote add origin <YOUR_GITHUB_REPO_URL>" -ForegroundColor White
Write-Host ""
Write-Host "2. Push to GitHub:" -ForegroundColor Yellow
Write-Host "   git branch -M main" -ForegroundColor White
Write-Host "   git push -u origin main" -ForegroundColor White
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green


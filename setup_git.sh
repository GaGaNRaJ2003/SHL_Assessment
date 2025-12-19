#!/bin/bash
# Git setup script for Windows (use Git Bash) or Linux/Mac

echo "=========================================="
echo "Git Repository Setup"
echo "=========================================="

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

echo ""
echo "=========================================="
echo "Next steps:"
echo "=========================================="
echo "1. Add your GitHub remote:"
echo "   git remote add origin <YOUR_GITHUB_REPO_URL>"
echo ""
echo "2. Push to GitHub:"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "=========================================="


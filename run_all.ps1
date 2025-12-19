# SHL Assessment Recommender - Complete Setup and Run Script (PowerShell)
# This script sets up the environment and runs the entire pipeline

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SHL Assessment Recommender - Setup & Run" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Green
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Green
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Green
pip install -r requirements.txt --quiet

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Warning: .env file not found!" -ForegroundColor Yellow
    Write-Host "Please create .env file with: GEMINI_API_KEY=your_key_here"
    Write-Host ""
    $response = Read-Host "Do you want to continue anyway? (y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        exit 1
    }
}

# Create data directory if it doesn't exist
if (-not (Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# Step 1: Crawl SHL catalog
Write-Host ""
Write-Host "Step 1: Crawling SHL catalog..." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
python src/crawler.py

# Check if assessments.json was created
if (-not (Test-Path "data/assessments.json")) {
    Write-Host "Error: assessments.json not created!" -ForegroundColor Red
    exit 1
}

# Check assessment count
$assessmentJson = Get-Content "data/assessments.json" | ConvertFrom-Json
$assessmentCount = $assessmentJson.Count
Write-Host ""
Write-Host "Found $assessmentCount assessments" -ForegroundColor Green

if ($assessmentCount -lt 377) {
    Write-Host "Warning: Only $assessmentCount assessments found (target: 377+)" -ForegroundColor Yellow
    Write-Host "Note: The system will work with $assessmentCount assessments for testing." -ForegroundColor Yellow
    Write-Host "You can improve the crawler later to reach 377+ assessments." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Continuing with current data..." -ForegroundColor Green
    # Auto-continue for now - can be changed to prompt if needed
    # $response = Read-Host "Continue anyway? (y/n)"
    # if ($response -ne "y" -and $response -ne "Y") {
    #     exit 1
    # }
}

# Step 2: Generate embeddings
Write-Host ""
Write-Host "Step 2: Generating embeddings..." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
python src/embeddings.py

# Check if vector DB was created
if (-not (Test-Path "data/faiss_index.bin")) {
    Write-Host "Error: Vector database not created!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Start the API:"
Write-Host "   uvicorn src.api:app --reload"
Write-Host ""
Write-Host "2. In another terminal, start the frontend:"
Write-Host "   .\venv\Scripts\Activate.ps1"
Write-Host "   streamlit run app/streamlit_app.py"
Write-Host ""
Write-Host "3. Or run evaluation:"
Write-Host "   cd notebooks"
Write-Host "   python evaluate.py"
Write-Host ""


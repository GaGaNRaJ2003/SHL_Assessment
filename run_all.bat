@echo off
REM SHL Assessment Recommender - Complete Setup and Run Script (Windows Batch)
REM This script sets up the environment and runs the entire pipeline

echo ==========================================
echo SHL Assessment Recommender - Setup ^& Run
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt --quiet

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found!
    echo Please create .env file with: GEMINI_API_KEY=your_key_here
    echo.
    set /p response="Do you want to continue anyway? (y/n): "
    if /i not "%response%"=="y" exit /b 1
)

REM Create data directory if it doesn't exist
if not exist "data" mkdir data

REM Step 1: Crawl SHL catalog
echo.
echo Step 1: Crawling SHL catalog...
echo ==========================================
python src/crawler.py

REM Check if assessments.json was created
if not exist "data\assessments.json" (
    echo Error: assessments.json not created!
    exit /b 1
)

REM Step 2: Generate embeddings
echo.
echo Step 2: Generating embeddings...
echo ==========================================
python src/embeddings.py

REM Check if vector DB was created
if not exist "data\faiss_index.bin" (
    echo Error: Vector database not created!
    exit /b 1
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Start the API:
echo    uvicorn src.api:app --reload
echo.
echo 2. In another terminal, start the frontend:
echo    venv\Scripts\activate.bat
echo    streamlit run app/streamlit_app.py
echo.
echo 3. Or run evaluation:
echo    cd notebooks
echo    python evaluate.py
echo.

pause



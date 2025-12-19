#!/bin/bash

# SHL Assessment Recommender - Complete Setup and Run Script
# This script sets up the environment and runs the entire pipeline

set -e  # Exit on error

echo "=========================================="
echo "SHL Assessment Recommender - Setup & Run"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt --quiet

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo "Please create .env file with: GEMINI_API_KEY=your_key_here"
    echo ""
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create data directory if it doesn't exist
mkdir -p data

# Step 1: Crawl SHL catalog
echo ""
echo -e "${GREEN}Step 1: Crawling SHL catalog...${NC}"
echo "=========================================="
python src/crawler.py

# Check if assessments.json was created
if [ ! -f "data/assessments.json" ]; then
    echo -e "${RED}Error: assessments.json not created!${NC}"
    exit 1
fi

# Check assessment count
ASSESSMENT_COUNT=$(python -c "import json; print(len(json.load(open('data/assessments.json'))))")
echo ""
echo -e "${GREEN}Found $ASSESSMENT_COUNT assessments${NC}"

if [ "$ASSESSMENT_COUNT" -lt 377 ]; then
    echo -e "${YELLOW}Warning: Only $ASSESSMENT_COUNT assessments found (target: 377+)${NC}"
    echo "You may need to improve the crawler or use Selenium for JavaScript content"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 2: Generate embeddings
echo ""
echo -e "${GREEN}Step 2: Generating embeddings...${NC}"
echo "=========================================="
python src/embeddings.py

# Check if vector DB was created
if [ ! -f "data/faiss_index.bin" ]; then
    echo -e "${RED}Error: Vector database not created!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Start the API:"
echo "   uvicorn src.api:app --reload"
echo ""
echo "2. In another terminal, start the frontend:"
echo "   source venv/bin/activate"
echo "   streamlit run app/streamlit_app.py"
echo ""
echo "3. Or run evaluation:"
echo "   cd notebooks"
echo "   python evaluate.py"
echo ""



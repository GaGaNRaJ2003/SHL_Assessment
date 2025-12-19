# SHL Assessment Recommendation System

An intelligent recommendation system that suggests relevant SHL assessments based on natural language queries or job descriptions. Built for the SHL AI Research Intern assessment.

## Overview

This system uses Retrieval-Augmented Generation (RAG) to recommend SHL Individual Test Solutions. Given a job description or natural language query, it returns 5-10 most relevant assessments with metadata including duration, test type, and support features.

## Architecture

```
User Query → Embedding → Vector Search (Top-20) → LLM Re-Ranking → Top 10 Recommendations
```

### Components

1. **Crawler** (`src/crawler.py`): Scrapes SHL product catalog to extract assessment metadata
2. **Embeddings** (`src/embeddings.py`): Generates embeddings using Gemini API and stores in ChromaDB
3. **Retriever** (`src/retriever.py`): Performs semantic search using vector similarity
4. **Reranker** (`src/reranker.py`): Uses Gemini LLM to re-rank candidates by relevance
5. **API** (`src/api.py`): FastAPI backend exposing `/health` and `/recommend` endpoints
6. **Frontend** (`app/streamlit_app.py`): Streamlit web interface for interactive queries

## Setup

### Prerequisites

- Python 3.8+
- Gemini API key ([Get one here](https://ai.google.dev/gemini-api/docs/pricing))

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd shl-assessment-recommender
```

2. Create and activate virtual environment (recommended):
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Copy .env.example to .env
# Windows:
copy .env.example .env
# Linux/Mac:
cp .env.example .env

# Edit .env and add your Gemini API key:
GEMINI_API_KEY=your_api_key_here
```

## Quick Start (Automated)

### Option 1: Run Everything at Once

**Windows (PowerShell):**
```powershell
.\run_all.ps1
```

**Windows (CMD):**
```cmd
run_all.bat
```

**Linux/Mac:**
```bash
chmod +x run_all.sh
./run_all.sh
```

This script will:
1. Create/activate virtual environment
2. Install dependencies
3. Crawl SHL catalog
4. Generate embeddings
5. Set up the vector database

## Usage (Manual Steps)

### Step 1: Crawl SHL Catalog

Extract assessment data from the SHL website:

```bash
python src/crawler.py
```

This will create `data/assessments.json` with all Individual Test Solutions (target: 377+ assessments).

**Note:** You may need to inspect the SHL catalog page structure and adjust the crawler if the HTML structure differs from expectations.

### Step 2: Generate Embeddings

Create embeddings and populate the vector database:

```bash
python src/embeddings.py
```

This will:
- Load assessments from `data/assessments.json`
- Generate embeddings using Gemini `text-embedding-004`
- Store in ChromaDB at `data/chroma_db/`

**Time:** ~5-10 minutes for 377 assessments (due to API rate limiting)

### Step 3: Start the API

```bash
uvicorn src.api:app --reload
```

API will be available at `http://localhost:8000`

- Health check: `GET http://localhost:8000/health`
- Recommendations: `POST http://localhost:8000/recommend` with JSON body `{"query": "your query here"}`

### Step 4: Start the Frontend

In a new terminal:

```bash
streamlit run app/streamlit_app.py
```

Open your browser to `http://localhost:8501`

## API Endpoints

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy"
}
```

### Get Recommendations

```bash
POST /recommend
Content-Type: application/json

{
  "query": "I am hiring for Java developers who can collaborate effectively with business teams."
}
```

Response:
```json
{
  "recommended_assessments": [
    {
      "url": "https://www.shl.com/solutions/products/product-catalog/view/java-8-new/",
      "name": "Java 8 (New)",
      "adaptive_support": "No",
      "description": "Multi-choice test that measures knowledge of Java 8...",
      "duration": 11,
      "remote_support": "Yes",
      "test_type": ["Knowledge & Skills"]
    },
    ...
  ]
}
```

## Evaluation

### Compute Recall@10 on Train Set

Use the provided notebook or script to evaluate performance:

```bash
python notebooks/evaluate.py
```

This computes Mean Recall@10 on the labeled train set.

### Generate Test Predictions

Generate predictions for the unlabeled test set:

```bash
python notebooks/generate_predictions.py
```

This creates `submission/predictions.csv` in the required format.

## Project Structure

```
shl-assessment-recommender/
├── data/
│   ├── assessments.json          # Crawled catalog (generated)
│   ├── chroma_db/                 # Vector database (generated)
│   ├── train.csv                  # Labeled train set
│   └── test.csv                   # Unlabeled test set
├── src/
│   ├── crawler.py                 # Web scraper
│   ├── embeddings.py              # Embedding generation
│   ├── retriever.py               # Vector search
│   ├── reranker.py                # LLM re-ranking
│   ├── api.py                     # FastAPI backend
│   └── utils.py                   # Helper functions
├── app/
│   └── streamlit_app.py           # Web frontend
├── notebooks/
│   └── evaluation.ipynb           # Evaluation scripts
├── submission/
│   └── predictions.csv            # Final predictions (generated)
├── requirements.txt
├── .env                           # Environment variables (create from .env.example)
└── README.md
```

## Key Features

- **Semantic Search**: Uses Gemini embeddings for understanding query intent
- **LLM Re-Ranking**: Gemini 1.5 Flash re-ranks candidates for better relevance
- **Duration Filtering**: Automatically extracts and applies duration constraints
- **URL Support**: Can fetch and parse job descriptions from URLs
- **Test Type Balancing**: Considers multiple test types (Knowledge, Personality, etc.)
- **Error Handling**: Graceful fallbacks if API calls fail

## Limitations & Future Work

- **Crawler**: May need adjustment if SHL catalog HTML structure changes
- **Rate Limiting**: Free-tier Gemini API has rate limits; consider batching
- **Evaluation**: Small train set (10 queries) limits statistical significance
- **Re-ranking**: Could be improved with cross-encoder models
- **Caching**: Add caching for frequently queried assessments

## Troubleshooting

### "Vector database not initialized"
Run `python src/embeddings.py` to populate the vector DB.

### "GEMINI_API_KEY not found"
Create a `.env` file with your API key (see Setup section).

### Crawler finds < 377 assessments
Inspect the SHL catalog page HTML and adjust `src/crawler.py` link extraction logic.

### API timeout errors
Increase timeout in `app/streamlit_app.py` or reduce query length.

## License

This project is created for the SHL AI Research Intern assessment.

## Contact

For questions or issues, please refer to the assessment instructions or contact the evaluation team.


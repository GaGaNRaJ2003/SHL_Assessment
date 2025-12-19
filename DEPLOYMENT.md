# Deployment Guide

## Quick Start

### 1. Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Key

Create `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

### 3. Generate Embeddings

```bash
# First, crawl assessments (if not already done)
python src/crawler.py

# Generate embeddings
python src/embeddings.py
```

### 4. Deploy API

**Option A: Render.com**
1. Create new Web Service
2. Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn src.api:app --host 0.0.0.0 --port $PORT`
5. Add environment variable: `GEMINI_API_KEY`

**Option B: Railway**
1. New Project → Deploy from GitHub
2. Add start command: `uvicorn src.api:app --host 0.0.0.0 --port $PORT`
3. Add environment variable: `GEMINI_API_KEY`

### 5. Deploy Frontend

**Streamlit Cloud:**
1. Go to https://share.streamlit.io
2. Connect GitHub repo
3. Main file: `app/streamlit_app.py`
4. Add environment variable: `API_URL=https://your-api-url.com`

## Environment Variables

- `GEMINI_API_KEY`: Required for embeddings generation
- `API_URL`: Optional, defaults to `http://localhost:8000`

## Local Testing

```bash
# Terminal 1: Start API
uvicorn src.api:app --reload

# Terminal 2: Start Frontend
streamlit run app/streamlit_app.py
```


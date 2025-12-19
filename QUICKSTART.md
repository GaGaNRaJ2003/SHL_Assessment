# Quick Start Guide

## Prerequisites Check

Run the setup verification:
```bash
python check_setup.py
```

## Quick Start (Automated)

Run everything at once:

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

## Step-by-Step Setup (Manual)

### 1. Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure API Key

Create `.env` file:
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```
GEMINI_API_KEY=your_api_key_here
```

Get your API key from: https://ai.google.dev/gemini-api/docs/pricing

### 4. Crawl SHL Catalog

```bash
python src/crawler.py
```

**Expected output:**
- Creates `data/assessments.json`
- Should find 377+ assessments
- Takes ~10-15 minutes (due to rate limiting)

**Troubleshooting:**
- If < 377 assessments found, inspect the catalog page HTML
- Adjust link extraction in `src/crawler.py` if needed

### 5. Generate Embeddings

```bash
python src/embeddings.py
```

**Expected output:**
- Creates `data/chroma_db/` directory
- Generates embeddings for all assessments
- Takes ~5-10 minutes (due to API rate limiting)

### 6. Start the API

```bash
uvicorn src.api:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Test it:
```bash
curl http://localhost:8000/health
```

### 7. Start the Frontend

In a new terminal:
```bash
streamlit run app/streamlit_app.py
```

**Expected output:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

## Testing the System

### Via API (curl)

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"I am hiring for Java developers who can collaborate effectively with business teams.\"}"
```

### Via Frontend

1. Open http://localhost:8501
2. Paste a job description or query
3. Click "Get Recommendations"
4. View results in table and expandable cards

## Evaluation

### Evaluate on Train Set

```bash
cd notebooks
python evaluate.py
```

This computes Mean Recall@10 on the labeled train set.

### Generate Test Predictions

```bash
cd notebooks
python generate_predictions.py
```

This creates `submission/predictions.csv` for submission.

## Common Issues

### "GEMINI_API_KEY not found"
- Ensure `.env` file exists and contains `GEMINI_API_KEY=...`

### "Vector database not initialized"
- Run `python src/embeddings.py` first

### "No assessments found"
- Ensure `data/assessments.json` exists
- Run `python src/crawler.py` if missing

### API timeout
- Increase timeout in `app/streamlit_app.py` (currently 60s)
- Or reduce query length

### Rate limiting errors
- Gemini free tier has rate limits
- Add delays between API calls
- Consider upgrading API tier for production

## Next Steps

1. **Improve Crawler**: Inspect SHL catalog HTML and refine extraction
2. **Tune Re-ranking**: Experiment with different prompts
3. **Add Caching**: Cache frequent queries
4. **Deploy**: Deploy API to cloud (Render, Railway, etc.)
5. **Evaluate**: Run evaluation script and analyze results

## Project Structure

```
shl-assessment-recommender/
├── data/              # Data files (CSV, JSON, vector DB)
├── src/               # Source code
├── app/               # Streamlit frontend
├── notebooks/         # Evaluation scripts
├── submission/        # Final predictions
└── requirements.txt   # Dependencies
```

## Support

Refer to `README.md` for detailed documentation.


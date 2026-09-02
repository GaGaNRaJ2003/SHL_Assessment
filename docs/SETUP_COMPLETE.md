# Setup Complete!

All dependencies have been successfully installed in the virtual environment.

## Next Steps

### 1. Activate Virtual Environment

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 2. Set Up API Key

Create a `.env` file in the project root:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key from: https://ai.google.dev/gemini-api/docs/pricing

### 3. Run the Pipeline

```bash
# Step 1: Crawl SHL catalog
python src/crawler.py

# Step 2: Generate embeddings
python src/embeddings.py

# Step 3: Start API (in one terminal)
uvicorn src.api:app --reload

# Step 4: Start Frontend (in another terminal)
streamlit run app/streamlit_app.py
```

## Important Notes

- **Always activate the virtual environment** before running any Python scripts
- The virtual environment is located in the `venv/` directory
- FAISS is now used instead of ChromaDB (better Windows support)
- Vector database files will be stored in `data/faiss_index.bin` and `data/faiss_metadata.pkl`

## Troubleshooting

If you see "ModuleNotFoundError", make sure:
1. Virtual environment is activated (you should see `(venv)` in your terminal prompt)
2. Dependencies are installed: `pip install -r requirements.txt`



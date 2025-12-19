from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from dotenv import load_dotenv

from src.retriever import get_vector_db
from src.advanced_retriever import retrieve_advanced
from src.utils import fetch_jd_from_url, clean_query

load_dotenv()

app = FastAPI(title="SHL Assessment Recommendation API")

# Global flag to track initialization
_initialized = False


class QueryRequest(BaseModel):
    query: str


class AssessmentResponse(BaseModel):
    url: str
    name: str
    adaptive_support: str
    description: str
    duration: int
    remote_support: str
    test_type: List[str]


class RecommendationResponse(BaseModel):
    recommended_assessments: List[AssessmentResponse]


def ensure_initialized():
    """Verify required files exist (pre-generated for instant startup)."""
    global _initialized
    
    if _initialized:
        return
    
    # Check if vector DB exists (should be pre-generated)
    index_file = 'data/faiss_index.bin'
    metadata_file = 'data/faiss_metadata.pkl'
    
    if not os.path.exists(index_file) or not os.path.exists(metadata_file):
        raise FileNotFoundError(
            f"Vector database files not found: {index_file}, {metadata_file}. "
            "Please ensure these files are committed to the repository. "
            "Run 'python src/embeddings.py' locally to generate them."
        )
    
    # XGBoost model is optional (will use fallback if not found)
    model_file = 'data/xgboost_reranker.pkl'
    if not os.path.exists(model_file):
        print("Warning: XGBoost model not found. Will use rule-based fallback.")
    
    _initialized = True


@app.on_event("startup")
async def startup_event():
    """Verify initialization on startup."""
    try:
        ensure_initialized()
        print("✓ API initialized successfully (using pre-generated files)")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        ensure_initialized()
        return {"status": "healthy", "initialized": _initialized}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/recommend", response_model=RecommendationResponse)
async def recommend_assessments(request: QueryRequest):
    """Recommend assessments based on query."""
    try:
        query = request.query.strip()
        
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Handle URL input
        if query.startswith('http://') or query.startswith('https://'):
            jd_text = fetch_jd_from_url(query)
            if jd_text:
                query = clean_query(jd_text)
            else:
                raise HTTPException(status_code=400, detail="Could not fetch content from URL")
        
        # Ensure initialization (lazy initialization if startup failed)
        try:
            ensure_initialized()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize system: {str(e)}. Please check that assessments.json exists and GEMINI_API_KEY is set."
            )
        
        # Get vector database
        try:
            vector_db = get_vector_db()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Vector database error: {str(e)}"
            )
        
        # Use advanced retriever with XGBoost re-ranking (best strategy - 61.56% recall)
        ranked = retrieve_advanced(
            query=query,
            vector_db=vector_db,
            top_k=10,
            use_llm_rerank=False,  # XGBoost is better and has no API limits
            use_xgboost_rerank=True  # Enable XGBoost re-ranking for best results (61.56% recall)
        )
        
        if not ranked:
            raise HTTPException(status_code=404, detail="No assessments found")
        
        # Format response
        assessments = []
        for cand in ranked[:10]:  # Max 10 results
            # Clean description - fix ellipsis encoding issue
            description = cand.get('description', '') or ''
            if description:
                # Replace common encoding issues with proper characters
                description = description.replace('â€¦', '…').replace('â€"', '—').replace('â€™', "'")
            
            assessments.append(AssessmentResponse(
                url=cand['url'],
                name=cand.get('name', 'Unknown'),
                adaptive_support=cand.get('adaptive_support', 'No'),
                description=description,
                duration=cand.get('duration', 0) or 0,
                remote_support=cand.get('remote_support', 'No'),
                test_type=cand.get('test_type', [])
            ))
        
        if len(assessments) < 5:
            raise HTTPException(
                status_code=500,
                detail=f"Could not generate minimum 5 recommendations. Got {len(assessments)}."
            )
        
        return RecommendationResponse(recommended_assessments=assessments)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


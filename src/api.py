from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv

from src.retriever import get_vector_db
from src.advanced_retriever import retrieve_advanced
from src.utils import fetch_jd_from_url, clean_query

load_dotenv()

app = FastAPI(title="SHL Assessment Recommendation API")


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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


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
        
        # Get vector database
        try:
            vector_db = get_vector_db()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Vector database not initialized. Please run embeddings.py first. Error: {str(e)}"
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


from typing import List, Dict, Optional
import faiss
import numpy as np
import pickle
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 768

INDEX_FILE = 'data/faiss_index.bin'
METADATA_FILE = 'data/faiss_metadata.pkl'


def get_query_embedding(query: str) -> List[float]:
    """Get embedding for query using Gemini.

    Returns a zero-vector fallback when Gemini is unavailable so retrieval
    can still proceed via keyword boosts.
    """
    try:
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=query,
            task_type="retrieval_query",
            output_dimensionality=EMBEDDING_DIM,
        )
        embedding = result.get('embedding') if isinstance(result, dict) else None
        if embedding and len(embedding) > 0:
            return embedding
        raise RuntimeError("Empty embedding returned from Gemini")
    except Exception as e:
        print(f"Error getting query embedding: {e}. Using zero-vector fallback.")
        return [0.0] * EMBEDDING_DIM


def get_vector_db():
    """Load FAISS index and metadata."""
    if not os.path.exists(INDEX_FILE) or not os.path.exists(METADATA_FILE):
        raise FileNotFoundError(
            f"Vector database not found. Please run embeddings.py first. "
            f"Looking for: {INDEX_FILE} and {METADATA_FILE}"
        )

    index = faiss.read_index(INDEX_FILE)
    with open(METADATA_FILE, 'rb') as f:
        metadata = pickle.load(f)

    return {'index': index, 'metadata': metadata}


def extract_keywords(query: str) -> List[str]:
    """Extract important keywords from query for boosting."""
    tech_keywords = [
        'java', 'python', 'javascript', 'sql', 'excel', 'data', 'analyst',
        'developer', 'engineer', 'sales', 'manager', 'admin', 'leadership',
        'verbal', 'numerical', 'cognitive', 'personality', 'seo', 'marketing',
        'communication', 'english', 'programming', 'coding', 'software'
    ]

    query_lower = query.lower()
    found = []
    for kw in tech_keywords:
        if kw in query_lower:
            found.append(kw)
    return found


def retrieve_candidates(
    query: str,
    vector_db: Dict,
    top_k: int = 20,
    max_duration: Optional[int] = None
) -> List[Dict]:
    """Retrieve candidate assessments using vector search with keyword boost."""
    query_embedding = get_query_embedding(query)
    if not query_embedding:
        return []

    index = vector_db['index']
    metadata = vector_db['metadata']

    query_vec = np.array([query_embedding], dtype='float32')
    faiss.normalize_L2(query_vec)

    search_k = min(top_k * 3, index.ntotal)
    distances, indices = index.search(query_vec, search_k)

    keywords = extract_keywords(query)

    candidates = []
    for i, idx in enumerate(indices[0]):
        if idx < len(metadata):
            meta = metadata[idx]

            if max_duration and meta.get('duration', 0) > max_duration:
                continue

            name_lower = meta['name'].lower()
            desc_lower = (meta.get('description', '') or '').lower()

            keyword_boost = 0.0
            for kw in keywords:
                if kw in name_lower:
                    keyword_boost += 0.15
                elif kw in desc_lower:
                    keyword_boost += 0.05

            combined_score = float(distances[0][i]) + keyword_boost

            candidates.append({
                'url': meta['url'],
                'alternate_urls': meta.get('alternate_urls', []),
                'name': meta['name'],
                'description': meta.get('description', ''),
                'duration': meta.get('duration', 0) or 0,
                'remote_support': meta.get('remote_support', 'No'),
                'adaptive_support': meta.get('adaptive_support', 'No'),
                'test_type': meta.get('test_type', []) if isinstance(meta.get('test_type'), list) else [],
                'distance': combined_score
            })

    candidates.sort(key=lambda x: x['distance'], reverse=True)

    return candidates[:top_k]

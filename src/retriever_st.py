"""
SentenceTransformer-based retriever.
Simple but effective approach inspired by TalentLens repository.
"""
import os
import faiss
import numpy as np
import pickle
from typing import List, Dict, Optional
import re

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from src.embeddings_st import get_model, get_vector_db_st, INDEX_FILE_ST, METADATA_FILE_ST


def get_query_embedding_st(query: str) -> np.ndarray:
    """Get embedding for query using SentenceTransformer."""
    model = get_model()
    if model is None:
        return None
    return model.encode(query, convert_to_numpy=True)


def retrieve_candidates_st(
    query: str,
    vector_db: Dict,
    top_k: int = 10
) -> List[Dict]:
    """
    Retrieve candidate assessments using SentenceTransformer embeddings.
    Simple approach - let the semantic search do the heavy lifting.
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("Error: sentence-transformers not available")
        return []
    
    if vector_db is None:
        print("Error: Vector DB not available")
        return []
    
    index = vector_db['index']
    metadata = vector_db['metadata']
    
    # Get query embedding
    query_embedding = get_query_embedding_st(query)
    if query_embedding is None:
        return []
    
    # Normalize for cosine similarity
    query_embedding = query_embedding.astype('float32').reshape(1, -1)
    faiss.normalize_L2(query_embedding)
    
    # Search
    search_k = min(top_k * 2, index.ntotal)  # Get more candidates for filtering
    distances, indices = index.search(query_embedding, search_k)
    
    # Build results
    candidates = []
    seen_urls = set()
    
    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        if idx < 0 or idx >= len(metadata):
            continue
        
        meta = metadata[idx]
        url = meta['url']
        
        # Deduplicate by URL
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        candidates.append({
            'name': meta['name'],
            'url': url,
            'alternate_urls': meta.get('alternate_urls', []),
            'description': meta.get('description', ''),
            'duration': meta.get('duration', 0),
            'remote_support': meta.get('remote_support', 'No'),
            'adaptive_support': meta.get('adaptive_support', 'No'),
            'test_type': meta.get('test_type', []),
            'score': float(dist),  # Cosine similarity (higher is better after normalization)
            'rank': len(candidates) + 1
        })
        
        if len(candidates) >= top_k:
            break
    
    return candidates


def retrieve_with_boost_st(
    query: str,
    vector_db: Dict,
    top_k: int = 10
) -> List[Dict]:
    """
    Enhanced retrieval with keyword boosting.
    Combines semantic search with keyword matching for better recall.
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return []
    
    if vector_db is None:
        return []
    
    index = vector_db['index']
    metadata = vector_db['metadata']
    
    # Get query embedding
    query_embedding = get_query_embedding_st(query)
    if query_embedding is None:
        return []
    
    # Normalize for cosine similarity
    query_embedding = query_embedding.astype('float32').reshape(1, -1)
    faiss.normalize_L2(query_embedding)
    
    # Get ALL candidates (or a large number)
    search_k = min(100, index.ntotal)
    distances, indices = index.search(query_embedding, search_k)
    
    # Extract keywords from query
    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w+\b', query_lower))
    
    # Important keywords to boost
    tech_keywords = {
        'java', 'python', 'sql', 'javascript', 'html', 'css', 'selenium', 'excel',
        'c#', '.net', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'typescript',
        'angular', 'react', 'vue', 'node', 'spring', 'django', 'flask'
    }
    role_keywords = {
        'sales', 'developer', 'manager', 'analyst', 'engineer', 'admin', 'administrative',
        'leadership', 'executive', 'consultant', 'qa', 'marketing', 'graduate', 'entry'
    }
    skill_keywords = {
        'cognitive', 'personality', 'numerical', 'verbal', 'reasoning', 'aptitude',
        'communication', 'behavioral', 'inductive', 'deductive', 'mechanical'
    }
    
    all_boost_keywords = tech_keywords | role_keywords | skill_keywords
    query_boost_keywords = query_words & all_boost_keywords
    
    # Build results with boosting
    candidates = []
    seen_urls = set()
    
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue
        
        meta = metadata[idx]
        url = meta['url']
        
        # Deduplicate by URL
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        # Calculate boost score based on keyword matches
        name_lower = meta['name'].lower()
        desc_lower = meta.get('description', '').lower()
        
        boost = 0.0
        
        # Check for keyword matches
        for keyword in query_boost_keywords:
            if keyword in name_lower:
                boost += 0.3  # Strong boost for name match
            elif keyword in desc_lower:
                boost += 0.1  # Smaller boost for description match
        
        # Check for partial matches in name
        for word in query_words:
            if len(word) > 3 and word in name_lower:
                boost += 0.15
        
        combined_score = float(dist) + boost
        
        candidates.append({
            'name': meta['name'],
            'url': url,
            'alternate_urls': meta.get('alternate_urls', []),
            'description': meta.get('description', ''),
            'duration': meta.get('duration', 0),
            'remote_support': meta.get('remote_support', 'No'),
            'adaptive_support': meta.get('adaptive_support', 'No'),
            'test_type': meta.get('test_type', []),
            'semantic_score': float(dist),
            'boost': boost,
            'score': combined_score,
            'rank': 0  # Will be set after sorting
        })
    
    # Sort by combined score (descending)
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # Assign ranks and limit to top_k
    for i, cand in enumerate(candidates[:top_k]):
        cand['rank'] = i + 1
    
    return candidates[:top_k]


if __name__ == "__main__":
    # Test the retriever
    db = get_vector_db_st()
    if db:
        test_queries = [
            "Java developer assessment",
            "Sales manager cognitive test",
            "Entry level graduate hiring",
            "Python programming skills"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            print("-" * 50)
            results = retrieve_with_boost_st(query, db, top_k=5)
            for r in results:
                print(f"  {r['rank']}. {r['name']} (score: {r['score']:.3f})")


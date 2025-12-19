"""
Ensemble Retriever - Combines multiple retrieval strategies with voting.
Strategies:
1. Advanced semantic + keyword retrieval (Gemini)
2. SentenceTransformer with keyword boost (Best: 33.33%)
3. Pure semantic retrieval
4. Keyword-only retrieval
5. Duration-filtered retrieval
"""
from typing import List, Dict, Optional
from collections import defaultdict
from src.advanced_retriever import retrieve_advanced, preprocess_query
from src.retriever import retrieve_candidates, get_vector_db
import numpy as np


def keyword_only_retrieve(
    query: str,
    query_info: Dict,
    vector_db: Dict,
    top_k: int = 20
) -> List[Dict]:
    """Pure keyword-based retrieval."""
    from src.retriever import get_query_embedding
    import faiss
    
    index = vector_db['index']
    metadata = vector_db['metadata']
    
    # Get basic embedding for broad search
    query_embedding = get_query_embedding(query)
    if not query_embedding:
        return []
    
    query_vec = np.array([query_embedding], dtype='float32')
    faiss.normalize_L2(query_vec)
    
    # Search broadly
    distances, indices = index.search(query_vec, min(top_k * 2, index.ntotal))
    
    query_lower = query.lower()
    skills = set(query_info['skills'])
    roles = set(query_info['roles'])
    
    candidates = []
    for i, idx in enumerate(indices[0]):
        if idx >= len(metadata):
            continue
        
        meta = metadata[idx]
        name_lower = meta['name'].lower()
        desc_lower = (meta.get('description', '') or '').lower()
        
        # Pure keyword score
        keyword_score = 0.0
        
        # Name matches (very strong)
        for skill in skills:
            if skill in name_lower:
                keyword_score += 0.30
        
        for role in roles:
            if role in name_lower:
                keyword_score += 0.25
        
        # Description matches
        for skill in skills:
            if skill in desc_lower:
                keyword_score += 0.10
        
        # Exact phrase matches
        for skill in skills:
            if skill in query_lower and skill in name_lower:
                keyword_score += 0.15
        
        if keyword_score > 0:
            candidates.append({
                'url': meta['url'],
                'alternate_urls': meta.get('alternate_urls', []),
                'name': meta['name'],
                'description': meta.get('description', ''),
                'duration': meta.get('duration', 0) or 0,
                'remote_support': meta.get('remote_support', 'No'),
                'adaptive_support': meta.get('adaptive_support', 'No'),
                'test_type': meta.get('test_type', []),
                'keyword_score': keyword_score,
                'distance': keyword_score
            })
    
    # Sort by keyword score
    candidates.sort(key=lambda x: x['keyword_score'], reverse=True)
    return candidates[:top_k]


def ensemble_retrieve(
    query: str,
    vector_db: Dict,
    top_k: int = 10,
    use_llm_rerank: bool = True,
    include_st: bool = True
) -> List[Dict]:
    """
    Ensemble retrieval combining multiple strategies with voting.
    
    Args:
        query: User query
        vector_db: Vector database (Gemini-based)
        top_k: Number of results to return
        use_llm_rerank: Whether to use LLM re-ranking
        include_st: Whether to include SentenceTransformer strategy (best performer)
    
    Returns:
        Ensemble-ranked list of candidates
    """
    query_info = preprocess_query(query)
    
    # Strategy 1: Advanced hybrid retrieval (Gemini)
    advanced_results = retrieve_advanced(query, vector_db, top_k=top_k * 2, use_llm_rerank=False)
    
    # Strategy 2: SentenceTransformer with keyword boost (Best: 33.33% recall)
    st_results = []
    if include_st:
        try:
            from src.retriever_st import retrieve_with_boost_st, get_vector_db_st
            st_db = get_vector_db_st()
            if st_db:
                st_results = retrieve_with_boost_st(query, st_db, top_k=top_k * 2)
        except Exception as e:
            print(f"Warning: SentenceTransformer not available: {e}")
    
    # Strategy 3: Pure semantic retrieval
    semantic_results = retrieve_candidates(query, vector_db, top_k=top_k * 2)
    
    # Strategy 4: Keyword-only retrieval
    keyword_results = keyword_only_retrieve(query, query_info, vector_db, top_k=top_k * 2)
    
    # Strategy 5: Duration-filtered (if duration constraint exists)
    duration_results = []
    if query_info.get('duration'):
        filtered = [r for r in advanced_results if r.get('duration', 0) <= query_info['duration'] * 1.2]
        duration_results = filtered[:top_k]
    
    # Collect all unique candidates with scores from each strategy
    candidate_scores = defaultdict(lambda: {
        'candidate': None,
        'scores': [],
        'ranks': []
    })
    
    # Score from advanced retrieval (Gemini)
    for rank, cand in enumerate(advanced_results):
        url = cand['url']
        candidate_scores[url]['candidate'] = cand
        candidate_scores[url]['scores'].append(cand.get('combined_score', 0))
        candidate_scores[url]['ranks'].append(rank + 1)
    
    # Score from SentenceTransformer (highest weight - best performer)
    for rank, cand in enumerate(st_results):
        url = cand['url']
        if url not in candidate_scores:
            candidate_scores[url]['candidate'] = cand
        # Use combined score (semantic + boost) from ST
        st_score = cand.get('score', cand.get('semantic_score', 0))
        candidate_scores[url]['scores'].append(st_score)
        candidate_scores[url]['ranks'].append(rank + 1)
    
    # Score from semantic retrieval
    for rank, cand in enumerate(semantic_results):
        url = cand['url']
        if url not in candidate_scores:
            candidate_scores[url]['candidate'] = cand
        candidate_scores[url]['scores'].append(cand.get('distance', 0))
        candidate_scores[url]['ranks'].append(rank + 1)
    
    # Score from keyword retrieval
    for rank, cand in enumerate(keyword_results):
        url = cand['url']
        if url not in candidate_scores:
            candidate_scores[url]['candidate'] = cand
        candidate_scores[url]['scores'].append(cand.get('keyword_score', 0))
        candidate_scores[url]['ranks'].append(rank + 1)
    
    # Calculate ensemble scores
    ensemble_candidates = []
    for url, data in candidate_scores.items():
        cand = data['candidate']
        scores = data['scores']
        ranks = data['ranks']
        
        # Weighted average score (ST gets highest weight if present, then advanced)
        scores_sorted = sorted(scores, reverse=True)
        if len(scores_sorted) >= 2:
            # If ST is present (usually highest), give it more weight
            ensemble_score = (scores_sorted[0] * 0.7 + scores_sorted[1] * 0.3)
        elif len(scores_sorted) == 1:
            ensemble_score = scores_sorted[0]
        else:
            ensemble_score = 0
        
        # Reciprocal rank fusion (RRF) - boost items that appear in multiple strategies
        rrf_score = sum(1.0 / (60 + rank) for rank in ranks)  # k=60 for RRF
        
        # Combined ensemble score
        final_score = ensemble_score * 0.7 + rrf_score * 0.3
        
        cand['ensemble_score'] = final_score
        cand['rrf_score'] = rrf_score
        ensemble_candidates.append(cand)
    
    # Sort by ensemble score
    ensemble_candidates.sort(key=lambda x: x.get('ensemble_score', 0), reverse=True)
    
    # Apply LLM re-ranking if requested
    if use_llm_rerank and len(ensemble_candidates) > 0:
        try:
            from src.llm_reranker import llm_rerank
            ensemble_candidates = llm_rerank(query, ensemble_candidates, top_k=top_k, use_fallback=True)
        except Exception as e:
            print(f"LLM re-ranking failed, using ensemble results: {e}")
    
    return ensemble_candidates[:top_k]

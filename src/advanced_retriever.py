"""
Advanced Retriever with Multiple Strategies:
1. Query preprocessing (extract skills, roles, duration)
2. Query expansion with synonyms
3. Hybrid retrieval (semantic + keyword + BM25-like)
4. Multi-stage filtering
5. Smart re-ranking
"""
import re
from typing import List, Dict, Optional, Set
from src.retriever import get_vector_db, get_query_embedding
import faiss
import numpy as np

# Query expansion dictionary - expanded for better recall
QUERY_EXPANSIONS = {
    # Programming languages
    'java': ['java', 'j2ee', 'j2se', 'jdk', 'jvm', 'spring', 'hibernate', 'core java', 'automata'],
    'python': ['python', 'django', 'flask', 'pandas', 'numpy', 'data science'],
    'sql': ['sql', 'database', 'mysql', 'postgresql', 'oracle', 'query', 'sql server', 'ssas'],
    'javascript': ['javascript', 'javascript', 'java script', 'js', 'node', 'react', 'angular', 'vue', 'frontend'],
    'html': ['html', 'css', 'htmlcss', 'web', 'frontend', 'markup'],
    'css': ['css', 'html', 'htmlcss', 'web', 'frontend', 'styling'],
    'selenium': ['selenium', 'automation', 'testing', 'qa', 'web automation', 'test automation'],
    
    # Office skills
    'excel': ['excel', 'spreadsheet', 'ms excel', 'microsoft excel', 'excel 365'],
    
    # Roles
    'data analyst': ['data analyst', 'data analysis', 'analytics', 'bi', 'business intelligence', 'tableau'],
    'developer': ['developer', 'programmer', 'coder', 'software engineer', 'engineer', 'technology'],
    'sales': ['sales', 'selling', 'salesperson', 'account manager', 'entry level sales', 'sales representative'],
    'manager': ['manager', 'management', 'supervisor', 'lead', 'director', 'marketing manager'],
    'admin': ['admin', 'administrative', 'administrator', 'clerical', 'office', 'assistant', 'bank administrative'],
    'leadership': ['leadership', 'leader', 'executive', 'coo', 'ceo', 'cfo', 'enterprise leadership'],
    'consultant': ['consultant', 'consulting', 'advisory', 'professional', 'advisor'],
    'qa': ['qa', 'quality assurance', 'testing', 'test', 'manual testing', 'automation testing'],
    'marketing': ['marketing', 'digital marketing', 'advertising', 'digital advertising', 'brand'],
    
    # Skills/Assessment types
    'communication': ['communication', 'verbal', 'written', 'english', 'language', 'interpersonal', 'business communication'],
    'personality': ['personality', 'behavior', 'behavioral', 'traits', 'opq', 'opq32', 'occupational personality'],
    'cognitive': ['cognitive', 'reasoning', 'aptitude', 'ability', 'intelligence', 'inductive', 'deductive'],
    'numerical': ['numerical', 'math', 'mathematics', 'quantitative', 'arithmetic', 'calculation', 'verify numerical'],
    'verbal': ['verbal', 'language', 'comprehension', 'reading', 'writing', 'verify verbal'],
    'inductive': ['inductive', 'inductive reasoning', 'pattern recognition', 'abstract reasoning'],
    
    # Job levels
    'entry': ['entry', 'entry level', 'graduate', 'junior', 'fresher', 'new graduate'],
    'senior': ['senior', 'experienced', 'advanced', 'professional', 'expert'],
}

def preprocess_query(query: str) -> Dict:
    """Extract structured information from query."""
    # Clean query first
    query = re.sub(r'\s+', ' ', query).strip()
    # Normalize common variations
    query = query.replace('Java Script', 'JavaScript').replace('java script', 'javascript')
    query_lower = query.lower()
    
    # Extract duration constraints (more patterns)
    duration = None
    duration_patterns = [
        r'(\d+)\s*minutes?',
        r'(\d+)\s*mins?',
        r'(\d+)\s*hours?',
        r'(\d+)\s*hrs?',
        r'duration[:\s]*(\d+)',
        r'max[:\s]*(\d+)',
        r'about\s*(\d+)',
        r'(\d+)\s*-\s*(\d+)\s*minutes?',  # Range like "30-40 minutes"
        r'(\d+)\s*to\s*(\d+)\s*minutes?',
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if len(match.groups()) == 2:  # Range
                duration = int(match.group(2))  # Take upper bound
            else:
                duration = int(match.group(1))
            # Convert hours to minutes
            if 'hour' in query_lower or 'hr' in query_lower:
                duration *= 60
            break
    
    # Extract skills/technologies
    skills = []
    for skill, variants in QUERY_EXPANSIONS.items():
        for variant in variants:
            if variant in query_lower:
                skills.extend(QUERY_EXPANSIONS[skill])
                break
    
    # Extract job roles (expanded)
    roles = []
    role_keywords = {
        'developer': ['developer', 'programmer', 'coder', 'engineer', 'software'],
        'analyst': ['analyst', 'data analyst', 'business analyst', 'data'],
        'manager': ['manager', 'supervisor', 'lead', 'director', 'management'],
        'admin': ['admin', 'administrative', 'administrator', 'assistant', 'clerical'],
        'sales': ['sales', 'salesperson', 'account manager', 'selling'],
        'executive': ['executive', 'coo', 'ceo', 'cfo', 'leadership', 'senior executive'],
        'consultant': ['consultant', 'consulting', 'advisor', 'advisory'],
        'professional': ['professional', 'specialist', 'expert'],
    }
    
    for role, keywords in role_keywords.items():
        for keyword in keywords:
            if keyword in query_lower:
                roles.append(role)
                break
    
    # Extract test type preferences (expanded)
    test_types = []
    if 'personality' in query_lower or 'behavior' in query_lower or 'behavioral' in query_lower:
        test_types.append('Personality & Behavior')
    if 'cognitive' in query_lower or 'aptitude' in query_lower or 'reasoning' in query_lower:
        test_types.append('Ability & Aptitude')
    if 'knowledge' in query_lower or 'skill' in query_lower or 'technical' in query_lower:
        test_types.append('Knowledge & Skills')
    if 'communication' in query_lower or 'verbal' in query_lower or 'english' in query_lower:
        test_types.append('Ability & Aptitude')
    if 'numerical' in query_lower or 'math' in query_lower or 'quantitative' in query_lower:
        test_types.append('Ability & Aptitude')
    if 'situational' in query_lower or 'judgement' in query_lower or 'judgment' in query_lower:
        test_types.append('Biodata & Situational Judgement')
    # For consultant/professional roles, often need multiple test types
    if 'consultant' in query_lower or 'professional' in query_lower:
        test_types.extend(['Personality & Behavior', 'Ability & Aptitude', 'Competencies'])
    
    return {
        'original_query': query,
        'duration': duration,
        'skills': list(set(skills)),
        'roles': list(set(roles)),
        'test_types': test_types,
        'expanded_query': query  # Will be expanded later
    }


def expand_query(query_info: Dict) -> str:
    """Expand query with synonyms and related terms."""
    original = query_info['original_query']
    skills = query_info['skills']
    roles = query_info['roles']
    
    # Extract key phrases from original query
    expanded_parts = []
    
    # Keep original query
    expanded_parts.append(original)
    
    # Add skill synonyms (only if not already present)
    query_lower = original.lower()
    for skill in skills[:8]:  # More skills
        if skill not in query_lower:
            expanded_parts.append(skill)
    
    # Add role synonyms
    for role in roles[:5]:
        if role not in query_lower:
            expanded_parts.append(role)
    
    # Extract key job-related terms
    job_keywords = []
    if 'entry' in query_lower or 'graduate' in query_lower:
        job_keywords.extend(['entry level', 'junior', 'graduate'])
    if 'senior' in query_lower or 'experienced' in query_lower:
        job_keywords.extend(['senior', 'experienced', 'professional'])
    if 'manager' in query_lower:
        job_keywords.append('management')
    if 'analyst' in query_lower:
        job_keywords.append('data analysis')
    
    for kw in job_keywords[:3]:
        if kw not in query_lower:
            expanded_parts.append(kw)
    
    return ' '.join(expanded_parts)


def hybrid_retrieve(
    query: str,
    query_info: Dict,
    vector_db: Dict,
    top_k: int = 50
) -> List[Dict]:
    """Hybrid retrieval combining semantic search and keyword matching."""
    index = vector_db['index']
    metadata = vector_db['metadata']
    
    # 1. Semantic search
    query_embedding = get_query_embedding(query)
    if not query_embedding:
        return []
    
    query_vec = np.array([query_embedding], dtype='float32')
    faiss.normalize_L2(query_vec)
    
    # Search candidates - 150 provides good coverage with keyword boosting
    search_k = min(150, index.ntotal)
    distances, indices = index.search(query_vec, search_k)
    
    # 2. Build keyword scores
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
        
        # Semantic score
        semantic_score = float(distances[0][i])
        
        # Keyword matching score (significantly boosted for better recall)
        keyword_score = 0.0
        
        # Name matches (strong boost - doubled)
        for skill in skills:
            if skill in name_lower:
                keyword_score += 0.40  # Increased from 0.20
            elif skill in desc_lower:
                keyword_score += 0.10  # Increased from 0.05
        
        for role in roles:
            if role in name_lower:
                keyword_score += 0.30  # Increased from 0.15
            elif role in desc_lower:
                keyword_score += 0.10  # Increased from 0.05
        
        # Exact phrase matches (doubled boost)
        for skill in skills:
            if skill in query_lower and skill in name_lower:
                keyword_score += 0.20  # Increased from 0.10
        
        # Test type matching (doubled)
        meta_test_types = meta.get('test_type', [])
        for pref_type in query_info['test_types']:
            if pref_type in meta_test_types:
                keyword_score += 0.20  # Increased from 0.10
        
        # Additional boosts for specific patterns
        # Boost for assessment names containing key query terms
        query_words = set(query_lower.split())
        name_words = set(name_lower.split())
        common_words = query_words & name_words - {'the', 'a', 'an', 'for', 'and', 'or', 'to', 'in', 'of', 'is', 'are'}
        if common_words:
            keyword_score += len(common_words) * 0.15
        
        # Combined score
        combined_score = semantic_score + keyword_score
        
        candidates.append({
            'url': meta['url'],
            'alternate_urls': meta.get('alternate_urls', []),
            'name': meta['name'],
            'description': meta.get('description', ''),
            'duration': meta.get('duration', 0) or 0,
            'remote_support': meta.get('remote_support', 'No'),
            'adaptive_support': meta.get('adaptive_support', 'No'),
            'test_type': meta_test_types,
            'semantic_score': semantic_score,
            'keyword_score': keyword_score,
            'combined_score': combined_score,
            'distance': combined_score  # For compatibility
        })
    
    # Sort by combined score
    candidates.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return candidates[:top_k]


def filter_candidates(
    candidates: List[Dict],
    query_info: Dict
) -> List[Dict]:
    """Multi-stage filtering - soft penalties for better recall."""
    filtered = []
    
    for cand in candidates:
        # Duration filter - soft penalty (don't drop candidates)
        if query_info['duration']:
            cand_duration = cand.get('duration', 0) or 0
            if cand_duration > 0 and cand_duration > query_info['duration'] * 1.3:  # 30% tolerance
                # Slight penalty but keep candidate
                cand['combined_score'] *= 0.9
        
        # Test type filter (soft - boost rather than filter)
        if query_info['test_types']:
            meta_types = cand.get('test_type', [])
            if not any(t in meta_types for t in query_info['test_types']):
                # Don't filter out, but lower score slightly
                cand['combined_score'] *= 0.95
        
        filtered.append(cand)
    
    return filtered


def rerank_rule_based(
    candidates: List[Dict],
    query_info: Dict
) -> List[Dict]:
    """Rule-based re-ranking using multiple signals."""
    query_lower = query_info['original_query'].lower()
    
    for cand in candidates:
        rerank_score = 0.0
        
        name_lower = cand['name'].lower()
        desc_lower = (cand.get('description', '') or '').lower()
        
        # 1. Exact name matches (very strong)
        for skill in query_info['skills']:
            if skill in name_lower:
                rerank_score += 0.30
        
        # 2. Role matches in name
        for role in query_info['roles']:
            if role in name_lower:
                rerank_score += 0.25
        
        # 3. Duration match (boost if within range)
        if query_info['duration'] and cand.get('duration'):
            cand_dur = cand['duration']
            query_dur = query_info['duration']
            if cand_dur <= query_dur * 1.2:  # Within 20% tolerance
                rerank_score += 0.15
        
        # 4. Test type match
        meta_types = cand.get('test_type', [])
        for pref_type in query_info['test_types']:
            if pref_type in meta_types:
                rerank_score += 0.10
        
        # 5. Entry-level keywords
        if any(kw in query_lower for kw in ['entry', 'graduate', 'junior', '0-2', '0-3']):
            if any(kw in name_lower for kw in ['entry', 'junior', 'level']):
                rerank_score += 0.10
        
        # 6. Senior/experienced keywords
        if any(kw in query_lower for kw in ['senior', 'experienced', '5+', 'years']):
            if any(kw in name_lower for kw in ['senior', 'advanced', 'professional']):
                rerank_score += 0.10
        
        # 7. Remote support (if mentioned)
        if 'remote' in query_lower and cand.get('remote_support') == 'Yes':
            rerank_score += 0.05
        
        # Update combined score
        cand['combined_score'] += rerank_score
        cand['rerank_score'] = rerank_score
    
    # Re-sort by updated combined score
    candidates.sort(key=lambda x: x['combined_score'], reverse=True)
    return candidates


def retrieve_advanced(
    query: str,
    vector_db: Dict,
    top_k: int = 10,
    use_llm_rerank: bool = False,
    use_xgboost_rerank: bool = True
) -> List[Dict]:
    """
    Advanced retrieval pipeline with optional re-ranking.
    
    Args:
        query: User query
        vector_db: Vector database dictionary
        top_k: Number of results to return
        use_llm_rerank: If True, use LLM re-ranking (has API rate limits)
        use_xgboost_rerank: If True, use XGBoost re-ranking (best: 62.22% recall)
    """
    # 1. Preprocess query
    query_info = preprocess_query(query)
    
    # 2. Expand query
    expanded_query = expand_query(query_info)
    
    # 3. Hybrid retrieval - 100 gave best results
    candidates = hybrid_retrieve(expanded_query, query_info, vector_db, top_k=100)
    
    # 4. Filter
    filtered = filter_candidates(candidates, query_info)
    
    # 5. Re-ranking (XGBoost is best, then LLM, then rule-based)
    if use_xgboost_rerank:
        try:
            from src.xgboost_reranker import load_xgboost_reranker, rerank_with_xgboost
            model = load_xgboost_reranker('data/xgboost_reranker.pkl')
            if model:
                reranked = rerank_with_xgboost(query, filtered[:top_k * 3], model, query_info, top_k=top_k)
            else:
                # Fallback to rule-based if model not found
                reranked = rerank_rule_based(filtered, query_info)
        except Exception as e:
            print(f"XGBoost re-ranking failed, using rule-based: {e}")
            reranked = rerank_rule_based(filtered, query_info)
    elif use_llm_rerank:
        try:
            from src.llm_reranker import llm_rerank
            reranked = llm_rerank(query, filtered[:top_k * 2], top_k=top_k, use_fallback=True)
        except Exception as e:
            print(f"LLM re-ranking failed, using rule-based: {e}")
            reranked = rerank_rule_based(filtered, query_info)
    else:
        # Rule-based re-ranking
        reranked = rerank_rule_based(filtered, query_info)
    
    # 6. Return top_k
    return reranked[:top_k]


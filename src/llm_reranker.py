"""
LLM-based Re-ranker with fallback to rule-based.
Uses Gemini API for intelligent re-ranking.
"""
import google.generativeai as genai
import os
import json
import re
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)


def llm_rerank(
    query: str,
    candidates: List[Dict],
    top_k: int = 10,
    use_fallback: bool = True
) -> List[Dict]:
    """
    Re-rank candidates using LLM with fallback to rule-based.
    
    Args:
        query: User query
        candidates: List of candidate assessments
        top_k: Number of top results to return
        use_fallback: If True, fallback to rule-based if LLM fails
    
    Returns:
        Re-ranked list of candidates
    """
    if not candidates:
        return []
    
    # Limit candidates for prompt (to avoid token limits)
    max_candidates = min(20, len(candidates))
    candidates_for_rerank = candidates[:max_candidates]
    
    try:
        # Format candidates for prompt
        candidates_text = ""
        for i, cand in enumerate(candidates_for_rerank, 1):
            name = cand.get('name', 'Unknown')
            desc = (cand.get('description', '') or '')[:150]
            url = cand.get('url', '')
            test_types = ', '.join(cand.get('test_type', [])) if cand.get('test_type') else 'Unknown'
            duration = cand.get('duration', 0) or 0
            
            candidates_text += f"{i}. {name}\n"
            candidates_text += f"   Description: {desc}...\n"
            candidates_text += f"   Test Types: {test_types}\n"
            if duration:
                candidates_text += f"   Duration: {duration} minutes\n"
            candidates_text += f"   URL: {url}\n\n"
        
        prompt = f"""You are an expert assessment recommendation system for SHL (a talent assessment company).

Given a user query and a list of candidate assessments, rank them by relevance to the query.
Consider:
- Technical skills mentioned (Java, Python, SQL, etc.)
- Job roles (developer, analyst, manager, etc.)
- Experience level (entry-level, senior, etc.)
- Duration constraints
- Test types (Knowledge & Skills, Personality, Cognitive Ability, etc.)

User Query: {query}

Candidate Assessments:
{candidates_text}

Return ONLY a JSON array of URLs in descending relevance order (most relevant first).
Format: ["url1", "url2", "url3", ...]
Return exactly {top_k} URLs, ranked from most relevant to least relevant.
"""
        
        # Try different Gemini models (use gemini-2.5-flash as primary)
        # Based on user's API key: gemini-2.5-flash
        models_to_try = [
            'gemini-2.5-flash',                 # Primary model (user's API key)
            'gemini-2.0-flash-lite',            # Fallback with higher quota
            'gemini-flash-lite-latest',         # Alternative fallback
            'gemini-2.0-flash',                 # Standard fallback
        ]
        
        ranked_urls = None
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,  # Low temperature for consistent ranking
                        "max_output_tokens": 2000,
                    }
                )
                
                response_text = response.text.strip()
                
                # Parse JSON response
                # Remove markdown code blocks if present
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0].strip()
                elif '```' in response_text:
                    parts = response_text.split('```')
                    for part in parts:
                        part = part.strip()
                        if part.startswith('[') or part.startswith('{'):
                            response_text = part
                            break
                
                # Try to parse JSON
                try:
                    ranked_urls = json.loads(response_text)
                    if isinstance(ranked_urls, list) and len(ranked_urls) > 0:
                        break  # Success!
                except json.JSONDecodeError:
                    # Try to extract URLs from text
                    url_pattern = r'https?://[^\s,\]]+'
                    urls_found = re.findall(url_pattern, response_text)
                    if urls_found:
                        ranked_urls = urls_found
                        break
            except Exception as e:
                print(f"  Model {model_name} failed: {e}")
                continue
        
        if ranked_urls and isinstance(ranked_urls, list):
            # Map URLs back to full candidate objects
            url_to_candidate = {cand['url']: cand for cand in candidates}
            # Also check alternate URLs
            for cand in candidates:
                for alt_url in cand.get('alternate_urls', []):
                    if alt_url not in url_to_candidate:
                        url_to_candidate[alt_url] = cand
            
            ranked_candidates = []
            seen_urls = set()
            
            for url in ranked_urls:
                # Try exact match first
                if url in url_to_candidate and url not in seen_urls:
                    ranked_candidates.append(url_to_candidate[url])
                    seen_urls.add(url)
                else:
                    # Try partial match (slug)
                    url_slug = url.split('/view/')[-1].rstrip('/') if '/view/' in url else url
                    for cand_url, cand in url_to_candidate.items():
                        if url_slug in cand_url and cand_url not in seen_urls:
                            ranked_candidates.append(cand)
                            seen_urls.add(cand_url)
                            break
            
            # Fill remaining slots with original order
            for cand in candidates:
                if cand['url'] not in seen_urls and len(ranked_candidates) < top_k:
                    ranked_candidates.append(cand)
                    seen_urls.add(cand['url'])
            
            return ranked_candidates[:top_k]
        
    except Exception as e:
        print(f"LLM re-ranking error: {e}")
    
    # Fallback to rule-based re-ranking
    if use_fallback:
        return rule_based_rerank(query, candidates, top_k)
    
    # Last resort: return original order
    return candidates[:top_k]


def rule_based_rerank(query: str, candidates: List[Dict], top_k: int) -> List[Dict]:
    """Rule-based re-ranking as fallback."""
    query_lower = query.lower()
    
    # Extract key terms
    skills = []
    roles = []
    
    skill_keywords = ['java', 'python', 'sql', 'javascript', 'excel', 'data', 'analyst']
    role_keywords = ['developer', 'analyst', 'manager', 'admin', 'sales', 'executive']
    
    for skill in skill_keywords:
        if skill in query_lower:
            skills.append(skill)
    
    for role in role_keywords:
        if role in query_lower:
            roles.append(role)
    
    # Score candidates
    for cand in candidates:
        score = cand.get('combined_score', 0.0)
        name_lower = cand.get('name', '').lower()
        
        # Boost for exact matches
        for skill in skills:
            if skill in name_lower:
                score += 0.20
        
        for role in roles:
            if role in name_lower:
                score += 0.15
        
        cand['rerank_score'] = score
    
    # Sort by rerank score
    candidates.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
    return candidates[:top_k]

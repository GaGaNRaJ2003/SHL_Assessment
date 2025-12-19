import google.generativeai as genai
import os
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)


def rerank_assessments(query: str, candidates: List[Dict], top_k: int = 10) -> List[Dict]:
    """Use LLM to re-rank candidate assessments."""
    
    if not candidates:
        return []
    
    # Limit candidates for prompt (to avoid token limits)
    max_candidates_for_prompt = 20
    candidates_for_prompt = candidates[:max_candidates_for_prompt]
    
    # Format candidates for prompt
    candidates_text = ""
    for i, cand in enumerate(candidates_for_prompt, 1):
        candidates_text += f"{i}. {cand['name']}\n"
        desc = cand.get('description', '')[:200] if cand.get('description') else 'No description'
        candidates_text += f"   Description: {desc}...\n"
        candidates_text += f"   URL: {cand['url']}\n"
        test_types = ', '.join(cand.get('test_type', [])) if cand.get('test_type') else 'Unknown'
        candidates_text += f"   Test Type: {test_types}\n"
        duration = cand.get('duration', 0) or 0
        candidates_text += f"   Duration: {duration} mins\n\n"
    
    prompt = f"""You are an SHL assessment recommendation assistant.
Given the following user query and candidate assessments, rank them by relevance.
Return ONLY a JSON array of URLs in descending relevance order (most relevant first).

User Query: {query}

Candidate Assessments:
{candidates_text}

Output format: ["url1", "url2", "url3", ...]
Return exactly {top_k} URLs, ranked from most relevant to least relevant.
"""
    
    try:
        # Try gemini-2.5-flash with fallback options (user's API key: gemini-2.5-flash)
        model_names = ['gemini-2.5-flash', 'gemini-2.0-flash-lite', 'gemini-flash-lite-latest', 'gemini-2.0-flash']
        model = None
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                break
            except Exception:
                continue
        if model is None:
            raise ValueError("No working Gemini model found")
        response = model.generate_content(prompt)
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            # Try to extract JSON from code block
            parts = response_text.split('```')
            for part in parts:
                part = part.strip()
                if part.startswith('[') or part.startswith('{'):
                    response_text = part
                    break
        
        # Try to parse JSON
        try:
            ranked_urls = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract URLs from text
            import re
            url_pattern = r'https?://[^\s,\]]+'
            ranked_urls = re.findall(url_pattern, response_text)
        
        if not isinstance(ranked_urls, list):
            ranked_urls = []
        
        # Map URLs back to full candidate objects
        url_to_candidate = {cand['url']: cand for cand in candidates}
        ranked_candidates = []
        seen_urls = set()
        
        for url in ranked_urls:
            if url in url_to_candidate and url not in seen_urls:
                ranked_candidates.append(url_to_candidate[url])
                seen_urls.add(url)
        
        # If LLM didn't return enough, fill with remaining candidates
        for cand in candidates:
            if cand['url'] not in seen_urls and len(ranked_candidates) < top_k:
                ranked_candidates.append(cand)
                seen_urls.add(cand['url'])
        
        return ranked_candidates[:top_k]
        
    except Exception as e:
        print(f"Error in re-ranking: {e}")
        # Fallback: return original candidates sorted by distance (most similar first)
        sorted_candidates = sorted(candidates, key=lambda x: x.get('distance', 1.0))
        return sorted_candidates[:top_k]


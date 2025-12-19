import re
from typing import Optional, List
import requests
from bs4 import BeautifulSoup


def extract_duration_from_query(query: str) -> Optional[int]:
    """Extract maximum duration constraint from query text."""
    patterns = [
        r'(\d+)\s*(?:mins?|minutes?)',
        r'(\d+)\s*(?:hour|hr)',
        r'(\d+)\s*(?:hour|hr)s?\s*(\d+)\s*(?:mins?|minutes?)',
    ]
    
    max_duration = None
    for pattern in patterns:
        matches = re.findall(pattern, query.lower())
        if matches:
            if isinstance(matches[0], tuple):
                hours, mins = matches[0]
                total = int(hours) * 60 + int(mins)
            else:
                total = int(matches[0])
            if max_duration is None or total < max_duration:
                max_duration = total
    
    return max_duration


def fetch_jd_from_url(url: str) -> Optional[str]:
    """Fetch job description text from a URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Extract text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None


def clean_query(query: str) -> str:
    """Remove common boilerplate from job descriptions."""
    # Remove SHL boilerplate
    boilerplate_patterns = [
        r'About Us.*?SHL is an equal opportunity employer\.?',
        r'#CareersAtSHL.*',
        r'Get In Touch.*',
        r'What SHL Can Offer You.*',
    ]
    
    cleaned = query
    for pattern in boilerplate_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    
    return cleaned.strip()



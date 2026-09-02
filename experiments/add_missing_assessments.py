"""Add missing assessments from train set."""
import json
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

BASE_URL = "https://www.shl.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def fetch_assessment(url):
    """Fetch assessment details from URL."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract name
        h1 = soup.find('h1')
        name = h1.get_text(strip=True) if h1 else 'Unknown'
        
        # Extract description
        meta_desc = soup.find('meta', {'name': 'description'})
        description = meta_desc.get('content') if meta_desc else None
        
        if not description:
            main = soup.find('main')
            if main:
                for p in main.find_all('p'):
                    text = p.get_text(strip=True)
                    if len(text) > 50:
                        description = text
                        break
        
        # Extract test types from page
        test_types = []
        text_content = soup.get_text()
        type_keywords = {
            'Ability & Aptitude': ['ability', 'aptitude', 'cognitive', 'reasoning'],
            'Knowledge & Skills': ['knowledge', 'skills', 'technical'],
            'Personality & Behavior': ['personality', 'behavior', 'opq'],
            'Biodata & Situational Judgement': ['situational', 'judgement', 'biodata'],
            'Simulations': ['simulation', 'simulated'],
            'Assessment Exercises': ['exercise', 'assessment center'],
            'Development & 360': ['development', '360', 'feedback'],
            'Competencies': ['competenc', 'competency']
        }
        
        for type_name, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_content.lower():
                    if type_name not in test_types:
                        test_types.append(type_name)
                    break
        
        return {
            'url': url,
            'name': name,
            'description': description,
            'duration': None,
            'remote_support': 'Yes',  # Default
            'adaptive_support': 'No',  # Default
            'test_type': test_types,
            'alternate_urls': []
        }
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def main():
    # Load existing
    with open('data/assessments.json', 'r') as f:
        existing = json.load(f)
    
    existing_slugs = set()
    for a in existing:
        url = a['url']
        if '/view/' in url:
            slug = url.split('/view/')[-1].rstrip('/')
            existing_slugs.add(slug)
    
    # Find missing from train set
    train_urls = set()
    with open('data/train.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row['Assessment_url'].strip()
            train_urls.add(url)
    
    missing = []
    for url in train_urls:
        if '/view/' in url:
            slug = url.split('/view/')[-1].rstrip('/')
            if slug not in existing_slugs:
                missing.append(url)
    
    print(f"Found {len(missing)} missing assessments")
    
    # Fetch missing assessments
    new_assessments = []
    for url in missing:
        print(f"Fetching: {url}")
        assessment = fetch_assessment(url)
        if assessment:
            new_assessments.append(assessment)
            # Add alternate URL
            if '/solutions/products/' in url:
                alt_url = url.replace('/solutions/products/', '/products/')
            else:
                alt_url = url.replace('/products/', '/solutions/products/')
            assessment['alternate_urls'] = [alt_url]
        time.sleep(0.5)
    
    # Merge
    all_assessments = existing + new_assessments
    
    # Save
    with open('data/assessments.json', 'w', encoding='utf-8') as f:
        json.dump(all_assessments, f, indent=2, ensure_ascii=False)
    
    print(f"\nAdded {len(new_assessments)} assessments")
    print(f"Total assessments: {len(all_assessments)}")

if __name__ == "__main__":
    main()



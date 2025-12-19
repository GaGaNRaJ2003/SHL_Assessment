"""
Quick crawler to get ALL assessments from both tables.
Will combine Individual Test Solutions + Pre-packaged Job Solutions.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin

BASE_URL = "https://www.shl.com"
CATALOG_BASE = "https://www.shl.com/products/product-catalog/"
OUTPUT_FILE = "data/assessments.json"

TEST_TYPE_MAP = {
    'A': 'Ability & Aptitude',
    'B': 'Biodata & Situational Judgement', 
    'C': 'Competencies',
    'D': 'Development & 360',
    'E': 'Assessment Exercises',
    'K': 'Knowledge & Skills',
    'P': 'Personality & Behavior',
    'S': 'Simulations'
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def fetch(session, url, retries=3):
    for i in range(retries):
        try:
            r = session.get(url, timeout=60)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            print(f"  Retry {i+1}: {e}")
            time.sleep(2)
    return None

def parse_rows(html):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    
    for row in soup.find_all('tr', attrs={'data-entity-id': True}):
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
        
        link = cells[0].find('a')
        if not link:
            continue
        
        name = link.get_text(strip=True)
        url = urljoin(BASE_URL, link.get('href', ''))
        remote = "Yes" if cells[1].find('img') else "No"
        adaptive = "Yes" if cells[2].find('img') else "No"
        
        types = []
        for c in cells[3].get_text(strip=True):
            if c in TEST_TYPE_MAP:
                types.append(TEST_TYPE_MAP[c])
        
        results.append({
            "url": url,
            "name": name,
            "description": None,
            "duration": None,
            "remote_support": remote,
            "adaptive_support": adaptive,
            "test_type": types
        })
    
    return results

def main():
    print("=" * 60)
    print("SHL Crawler - All Assessments")
    print("=" * 60)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_data = {}
    
    # Crawl Type 1 (Individual Test Solutions) - 32 pages
    print("\n[1] Individual Test Solutions (type=1)")
    for i in range(35):
        start = i * 12
        url = f"{CATALOG_BASE}?start={start}&type=1"
        print(f"  Page {i+1} start={start}...", end=" ")
        
        html = fetch(session, url)
        if not html:
            print("FAILED")
            break
        
        rows = parse_rows(html)
        if not rows:
            print("empty - done")
            break
        
        for r in rows:
            all_data[r['url']] = r
        print(f"{len(rows)} rows, total: {len(all_data)}")
        time.sleep(0.3)
    
    # Crawl Type 2 (Pre-packaged Job Solutions) - 12 pages
    print("\n[2] Pre-packaged Job Solutions (type=2)")
    for i in range(15):
        start = i * 12
        url = f"{CATALOG_BASE}?start={start}&type=2"
        print(f"  Page {i+1} start={start}...", end=" ")
        
        html = fetch(session, url)
        if not html:
            print("FAILED")
            break
        
        rows = parse_rows(html)
        if not rows:
            print("empty - done")
            break
        
        for r in rows:
            all_data[r['url']] = r
        print(f"{len(rows)} rows, total: {len(all_data)}")
        time.sleep(0.3)
    
    # Save
    assessments = list(all_data.values())
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"TOTAL: {len(assessments)} assessments saved to {OUTPUT_FILE}")
    print("=" * 60)
    
    if len(assessments) >= 377:
        print("SUCCESS: 377+ reached!")

if __name__ == "__main__":
    main()



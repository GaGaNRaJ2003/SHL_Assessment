"""
SHL Product Catalog Crawler - Simple & Robust Version
Crawls all Individual Test Solutions using simple pagination.

Based on pagination discovery:
- type=1 is Individual Test Solutions 
- type=2 is Pre-packaged Job Solutions (we ignore)
- 32 pages total (start=0, 12, 24, ... 372)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from urllib.parse import urljoin
from typing import List, Dict, Optional

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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page(session: requests.Session, url: str) -> Optional[str]:
    """Fetch a page with retries."""
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.text
            print(f"    Status {resp.status_code}")
        except Exception as e:
            print(f"    Error: {e}")
        time.sleep(1)
    return None


def parse_catalog_page(html: str) -> List[Dict]:
    """Parse a catalog page and extract all assessment rows."""
    soup = BeautifulSoup(html, 'html.parser')
    assessments = []
    
    # Find ALL rows with data-entity-id (these are assessment rows)
    rows = soup.find_all('tr', attrs={'data-entity-id': True})
    
    for row in rows:
        try:
            entity_id = row.get('data-entity-id')
            cells = row.find_all('td')
            
            if len(cells) < 4:
                continue
            
            # Name and URL from first cell
            link = cells[0].find('a')
            if not link:
                continue
                
            name = link.get_text(strip=True)
            href = link.get('href', '')
            url = urljoin(BASE_URL, href)
            
            # Remote support (check for image in cell 1)
            remote = "Yes" if cells[1].find('img') else "No"
            
            # Adaptive support (check for image in cell 2)
            adaptive = "Yes" if cells[2].find('img') else "No"
            
            # Test types from cell 3
            type_text = cells[3].get_text(strip=True)
            test_types = []
            for char in type_text:
                if char in TEST_TYPE_MAP:
                    test_types.append(TEST_TYPE_MAP[char])
            
            assessments.append({
                "url": url,
                "name": name,
                "description": None,
                "duration": None,
                "remote_support": remote,
                "adaptive_support": adaptive,
                "test_type": test_types
            })
            
        except Exception as e:
            print(f"    Error parsing row: {e}")
            continue
    
    return assessments


def get_description(session: requests.Session, url: str) -> Optional[str]:
    """Get description from individual assessment page."""
    html = fetch_page(session, url)
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try meta description first
    meta = soup.find('meta', {'name': 'description'})
    if meta and meta.get('content'):
        return meta.get('content')
    
    # Try finding a description paragraph
    main = soup.find('main')
    if main:
        for p in main.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 50:
                return text
    
    return None


def main():
    print("=" * 60)
    print("SHL Catalog Crawler - Simple Version")
    print("Target: Individual Test Solutions (377+)")
    print("=" * 60)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_assessments = {}
    
    # Crawl all pages for type=1 (Individual Test Solutions)
    # 32 pages x 12 items = 384 max
    print("\n[Phase 1] Crawling catalog pages...")
    
    for page_num in range(40):  # Extra margin
        start = page_num * 12
        url = f"{CATALOG_BASE}?start={start}&type=1"
        
        print(f"  Page {page_num+1} (start={start})")
        html = fetch_page(session, url)
        
        if not html:
            print(f"    Failed to fetch, stopping")
            break
        
        assessments = parse_catalog_page(html)
        
        if not assessments:
            print(f"    No assessments found, stopping")
            break
        
        for a in assessments:
            if a['url'] not in all_assessments:
                all_assessments[a['url']] = a
        
        print(f"    Found {len(assessments)} | Total: {len(all_assessments)}")
        
        # Stop if we've gone 2 pages without new items
        time.sleep(0.3)
    
    print(f"\n  Total unique assessments from catalog: {len(all_assessments)}")
    
    # Save intermediate results
    save_results(list(all_assessments.values()))
    
    # Phase 2: Enrich with descriptions
    print("\n[Phase 2] Fetching descriptions...")
    
    assessments_list = list(all_assessments.values())
    for i, assessment in enumerate(assessments_list):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(assessments_list)}")
            save_results(assessments_list)
        
        desc = get_description(session, assessment['url'])
        if desc:
            assessment['description'] = desc
        
        time.sleep(0.15)
    
    # Final save
    save_results(assessments_list)
    
    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print(f"Total assessments: {len(assessments_list)}")
    print(f"Saved to: {OUTPUT_FILE}")
    
    if len(assessments_list) >= 377:
        print("\n*** SUCCESS: 377+ assessments reached! ***")
    else:
        print(f"\n*** WARNING: Only {len(assessments_list)} found ***")


def save_results(assessments: List[Dict]):
    """Save to JSON file."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()



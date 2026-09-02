"""
SHL Product Catalog Crawler - Final Version
Based on the approach from: https://github.com/singhsourav0/SHL_Recommendation

Extracts assessments using data-entity-id attributes from the catalog tables.
Target: 377+ Individual Test Solutions
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from urllib.parse import urljoin
from typing import List, Dict, Optional

# Constants
BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/products/product-catalog/"
OUTPUT_FILE = "data/assessments.json"

# Test type code mapping
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

# Request settings
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_page(session: requests.Session, url: str, retries: int = 3) -> Optional[str]:
    """Fetch a page with retry logic."""
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=30)
            if response.status_code == 200:
                return response.text
            else:
                print(f"  [Attempt {attempt+1}] Status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  [Attempt {attempt+1}] Error: {e}")
        
        if attempt < retries - 1:
            time.sleep(2)
    
    return None


def extract_assessments_from_page(html: str, table_type: str = "Individual Test Solutions") -> List[Dict]:
    """Extract assessment data from a catalog page."""
    soup = BeautifulSoup(html, 'html.parser')
    assessments = []
    
    # Find all tables and look for the one with our target type
    tables = soup.find_all('table')
    
    for table in tables:
        # Check if this is the right table by looking at header
        header_row = table.find('tr')
        if header_row:
            header_text = header_row.get_text(strip=True)
            if table_type not in header_text:
                continue
        
        # Process all data rows (those with data-entity-id)
        rows = table.find_all('tr', attrs={'data-entity-id': True})
        
        for row in rows:
            entity_id = row.get('data-entity-id')
            cells = row.find_all('td')
            
            if len(cells) >= 4:
                # Cell 0: Assessment Name and URL
                name_cell = cells[0]
                link = name_cell.find('a')
                if link:
                    name = link.get_text(strip=True)
                    href = link.get('href', '')
                    url = urljoin(BASE_URL, href)
                else:
                    continue  # Skip if no link
                
                # Cell 1: Remote Testing (checkmark image if supported)
                remote_cell = cells[1]
                remote_img = remote_cell.find('img')
                # Check for span with class containing check
                remote_span = remote_cell.find('span')
                has_remote = remote_img is not None or (remote_span and remote_span.get_text(strip=True))
                
                # Cell 2: Adaptive/IRT (checkmark image if supported)
                adaptive_cell = cells[2]
                adaptive_img = adaptive_cell.find('img')
                adaptive_span = adaptive_cell.find('span')
                has_adaptive = adaptive_img is not None or (adaptive_span and adaptive_span.get_text(strip=True))
                
                # Cell 3: Test Types (single letter codes)
                type_cell = cells[3]
                # Get all individual type indicators (usually in spans or divs)
                type_elements = type_cell.find_all(['span', 'div'])
                test_types = []
                
                if type_elements:
                    for el in type_elements:
                        code = el.get_text(strip=True)
                        if code in TEST_TYPE_MAP:
                            test_types.append(TEST_TYPE_MAP[code])
                else:
                    # Fallback: parse text content
                    type_text = type_cell.get_text(strip=True)
                    for code in type_text.split():
                        if code in TEST_TYPE_MAP:
                            test_types.append(TEST_TYPE_MAP[code])
                
                assessments.append({
                    "entity_id": entity_id,
                    "url": url,
                    "name": name,
                    "description": None,  # Will be enriched later
                    "duration": None,  # Will be enriched later
                    "remote_support": "Yes" if has_remote else "No",
                    "adaptive_support": "Yes" if has_adaptive else "No",
                    "test_type": test_types
                })
    
    return assessments


def get_assessment_details(session: requests.Session, url: str) -> Dict:
    """Fetch additional details from an individual assessment page."""
    html = fetch_page(session, url)
    if not html:
        return {}
    
    soup = BeautifulSoup(html, 'html.parser')
    details = {}
    
    # Extract description from meta tag or page content
    meta_desc = soup.find('meta', {'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        details['description'] = meta_desc.get('content')
    else:
        # Try to find description in the main content
        main_content = soup.find('main') or soup.find('article')
        if main_content:
            paragraphs = main_content.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:
                    details['description'] = text
                    break
    
    # Look for duration/length information
    text_content = soup.get_text()
    duration_patterns = [
        r'(\d+)\s*minutes?',
        r'Duration[:\s]*(\d+)',
        r'Assessment Length[:\s]*(\d+)',
        r'(\d+)\s*mins?'
    ]
    
    for pattern in duration_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            try:
                details['duration'] = int(match.group(1))
                break
            except ValueError:
                pass
    
    return details


def crawl_catalog():
    """Main crawling function."""
    print("=" * 70)
    print("SHL Product Catalog Crawler - Final Version")
    print("Target: Individual Test Solutions (377+ assessments)")
    print("Based on: https://github.com/singhsourav0/SHL_Recommendation")
    print("=" * 70)
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    all_assessments = {}  # Use dict to deduplicate by URL
    
    # Pagination: type=1 is Individual Test Solutions, type=2 is Pre-packaged Job Solutions
    # We only want type=1
    # Each page has 12 items, pages go from start=0 to start=372+ (32+ pages)
    
    print("\n[Step 1] Crawling Individual Test Solutions catalog pages...")
    
    # Start with page 0 and continue until we find no more items
    page_num = 0
    max_pages = 40  # Safety limit
    consecutive_empty = 0
    
    while page_num < max_pages and consecutive_empty < 3:
        start = page_num * 12
        url = f"{CATALOG_URL}?start={start}&type=1"
        
        print(f"\n  Page {page_num + 1} (start={start}): {url}")
        html = fetch_page(session, url)
        
        if html:
            assessments = extract_assessments_from_page(html)
            
            if assessments:
                consecutive_empty = 0
                for a in assessments:
                    if a['url'] not in all_assessments:
                        all_assessments[a['url']] = a
                
                print(f"    Found {len(assessments)} assessments (Total unique: {len(all_assessments)})")
            else:
                consecutive_empty += 1
                print(f"    No assessments found on this page")
        else:
            consecutive_empty += 1
            print(f"    Failed to fetch page")
        
        page_num += 1
        time.sleep(0.5)  # Be polite
    
    print(f"\n  Catalog crawling complete. Total assessments: {len(all_assessments)}")
    
    # Enrich with details from individual pages
    print("\n[Step 2] Enriching assessments with details from individual pages...")
    
    assessments_list = list(all_assessments.values())
    enriched_count = 0
    
    for i, assessment in enumerate(assessments_list):
        if i % 50 == 0:
            print(f"\n  Progress: {i}/{len(assessments_list)} assessments processed")
        
        url = assessment['url']
        details = get_assessment_details(session, url)
        
        if details:
            assessment.update(details)
            enriched_count += 1
        
        # Save progress every 100 assessments
        if (i + 1) % 100 == 0:
            save_assessments(assessments_list)
            print(f"    [Saved progress: {len(assessments_list)} assessments]")
        
        time.sleep(0.2)  # Be polite
    
    print(f"\n  Enrichment complete. {enriched_count} assessments enriched with details.")
    
    # Final save
    save_assessments(assessments_list)
    
    # Summary
    print("\n" + "=" * 70)
    print("CRAWLING COMPLETE")
    print("=" * 70)
    print(f"Total assessments: {len(assessments_list)}")
    print(f"Output saved to: {OUTPUT_FILE}")
    
    if len(assessments_list) >= 377:
        print("\n*** SUCCESS: Target of 377+ assessments reached! ***")
    else:
        print(f"\n*** WARNING: Only {len(assessments_list)} assessments found. Target is 377+. ***")
    
    return assessments_list


def save_assessments(assessments: List[Dict]):
    """Save assessments to JSON file."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    # Remove entity_id from output (not needed in final format)
    output = []
    for a in assessments:
        item = {k: v for k, v in a.items() if k != 'entity_id'}
        output.append(item)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    crawl_catalog()

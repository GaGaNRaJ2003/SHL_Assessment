"""
Comprehensive SHL Product Catalog Crawler
Systematically crawls all Individual Test Solutions from the SHL catalog.
Target: 377+ assessments

URL Pattern discovered:
- Catalog pages: /products/product-catalog/?start=X&type=1
- Individual pages: 32 total (start=0,12,24...372)
- Each page shows 12 items
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from urllib.parse import urljoin, urlparse, parse_qs
from typing import List, Dict, Set, Optional, Tuple

# Constants
BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/products/product-catalog/"
OUTPUT_FILE = "data/assessments.json"
PROGRESS_FILE = "data/crawler_progress.json"

# Request settings
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def get_session() -> requests.Session:
    """Create a session with retry capabilities."""
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_page(session: requests.Session, url: str, retries: int = 3) -> Optional[str]:
    """Fetch a page with retry logic."""
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=30)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                print(f"  [404] Not found: {url}")
                return None
            else:
                print(f"  [Attempt {attempt+1}] Status {response.status_code} for {url}")
        except requests.exceptions.RequestException as e:
            print(f"  [Attempt {attempt+1}] Error: {e}")
        
        if attempt < retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return None


def extract_catalog_data(html: str, table_type: str = "Individual Test Solutions") -> List[Dict]:
    """Extract assessment URLs and metadata from a catalog page."""
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    
    # Test type code mapping
    test_type_map = {
        'A': 'Ability & Aptitude',
        'B': 'Biodata & Situational Judgement',
        'C': 'Competencies',
        'D': 'Development & 360',
        'E': 'Assessment Exercises',
        'K': 'Knowledge & Skills',
        'P': 'Personality & Behavior',
        'S': 'Simulations'
    }
    
    # Find all tables
    tables = soup.find_all('table')
    
    for table in tables:
        # Check table header to identify if it's Individual Test Solutions
        header_row = table.find('tr')
        if header_row:
            first_cell = header_row.find(['th', 'td'])
            if first_cell:
                header_text = first_cell.get_text(strip=True)
                if table_type in header_text:
                    # This is the Individual Test Solutions table
                    rows = table.find_all('tr')[1:]  # Skip header row
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            # First cell: Name and URL
                            first_cell = cells[0]
                            link = first_cell.find('a')
                            if link and link.get('href'):
                                href = link.get('href')
                                if '/view/' in href:
                                    full_url = urljoin(BASE_URL, href)
                                    name = link.get_text(strip=True)
                                    
                                    # Second cell: Remote Testing (checkmark present?)
                                    remote_cell = cells[1]
                                    has_remote = bool(remote_cell.find('img') or 
                                                     remote_cell.find('span') or 
                                                     '✓' in remote_cell.get_text())
                                    
                                    # Third cell: Adaptive/IRT
                                    adaptive_cell = cells[2]
                                    has_adaptive = bool(adaptive_cell.find('img') or 
                                                       adaptive_cell.find('span') or 
                                                       '✓' in adaptive_cell.get_text())
                                    
                                    # Fourth cell: Test Type codes
                                    type_cell = cells[3]
                                    type_text = type_cell.get_text(strip=True)
                                    test_types = []
                                    for code in type_text.split():
                                        if code in test_type_map:
                                            test_types.append(test_type_map[code])
                                    
                                    results.append({
                                        "url": full_url,
                                        "name": name,
                                        "remote_support": "Yes" if has_remote else "No",
                                        "adaptive_support": "Yes" if has_adaptive else "No",
                                        "test_type": test_types
                                    })
    
    return results


def parse_assessment_page(session: requests.Session, url: str) -> Optional[Dict]:
    """Parse an individual assessment page to extract details."""
    html = fetch_page(session, url)
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    assessment = {
        "url": url,
        "name": None,
        "description": None,
        "duration": None,
        "remote_support": None,
        "adaptive_support": None,
        "test_type": []
    }
    
    # Extract name from h1
    h1 = soup.find('h1')
    if h1:
        assessment["name"] = h1.get_text(strip=True)
    
    # Look for description in various places
    # Try meta description first
    meta_desc = soup.find('meta', {'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        assessment["description"] = meta_desc.get('content')
    
    # Try to find description in the main content
    if not assessment["description"]:
        # Look for paragraphs after h1
        content_div = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|description', re.I))
        if content_div:
            paragraphs = content_div.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 50:  # Reasonable description length
                    assessment["description"] = text
                    break
    
    # Look for duration
    duration_patterns = [
        r'(\d+)\s*minutes?',
        r'Duration[:\s]*(\d+)',
        r'Time[:\s]*(\d+)',
        r'(\d+)\s*mins?'
    ]
    
    text_content = soup.get_text()
    for pattern in duration_patterns:
        match = re.search(pattern, text_content, re.IGNORECASE)
        if match:
            assessment["duration"] = int(match.group(1))
            break
    
    # Look for Remote Testing support (usually indicated by checkmarks or icons)
    remote_indicators = ['remote', 'online', 'proctored']
    for indicator in remote_indicators:
        if re.search(rf'\b{indicator}\b', text_content, re.IGNORECASE):
            assessment["remote_support"] = "Yes"
            break
    if not assessment["remote_support"]:
        assessment["remote_support"] = "Yes"  # Default based on catalog showing checkmarks
    
    # Look for Adaptive/IRT support
    adaptive_indicators = ['adaptive', 'irt', 'computer adaptive']
    for indicator in adaptive_indicators:
        if re.search(rf'\b{indicator}\b', text_content, re.IGNORECASE):
            assessment["adaptive_support"] = "Yes"
            break
    if not assessment["adaptive_support"]:
        assessment["adaptive_support"] = "No"
    
    # Try to determine test type from content
    test_types = {
        'A': 'Ability & Aptitude',
        'B': 'Biodata & Situational Judgement',
        'C': 'Competencies',
        'D': 'Development & 360',
        'E': 'Assessment Exercises',
        'K': 'Knowledge & Skills',
        'P': 'Personality & Behavior',
        'S': 'Simulations'
    }
    
    # Look for test type indicators in the page
    for code, type_name in test_types.items():
        if type_name.lower() in text_content.lower():
            if type_name not in assessment["test_type"]:
                assessment["test_type"].append(type_name)
    
    # If no test types found, try to infer from keywords
    if not assessment["test_type"]:
        type_keywords = {
            'Ability & Aptitude': ['ability', 'aptitude', 'cognitive', 'reasoning', 'numerical', 'verbal'],
            'Knowledge & Skills': ['knowledge', 'skills', 'technical', 'programming', 'software'],
            'Personality & Behavior': ['personality', 'behavior', 'behavioural', 'opq'],
            'Biodata & Situational Judgement': ['situational', 'judgement', 'biodata', 'sjt'],
            'Simulations': ['simulation', 'simulated', 'interactive'],
            'Assessment Exercises': ['exercise', 'assessment center', 'in-tray'],
            'Development & 360': ['development', '360', 'feedback', 'leadership'],
            'Competencies': ['competenc', 'competency']
        }
        
        for type_name, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_content.lower():
                    if type_name not in assessment["test_type"]:
                        assessment["test_type"].append(type_name)
                    break
    
    return assessment


def save_progress(progress: Dict):
    """Save crawler progress."""
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2)


def load_progress() -> Dict:
    """Load crawler progress."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"crawled_pages": [], "crawled_urls": [], "assessments": []}


def save_assessments(assessments: List[Dict]):
    """Save assessments to file."""
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)


def discover_all_catalog_pages(session: requests.Session) -> List[str]:
    """Discover all catalog pages for Individual Test Solutions."""
    pages = []
    
    # First, fetch the main catalog page to find pagination info
    html = fetch_page(session, CATALOG_URL)
    if not html:
        print("Failed to fetch main catalog page")
        # Use known pagination structure as fallback
        for start in range(0, 384, 12):  # 32 pages * 12 items
            pages.append(f"{CATALOG_URL}?start={start}&type=1")
        return pages
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find pagination for Individual Test Solutions (type=1)
    # Look for links with type=1
    pagination_links = soup.find_all('a', href=re.compile(r'type=1'))
    
    max_start = 0
    for link in pagination_links:
        href = link.get('href', '')
        parsed = urlparse(href)
        params = parse_qs(parsed.query)
        if 'start' in params:
            try:
                start_val = int(params['start'][0])
                if start_val > max_start:
                    max_start = start_val
            except (ValueError, IndexError):
                pass
    
    # Also look for page numbers in text
    page_nums = re.findall(r'link "(\d+)".*?type=1', str(soup))
    for num in page_nums:
        try:
            page = int(num)
            calc_start = (page - 1) * 12
            if calc_start > max_start:
                max_start = calc_start
        except ValueError:
            pass
    
    # Generate all page URLs
    # Based on browser inspection, we know there are 32 pages (start=372 max)
    if max_start < 372:
        max_start = 372  # Use known value
    
    for start in range(0, max_start + 12, 12):
        pages.append(f"{CATALOG_URL}?start={start}&type=1")
    
    print(f"Discovered {len(pages)} catalog pages to crawl")
    return pages


def crawl_catalog():
    """Main crawling function."""
    print("=" * 60)
    print("SHL Product Catalog Crawler - Comprehensive Edition")
    print("Target: Individual Test Solutions (377+ assessments)")
    print("=" * 60)
    
    session = get_session()
    
    # Load progress
    progress = load_progress()
    crawled_pages = set(progress.get("crawled_pages", []))
    crawled_urls = set(progress.get("crawled_urls", []))
    assessments_dict = {a["url"]: a for a in progress.get("assessments", [])}
    
    print(f"\nResuming from progress: {len(assessments_dict)} assessments already crawled")
    
    # Discover all catalog pages
    print("\n[Step 1] Discovering catalog pages...")
    catalog_pages = discover_all_catalog_pages(session)
    
    # Collect all assessment data from catalog pages
    print("\n[Step 2] Extracting assessment data from catalog pages...")
    catalog_data = {}  # url -> data from catalog
    
    for i, page_url in enumerate(catalog_pages):
        print(f"  [{i+1}/{len(catalog_pages)}] Fetching: {page_url}")
        html = fetch_page(session, page_url)
        
        if html:
            items = extract_catalog_data(html)
            print(f"    Found {len(items)} assessments")
            for item in items:
                catalog_data[item["url"]] = item
            crawled_pages.add(page_url)
            
            # Save progress after each page
            progress["crawled_pages"] = list(crawled_pages)
            save_progress(progress)
        else:
            print(f"    FAILED to fetch page")
        
        time.sleep(0.5)  # Be polite
    
    print(f"\nTotal unique assessments from catalog: {len(catalog_data)}")
    
    # Enrich with detailed info from individual pages
    print("\n[Step 3] Enriching assessments with detailed info...")
    new_count = 0
    enriched_count = 0
    
    urls_to_process = list(catalog_data.keys())
    total_urls = len(urls_to_process)
    
    for i, url in enumerate(urls_to_process):
        # Get base data from catalog
        base_data = catalog_data[url]
        
        # Check if we already have this assessment enriched
        if url in assessments_dict and assessments_dict[url].get("description"):
            print(f"  [{i+1}/{total_urls}] Already enriched: {base_data['name'][:40]}...")
            continue
        
        print(f"  [{i+1}/{total_urls}] Enriching: {base_data['name'][:40]}...")
        
        # Fetch detailed info from the assessment page
        detailed = parse_assessment_page(session, url)
        
        if detailed:
            # Merge: catalog data takes priority for test_type, remote/adaptive
            # Detail page provides description and duration
            assessment = {
                "url": url,
                "name": base_data.get("name") or detailed.get("name"),
                "description": detailed.get("description"),
                "duration": detailed.get("duration"),
                "remote_support": base_data.get("remote_support", "Yes"),
                "adaptive_support": base_data.get("adaptive_support", "No"),
                "test_type": base_data.get("test_type") or detailed.get("test_type", [])
            }
            assessments_dict[url] = assessment
            enriched_count += 1
            
            if url not in crawled_urls:
                new_count += 1
            
            crawled_urls.add(url)
        else:
            # Even if detail fetch fails, save catalog data
            assessments_dict[url] = base_data
            crawled_urls.add(url)
            print(f"    Using catalog-only data")
        
        # Save progress every 20 assessments
        if (i + 1) % 20 == 0:
            progress["crawled_urls"] = list(crawled_urls)
            progress["assessments"] = list(assessments_dict.values())
            save_progress(progress)
            save_assessments(list(assessments_dict.values()))
            print(f"    [Progress saved: {len(assessments_dict)} assessments]")
        
        time.sleep(0.3)  # Be polite
    
    # Final save
    final_assessments = list(assessments_dict.values())
    progress["crawled_urls"] = list(crawled_urls)
    progress["assessments"] = final_assessments
    save_progress(progress)
    save_assessments(final_assessments)
    
    # Summary
    print("\n" + "=" * 60)
    print("CRAWLING COMPLETE")
    print("=" * 60)
    print(f"Total assessments: {len(final_assessments)}")
    print(f"New assessments this run: {new_count}")
    print(f"Enriched this run: {enriched_count}")
    print(f"Output saved to: {OUTPUT_FILE}")
    
    if len(final_assessments) >= 377:
        print("\n[SUCCESS] Target of 377+ assessments reached!")
    else:
        print(f"\n[WARNING] Only {len(final_assessments)} assessments found. Target is 377+.")
        print("Consider re-running or checking the crawler logic.")
    
    return final_assessments


if __name__ == "__main__":
    crawl_catalog()


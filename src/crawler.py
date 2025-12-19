import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set
from tqdm import tqdm
import time
import re
import os
from urllib.parse import urljoin, urlparse


BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"


def extract_test_type(text: str) -> List[str]:
    """Extract test type codes (A, B, C, D, E, K, P, S) from text."""
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
    
    found = []
    text_lower = text.lower()
    
    # Check for test type names
    for code, name in test_types.items():
        if name.lower() in text_lower:
            found.append(name)
    
    # If nothing found, check for common keywords
    if not found:
        if any(word in text_lower for word in ['ability', 'aptitude', 'cognitive']):
            found.append('Ability & Aptitude')
        if any(word in text_lower for word in ['personality', 'behavior', 'behaviour', 'trait']):
            found.append('Personality & Behavior')
        if any(word in text_lower for word in ['knowledge', 'skill', 'technical', 'programming']):
            found.append('Knowledge & Skills')
        if any(word in text_lower for word in ['competency', 'competence']):
            found.append('Competencies')
    
    return found if found else ['Unknown']


def parse_assessment_page(url: str) -> Dict:
    """Parse a single assessment page and extract metadata."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract name (usually in h1 or title)
        name = ""
        h1 = soup.find('h1')
        if h1:
            name = h1.get_text().strip()
        else:
            title = soup.find('title')
            if title:
                name = title.get_text().strip()
                name = re.sub(r'\s*\|\s*SHL.*', '', name)
        
        # Extract description (meta description or first paragraph)
        description = ""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc.get('content').strip()
        else:
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50:
                    description = text
                    break
        
        # Extract duration
        duration = None
        duration_patterns = [
            r'(\d+)\s*(?:mins?|minutes?)',
            r'(\d+)\s*(?:hour|hr)s?',
        ]
        text_content = soup.get_text()
        for pattern in duration_patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                duration = int(match.group(1))
                if 'hour' in match.group(0).lower() or 'hr' in match.group(0).lower():
                    duration *= 60
                break
        
        # Extract remote support and adaptive support
        remote_support = "No"
        adaptive_support = "No"
        
        text_lower = text_content.lower()
        if any(word in text_lower for word in ['remote', 'online', 'virtual', 'web-based']):
            remote_support = "Yes"
        if any(word in text_lower for word in ['adaptive', 'tailored', 'personalized', 'dynamic']):
            adaptive_support = "Yes"
        
        # Extract test type
        test_type = extract_test_type(text_content)
        
        return {
            'url': url,
            'name': name,
            'description': description[:512] if description else "",
            'duration': duration,
            'remote_support': remote_support,
            'adaptive_support': adaptive_support,
            'test_type': test_type
        }
    except Exception as e:
        print(f"\nError parsing {url}: {e}")
        return None


def check_sitemap() -> List[str]:
    """Check for sitemap.xml that might contain all assessment URLs."""
    sitemap_urls = [
        'https://www.shl.com/sitemap.xml',
        'https://www.shl.com/sitemap_index.xml',
    ]
    
    assessment_urls = set()
    
    for sitemap_url in sitemap_urls:
        try:
            response = requests.get(sitemap_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                urls = soup.find_all('url')
                for url in urls:
                    loc = url.find('loc')
                    if loc and '/view/' in loc.text:
                        assessment_urls.add(loc.text)
                if assessment_urls:
                    print(f"Found {len(assessment_urls)} URLs in sitemap")
                    return list(assessment_urls)
        except Exception as e:
            print(f"Sitemap check failed: {e}")
            continue
    
    return []


def find_assessment_urls_from_catalog() -> List[str]:
    """Find all assessment URLs using enhanced multi-strategy approach."""
    assessment_urls = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Strategy 1: Load URLs from train set (must have these)
    print("Loading URLs from train set...")
    try:
        import pandas as pd
        df_train = pd.read_csv('data/train.csv')
        train_urls = set(df_train['Assessment_url'].unique())
        assessment_urls.update(train_urls)
        print(f"  ✓ Added {len(train_urls)} URLs from train set")
    except Exception as e:
        print(f"  ✗ Error loading train set: {e}")
    
    # Strategy 2: Check sitemap
    print("Checking sitemap...")
    sitemap_urls = check_sitemap()
    if sitemap_urls:
        assessment_urls.update(sitemap_urls)
        print(f"  ✓ Found {len(sitemap_urls)} URLs from sitemap")
    
    # Strategy 3: Scrape main catalog page
    print("Scraping catalog page...")
    try:
        response = requests.get(CATALOG_URL, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        initial_count = len(assessment_urls)
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/view/' in href:
                if href.startswith('http'):
                    assessment_urls.add(href)
                elif href.startswith('/'):
                    assessment_urls.add(f"{BASE_URL}{href}")
                else:
                    assessment_urls.add(f"{CATALOG_URL}{href}")
        
        print(f"  ✓ Found {len(assessment_urls) - initial_count} additional URLs from catalog page")
        
        # Strategy 4: Pagination
        print("Checking pagination...")
        pagination_links = soup.find_all('a', href=True)
        for link in pagination_links:
            href = link.get('href', '')
            text = link.get_text().strip().lower()
            if any(indicator in text for indicator in ['next', 'page', '2', '3', 'more']) and ('/product-catalog' in href or '/catalog' in href):
                full_url = urljoin(CATALOG_URL, href)
                try:
                    page_response = requests.get(full_url, headers=headers, timeout=30)
                    page_soup = BeautifulSoup(page_response.content, 'html.parser')
                    page_count = len(assessment_urls)
                    for page_link in page_soup.find_all('a', href=True):
                        page_href = page_link['href']
                        if '/view/' in page_href:
                            if page_href.startswith('http'):
                                assessment_urls.add(page_href)
                            elif page_href.startswith('/'):
                                assessment_urls.add(f"{BASE_URL}{page_href}")
                    if len(assessment_urls) > page_count:
                        print(f"    Found {len(assessment_urls) - page_count} URLs from pagination")
                    time.sleep(1)
                except:
                    continue
        
        # Strategy 5: Systematic pagination
        print("Trying systematic pagination...")
        pagination_urls = try_systematic_pagination(headers)
        assessment_urls.update(pagination_urls)
        print(f"  ✓ Found {len(pagination_urls)} URLs from systematic pagination")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Strategy 6: Try Selenium (if available)
    print("Trying Selenium for JavaScript content...")
    selenium_urls = try_selenium_crawl()
    if selenium_urls:
        assessment_urls.update(selenium_urls)
        print(f"  ✓ Found {len(selenium_urls)} URLs with Selenium")
    else:
        print("  ✗ Selenium not available or failed")
    
    # Filter pre-packaged
    filtered_urls = [u for u in assessment_urls if 'pre-packaged' not in u.lower() and 'job-solution' not in u.lower()]
    
    print(f"\nTotal found: {len(assessment_urls)} URLs")
    print(f"After filtering: {len(filtered_urls)} URLs")
    return filtered_urls


def try_systematic_pagination(headers: dict) -> Set[str]:
    """Try systematic pagination patterns."""
    urls = set()
    
    bases = [
        'https://www.shl.com/products/product-catalog/',
        'https://www.shl.com/solutions/products/product-catalog/',
    ]
    
    for base in bases:
        for start in range(0, 500, 12):
            for ptype in [1, 2]:
                try:
                    url = f"{base}?start={start}&type={ptype}"
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        found = False
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if '/view/' in href:
                                found = True
                                if href.startswith('http'):
                                    urls.add(href)
                                elif href.startswith('/'):
                                    urls.add(f"{BASE_URL}{href}")
                        if not found and start > 0:
                            break
                    time.sleep(0.3)
                except:
                    continue
    
    return urls


def try_selenium_crawl() -> Set[str]:
    """Try Selenium crawl."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager
        
        urls = set()
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            for catalog_url in [
                'https://www.shl.com/solutions/products/product-catalog/',
                'https://www.shl.com/products/product-catalog/',
            ]:
                driver.get(catalog_url)
                time.sleep(5)
                
                # Scroll to load
                for _ in range(25):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
                
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute('href')
                    if href and '/view/' in href:
                        urls.add(href)
        finally:
            driver.quit()
        
        return urls
    except:
        return set()


def crawl_catalog() -> List[Dict]:
    """Crawl SHL product catalog and extract all Individual Test Solutions."""
    print("Starting catalog crawl...")
    print(f"Target: 377+ Individual Test Solutions")
    print("="*60)
    
    # Get assessment URLs
    assessment_urls = find_assessment_urls_from_catalog()
    
    if not assessment_urls:
        print("Warning: No assessment URLs found.")
        return []
    
    # Parse each assessment page
    assessments = []
    failed = 0
    
    print(f"\nParsing {len(assessment_urls)} assessment pages...")
    print("="*60)
    for url in tqdm(assessment_urls, desc="Parsing assessments"):
        assessment = parse_assessment_page(url)
        if assessment and assessment.get('name'):
            assessments.append(assessment)
        else:
            failed += 1
        time.sleep(0.5)  # Rate limiting
    
    print(f"\n{'='*60}")
    print(f"Successfully crawled {len(assessments)} assessments")
    print(f"Failed to parse: {failed} URLs")
    
    if len(assessments) < 377:
        print(f"\nWarning: Only found {len(assessments)} assessments, target is 377+")
        print("\nPossible solutions:")
        print("1. The website uses JavaScript to load content - consider using Selenium/Playwright")
        print("2. There may be an API endpoint - check browser Network tab")
        print("3. Assessments might be in a different section of the site")
        print("4. Try inspecting the page source in browser DevTools")
    
    return assessments


if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    
    assessments = crawl_catalog()
    
    output_path = 'data/assessments.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"Saved {len(assessments)} assessments to {output_path}")
    print(f"Target: 377+ assessments. Actual: {len(assessments)}")
    
    if assessments:
        print("\nSample assessment:")
        print(json.dumps(assessments[0], indent=2))

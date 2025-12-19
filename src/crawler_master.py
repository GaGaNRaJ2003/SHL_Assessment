"""
Master crawler - combines all strategies and saves incrementally.
This is the main crawler to use for finding 377+ assessments.
"""
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set
from tqdm import tqdm
import time
import re
import os
from urllib.parse import urljoin
import pandas as pd

BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"


def extract_test_type(text: str) -> List[str]:
    """Extract test type codes."""
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
    
    for code, name in test_types.items():
        if name.lower() in text_lower:
            found.append(name)
    
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


def parse_assessment_page(url: str, max_retries: int = 2) -> Dict:
    """Parse assessment page with retry."""
    for attempt in range(max_retries):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            name = ""
            h1 = soup.find('h1')
            if h1:
                name = h1.get_text().strip()
            else:
                title = soup.find('title')
                if title:
                    name = re.sub(r'\s*\|\s*SHL.*', '', title.get_text().strip())
            
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc.get('content').strip()
            else:
                for p in soup.find_all('p'):
                    text = p.get_text().strip()
                    if len(text) > 50:
                        description = text
                        break
            
            duration = None
            text_content = soup.get_text()
            for pattern in [r'(\d+)\s*(?:mins?|minutes?)', r'(\d+)\s*(?:hour|hr)s?']:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    duration = int(match.group(1))
                    if 'hour' in match.group(0).lower():
                        duration *= 60
                    break
            
            text_lower = text_content.lower()
            remote_support = "Yes" if any(w in text_lower for w in ['remote', 'online', 'virtual']) else "No"
            adaptive_support = "Yes" if any(w in text_lower for w in ['adaptive', 'tailored']) else "No"
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
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            return None
    return None


def discover_all_urls() -> Set[str]:
    """Discover all URLs using all available strategies."""
    all_urls = set()
    
    print("="*70)
    print("MASTER CRAWLER - All Strategies")
    print("="*70)
    print()
    
    # Strategy 1: Train set (CRITICAL - must have these)
    print("[1/6] Loading train set URLs...")
    try:
        df_train = pd.read_csv('data/train.csv')
        train_urls = set(df_train['Assessment_url'].unique())
        all_urls.update(train_urls)
        print(f"    ✓ Added {len(train_urls)} URLs from train set")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Strategy 2: Sitemap
    print("\n[2/6] Checking sitemap...")
    sitemap_urls = check_sitemap()
    if sitemap_urls:
        all_urls.update(sitemap_urls)
        print(f"    ✓ Found {len(sitemap_urls)} URLs from sitemap")
    else:
        print("    ✗ No sitemap found")
    
    # Strategy 3: Main catalog pages
    print("\n[3/6] Scraping catalog pages...")
    catalog_urls = scrape_catalog_pages()
    all_urls.update(catalog_urls)
    print(f"    ✓ Found {len(catalog_urls)} URLs from catalog pages")
    
    # Strategy 4: Systematic pagination
    print("\n[4/6] Systematic pagination discovery...")
    pagination_urls = systematic_pagination()
    all_urls.update(pagination_urls)
    print(f"    ✓ Found {len(pagination_urls)} URLs from pagination")
    
    # Strategy 5: Selenium (JavaScript content)
    print("\n[5/6] Using Selenium for JavaScript content...")
    selenium_urls = selenium_crawl()
    all_urls.update(selenium_urls)
    print(f"    ✓ Found {len(selenium_urls)} URLs with Selenium")
    
    # Strategy 6: Try both URL patterns for train set slugs
    print("\n[6/6] Trying URL pattern variations...")
    pattern_urls = try_url_patterns()
    all_urls.update(pattern_urls)
    print(f"    ✓ Found {len(pattern_urls)} URLs from pattern matching")
    
    print()
    print("="*70)
    print(f"TOTAL UNIQUE URLs DISCOVERED: {len(all_urls)}")
    print("="*70)
    
    return all_urls


def check_sitemap() -> Set[str]:
    """Check sitemap."""
    urls = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    sitemaps = [
        'https://www.shl.com/sitemap.xml',
        'https://www.shl.com/sitemap_index.xml',
        'https://www.shl.com/robots.txt',
    ]
    
    for sitemap_url in sitemaps:
        try:
            response = requests.get(sitemap_url, headers=headers, timeout=10)
            if response.status_code == 200:
                if 'robots' in sitemap_url:
                    # Extract sitemap URLs from robots.txt
                    for line in response.text.split('\n'):
                        if 'sitemap' in line.lower():
                            sm_url = line.split(':', 1)[1].strip()
                            try:
                                sm_response = requests.get(sm_url, headers=headers, timeout=10)
                                soup = BeautifulSoup(sm_response.content, 'xml')
                                for url_tag in soup.find_all('url'):
                                    loc = url_tag.find('loc')
                                    if loc and '/view/' in loc.text:
                                        urls.add(loc.text)
                            except:
                                pass
                else:
                    soup = BeautifulSoup(response.content, 'xml')
                    for url_tag in soup.find_all('url'):
                        loc = url_tag.find('loc')
                        if loc and '/view/' in loc.text:
                            urls.add(loc.text)
        except:
            continue
    
    return urls


def scrape_catalog_pages() -> Set[str]:
    """Scrape catalog pages."""
    urls = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    pages = [
        'https://www.shl.com/solutions/products/product-catalog/',
        'https://www.shl.com/products/product-catalog/',
    ]
    
    for page_url in pages:
        try:
            response = requests.get(page_url, headers=headers, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/view/' in href:
                        if href.startswith('http'):
                            urls.add(href)
                        elif href.startswith('/'):
                            urls.add(f"{BASE_URL}{href}")
        except:
            continue
    
    return urls


def systematic_pagination() -> Set[str]:
    """Systematic pagination."""
    urls = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    bases = [
        'https://www.shl.com/products/product-catalog/',
        'https://www.shl.com/solutions/products/product-catalog/',
    ]
    
    for base in bases:
        for start in range(0, 600, 12):
            for ptype in [1, 2]:
                try:
                    url = f"{base}?start={start}&type={ptype}"
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        page_urls = set()
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if '/view/' in href:
                                if href.startswith('http'):
                                    page_urls.add(href)
                                elif href.startswith('/'):
                                    page_urls.add(f"{BASE_URL}{href}")
                        if page_urls:
                            urls.update(page_urls)
                        elif start > 0:
                            break  # No more pages
                    time.sleep(0.2)
                except:
                    continue
    
    return urls


def selenium_crawl() -> Set[str]:
    """Selenium crawl."""
    urls = set()
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager
        
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
                
                # Scroll extensively
                for _ in range(30):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.5)
                
                # Extract links
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute('href')
                    if href and '/view/' in href:
                        urls.add(href)
        finally:
            driver.quit()
    except Exception as e:
        pass
    
    return urls


def try_url_patterns() -> Set[str]:
    """Try URL patterns."""
    urls = set()
    
    # Get slugs from train set
    try:
        df = pd.read_csv('data/train.csv')
        slugs = set()
        for url in df['Assessment_url'].unique():
            slug = url.split('/view/')[-1].rstrip('/')
            slugs.add(slug)
        
        # Try both URL patterns
        bases = [
            'https://www.shl.com/products/product-catalog/view/',
            'https://www.shl.com/solutions/products/product-catalog/view/',
        ]
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        for base in bases:
            for slug in list(slugs)[:20]:  # Test first 20
                test_url = f"{base}{slug}/"
                try:
                    response = requests.head(test_url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        urls.add(test_url)
                except:
                    pass
    except:
        pass
    
    return urls


def crawl_master() -> List[Dict]:
    """Master crawl function."""
    print("Starting MASTER CRAWLER...")
    print("Target: 377+ Individual Test Solutions")
    print()
    
    # Discover all URLs
    all_urls = discover_all_urls()
    
    # Filter pre-packaged
    filtered = [u for u in all_urls if 'pre-packaged' not in u.lower() and 'job-solution' not in u.lower()]
    
    print()
    print(f"After filtering: {len(filtered)} URLs")
    print()
    
    if len(filtered) < 377:
        print(f"⚠ Warning: Only {len(filtered)} URLs found (target: 377+)")
        print("Continuing with available URLs...")
        print()
    
    # Parse all pages
    print(f"Parsing {len(filtered)} assessment pages...")
    print("="*70)
    
    assessments = []
    failed = 0
    
    for url in tqdm(filtered, desc="Parsing"):
        assessment = parse_assessment_page(url)
        if assessment and assessment.get('name'):
            assessments.append(assessment)
        else:
            failed += 1
        time.sleep(0.2)
    
    print(f"\n{'='*70}")
    print(f"Successfully parsed: {len(assessments)}")
    print(f"Failed: {failed}")
    print(f"Target: 377+. Actual: {len(assessments)}")
    print("="*70)
    
    return assessments


if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    
    assessments = crawl_master()
    
    output_path = 'data/assessments.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(assessments)} assessments to {output_path}")
    
    if assessments:
        print("\nSample assessment:")
        print(json.dumps(assessments[0], indent=2))



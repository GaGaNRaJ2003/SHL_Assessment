"""
Aggressive crawler that tries multiple strategies to find all 377+ assessments.
This version tries harder and explores more thoroughly.
"""
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set
from tqdm import tqdm
import time
import re
import os
from urllib.parse import urljoin, urlparse, parse_qs, unquote
import sys

# Try to import Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


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
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
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
                    name = title.get_text().strip()
                    name = re.sub(r'\s*\|\s*SHL.*', '', name)
            
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
            
            duration = None
            text_content = soup.get_text()
            for pattern in [r'(\d+)\s*(?:mins?|minutes?)', r'(\d+)\s*(?:hour|hr)s?']:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    duration = int(match.group(1))
                    if 'hour' in match.group(0).lower():
                        duration *= 60
                    break
            
            remote_support = "Yes" if any(w in text_content.lower() for w in ['remote', 'online', 'virtual']) else "No"
            adaptive_support = "Yes" if any(w in text_content.lower() for w in ['adaptive', 'tailored']) else "No"
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


def get_urls_from_selenium() -> Set[str]:
    """Use Selenium to get all URLs."""
    if not SELENIUM_AVAILABLE:
        return set()
    
    urls = set()
    print("Using Selenium to crawl JavaScript content...")
    
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # Load catalog
            driver.get(CATALOG_URL)
            time.sleep(5)
            
            # Scroll multiple times
            for _ in range(15):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            # Extract links
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute('href')
                if href and '/view/' in href:
                    urls.add(href)
            
            print(f"  Found {len(urls)} URLs with Selenium")
        finally:
            driver.quit()
    except Exception as e:
        print(f"  Selenium error: {e}")
    
    return urls


def get_urls_from_pagination() -> Set[str]:
    """Systematic pagination discovery."""
    urls = set()
    print("Trying systematic pagination...")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # Try both URL patterns
    bases = [
        'https://www.shl.com/products/product-catalog/',
        'https://www.shl.com/solutions/products/product-catalog/',
    ]
    
    for base in bases:
        for start in range(0, 500, 12):
            for ptype in [1, 2]:
                try:
                    url = f"{base}?start={start}&type={ptype}"
                    response = requests.get(url, headers=headers, timeout=10)
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
                            break  # No more pages
                    time.sleep(0.3)
                except:
                    continue
    
    print(f"  Found {len(urls)} URLs from pagination")
    return urls


def get_urls_from_train_set() -> Set[str]:
    """Get URLs from train set."""
    urls = set()
    try:
        import pandas as pd
        df = pd.read_csv('data/train.csv')
        urls = set(df['Assessment_url'].unique())
        print(f"  Found {len(urls)} URLs from train set")
    except:
        pass
    return urls


def get_urls_from_sitemap() -> Set[str]:
    """Try sitemap."""
    urls = set()
    print("Checking sitemap...")
    
    sitemaps = [
        'https://www.shl.com/sitemap.xml',
        'https://www.shl.com/sitemap_index.xml',
        'https://www.shl.com/robots.txt',
    ]
    
    for sitemap_url in sitemaps:
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                if 'sitemap' in sitemap_url:
                    soup = BeautifulSoup(response.content, 'xml')
                    for url_tag in soup.find_all('url'):
                        loc = url_tag.find('loc')
                        if loc and '/view/' in loc.text:
                            urls.add(loc.text)
                elif 'robots' in sitemap_url:
                    # Extract sitemap URLs from robots.txt
                    for line in response.text.split('\n'):
                        if 'sitemap' in line.lower():
                            sitemap_line = line.split(':', 1)[1].strip()
                            try:
                                sm_response = requests.get(sitemap_line, timeout=10)
                                sm_soup = BeautifulSoup(sm_response.content, 'xml')
                                for url_tag in sm_soup.find_all('url'):
                                    loc = url_tag.find('loc')
                                    if loc and '/view/' in loc.text:
                                        urls.add(loc.text)
                            except:
                                pass
        except:
            continue
    
    if urls:
        print(f"  Found {len(urls)} URLs from sitemap")
    return urls


def crawl_aggressive() -> List[Dict]:
    """Aggressive crawling with all strategies."""
    print("="*70)
    print("AGGRESSIVE CRAWLER - Finding All 377+ Assessments")
    print("="*70)
    print()
    
    all_urls = set()
    
    # Strategy 1: Sitemap
    all_urls.update(get_urls_from_sitemap())
    
    # Strategy 2: Train set (must have these)
    all_urls.update(get_urls_from_train_set())
    
    # Strategy 3: Selenium
    all_urls.update(get_urls_from_selenium())
    
    # Strategy 4: Pagination
    all_urls.update(get_urls_from_pagination())
    
    # Strategy 5: Main catalog page
    print("Scraping main catalog page...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(CATALOG_URL, headers=headers, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/view/' in href:
                if href.startswith('http'):
                    all_urls.add(href)
                elif href.startswith('/'):
                    all_urls.add(f"{BASE_URL}{href}")
        print(f"  Found additional URLs from main page")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Filter pre-packaged
    filtered = [u for u in all_urls if 'pre-packaged' not in u.lower() and 'job-solution' not in u.lower()]
    
    print()
    print("="*70)
    print(f"Total unique URLs found: {len(all_urls)}")
    print(f"After filtering: {len(filtered)}")
    print("="*70)
    print()
    
    # Parse all pages
    print(f"Parsing {len(filtered)} assessment pages...")
    assessments = []
    
    for url in tqdm(filtered, desc="Parsing"):
        assessment = parse_assessment_page(url)
        if assessment and assessment.get('name'):
            assessments.append(assessment)
        time.sleep(0.2)
    
    print(f"\nSuccessfully parsed {len(assessments)} assessments")
    
    return assessments


if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    
    assessments = crawl_aggressive()
    
    output_path = 'data/assessments.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(assessments)} assessments")
    print(f"Target: 377+. Actual: {len(assessments)}")



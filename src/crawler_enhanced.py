"""
Enhanced crawler with multiple strategies to find all 377+ assessments.
Uses Selenium for JavaScript content, API discovery, and improved pagination.
"""
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set
from tqdm import tqdm
import time
import re
import os
from urllib.parse import urljoin, urlparse, parse_qs
import sys

# Try to import Selenium (optional)
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
    print("Warning: Selenium not installed. Install with: pip install selenium webdriver-manager")


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


def parse_assessment_page(url: str, max_retries: int = 3) -> Dict:
    """Parse a single assessment page with retry logic."""
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            timeout = 45 if attempt > 0 else 30
            response = requests.get(url, headers=headers, timeout=timeout)
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
            
            remote_support = "No"
            adaptive_support = "No"
            
            text_lower = text_content.lower()
            if any(word in text_lower for word in ['remote', 'online', 'virtual', 'web-based']):
                remote_support = "Yes"
            if any(word in text_lower for word in ['adaptive', 'tailored', 'personalized', 'dynamic']):
                adaptive_support = "Yes"
            
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
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                print(f"\nTimeout on {url}, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                print(f"\nError parsing {url}: Timeout after {max_retries} attempts")
                return None
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"\nError parsing {url}: {e}")
            return None
    return None


def find_urls_with_selenium() -> List[str]:
    """Use Selenium to find URLs from JavaScript-loaded content."""
    if not SELENIUM_AVAILABLE:
        print("Selenium not available, skipping JavaScript-based crawling")
        return []
    
    print("Using Selenium to crawl JavaScript-loaded content...")
    assessment_urls = set()
    
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # Load main catalog page
            print("  Loading catalog page...")
            driver.get(CATALOG_URL)
            time.sleep(5)  # Wait for JavaScript to load
            
            # Scroll to load more content
            print("  Scrolling to load content...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scrolls = 10
            
            while scroll_attempts < max_scrolls:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            # Find all links
            print("  Extracting links...")
            links = driver.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href and '/view/' in href:
                        assessment_urls.add(href)
                except:
                    continue
            
            # Try clicking "Load More" or pagination buttons if they exist
            try:
                load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Load More')] | //a[contains(text(), 'More')] | //a[contains(text(), 'Next')]")
                for button in load_more_buttons[:5]:  # Limit to 5 clicks
                    try:
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(3)
                        # Extract new links
                        new_links = driver.find_elements(By.TAG_NAME, "a")
                        for link in new_links:
                            href = link.get_attribute('href')
                            if href and '/view/' in href:
                                assessment_urls.add(href)
                    except:
                        continue
            except:
                pass
            
            print(f"  Found {len(assessment_urls)} URLs with Selenium")
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"  Error with Selenium: {e}")
        print("  Falling back to requests-based crawling")
    
    return list(assessment_urls)


def try_api_endpoints() -> List[str]:
    """Try to find API endpoints that return assessment data."""
    print("Trying to find API endpoints...")
    assessment_urls = set()
    
    # Common API endpoint patterns
    api_patterns = [
        'https://www.shl.com/api/products',
        'https://www.shl.com/api/catalog',
        'https://www.shl.com/api/assessments',
        'https://www.shl.com/solutions/products/product-catalog/api',
        'https://www.shl.com/api/v1/products',
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    for api_url in api_patterns:
        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Try to extract URLs from JSON response
                    if isinstance(data, dict):
                        # Recursively search for URLs
                        def extract_urls(obj, urls_set):
                            if isinstance(obj, dict):
                                for v in obj.values():
                                    extract_urls(v, urls_set)
                            elif isinstance(obj, list):
                                for item in obj:
                                    extract_urls(item, urls_set)
                            elif isinstance(obj, str) and '/view/' in obj:
                                urls_set.add(obj)
                        
                        extract_urls(data, assessment_urls)
                        if assessment_urls:
                            print(f"  Found {len(assessment_urls)} URLs from API: {api_url}")
                            return list(assessment_urls)
                except:
                    pass
        except:
            continue
    
    return []


def find_urls_with_pagination() -> List[str]:
    """Try systematic pagination discovery."""
    print("Trying systematic pagination...")
    assessment_urls = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Try different pagination patterns
    base_urls = [
        'https://www.shl.com/products/product-catalog/',
        'https://www.shl.com/solutions/products/product-catalog/',
    ]
    
    for base_url in base_urls:
        # Try different pagination parameters
        for start in range(0, 500, 12):  # Common pagination size
            for page_type in [1, 2]:  # Different types
                pagination_url = f"{base_url}?start={start}&type={page_type}"
                try:
                    response = requests.get(pagination_url, headers=headers, timeout=15)
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
                            assessment_urls.update(page_urls)
                            print(f"  Found {len(page_urls)} URLs at start={start}, type={page_type}")
                        else:
                            # If no URLs found, might have reached the end
                            break
                    time.sleep(0.5)
                except:
                    continue
    
    return list(assessment_urls)


def find_urls_from_train_set() -> List[str]:
    """Extract URLs from train set to ensure we have those assessments."""
    print("Extracting URLs from train set...")
    train_urls = set()
    
    try:
        import pandas as pd
        df_train = pd.read_csv('data/train.csv')
        train_urls = set(df_train['Assessment_url'].unique())
        print(f"  Found {len(train_urls)} unique URLs in train set")
    except Exception as e:
        print(f"  Error reading train set: {e}")
    
    return list(train_urls)


def crawl_catalog_enhanced() -> List[Dict]:
    """Enhanced crawler with multiple strategies."""
    print("="*70)
    print("Enhanced Crawler - Multiple Strategies")
    print("="*70)
    print(f"Target: 377+ Individual Test Solutions\n")
    
    all_urls = set()
    
    # Strategy 1: Try API endpoints
    api_urls = try_api_endpoints()
    if api_urls:
        all_urls.update(api_urls)
        print(f"Strategy 1 (API): Found {len(api_urls)} URLs\n")
    
    # Strategy 2: Use Selenium for JavaScript content
    selenium_urls = find_urls_with_selenium()
    if selenium_urls:
        all_urls.update(selenium_urls)
        print(f"Strategy 2 (Selenium): Found {len(selenium_urls)} URLs\n")
    
    # Strategy 3: Systematic pagination
    pagination_urls = find_urls_with_pagination()
    if pagination_urls:
        all_urls.update(pagination_urls)
        print(f"Strategy 3 (Pagination): Found {len(pagination_urls)} URLs\n")
    
    # Strategy 4: Get URLs from train set (to ensure we have those)
    train_urls = find_urls_from_train_set()
    if train_urls:
        all_urls.update(train_urls)
        print(f"Strategy 4 (Train Set): Added {len(train_urls)} URLs\n")
    
    # Strategy 5: Original catalog scraping
    print("Strategy 5: Original catalog scraping...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(CATALOG_URL, headers=headers, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/view/' in href:
                if href.startswith('http'):
                    all_urls.add(href)
                elif href.startswith('/'):
                    all_urls.add(f"{BASE_URL}{href}")
        print(f"  Found {len([u for u in all_urls if u not in train_urls])} additional URLs\n")
    except Exception as e:
        print(f"  Error: {e}\n")
    
    # Filter out pre-packaged solutions
    filtered_urls = []
    for url in all_urls:
        if 'pre-packaged' not in url.lower() and 'job-solution' not in url.lower():
            filtered_urls.append(url)
    
    print("="*70)
    print(f"Total unique URLs found: {len(all_urls)}")
    print(f"After filtering (removing pre-packaged): {len(filtered_urls)}")
    print("="*70)
    
    if len(filtered_urls) < 377:
        print(f"\nWarning: Only found {len(filtered_urls)} URLs (target: 377+)")
        print("Trying additional strategies...")
        
        # Try more URL patterns
        print("\nTrying additional URL discovery...")
        # Check if there's a pattern we can follow
        # Try to construct URLs based on known patterns
        known_slugs = ['java-8-new', 'python-new', 'sql-server-new']
        for slug in known_slugs:
            test_urls = [
                f"https://www.shl.com/products/product-catalog/view/{slug}/",
                f"https://www.shl.com/solutions/products/product-catalog/view/{slug}/",
            ]
            for test_url in test_urls:
                if test_url not in filtered_urls:
                    filtered_urls.append(test_url)
    
    # Parse all assessment pages
    print(f"\nParsing {len(filtered_urls)} assessment pages...")
    print("="*70)
    
    assessments = []
    failed = 0
    
    for url in tqdm(filtered_urls, desc="Parsing assessments"):
        assessment = parse_assessment_page(url)
        if assessment and assessment.get('name'):
            assessments.append(assessment)
        else:
            failed += 1
        time.sleep(0.3)  # Rate limiting
    
    print(f"\n{'='*70}")
    print(f"Successfully crawled {len(assessments)} assessments")
    print(f"Failed to parse: {failed} URLs")
    
    if len(assessments) < 377:
        print(f"\nWarning: Only found {len(assessments)} assessments, target is 377+")
        print("\nNext steps to try:")
        print("1. Manually inspect the SHL catalog page in browser")
        print("2. Check Network tab for API calls")
        print("3. Look for sitemap.xml or robots.txt")
        print("4. Try different base URLs or category pages")
    else:
        print(f"\nSuccess! Found {len(assessments)} assessments (target: 377+)")
    
    return assessments


if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    
    assessments = crawl_catalog_enhanced()
    
    output_path = 'data/assessments.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"Saved {len(assessments)} assessments to {output_path}")
    print(f"Target: 377+ assessments. Actual: {len(assessments)}")
    
    if assessments:
        print("\nSample assessment:")
        print(json.dumps(assessments[0], indent=2))



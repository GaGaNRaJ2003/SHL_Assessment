"""
Smart crawler that uses train set URLs as seed and discovers more systematically.
This version tries to find all 377+ assessments through intelligent discovery.
"""
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set
from tqdm import tqdm
import time
import re
import os
from urllib.parse import urljoin, unquote
import pandas as pd

BASE_URL = "https://www.shl.com"


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
    """Parse assessment page."""
    for attempt in range(max_retries):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            name = h1.get_text().strip() if (h1 := soup.find('h1')) else ""
            if not name:
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


def get_train_set_urls() -> Set[str]:
    """Get all URLs from train set."""
    urls = set()
    try:
        df = pd.read_csv('data/train.csv')
        urls = set(df['Assessment_url'].unique())
        print(f"Loaded {len(urls)} URLs from train set")
    except Exception as e:
        print(f"Error loading train set: {e}")
    return urls


def discover_urls_with_selenium() -> Set[str]:
    """Use Selenium to discover URLs from JavaScript-loaded content."""
    urls = set()
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        
        print("Starting Selenium crawler...")
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # Try both catalog URLs
            catalog_urls = [
                'https://www.shl.com/solutions/products/product-catalog/',
                'https://www.shl.com/products/product-catalog/',
            ]
            
            for catalog_url in catalog_urls:
                print(f"  Loading {catalog_url}...")
                driver.get(catalog_url)
                
                # Wait for page to load
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except:
                    pass
                
                time.sleep(3)
                
                # Scroll multiple times to trigger lazy loading
                print("  Scrolling to load content...")
                last_height = 0
                scroll_count = 0
                max_scrolls = 30
                
                while scroll_count < max_scrolls:
                    # Scroll down
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
                    # Check if new content loaded
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        scroll_count += 1
                        if scroll_count > 3:
                            break
                    else:
                        scroll_count = 0
                        last_height = new_height
                    
                    # Extract links periodically
                    if scroll_count % 5 == 0:
                        links = driver.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            try:
                                href = link.get_attribute('href')
                                if href and '/view/' in href:
                                    urls.add(href)
                            except:
                                pass
                
                # Final extraction of all links
                print("  Extracting all links...")
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        if href and '/view/' in href:
                            urls.add(href)
                    except:
                        pass
                
                # Try clicking "Load More" or pagination buttons
                try:
                    buttons = driver.find_elements(By.XPATH, 
                        "//button[contains(text(), 'Load')] | "
                        "//a[contains(text(), 'More')] | "
                        "//a[contains(text(), 'Next')] | "
                        "//button[contains(@class, 'load')] | "
                        "//a[contains(@class, 'pagination')]"
                    )
                    for button in buttons[:10]:
                        try:
                            driver.execute_script("arguments[0].click();", button)
                            time.sleep(2)
                            # Extract new links
                            new_links = driver.find_elements(By.TAG_NAME, "a")
                            for link in new_links:
                                href = link.get_attribute('href')
                                if href and '/view/' in href:
                                    urls.add(href)
                        except:
                            continue
                except:
                    pass
            
            print(f"  Found {len(urls)} URLs with Selenium")
            
        finally:
            driver.quit()
            
    except ImportError:
        print("  Selenium not available. Install with: pip install selenium webdriver-manager")
    except Exception as e:
        print(f"  Selenium error: {e}")
    
    return urls


def discover_urls_pagination() -> Set[str]:
    """Systematic pagination discovery."""
    urls = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    print("Trying systematic pagination...")
    
    bases = [
        ('https://www.shl.com/products/product-catalog/', 'products'),
        ('https://www.shl.com/solutions/products/product-catalog/', 'solutions'),
    ]
    
    for base_url, base_name in bases:
        print(f"  Trying {base_name} base URL...")
        
        # Try different pagination patterns
        for page_size in [12, 24, 48]:
            consecutive_empty = 0
            for start in range(0, 600, page_size):
                for ptype in [1, 2]:
                    try:
                        url = f"{base_url}?start={start}&type={ptype}"
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
                                consecutive_empty = 0
                                print(f"    Found {len(page_urls)} URLs at start={start}, type={ptype}")
                            else:
                                consecutive_empty += 1
                                if consecutive_empty > 2:
                                    break
                        time.sleep(0.3)
                    except Exception as e:
                        continue
                
                if consecutive_empty > 2:
                    break
    
    print(f"  Found {len(urls)} URLs from pagination")
    return urls


def discover_urls_from_existing() -> Set[str]:
    """Try to discover URLs by checking existing assessments for related links."""
    urls = set()
    
    # Load existing assessments
    try:
        with open('data/assessments.json', 'r', encoding='utf-8') as f:
            existing = json.load(f)
        
        # Extract slugs
        slugs = set()
        for assessment in existing:
            url = assessment.get('url', '')
            if '/view/' in url:
                slug = url.split('/view/')[-1].rstrip('/')
                slugs.add(slug)
        
        # Try variations of slugs
        print(f"Trying variations of {len(slugs)} known slugs...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        bases = [
            'https://www.shl.com/products/product-catalog/view/',
            'https://www.shl.com/solutions/products/product-catalog/view/',
        ]
        
        for base in bases:
            for slug in list(slugs)[:20]:  # Test with first 20
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


def crawl_smart() -> List[Dict]:
    """Smart crawl using multiple strategies."""
    print("="*70)
    print("SMART CRAWLER - Finding All 377+ Assessments")
    print("="*70)
    print()
    
    all_urls = set()
    
    # Strategy 1: Train set (must have these)
    print("Strategy 1: Loading train set URLs...")
    train_urls = get_train_set_urls()
    all_urls.update(train_urls)
    print(f"  ✓ Added {len(train_urls)} URLs from train set\n")
    
    # Strategy 2: Selenium for JavaScript content
    print("Strategy 2: Using Selenium for JavaScript content...")
    selenium_urls = discover_urls_with_selenium()
    all_urls.update(selenium_urls)
    print(f"  ✓ Added {len(selenium_urls)} URLs from Selenium\n")
    
    # Strategy 3: Systematic pagination
    print("Strategy 3: Systematic pagination...")
    pagination_urls = discover_urls_pagination()
    all_urls.update(pagination_urls)
    print(f"  ✓ Added {len(pagination_urls)} URLs from pagination\n")
    
    # Strategy 4: Check sitemap
    print("Strategy 4: Checking sitemap...")
    sitemap_urls = check_sitemap_comprehensive()
    all_urls.update(sitemap_urls)
    print(f"  ✓ Added {len(sitemap_urls)} URLs from sitemap\n")
    
    # Strategy 5: Main catalog page
    print("Strategy 5: Scraping main catalog pages...")
    catalog_urls = scrape_catalog_pages()
    all_urls.update(catalog_urls)
    print(f"  ✓ Added {len(catalog_urls)} URLs from catalog pages\n")
    
    # Filter pre-packaged
    filtered = [u for u in all_urls if 'pre-packaged' not in u.lower() and 'job-solution' not in u.lower()]
    
    print("="*70)
    print(f"TOTAL UNIQUE URLs: {len(all_urls)}")
    print(f"AFTER FILTERING: {len(filtered)}")
    print("="*70)
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


def check_sitemap_comprehensive() -> Set[str]:
    """Comprehensive sitemap checking."""
    urls = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # Check robots.txt
    try:
        response = requests.get('https://www.shl.com/robots.txt', headers=headers, timeout=10)
        if response.status_code == 200:
            for line in response.text.split('\n'):
                if 'sitemap' in line.lower():
                    sitemap_url = line.split(':', 1)[1].strip()
                    try:
                        sm_response = requests.get(sitemap_url, headers=headers, timeout=10)
                        if sm_response.status_code == 200:
                            soup = BeautifulSoup(sm_response.content, 'xml')
                            for url_tag in soup.find_all('url'):
                                loc = url_tag.find('loc')
                                if loc and '/view/' in loc.text:
                                    urls.add(loc.text)
                    except:
                        pass
    except:
        pass
    
    # Direct sitemap checks
    for sitemap in [
        'https://www.shl.com/sitemap.xml',
        'https://www.shl.com/sitemap_index.xml',
        'https://www.shl.com/sitemap-products.xml',
    ]:
        try:
            response = requests.get(sitemap, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                for url_tag in soup.find_all('url'):
                    loc = url_tag.find('loc')
                    if loc and '/view/' in loc.text:
                        urls.add(loc.text)
        except:
            continue
    
    return urls


def scrape_catalog_pages() -> Set[str]:
    """Scrape main catalog pages."""
    urls = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    catalog_pages = [
        'https://www.shl.com/solutions/products/product-catalog/',
        'https://www.shl.com/products/product-catalog/',
        'https://www.shl.com/solutions/products/product-catalog/individual-test-solutions/',
    ]
    
    for page_url in catalog_pages:
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


if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    
    assessments = crawl_smart()
    
    output_path = 'data/assessments.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(assessments)} assessments to {output_path}")
    
    if assessments:
        print("\nSample assessment:")
        print(json.dumps(assessments[0], indent=2))



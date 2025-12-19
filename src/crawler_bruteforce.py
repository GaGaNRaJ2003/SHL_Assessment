"""
Brute-force URL discovery - tries common assessment name patterns.
This complements the other crawlers by checking if URLs exist.
"""
import requests
from typing import Set
import time
from tqdm import tqdm

BASE_URL = "https://www.shl.com"


def try_url_patterns() -> Set[str]:
    """Try common assessment name patterns."""
    urls = set()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # Common assessment name patterns from train set and known assessments
    common_patterns = [
        # Programming languages
        'java', 'python', 'javascript', 'sql', 'html', 'css', 'c++', 'csharp', 'php', 'ruby',
        # Frameworks
        'react', 'angular', 'vue', 'node', 'django', 'flask', 'spring', 'net',
        # Skills
        'excel', 'word', 'powerpoint', 'outlook', 'sharepoint',
        # Domains
        'sales', 'marketing', 'finance', 'accounting', 'hr', 'customer-service',
        # Test types
        'verbal', 'numerical', 'logical', 'cognitive', 'personality',
        # Common suffixes
        '-new', '-v1', '-v2', '-7-1', '-8-0', '-entry-level', '-advanced',
    ]
    
    # Base URL patterns
    bases = [
        'https://www.shl.com/products/product-catalog/view/',
        'https://www.shl.com/solutions/products/product-catalog/view/',
    ]
    
    print("Trying common assessment name patterns...")
    print("(This may take a while - checking if URLs exist)")
    
    # Try combinations
    for base in bases:
        for pattern in tqdm(common_patterns[:20], desc=f"Checking {base.split('/')[-3]}"):  # Limit to first 20
            test_urls = [
                f"{base}{pattern}/",
                f"{base}{pattern}-new/",
                f"{base}{pattern}-assessment/",
            ]
            for test_url in test_urls:
                try:
                    response = requests.head(test_url, headers=headers, timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        urls.add(test_url)
                except:
                    pass
                time.sleep(0.1)
    
    return urls


if __name__ == "__main__":
    urls = try_url_patterns()
    print(f"\nFound {len(urls)} potential URLs from pattern matching")
    for url in list(urls)[:10]:
        print(f"  {url}")



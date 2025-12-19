# Crawler Strategy - Finding 377+ Assessments

## Current Status
- **Found:** 48 assessments (from initial crawl)
- **Target:** 377+ assessments
- **Gap:** Need to find ~329 more assessments

## Strategies Implemented

### 1. Master Crawler (`src/crawler_master.py`)
**Status:** Running in background

This crawler combines all strategies:
- ✅ Loads train set URLs (54 URLs - must have these)
- ✅ Checks sitemap.xml
- ✅ Scrapes catalog pages
- ✅ Systematic pagination discovery
- ✅ Selenium for JavaScript content
- ✅ URL pattern matching

### 2. Enhanced Crawler (`src/crawler_enhanced.py`)
Multi-strategy approach with detailed logging.

### 3. Smart Crawler (`src/crawler_smart.py`)
Intelligent discovery using train set as seed.

### 4. Aggressive Crawler (`src/crawler_aggressive.py`)
Tries harder with more pagination patterns.

## Why We're Not Finding 377+

The SHL website likely:
1. **Loads content via JavaScript** - Requires Selenium/Playwright
2. **Uses an API endpoint** - Need to find the actual API
3. **Has complex pagination** - May need to discover the exact pattern
4. **Requires authentication** - Some content might be behind login

## Next Steps to Try

### Option A: Manual Investigation (Recommended)
1. Open SHL catalog in browser: https://www.shl.com/solutions/products/product-catalog/
2. Open Developer Tools (F12)
3. Go to Network tab
4. Reload page and look for:
   - API calls (JSON responses)
   - XHR/Fetch requests
   - Any endpoint returning assessment data
5. Check if there's a "Load More" button or infinite scroll
6. Inspect page source for embedded JSON data

### Option B: Enhanced Selenium
- Add explicit waits for dynamic content
- Try clicking all buttons/links that might load more
- Scroll more aggressively
- Wait for specific elements to appear

### Option C: API Discovery
- Check browser Network tab for API calls
- Try common API patterns:
  - `/api/products`
  - `/api/catalog`
  - `/api/assessments`
  - GraphQL endpoints

### Option D: URL Pattern Generation
- Extract all slugs from train set
- Try generating URLs based on patterns
- Check if URLs exist (HEAD requests)

## Current Crawlers Running

1. `crawler_smart.py` - Running in background
2. `crawler_master.py` - Running in background

## How to Check Progress

```powershell
# Check current count
python -c "import json; print(len(json.load(open('data/assessments.json'))))"

# Check if crawler is still running
Get-Process python | Where-Object {$_.Path -like "*venv*"}
```

## If Still < 377 After All Strategies

You may need to:
1. **Manually inspect the website** to understand its structure
2. **Contact SHL** for API access or data export
3. **Use a different approach** - perhaps the assessments are in a different location
4. **Check if there's a different catalog URL** or section

## Recommendation

Let the master crawler finish, then:
1. Check the final count
2. If still < 377, manually inspect the website
3. Look for API endpoints in browser Network tab
4. Consider using Playwright instead of Selenium (more modern)



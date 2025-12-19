"""
Analyze which queries have low recall and what assessments are being missed.
This will help us target improvements better.
"""
import sys
import os
import csv
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.advanced_retriever import retrieve_advanced
from src.retriever import get_vector_db
from src.url_utils import normalize_url_to_slug, get_all_url_variants
import json

def main():
    # Load assessments to get names
    with open('data/assessments.json', 'r', encoding='utf-8') as f:
        assessments = json.load(f)
    
    url_to_name = {}
    for ass in assessments:
        url_to_name[ass['url']] = ass['name']
        for alt_url in ass.get('alternate_urls', []):
            url_to_name[alt_url] = ass['name']
    
    # Load train data
    train_queries = defaultdict(set)
    train_urls = defaultdict(list)
    
    with open('data/train.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['Query'].strip()
            url = row['Assessment_url'].strip()
            train_queries[query].add(normalize_url_to_slug(url))
            train_urls[query].append(url)
    
    vector_db = get_vector_db()
    
    print("="*70)
    print("LOW RECALL QUERY ANALYSIS")
    print("="*70)
    
    results = []
    
    for query, relevant_slugs in train_queries.items():
        recommendations = retrieve_advanced(query, vector_db, top_k=10, use_xgboost_rerank=True)
        
        recommended_slugs = set()
        for r in recommendations:
            url = r.get('url', '')
            alternate_urls = r.get('alternate_urls', [])
            variants = get_all_url_variants(url, alternate_urls)
            recommended_slugs.update(variants)
        
        hits = len(relevant_slugs & recommended_slugs)
        recall = hits / len(relevant_slugs) if relevant_slugs else 0
        
        missed = relevant_slugs - recommended_slugs
        
        # Get names of missed assessments
        missed_names = []
        for url in train_urls[query]:
            slug = normalize_url_to_slug(url)
            if slug in missed:
                name = url_to_name.get(url, 'Unknown')
                missed_names.append(name)
        
        results.append({
            'query': query,
            'recall': recall,
            'hits': hits,
            'total': len(relevant_slugs),
            'missed': list(missed),
            'missed_names': missed_names
        })
    
    # Sort by recall
    results.sort(key=lambda x: x['recall'])
    
    print("\nQueries with LOWEST Recall:")
    print("-"*70)
    for r in results[:5]:
        print(f"\nQuery: {r['query'][:80]}...")
        print(f"  Recall: {r['recall']:.2%} ({r['hits']}/{r['total']})")
        print(f"  Missed Assessments ({len(r['missed_names'])}):")
        for name in r['missed_names'][:5]:
            print(f"    - {name}")
    
    print("\n" + "="*70)
    print("PATTERN ANALYSIS")
    print("="*70)
    
    # Find common patterns in missed assessments
    all_missed_names = []
    for r in results:
        all_missed_names.extend(r['missed_names'])
    
    from collections import Counter
    missed_counts = Counter(all_missed_names)
    
    print("\nMost Frequently Missed Assessments:")
    for name, count in missed_counts.most_common(10):
        print(f"  {name}: missed in {count} queries")
    
    # Analyze query types with low recall
    low_recall_queries = [r for r in results if r['recall'] < 0.5]
    print(f"\nQueries with recall < 50%: {len(low_recall_queries)}/{len(results)}")
    
    if low_recall_queries:
        print("\nCommon patterns in low-recall queries:")
        patterns = {
            'consultant': sum(1 for r in low_recall_queries if 'consultant' in r['query'].lower()),
            'qa': sum(1 for r in low_recall_queries if 'qa' in r['query'].lower() or 'quality' in r['query'].lower()),
            'marketing': sum(1 for r in low_recall_queries if 'marketing' in r['query'].lower()),
            'manager': sum(1 for r in low_recall_queries if 'manager' in r['query'].lower()),
        }
        for pattern, count in patterns.items():
            if count > 0:
                print(f"  {pattern}: {count} queries")

if __name__ == "__main__":
    main()


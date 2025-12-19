"""
Comprehensive verification of recall improvements and strategies.
Analyzes URL normalization effectiveness and identifies bottlenecks.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import json
import csv
from collections import defaultdict
from src.advanced_retriever import retrieve_advanced
from src.retriever import get_vector_db
from src.url_utils import normalize_url_to_slug, get_all_url_variants

def analyze_url_matching():
    """Analyze if URL normalization is working correctly."""
    print("="*70)
    print("URL NORMALIZATION VERIFICATION")
    print("="*70)
    
    # Load train data
    train_queries = defaultdict(set)
    train_urls = []
    with open('data/train.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['Query'].strip()
            url = row['Assessment_url'].strip()
            train_queries[query].add(normalize_url_to_slug(url))
            train_urls.append(url)
    
    # Load assessments
    with open('data/assessments.json', 'r', encoding='utf-8') as f:
        assessments = json.load(f)
    
    # Check URL coverage
    train_slugs = set()
    for url in train_urls:
        train_slugs.add(normalize_url_to_slug(url))
    
    assessment_slugs = set()
    for a in assessments:
        url = a.get('url', '')
        alternate_urls = a.get('alternate_urls', [])
        variants = get_all_url_variants(url, alternate_urls)
        assessment_slugs.update(variants)
    
    # Coverage analysis
    missing_slugs = train_slugs - assessment_slugs
    coverage = len(train_slugs & assessment_slugs) / len(train_slugs) if train_slugs else 0
    
    print(f"\nTrain Set URLs: {len(train_urls)}")
    print(f"Unique Train Slugs: {len(train_slugs)}")
    print(f"Assessment Slugs (with alternates): {len(assessment_slugs)}")
    print(f"Coverage: {coverage:.2%} ({len(train_slugs & assessment_slugs)}/{len(train_slugs)})")
    
    if missing_slugs:
        print(f"\nMissing Slugs ({len(missing_slugs)}):")
        for slug in list(missing_slugs)[:10]:
            print(f"  - {slug}")
        if len(missing_slugs) > 10:
            print(f"  ... and {len(missing_slugs) - 10} more")
    else:
        print("\n[SUCCESS] All train set URLs are covered!")
    
    return coverage, missing_slugs


def per_query_analysis():
    """Analyze recall per query to identify bottlenecks."""
    print("\n" + "="*70)
    print("PER-QUERY RECALL ANALYSIS")
    print("="*70)
    
    vector_db = get_vector_db()
    
    train_queries = defaultdict(set)
    with open('data/train.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['Query'].strip()
            url = row['Assessment_url'].strip()
            train_queries[query].add(normalize_url_to_slug(url))
    
    results = []
    for query, relevant_slugs in train_queries.items():
        try:
            # Get recommendations
            recommendations = retrieve_advanced(query, vector_db, top_k=10, use_llm_rerank=False)
            
            # Get recommended slugs
            recommended_slugs = set()
            for r in recommendations:
                url = r.get('url', '')
                alternate_urls = r.get('alternate_urls', [])
                variants = get_all_url_variants(url, alternate_urls)
                recommended_slugs.update(variants)
            
            # Calculate recall
            hits = len(relevant_slugs & recommended_slugs)
            recall = hits / len(relevant_slugs) if relevant_slugs else 0
            
            # Find which relevant URLs were missed
            missed = relevant_slugs - recommended_slugs
            
            results.append({
                'query': query[:60] + '...' if len(query) > 60 else query,
                'relevant_count': len(relevant_slugs),
                'hits': hits,
                'recall': recall,
                'missed_count': len(missed),
                'missed_slugs': list(missed)[:3]  # Show first 3
            })
        except Exception as e:
            print(f"Error with query: {e}")
            results.append({
                'query': query[:60] + '...' if len(query) > 60 else query,
                'relevant_count': len(relevant_slugs),
                'hits': 0,
                'recall': 0.0,
                'missed_count': len(relevant_slugs),
                'missed_slugs': []
            })
    
    # Sort by recall (lowest first)
    results.sort(key=lambda x: x['recall'])
    
    print("\nQueries with Lowest Recall:")
    print("-" * 70)
    for r in results[:5]:
        print(f"\nQuery: {r['query']}")
        print(f"  Recall: {r['recall']:.2%} ({r['hits']}/{r['relevant_count']})")
        print(f"  Missed: {r['missed_count']} assessments")
        if r['missed_slugs']:
            print(f"  Sample missed slugs: {', '.join(r['missed_slugs'][:3])}")
    
    print("\nQueries with Highest Recall:")
    print("-" * 70)
    for r in results[-5:]:
        print(f"\nQuery: {r['query']}")
        print(f"  Recall: {r['recall']:.2%} ({r['hits']}/{r['relevant_count']})")
        print(f"  Missed: {r['missed_count']} assessments")
    
    # Statistics
    mean_recall = sum(r['recall'] for r in results) / len(results) if results else 0
    min_recall = min(r['recall'] for r in results) if results else 0
    max_recall = max(r['recall'] for r in results) if results else 0
    
    print("\n" + "="*70)
    print("RECALL STATISTICS")
    print("="*70)
    print(f"Mean Recall@10: {mean_recall:.4f} ({mean_recall*100:.2f}%)")
    print(f"Min Recall@10: {min_recall:.4f} ({min_recall*100:.2f}%)")
    print(f"Max Recall@10: {max_recall:.4f} ({max_recall*100:.2f}%)")
    print(f"Queries with 0% recall: {sum(1 for r in results if r['recall'] == 0)}")
    print(f"Queries with 100% recall: {sum(1 for r in results if r['recall'] == 1.0)}")
    
    return results


def verify_alternate_urls():
    """Verify that alternate URLs are correctly generated and stored."""
    print("\n" + "="*70)
    print("ALTERNATE URLS VERIFICATION")
    print("="*70)
    
    with open('data/assessments.json', 'r', encoding='utf-8') as f:
        assessments = json.load(f)
    
    total_assessments = len(assessments)
    with_alternates = sum(1 for a in assessments if a.get('alternate_urls'))
    without_alternates = total_assessments - with_alternates
    
    print(f"\nTotal Assessments: {total_assessments}")
    print(f"With Alternate URLs: {with_alternates} ({with_alternates/total_assessments*100:.1f}%)")
    print(f"Without Alternate URLs: {without_alternates} ({without_alternates/total_assessments*100:.1f}%)")
    
    # Sample check
    print("\nSample Assessments with Alternate URLs:")
    count = 0
    for a in assessments:
        if a.get('alternate_urls') and count < 3:
            print(f"\n  Name: {a.get('name', 'N/A')[:50]}")
            print(f"  Primary URL: {a.get('url', 'N/A')[:80]}")
            print(f"  Alternate URLs: {len(a.get('alternate_urls', []))}")
            for alt in a.get('alternate_urls', [])[:2]:
                print(f"    - {alt[:80]}")
            count += 1
    
    return with_alternates / total_assessments if total_assessments > 0 else 0


def suggest_improvements(results):
    """Suggest improvements based on analysis."""
    print("\n" + "="*70)
    print("IMPROVEMENT SUGGESTIONS")
    print("="*70)
    
    # Analyze low-recall queries
    low_recall = [r for r in results if r['recall'] < 0.3]
    high_missed = [r for r in results if r['missed_count'] > 5]
    
    suggestions = []
    
    if low_recall:
        suggestions.append({
            'issue': f"{len(low_recall)} queries have recall < 30%",
            'suggestion': "Consider query expansion, synonym dictionaries, or domain-specific embeddings"
        })
    
    if high_missed:
        suggestions.append({
            'issue': f"{len(high_missed)} queries missing >5 relevant assessments",
            'suggestion': "Increase top_k in retrieval (currently 40 candidates), or improve semantic matching"
        })
    
    # Check for common patterns in missed assessments
    all_missed = []
    for r in results:
        all_missed.extend(r.get('missed_slugs', []))
    
    if all_missed:
        from collections import Counter
        missed_counts = Counter(all_missed)
        most_missed = missed_counts.most_common(5)
        
        if most_missed:
            suggestions.append({
                'issue': f"Most frequently missed assessments: {', '.join([s[0] for s in most_missed[:3]])}",
                'suggestion': "Review these assessments' descriptions/names - may need better keyword matching or description enrichment"
            })
    
    suggestions.append({
        'issue': "LLM re-ranking is failing (API model errors)",
        'suggestion': "Fix Gemini API model names or use alternative re-ranking approach"
    })
    
    suggestions.append({
        'issue': "Current recall: ~36.67%",
        'suggestion': "Consider: 1) Increasing retrieval candidates (top_k*4 to top_k*6), 2) Better query preprocessing, 3) Cross-encoder re-ranking, 4) BM25 hybrid search"
    })
    
    print("\nKey Issues and Suggestions:")
    for i, s in enumerate(suggestions, 1):
        print(f"\n{i}. Issue: {s['issue']}")
        print(f"   Suggestion: {s['suggestion']}")
    
    return suggestions


def main():
    """Run all verification analyses."""
    print("\n" + "="*70)
    print("RECALL IMPROVEMENT VERIFICATION REPORT")
    print("="*70)
    
    # 1. URL Matching Analysis
    coverage, missing_slugs = analyze_url_matching()
    
    # 2. Alternate URLs Verification
    alt_url_coverage = verify_alternate_urls()
    
    # 3. Per-Query Analysis
    results = per_query_analysis()
    
    # 4. Improvement Suggestions
    suggestions = suggest_improvements(results)
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    print(f"[OK] URL Coverage: {coverage:.2%}")
    print(f"[OK] Alternate URLs Coverage: {alt_url_coverage:.2%}")
    print(f"[OK] Mean Recall@10: {sum(r['recall'] for r in results) / len(results):.4f}" if results else "N/A")
    print(f"[OK] Improvement Suggestions: {len(suggestions)}")
    
    if coverage < 1.0:
        print(f"\n[WARNING] {len(missing_slugs)} train set URLs are missing from assessments!")
    else:
        print("\n[SUCCESS] All train set URLs are covered in assessments")
    
    if alt_url_coverage < 0.95:
        print(f"\n[WARNING] Only {alt_url_coverage:.1%} assessments have alternate URLs")
    else:
        print("\n[SUCCESS] Most assessments have alternate URLs")


if __name__ == "__main__":
    main()


"""Evaluate with different top_k values to find optimal retrieval."""
import json
import csv
from collections import defaultdict
from src.retriever import retrieve_candidates, get_vector_db

def normalize_url(url):
    """Extract slug from URL."""
    url = url.lower().strip().rstrip('/')
    if '/view/' in url:
        return url.split('/view/')[-1].rstrip('/')
    return url

def evaluate_with_topk(vector_db, train_queries, top_k, eval_k=10):
    """Evaluate with specific top_k retrieval, evaluating top eval_k."""
    recalls = []
    for query, relevant_slugs in train_queries.items():
        results = retrieve_candidates(query, vector_db, top_k=top_k)
        
        # Get recommended slugs from top eval_k results
        recommended_slugs = set()
        for r in results[:eval_k]:
            recommended_slugs.add(normalize_url(r['url']))
            for alt_url in r.get('alternate_urls', []):
                recommended_slugs.add(normalize_url(alt_url))
        
        hits = len(relevant_slugs & recommended_slugs)
        recall = hits / len(relevant_slugs) if relevant_slugs else 0
        recalls.append(recall)
    
    return sum(recalls) / len(recalls) if recalls else 0

def main():
    print("Loading vector database...")
    vector_db = get_vector_db()
    
    print("Loading train data...")
    train_queries = defaultdict(set)
    with open('data/train.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['Query'].strip()
            url = row['Assessment_url'].strip()
            train_queries[query].add(normalize_url(url))
    
    print(f"Found {len(train_queries)} unique queries\n")
    
    # Test different top_k values
    print("Testing different retrieval depths...")
    for top_k in [10, 15, 20, 30, 50]:
        recall = evaluate_with_topk(vector_db, train_queries, top_k)
        print(f"  top_k={top_k:2d} -> Mean Recall@10: {recall:.4f}")
    
    # Detailed evaluation with top_k=30
    print("\n" + "=" * 60)
    print("Detailed results with top_k=30:")
    print("=" * 60)
    
    for query, relevant_slugs in train_queries.items():
        results = retrieve_candidates(query, vector_db, top_k=30)
        
        recommended_slugs = set()
        for r in results[:10]:
            recommended_slugs.add(normalize_url(r['url']))
            for alt_url in r.get('alternate_urls', []):
                recommended_slugs.add(normalize_url(alt_url))
        
        hits = len(relevant_slugs & recommended_slugs)
        recall = hits / len(relevant_slugs) if relevant_slugs else 0
        
        print(f"\nQuery: {query[:70]}...")
        print(f"  Relevant: {len(relevant_slugs)}, Hits: {hits}, Recall: {recall:.2%}")
        if hits > 0:
            print(f"  Matched: {list(relevant_slugs & recommended_slugs)[:3]}")
        
        # Show what we're recommending vs what's expected
        missed = relevant_slugs - recommended_slugs
        if missed:
            print(f"  Missing: {list(missed)[:3]}...")

if __name__ == "__main__":
    main()


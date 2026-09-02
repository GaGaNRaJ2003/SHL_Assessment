"""Evaluate with advanced retriever."""
import json
import csv
from collections import defaultdict
from src.advanced_retriever import retrieve_advanced
from src.retriever import get_vector_db

def normalize_url(url):
    """Extract slug from URL."""
    url = url.lower().strip().rstrip('/')
    if '/view/' in url:
        return url.split('/view/')[-1].rstrip('/')
    return url

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
    
    recalls = []
    for query, relevant_slugs in train_queries.items():
        print(f"Query: {query[:70]}...")
        
        # Use advanced retriever
        results = retrieve_advanced(query, vector_db, top_k=10)
        
        # Get recommended slugs (including alternate URLs)
        recommended_slugs = set()
        for r in results:
            recommended_slugs.add(normalize_url(r['url']))
            for alt_url in r.get('alternate_urls', []):
                recommended_slugs.add(normalize_url(alt_url))
        
        # Calculate recall
        hits = len(relevant_slugs & recommended_slugs)
        recall = hits / len(relevant_slugs) if relevant_slugs else 0
        recalls.append(recall)
        
        print(f"  Relevant: {len(relevant_slugs)}, Hits: {hits}, Recall@10: {recall:.4f}")
        if hits > 0:
            matched = list(relevant_slugs & recommended_slugs)[:5]
            print(f"  Matched: {matched}")
        else:
            missing = list(relevant_slugs)[:3]
            print(f"  Missing: {missing}")
        print()
    
    mean_recall = sum(recalls) / len(recalls) if recalls else 0
    print("=" * 60)
    print(f"MEAN RECALL@10 (Advanced): {mean_recall:.4f} ({mean_recall*100:.2f}%)")
    print("=" * 60)
    
    # Show improvement breakdown
    print("\nPer-query breakdown:")
    for i, (query, recall) in enumerate(zip(train_queries.keys(), recalls)):
        print(f"  {i+1}. {recall:.2%} - {query[:50]}...")

if __name__ == "__main__":
    main()



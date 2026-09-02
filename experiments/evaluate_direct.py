"""Direct evaluation without API - just retriever."""
import json
import csv
from collections import defaultdict
from src.retriever import retrieve_candidates, get_vector_db

def normalize_url(url):
    """Normalize URL for comparison - extract slug."""
    url = url.lower().strip().rstrip('/')
    # Extract slug from URL
    if '/view/' in url:
        slug = url.split('/view/')[-1].rstrip('/')
        return slug
    return url

def main():
    # Load vector DB
    print("Loading vector database...")
    vector_db = get_vector_db()
    
    # Load train data
    print("Loading train data...")
    train_queries = defaultdict(set)
    with open('data/train.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['Query'].strip()
            url = row['Assessment_url'].strip()
            train_queries[query].add(normalize_url(url))
    
    print(f"Found {len(train_queries)} unique queries")
    
    # Evaluate
    recalls = []
    for query, relevant_slugs in train_queries.items():
        # Get recommendations (increase top_k for better recall)
        results = retrieve_candidates(query, vector_db, top_k=15)
        
        # Get recommended slugs (including alternate URLs)
        recommended_slugs = set()
        for r in results[:10]:  # Take top 10 for evaluation
            recommended_slugs.add(normalize_url(r['url']))
            # Also add alternate URLs
            for alt_url in r.get('alternate_urls', []):
                recommended_slugs.add(normalize_url(alt_url))
        
        # Calculate recall
        hits = len(relevant_slugs & recommended_slugs)
        recall = hits / len(relevant_slugs) if relevant_slugs else 0
        recalls.append(recall)
        
        print(f"\nQuery: {query[:80]}...")
        print(f"  Relevant: {len(relevant_slugs)}, Hits: {hits}, Recall@10: {recall:.4f}")
        if hits > 0:
            matched = relevant_slugs & recommended_slugs
            print(f"  Matched: {list(matched)[:3]}")
    
    mean_recall = sum(recalls) / len(recalls) if recalls else 0
    print(f"\n{'='*60}")
    print(f"MEAN RECALL@10: {mean_recall:.4f}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()


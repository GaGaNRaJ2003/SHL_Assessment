"""Evaluation with LLM re-ranking."""
import json
import csv
from collections import defaultdict
from src.retriever import retrieve_candidates, get_vector_db
from src.reranker import rerank_assessments

def normalize_url(url):
    """Normalize URL for comparison - extract slug."""
    url = url.lower().strip().rstrip('/')
    if '/view/' in url:
        slug = url.split('/view/')[-1].rstrip('/')
        return slug
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
        print(f"Query: {query[:60]}...")
        
        # Get more candidates for re-ranking
        results = retrieve_candidates(query, vector_db, top_k=25)
        print(f"  Retrieved: {len(results)} candidates")
        
        # Re-rank with LLM
        reranked = rerank_assessments(query, results, top_k=10)
        print(f"  Re-ranked: {len(reranked)} results")
        
        # Get recommended slugs (including alternate URLs)
        recommended_slugs = set()
        for r in reranked:
            recommended_slugs.add(normalize_url(r['url']))
            for alt_url in r.get('alternate_urls', []):
                recommended_slugs.add(normalize_url(alt_url))
        
        # Calculate recall
        hits = len(relevant_slugs & recommended_slugs)
        recall = hits / len(relevant_slugs) if relevant_slugs else 0
        recalls.append(recall)
        
        print(f"  Relevant: {len(relevant_slugs)}, Hits: {hits}, Recall@10: {recall:.4f}")
        if hits > 0:
            matched = list(relevant_slugs & recommended_slugs)[:3]
            print(f"  Matched: {matched}")
        print()
    
    mean_recall = sum(recalls) / len(recalls) if recalls else 0
    print("=" * 60)
    print(f"MEAN RECALL@10 (with re-ranking): {mean_recall:.4f}")
    print("=" * 60)

if __name__ == "__main__":
    main()



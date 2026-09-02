"""Evaluate ensemble retriever."""
import json
import csv
from collections import defaultdict
from src.ensemble_retriever import ensemble_retrieve
from src.retriever import get_vector_db

def normalize_url(url):
    """Extract slug from URL."""
    url = url.lower().strip().rstrip('/')
    if '/view/' in url:
        return url.split('/view/')[-1].rstrip('/')
    return url

def main():
    print("=" * 70)
    print("ENSEMBLE RETRIEVER EVALUATION")
    print("=" * 70)
    
    print("\nLoading vector database...")
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
    
    # Test with and without LLM re-ranking
    print("Testing ensemble retriever WITH LLM re-ranking:")
    print("-" * 70)
    
    recalls_with_llm = []
    for query, relevant_slugs in train_queries.items():
        print(f"\nQuery: {query[:60]}...")
        
        results = ensemble_retrieve(query, vector_db, top_k=10, use_llm_rerank=True)
        
        recommended_slugs = set()
        for r in results:
            recommended_slugs.add(normalize_url(r['url']))
            for alt_url in r.get('alternate_urls', []):
                recommended_slugs.add(normalize_url(alt_url))
        
        hits = len(relevant_slugs & recommended_slugs)
        recall = hits / len(relevant_slugs) if relevant_slugs else 0
        recalls_with_llm.append(recall)
        
        print(f"  Relevant: {len(relevant_slugs)}, Hits: {hits}, Recall@10: {recall:.4f}")
        if hits > 0:
            matched = list(relevant_slugs & recommended_slugs)[:5]
            print(f"  Matched: {matched}")
        else:
            missing = list(relevant_slugs)[:3]
            print(f"  Missing: {missing}")
    
    mean_recall_with_llm = sum(recalls_with_llm) / len(recalls_with_llm) if recalls_with_llm else 0
    
    print("\n" + "=" * 70)
    print("Testing ensemble retriever WITHOUT LLM re-ranking:")
    print("-" * 70)
    
    recalls_without_llm = []
    for query, relevant_slugs in train_queries.items():
        print(f"\nQuery: {query[:60]}...")
        
        results = ensemble_retrieve(query, vector_db, top_k=10, use_llm_rerank=False)
        
        recommended_slugs = set()
        for r in results:
            recommended_slugs.add(normalize_url(r['url']))
            for alt_url in r.get('alternate_urls', []):
                recommended_slugs.add(normalize_url(alt_url))
        
        hits = len(relevant_slugs & recommended_slugs)
        recall = hits / len(relevant_slugs) if relevant_slugs else 0
        recalls_without_llm.append(recall)
        
        print(f"  Relevant: {len(relevant_slugs)}, Hits: {hits}, Recall@10: {recall:.4f}")
        if hits > 0:
            matched = list(relevant_slugs & recommended_slugs)[:5]
            print(f"  Matched: {matched}")
    
    mean_recall_without_llm = sum(recalls_without_llm) / len(recalls_without_llm) if recalls_without_llm else 0
    
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Mean Recall@10 WITH LLM re-ranking:    {mean_recall_with_llm:.4f} ({mean_recall_with_llm*100:.2f}%)")
    print(f"Mean Recall@10 WITHOUT LLM re-ranking: {mean_recall_without_llm:.4f} ({mean_recall_without_llm*100:.2f}%)")
    
    if mean_recall_with_llm >= mean_recall_without_llm:
        print(f"\n✓ LLM re-ranking improves recall by {((mean_recall_with_llm - mean_recall_without_llm) * 100):.2f}%")
        best_method = "WITH LLM"
        best_recall = mean_recall_with_llm
    else:
        print(f"\n⚠ LLM re-ranking decreases recall by {((mean_recall_without_llm - mean_recall_with_llm) * 100):.2f}%")
        best_method = "WITHOUT LLM"
        best_recall = mean_recall_without_llm
    
    print(f"\nBest method: {best_method}")
    print(f"Best Recall@10: {best_recall:.4f} ({best_recall*100:.2f}%)")
    print("=" * 70)

if __name__ == "__main__":
    main()


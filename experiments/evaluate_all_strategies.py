"""Comprehensive evaluation of all retrieval strategies."""
import json
import csv
from collections import defaultdict
from src.advanced_retriever import retrieve_advanced
from src.ensemble_retriever import ensemble_retrieve
from src.retriever import get_vector_db
from src.url_utils import normalize_url_to_slug, get_all_url_variants

def evaluate_strategy(strategy_name, retrieve_func, vector_db, train_queries, **kwargs):
    """Evaluate a retrieval strategy using unified URL normalization."""
    print(f"\n{'='*60}")
    print(f"Evaluating: {strategy_name}")
    print(f"{'='*60}")
    
    recalls = []
    for query, relevant_slugs in train_queries.items():
        try:
            results = retrieve_func(query, vector_db, **kwargs)
            
            # Get recommended slugs (including alternate URLs) using unified normalization
            recommended_slugs = set()
            for r in results:
                url = r.get('url', '')
                alternate_urls = r.get('alternate_urls', [])
                # Get all URL variants (primary + alternates) normalized to slugs
                variants = get_all_url_variants(url, alternate_urls)
                recommended_slugs.update(variants)
            
            # Calculate recall
            hits = len(relevant_slugs & recommended_slugs)
            recall = hits / len(relevant_slugs) if relevant_slugs else 0
            recalls.append(recall)
            
        except Exception as e:
            print(f"Error with query: {e}")
            recalls.append(0.0)
    
    mean_recall = sum(recalls) / len(recalls) if recalls else 0
    print(f"\nMean Recall@10: {mean_recall:.4f} ({mean_recall*100:.2f}%)")
    
    return mean_recall, recalls

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
            # Use unified normalization to extract slug
            train_queries[query].add(normalize_url_to_slug(url))
    
    print(f"Found {len(train_queries)} unique queries")
    
    # Test all strategies
    results = {}
    
    # Strategy 1: Advanced retriever (baseline)
    recall1, _ = evaluate_strategy(
        "Advanced Retriever (Rule-based)",
        retrieve_advanced,
        vector_db,
        train_queries,
        top_k=10,
        use_llm_rerank=False
    )
    results['Advanced (Rule-based)'] = recall1
    
    # Strategy 2: Advanced + LLM re-ranking
    recall2, _ = evaluate_strategy(
        "Advanced Retriever + LLM Re-ranking",
        retrieve_advanced,
        vector_db,
        train_queries,
        top_k=10,
        use_llm_rerank=True
    )
    results['Advanced + LLM'] = recall2
    
    # Strategy 3: Ensemble (without LLM)
    recall3, _ = evaluate_strategy(
        "Ensemble Retriever (No LLM)",
        ensemble_retrieve,
        vector_db,
        train_queries,
        top_k=10,
        use_llm_rerank=False
    )
    results['Ensemble (No LLM)'] = recall3
    
    # Strategy 4: Ensemble + LLM
    recall4, _ = evaluate_strategy(
        "Ensemble Retriever + LLM Re-ranking",
        ensemble_retrieve,
        vector_db,
        train_queries,
        top_k=10,
        use_llm_rerank=True
    )
    results['Ensemble + LLM'] = recall4
    
    # Summary
    print("\n" + "="*60)
    print("FINAL RESULTS SUMMARY")
    print("="*60)
    
    best_strategy = max(results.items(), key=lambda x: x[1])
    print(f"\nBest Strategy: {best_strategy[0]}")
    print(f"Best Recall@10: {best_strategy[1]:.4f} ({best_strategy[1]*100:.2f}%)")
    
    print("\nAll Strategies:")
    for strategy, recall in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"  {strategy:30s}: {recall:.4f} ({recall*100:.2f}%)")
    
    # Ensure we didn't decrease recall
    baseline = results['Advanced (Rule-based)']
    if best_strategy[1] < baseline:
        print(f"\n⚠️  WARNING: Best strategy ({best_strategy[1]:.4f}) is lower than baseline ({baseline:.4f})")
        print("Using baseline strategy for final predictions.")
        return 'Advanced (Rule-based)'
    else:
        print(f"\n[SUCCESS] Best strategy improves over baseline by {((best_strategy[1]/baseline - 1) * 100):.1f}%")
        return best_strategy[0]

if __name__ == "__main__":
    best = main()
    print(f"\nRecommended strategy for production: {best}")


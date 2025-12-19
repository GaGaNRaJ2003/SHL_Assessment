"""
Evaluate XGBoost re-ranking vs other strategies.
"""
import sys
import os
import csv
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.advanced_retriever import retrieve_advanced, preprocess_query
from src.retriever import get_vector_db
from src.xgboost_reranker import train_xgboost_reranker, load_xgboost_reranker, rerank_with_xgboost
from src.url_utils import normalize_url_to_slug, get_all_url_variants


def evaluate_with_reranker(strategy_name, retrieve_func, rerank_func, vector_db, train_queries, top_k=10):
    """Evaluate a retrieval strategy with a specific re-ranker."""
    total_recall = 0.0
    query_count = 0
    
    print(f"\n{'='*60}")
    print(f"Evaluating: {strategy_name}")
    print(f"{'='*60}")
    
    for query, relevant_slugs in train_queries.items():
        try:
            # Get initial candidates
            candidates = retrieve_func(query, vector_db, top_k=top_k * 3)  # Get more for re-ranking
            
            # Apply re-ranker
            reranked = rerank_func(query, candidates, top_k=top_k)
            
            # Get recommended URL slugs
            recommended_slugs = set()
            for r in reranked:
                url = r.get('url', '')
                alternate_urls = r.get('alternate_urls', [])
                variants = get_all_url_variants(url, alternate_urls)
                recommended_slugs.update(variants)
            
            # Calculate recall
            matches = len(relevant_slugs & recommended_slugs)
            recall = matches / len(relevant_slugs) if relevant_slugs else 0.0
            total_recall += recall
            query_count += 1
        except Exception as e:
            print(f"Error processing query '{query[:50]}...': {e}")
            continue
    
    mean_recall = total_recall / query_count if query_count > 0 else 0.0
    print(f"\nMean Recall@{top_k}: {mean_recall:.4f} ({mean_recall*100:.2f}%)")
    print(f"Total queries evaluated: {query_count}")
    
    return mean_recall


def main():
    # Load train data
    train_path = 'data/train.csv'
    if not os.path.exists(train_path):
        print(f"Error: {train_path} not found")
        return
    
    train_queries = defaultdict(set)
    with open(train_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['Query'].strip()
            url = row['Assessment_url'].strip()
            train_queries[query].add(normalize_url_to_slug(url))
    
    print(f"Loaded {len(train_queries)} unique queries from train set")
    
    vector_db = get_vector_db()
    
    results = {}
    
    # Baseline: No re-ranking
    def no_rerank(query, candidates, top_k=10):
        return candidates[:top_k]
    
    recall_baseline = evaluate_with_reranker(
        "Baseline (No Re-ranking)",
        retrieve_advanced,
        no_rerank,
        vector_db,
        train_queries
    )
    results["Baseline"] = recall_baseline
    
    # Train XGBoost model
    print("\n" + "="*60)
    print("Training XGBoost Re-ranker")
    print("="*60)
    
    model_path = 'data/xgboost_reranker.pkl'
    model = train_xgboost_reranker(train_path, vector_db, retrieve_advanced, model_path)
    
    if model:
        # Test XGBoost re-ranking
        def xgboost_rerank_wrapper(query, candidates, top_k=10):
            query_info = preprocess_query(query)
            return rerank_with_xgboost(query, candidates, model, query_info, top_k)
        
        recall_xgboost = evaluate_with_reranker(
            "XGBoost Re-ranking",
            retrieve_advanced,
            xgboost_rerank_wrapper,
            vector_db,
            train_queries
        )
        results["XGBoost"] = recall_xgboost
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY - Mean Recall@10")
    print("="*60)
    for name, recall in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name}: {recall*100:.2f}%")
    
    if results:
        best = max(results.items(), key=lambda x: x[1])
        print(f"\n{'='*60}")
        print(f"Best strategy: {best[0]} ({best[1]*100:.2f}%)")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()


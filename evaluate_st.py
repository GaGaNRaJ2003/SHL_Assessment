"""
Evaluate SentenceTransformer-based retrieval vs Gemini-based retrieval.
"""
import sys
import os
import csv
from collections import defaultdict

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.url_utils import normalize_url_to_slug, get_all_url_variants


def evaluate_strategy(strategy_name, retrieve_func, vector_db, train_queries, top_k=10):
    """Evaluate a retrieval strategy on train queries."""
    total_recall = 0.0
    query_count = 0
    
    print(f"\n{'='*60}")
    print(f"Evaluating: {strategy_name}")
    print(f"{'='*60}")
    
    for query, relevant_slugs in train_queries.items():
        results = retrieve_func(query, vector_db, top_k=top_k)
        
        # Get recommended URL slugs
        recommended_slugs = set()
        for r in results:
            url = r.get('url', '')
            alternate_urls = r.get('alternate_urls', [])
            variants = get_all_url_variants(url, alternate_urls)
            recommended_slugs.update(variants)
        
        # Calculate recall
        matches = len(relevant_slugs & recommended_slugs)
        recall = matches / len(relevant_slugs) if relevant_slugs else 0.0
        total_recall += recall
        query_count += 1
    
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
    
    results = {}
    
    # Test 1: SentenceTransformer simple retrieval
    try:
        from src.retriever_st import retrieve_candidates_st, get_vector_db_st
        
        db_st = get_vector_db_st()
        if db_st:
            recall = evaluate_strategy(
                "SentenceTransformer (Simple)",
                retrieve_candidates_st,
                db_st,
                train_queries
            )
            results["ST Simple"] = recall
        else:
            print("SentenceTransformer DB not available. Run: python src/embeddings_st.py")
    except Exception as e:
        print(f"Error with SentenceTransformer simple: {e}")
    
    # Test 2: SentenceTransformer with keyword boosting
    try:
        from src.retriever_st import retrieve_with_boost_st, get_vector_db_st
        
        db_st = get_vector_db_st()
        if db_st:
            recall = evaluate_strategy(
                "SentenceTransformer (Keyword Boost)",
                retrieve_with_boost_st,
                db_st,
                train_queries
            )
            results["ST Boosted"] = recall
    except Exception as e:
        print(f"Error with SentenceTransformer boosted: {e}")
    
    # Test 3: Gemini advanced retriever (current best)
    try:
        from src.advanced_retriever import retrieve_advanced
        from src.retriever import get_vector_db
        
        db_gemini = get_vector_db()
        if db_gemini:
            # Wrapper to match interface
            def gemini_retrieve(query, db, top_k=10):
                return retrieve_advanced(query, db, top_k=top_k, use_llm_rerank=False)
            
            recall = evaluate_strategy(
                "Gemini Advanced (Current)",
                gemini_retrieve,
                db_gemini,
                train_queries
            )
            results["Gemini Advanced"] = recall
    except Exception as e:
        print(f"Error with Gemini advanced: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for name, recall in sorted(results.items(), key=lambda x: x[1], reverse=True):
        print(f"  {name}: {recall*100:.2f}%")
    
    if results:
        best = max(results.items(), key=lambda x: x[1])
        print(f"\nBest strategy: {best[0]} ({best[1]*100:.2f}%)")


if __name__ == "__main__":
    main()


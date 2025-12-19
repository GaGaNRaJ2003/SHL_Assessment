"""
Evaluate current system (Advanced Retriever + XGBoost Re-ranking) with fixes.
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
    
    # Load vector DB
    print("Loading vector database...")
    vector_db = get_vector_db()
    
    # Evaluate with current system (XGBoost re-ranking)
    print("\n" + "="*60)
    print("Evaluating: Advanced Retriever + XGBoost Re-ranking")
    print("="*60)
    
    total_recall = 0.0
    query_count = 0
    per_query_recalls = []
    
    for query, relevant_slugs in train_queries.items():
        try:
            # Get recommendations using current system (same as submission)
            results = retrieve_advanced(
                query=query,
                vector_db=vector_db,
                top_k=10,
                use_llm_rerank=False,
                use_xgboost_rerank=True
            )
            
            # Get recommended URL slugs (including alternate URLs)
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
            per_query_recalls.append((query, recall, matches, len(relevant_slugs)))
            
        except Exception as e:
            print(f"Error processing query '{query[:50]}...': {e}")
            continue
    
    mean_recall = total_recall / query_count if query_count > 0 else 0.0
    
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Mean Recall@10: {mean_recall:.4f} ({mean_recall*100:.2f}%)")
    print(f"Total queries evaluated: {query_count}")
    
    # Per-query breakdown
    print(f"\n{'='*60}")
    print("Per-Query Recall:")
    print(f"{'='*60}")
    for query, recall, matches, total in sorted(per_query_recalls, key=lambda x: x[1]):
        print(f"  {recall*100:5.2f}% ({matches}/{total}) - {query[:60]}...")
    
    print(f"\n{'='*60}")
    print(f"Final Mean Recall@10: {mean_recall*100:.2f}%")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()


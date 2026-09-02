"""Generate predictions for test set directly (no API needed).
Uses Gemini Advanced retriever (best performing: 33.56% recall).
"""
import os
import csv
import sys
from tqdm import tqdm

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.advanced_retriever import retrieve_advanced
from src.retriever import get_vector_db

def main():
    print("Loading vector database...")
    vector_db = get_vector_db()
    
    # Load test queries
    test_path = 'data/test.csv'
    print(f"Loading test queries from {test_path}...")
    
    queries = []
    with open(test_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['Query'].strip()
            if query not in queries:
                queries.append(query)
    
    print(f"Found {len(queries)} unique test queries")
    
    # Generate predictions using Gemini Advanced (best: 33.56% recall)
    predictions = []
    for query in tqdm(queries, desc="Generating predictions"):
        # Get top 10 recommendations using advanced retriever with XGBoost re-ranking (best: 62.22% recall)
        results = retrieve_advanced(query, vector_db, top_k=10, use_llm_rerank=False, use_xgboost_rerank=True)
        
        for r in results:
            predictions.append({
                'Query': query,
                'Assessment_url': r['url']
            })
    
    # Save predictions
    os.makedirs('submission', exist_ok=True)
    output_path = 'submission/predictions.csv'
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Query', 'Assessment_url'])
        writer.writeheader()
        writer.writerows(predictions)
    
    print(f"\nGenerated {len(predictions)} predictions")
    print(f"Saved to {output_path}")
    print(f"Average {len(predictions)/len(queries):.1f} recommendations per query")

if __name__ == "__main__":
    main()


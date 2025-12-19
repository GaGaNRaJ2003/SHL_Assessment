"""
Generate submission CSV for test set using XGBoost re-ranking (best: 61.56% recall).
Format: Query, Assessment_url (as per Appendix 3)
"""
import sys
import os
import csv
from tqdm import tqdm

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
            queries.append(query)
    
    print(f"Found {len(queries)} test queries")
    
    # Generate predictions using XGBoost re-ranking (best: 61.56% recall)
    predictions = []
    for query in tqdm(queries, desc="Generating predictions"):
        # Get top 10 recommendations using XGBoost re-ranking
        results = retrieve_advanced(
            query, 
            vector_db, 
            top_k=10, 
            use_llm_rerank=False, 
            use_xgboost_rerank=True
        )
        
        for r in results:
            predictions.append({
                'Query': query,
                'Assessment_url': r['url']
            })
    
    # Save predictions in submission format (Appendix 3)
    os.makedirs('submission', exist_ok=True)
    output_path = 'submission/predictions.csv'
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Query', 'Assessment_url'])
        writer.writeheader()
        writer.writerows(predictions)
    
    print(f"\nGenerated {len(predictions)} predictions")
    print(f"Saved to {output_path}")
    print(f"Average {len(predictions)/len(queries):.1f} recommendations per query")
    
    # Verify format
    print("\nVerifying format...")
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        first_row = next(reader)
        if 'Query' in first_row and 'Assessment_url' in first_row:
            print("✓ Format correct: Query, Assessment_url")
        else:
            print("✗ Format error: Expected Query, Assessment_url")
    
    # Show sample
    print("\nSample predictions:")
    with open(output_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i < 3:
                print(f"  Query: {row['Query'][:60]}...")
                print(f"  URL: {row['Assessment_url']}")
            else:
                break

if __name__ == "__main__":
    main()


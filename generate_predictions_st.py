"""Generate predictions for test set using SentenceTransformer (best performing approach)."""
import sys
import os
import csv
from tqdm import tqdm

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.retriever_st import retrieve_with_boost_st, get_vector_db_st

def main():
    print("Loading SentenceTransformer vector database...")
    vector_db = get_vector_db_st()
    
    if vector_db is None:
        print("Error: SentenceTransformer vector DB not found.")
        print("Please run: python src/embeddings_st.py")
        return
    
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
    
    # Generate predictions using SentenceTransformer with keyword boost
    predictions = []
    for query in tqdm(queries, desc="Generating predictions"):
        # Get top 10 recommendations using SentenceTransformer with keyword boost
        results = retrieve_with_boost_st(query, vector_db, top_k=10)
        
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


"""
Generate predictions for the test set and save in submission format.
"""
import sys
import os
import pandas as pd
import requests
from tqdm import tqdm
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_URL = os.getenv('API_URL', 'http://localhost:8000')


def generate_predictions(test_csv_path: str, output_path: str, api_url: str = API_URL):
    """Generate predictions for test queries."""
    # Load test set
    df_test = pd.read_csv(test_csv_path)
    
    # Get unique queries
    unique_queries = df_test['Query'].unique()
    
    print(f"Found {len(unique_queries)} unique queries in test set")
    
    predictions = []
    
    for query in tqdm(unique_queries, desc="Generating predictions"):
        try:
            # Call API
            response = requests.post(
                f"{api_url}/recommend",
                json={"query": query},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract assessment URLs
            assessments = data.get('recommended_assessments', [])
            for assessment in assessments:
                predictions.append({
                    'Query': query,
                    'Assessment_url': assessment['url']
                })
            
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"Error processing query: {query[:50]}... - {e}")
            continue
    
    # Save to CSV
    df_predictions = pd.DataFrame(predictions)
    df_predictions.to_csv(output_path, index=False)
    
    print(f"\nGenerated {len(predictions)} predictions")
    print(f"Saved to {output_path}")
    
    # Print statistics
    print(f"\nStatistics:")
    print(f"  Total predictions: {len(predictions)}")
    print(f"  Unique queries: {df_predictions['Query'].nunique()}")
    print(f"  Average recommendations per query: {len(predictions) / len(unique_queries):.1f}")


if __name__ == "__main__":
    # Get the project root directory (parent of notebooks)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_path = os.path.join(project_root, 'data', 'test.csv')
    output_path = os.path.join(project_root, 'submission', 'predictions.csv')
    
    # Ensure submission directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if not os.path.exists(test_path):
        print(f"Error: Test file not found at {test_path}")
        print("Please ensure the test CSV is in the data/ directory")
        sys.exit(1)
    
    generate_predictions(test_path, output_path)
    print("\nDone! Check submission/predictions.csv")


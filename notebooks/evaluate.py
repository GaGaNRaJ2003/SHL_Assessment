"""
Evaluate the system using Mean Recall@10 on the train set.
"""
import sys
import os
import pandas as pd
import requests
from tqdm import tqdm
import time
from collections import defaultdict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.url_utils import normalize_url_to_slug, get_all_url_variants

API_URL = os.getenv('API_URL', 'http://localhost:8000')


def compute_recall_at_k(relevant_urls: set, recommended_assessments: list, k: int = 10) -> float:
    """
    Compute Recall@K with unified URL normalization.
    Considers both primary URL and alternate URLs for matching.
    """
    if not relevant_urls:
        return 0.0
    
    # Normalize relevant URLs to slugs
    normalized_relevant = set()
    for url in relevant_urls:
        normalized_relevant.add(normalize_url_to_slug(url))
    
    # Normalize recommended URLs (including alternate URLs)
    normalized_recommended = set()
    for assessment in recommended_assessments[:k]:
        url = assessment.get('url', '')
        alternate_urls = assessment.get('alternate_urls', [])
        # Get all variants (primary + alternates)
        variants = get_all_url_variants(url, alternate_urls)
        normalized_recommended.update(variants)
    
    # Calculate hits
    relevant_found = len(normalized_recommended & normalized_relevant)
    
    return relevant_found / len(normalized_relevant) if normalized_relevant else 0.0


def evaluate_on_train_set(train_csv_path: str, api_url: str = API_URL, k: int = 10):
    """Evaluate system on labeled train set."""
    # Load train set
    df_train = pd.read_csv(train_csv_path)
    
    # Group by query to get relevant URLs for each query
    query_to_relevant = defaultdict(set)
    for _, row in df_train.iterrows():
        query_to_relevant[row['Query']].add(row['Assessment_url'])
    
    print(f"Found {len(query_to_relevant)} unique queries in train set")
    
    recalls = []
    query_results = []
    
    for query, relevant_urls in tqdm(query_to_relevant.items(), desc="Evaluating"):
        try:
            # Call API
            response = requests.post(
                f"{api_url}/recommend",
                json={"query": query},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract recommended assessments (with alternate URLs)
            recommended_assessments = data.get('recommended_assessments', [])
            
            # Compute Recall@K (now considers alternate URLs)
            recall = compute_recall_at_k(relevant_urls, recommended_assessments, k=k)
            recalls.append(recall)
            
            query_results.append({
                'Query': query[:100] + '...' if len(query) > 100 else query,
                'Relevant Count': len(relevant_urls),
                'Recommended Count': len(recommended_assessments),
                f'Recall@{k}': recall
            })
            
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            print(f"Error processing query: {query[:50]}... - {e}")
            recalls.append(0.0)
            continue
    
    # Compute mean recall
    mean_recall = sum(recalls) / len(recalls) if recalls else 0.0
    
    # Print results
    print("\n" + "="*80)
    print("EVALUATION RESULTS")
    print("="*80)
    print(f"\nMean Recall@{k}: {mean_recall:.4f}")
    print(f"Number of queries: {len(recalls)}")
    print(f"Min Recall@{k}: {min(recalls):.4f}")
    print(f"Max Recall@{k}: {max(recalls):.4f}")
    
    # Print per-query results
    print("\n" + "-"*80)
    print("Per-Query Results:")
    print("-"*80)
    df_results = pd.DataFrame(query_results)
    print(df_results.to_string(index=False))
    
    return mean_recall, df_results


if __name__ == "__main__":
    # Get the project root directory (parent of notebooks)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    train_path = os.path.join(project_root, 'data', 'train.csv')
    
    if not os.path.exists(train_path):
        print(f"Error: Train file not found at {train_path}")
        print("Please ensure the train CSV is in the data/ directory")
        sys.exit(1)
    
    mean_recall, results_df = evaluate_on_train_set(train_path)
    print(f"\n\nFinal Mean Recall@10: {mean_recall:.4f}")


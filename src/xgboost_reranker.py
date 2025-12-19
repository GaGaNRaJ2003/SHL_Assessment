"""
XGBoost-based Re-ranker for assessment recommendations.
Learns from training data to improve ranking without API calls.
"""
import os
import json
import csv
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from collections import defaultdict
import re

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: xgboost not installed. Run: pip install xgboost")


def extract_features(query: str, candidate: Dict, query_info: Dict = None) -> Dict:
    """
    Extract features for XGBoost ranking.
    
    Features:
    1. Semantic similarity score (from vector search)
    2. Keyword match scores (name, description)
    3. Duration match score
    4. Test type match score
    5. Query-candidate text similarity
    6. Role/skill match indicators
    """
    if query_info is None:
        query_info = {}
    
    features = {}
    
    # 1. Semantic similarity (normalized to 0-1)
    semantic_score = candidate.get('distance', 0.0)
    if isinstance(semantic_score, (int, float)):
        # FAISS cosine similarity is typically 0-1 after normalization
        features['semantic_score'] = float(semantic_score)
    else:
        features['semantic_score'] = 0.0
    
    # Also check combined_score if available
    combined_score = candidate.get('combined_score', 0.0)
    if isinstance(combined_score, (int, float)):
        features['combined_score'] = float(combined_score)
    else:
        features['combined_score'] = semantic_score
    
    # 2. Keyword match scores
    query_lower = query.lower()
    name = candidate.get('name', '').lower()
    description = (candidate.get('description', '') or '').lower()
    
    # Extract keywords from query
    query_words = set(re.findall(r'\b\w+\b', query_lower))
    query_words = {w for w in query_words if len(w) > 2}  # Filter short words
    
    # Name keyword matches
    name_matches = sum(1 for word in query_words if word in name)
    features['name_keyword_matches'] = name_matches
    features['name_keyword_ratio'] = name_matches / len(query_words) if query_words else 0.0
    
    # Description keyword matches
    desc_matches = sum(1 for word in query_words if word in description)
    features['desc_keyword_matches'] = desc_matches
    features['desc_keyword_ratio'] = desc_matches / len(query_words) if query_words else 0.0
    
    # Exact phrase matches
    features['exact_name_match'] = 1.0 if any(word in name for word in query_words if len(word) > 4) else 0.0
    
    # 3. Duration match
    query_duration = query_info.get('duration', None)
    candidate_duration = candidate.get('duration', 0) or 0
    
    if query_duration and candidate_duration:
        duration_diff = abs(query_duration - candidate_duration)
        duration_ratio = min(candidate_duration, query_duration) / max(candidate_duration, query_duration) if max(candidate_duration, query_duration) > 0 else 0.0
        features['duration_match'] = duration_ratio
        features['duration_diff'] = duration_diff / 60.0  # Normalize to hours
    else:
        features['duration_match'] = 0.5  # Neutral if no duration constraint
        features['duration_diff'] = 0.0
    
    # 4. Test type match
    query_test_types = query_info.get('test_types', [])
    candidate_test_types = candidate.get('test_type', [])
    
    if isinstance(candidate_test_types, str):
        candidate_test_types = [candidate_test_types]
    
    if query_test_types and candidate_test_types:
        type_match = len(set(query_test_types) & set(candidate_test_types))
        features['test_type_matches'] = type_match
        features['test_type_match_ratio'] = type_match / len(query_test_types) if query_test_types else 0.0
    else:
        features['test_type_matches'] = 0.0
        features['test_type_match_ratio'] = 0.0
    
    # 5. Role/skill indicators
    skills = query_info.get('skills', [])
    roles = query_info.get('roles', [])
    
    # Skill matches in name
    skill_name_matches = sum(1 for skill in skills if skill.lower() in name)
    features['skill_name_matches'] = skill_name_matches
    
    # Role matches in name
    role_name_matches = sum(1 for role in roles if role.lower() in name)
    features['role_name_matches'] = role_name_matches
    
    # 6. Remote/Adaptive support indicators
    features['remote_support'] = 1.0 if candidate.get('remote_support', 'No') == 'Yes' else 0.0
    features['adaptive_support'] = 1.0 if candidate.get('adaptive_support', 'No') == 'Yes' else 0.0
    
    # 7. Text length features (can indicate detail level)
    features['name_length'] = len(name) / 100.0  # Normalize
    features['desc_length'] = len(description) / 500.0  # Normalize
    
    return features


def prepare_training_data(train_csv_path: str, vector_db, retrieve_func) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare training data from train set.
    For each query-candidate pair, extract features and label (1 if relevant, 0 if not).
    """
    if not XGBOOST_AVAILABLE:
        return None, None
    
    # Load train data
    train_queries = defaultdict(set)
    with open(train_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['Query'].strip()
            url = row['Assessment_url'].strip()
            train_queries[query].add(url)
    
    print(f"Preparing training data from {len(train_queries)} queries...")
    
    # Import query preprocessing
    from src.advanced_retriever import preprocess_query
    from src.url_utils import normalize_url_to_slug, get_all_url_variants
    
    X_features = []
    y_labels = []
    
    for query, relevant_urls in train_queries.items():
        # Get candidates using retrieval function
        candidates = retrieve_func(query, vector_db, top_k=50)  # Get more candidates
        
        # Normalize relevant URLs
        relevant_slugs = set()
        for url in relevant_urls:
            relevant_slugs.add(normalize_url_to_slug(url))
        
        query_info = preprocess_query(query)
        
        # Extract features for each candidate
        for cand in candidates:
            features = extract_features(query, cand, query_info)
            X_features.append(features)
            
            # Label: 1 if relevant, 0 if not
            cand_urls = get_all_url_variants(cand.get('url', ''), cand.get('alternate_urls', []))
            is_relevant = 1 if len(relevant_slugs & cand_urls) > 0 else 0
            y_labels.append(is_relevant)
    
    # Convert to DataFrame
    X_df = pd.DataFrame(X_features)
    y_df = pd.Series(y_labels)
    
    print(f"Prepared {len(X_df)} training samples ({sum(y_labels)} positive, {len(y_labels) - sum(y_labels)} negative)")
    
    return X_df, y_df


def train_xgboost_reranker(train_csv_path: str, vector_db, retrieve_func, model_path: str = 'data/xgboost_reranker.pkl'):
    """
    Train XGBoost model for re-ranking.
    """
    if not XGBOOST_AVAILABLE:
        print("Error: xgboost not available")
        return None
    
    X, y = prepare_training_data(train_csv_path, vector_db, retrieve_func)
    
    if X is None or len(X) == 0:
        print("Error: No training data prepared")
        return None
    
    print("Training XGBoost model...")
    
    # Use XGBClassifier for binary classification (simpler than ranking)
    # We'll optimize for recall by using class_weight
    from sklearn.utils.class_weight import compute_sample_weight
    
    model = xgb.XGBClassifier(
        objective='binary:logistic',
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        scale_pos_weight=len(y[y==0]) / len(y[y==1]) if len(y[y==1]) > 0 else 1.0,  # Handle class imbalance
        eval_metric='logloss'
    )
    
    # Train model
    model.fit(X.values, y.values)
    
    # Save model using pickle
    import pickle
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved to {model_path}")
    
    return model


def load_xgboost_reranker(model_path: str = 'data/xgboost_reranker.pkl'):
    """Load trained XGBoost model."""
    if not XGBOOST_AVAILABLE:
        return None
    
    if not os.path.exists(model_path):
        return None
    
    import pickle
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    return model


def rerank_with_xgboost(
    query: str,
    candidates: List[Dict],
    model,
    query_info: Dict = None,
    top_k: int = 10
) -> List[Dict]:
    """
    Re-rank candidates using trained XGBoost model.
    """
    if not XGBOOST_AVAILABLE or model is None:
        return candidates[:top_k]
    
    if not candidates:
        return []
    
    # Extract features for all candidates
    if query_info is None:
        from src.advanced_retriever import preprocess_query
        query_info = preprocess_query(query)
    
    features_list = []
    for cand in candidates:
        features = extract_features(query, cand, query_info)
        features_list.append(features)
    
    # Convert to DataFrame
    X = pd.DataFrame(features_list)
    
    # Get probability scores (higher = more likely to be relevant)
    scores = model.predict_proba(X.values)[:, 1]  # Probability of positive class
    
    # Add scores to candidates and sort
    for i, cand in enumerate(candidates):
        cand['xgboost_score'] = float(scores[i])
    
    # Sort by XGBoost score (descending)
    candidates.sort(key=lambda x: x.get('xgboost_score', 0), reverse=True)
    
    return candidates[:top_k]


if __name__ == "__main__":
    # Test training
    from src.advanced_retriever import retrieve_advanced
    from src.retriever import get_vector_db
    
    print("Loading vector database...")
    vector_db = get_vector_db()
    
    print("Training XGBoost re-ranker...")
    model = train_xgboost_reranker(
        'data/train.csv',
        vector_db,
        retrieve_advanced,
        'data/xgboost_reranker.pkl'
    )
    
    if model:
        print("XGBoost model trained successfully!")
    else:
        print("Failed to train model")


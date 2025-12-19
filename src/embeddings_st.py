"""
SentenceTransformer-based embeddings module.
Uses all-MiniLM-L6-v2 model which is proven effective for semantic similarity tasks.
This approach is inspired by TalentLens repository.
"""
import os
import json
import faiss
import numpy as np
import pickle
from typing import List, Dict
from tqdm import tqdm

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Run: pip install sentence-transformers")

# FAISS index and metadata storage (separate from Gemini embeddings)
INDEX_FILE_ST = 'data/faiss_index_st.bin'
METADATA_FILE_ST = 'data/faiss_metadata_st.pkl'

# Initialize model globally for efficiency
_model = None

def get_model():
    """Get or initialize the SentenceTransformer model."""
    global _model
    if _model is None and SENTENCE_TRANSFORMERS_AVAILABLE:
        print("Loading SentenceTransformer model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        print("Model loaded successfully!")
    return _model


def get_embedding_st(text: str) -> np.ndarray:
    """Get embedding for text using SentenceTransformer."""
    model = get_model()
    if model is None:
        return None
    return model.encode(text, convert_to_numpy=True)


def get_embeddings_batch_st(texts: List[str]) -> np.ndarray:
    """Get embeddings for multiple texts efficiently."""
    model = get_model()
    if model is None:
        return None
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=True)


def create_document_text(assessment: Dict) -> str:
    """
    Create rich document text for embedding.
    Following TalentLens approach: concatenate ALL relevant fields.
    """
    parts = []
    
    # Name (most important)
    name = assessment.get('name', '')
    if name:
        parts.append(name)
    
    # Description
    description = assessment.get('description', '') or ''
    if description:
        parts.append(description)
    
    # URL (can contain useful context like product names)
    url = assessment.get('url', '')
    if url:
        # Extract meaningful part from URL
        if '/view/' in url:
            slug = url.split('/view/')[-1].strip('/')
            # Convert slug to readable format
            readable = slug.replace('-', ' ').replace('_', ' ')
            parts.append(readable)
    
    # Duration
    duration = assessment.get('duration', 0) or 0
    if duration:
        parts.append(f"{duration} minutes")
    
    # Test types
    test_types = assessment.get('test_type', [])
    if test_types:
        if isinstance(test_types, list):
            parts.append(', '.join(test_types))
        else:
            parts.append(str(test_types))
    
    # Remote support
    remote = assessment.get('remote_support', 'No')
    if remote == 'Yes':
        parts.append('remote testing supported')
    
    # Adaptive support
    adaptive = assessment.get('adaptive_support', 'No')
    if adaptive == 'Yes':
        parts.append('adaptive IRT assessment')
    
    return ': '.join(parts)


def initialize_vector_db_st(assessments: List[Dict], force_rebuild: bool = False):
    """Initialize FAISS index with SentenceTransformer embeddings."""
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("Error: sentence-transformers not available")
        return None
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Check if index already exists
    if os.path.exists(INDEX_FILE_ST) and os.path.exists(METADATA_FILE_ST) and not force_rebuild:
        print(f"SentenceTransformer Vector DB already exists. Loading from {INDEX_FILE_ST}")
        index = faiss.read_index(INDEX_FILE_ST)
        with open(METADATA_FILE_ST, 'rb') as f:
            metadata = pickle.load(f)
        print(f"Loaded {index.ntotal} assessments from existing index")
        return {'index': index, 'metadata': metadata}
    
    if force_rebuild:
        print("Rebuilding SentenceTransformer vector DB...")
        if os.path.exists(INDEX_FILE_ST):
            os.remove(INDEX_FILE_ST)
        if os.path.exists(METADATA_FILE_ST):
            os.remove(METADATA_FILE_ST)
    
    # Create document texts
    print("Creating document texts...")
    texts = []
    metadatas = []
    
    for assessment in assessments:
        text = create_document_text(assessment)
        texts.append(text)
        
        # Store full metadata including alternate URLs
        metadatas.append({
            'url': assessment['url'],
            'alternate_urls': assessment.get('alternate_urls', []),
            'name': assessment['name'],
            'description': assessment.get('description', '') or '',
            'duration': assessment.get('duration', 0) or 0,
            'remote_support': assessment.get('remote_support', 'No'),
            'adaptive_support': assessment.get('adaptive_support', 'No'),
            'test_type': assessment.get('test_type', [])
        })
    
    # Generate embeddings (batch processing is much faster)
    print(f"Generating embeddings for {len(texts)} documents...")
    embeddings = get_embeddings_batch_st(texts)
    
    if embeddings is None:
        print("Error: Failed to generate embeddings")
        return None
    
    # Get embedding dimension
    dim = embeddings.shape[1]
    print(f"Embedding dimension: {dim}")
    
    # Create FAISS index with Inner Product (for cosine similarity after normalization)
    index = faiss.IndexFlatIP(dim)
    
    # Normalize embeddings for cosine similarity
    embeddings_normalized = embeddings.astype('float32')
    faiss.normalize_L2(embeddings_normalized)
    
    # Add to index
    index.add(embeddings_normalized)
    
    # Save index and metadata
    faiss.write_index(index, INDEX_FILE_ST)
    with open(METADATA_FILE_ST, 'wb') as f:
        pickle.dump(metadatas, f)
    
    print(f"Added {index.ntotal} assessments to SentenceTransformer vector DB")
    print(f"Saved index to {INDEX_FILE_ST} and metadata to {METADATA_FILE_ST}")
    
    return {'index': index, 'metadata': metadatas}


def get_vector_db_st():
    """Load the SentenceTransformer vector database."""
    if not os.path.exists(INDEX_FILE_ST) or not os.path.exists(METADATA_FILE_ST):
        print(f"SentenceTransformer Vector DB not found. Please run initialize_vector_db_st first.")
        return None
    
    index = faiss.read_index(INDEX_FILE_ST)
    with open(METADATA_FILE_ST, 'rb') as f:
        metadata = pickle.load(f)
    
    return {'index': index, 'metadata': metadata}


if __name__ == "__main__":
    # Load assessments
    assessments_path = 'data/assessments.json'
    if not os.path.exists(assessments_path):
        print(f"Error: {assessments_path} not found. Please run crawler.py first.")
        exit(1)
    
    with open(assessments_path, 'r', encoding='utf-8') as f:
        assessments = json.load(f)
    
    print(f"Loaded {len(assessments)} assessments from {assessments_path}")
    
    # Initialize vector DB with force rebuild
    db = initialize_vector_db_st(assessments, force_rebuild=True)
    if db:
        print("SentenceTransformer Vector DB initialized successfully!")


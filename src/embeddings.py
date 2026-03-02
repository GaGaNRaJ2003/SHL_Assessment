import os
import json
import faiss
import numpy as np
import pickle
import google.generativeai as genai
from typing import List, Dict
from dotenv import load_dotenv
import time

load_dotenv()

EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 768

api_key = os.getenv('GEMINI_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

INDEX_FILE = 'data/faiss_index.bin'
METADATA_FILE = 'data/faiss_metadata.pkl'


def get_embedding(text: str, task_type: str = "retrieval_document") -> List[float]:
    """Get embedding for text using Gemini."""
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type=task_type,
            output_dimensionality=EMBEDDING_DIM,
        )
        return result['embedding']
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None


def initialize_vector_db(assessments: List[Dict], force_rebuild: bool = False):
    """Initialize FAISS index with assessment embeddings."""
    os.makedirs('data', exist_ok=True)

    if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE) and not force_rebuild:
        print(f"Vector DB already exists. Loading from {INDEX_FILE}")
        index = faiss.read_index(INDEX_FILE)
        with open(METADATA_FILE, 'rb') as f:
            metadata = pickle.load(f)
        print(f"Loaded {index.ntotal} assessments from existing index")
        return {'index': index, 'metadata': metadata}

    if force_rebuild and os.path.exists(INDEX_FILE):
        print("Rebuilding vector DB...")
        os.remove(INDEX_FILE)
        if os.path.exists(METADATA_FILE):
            os.remove(METADATA_FILE)

    print("Generating embeddings...")
    texts = []
    metadatas = []

    for assessment in assessments:
        name = assessment.get('name', '')
        description = assessment.get('description', '') or ''
        test_types = assessment.get('test_type', [])
        remote = assessment.get('remote_support', 'No')
        adaptive = assessment.get('adaptive_support', 'No')
        duration = assessment.get('duration', 0) or 0

        text_parts = [name]
        if description:
            text_parts.append(description)
        if test_types:
            text_parts.append(f"Test types: {', '.join(test_types)}")
        if remote == 'Yes':
            text_parts.append("Supports remote testing")
        if adaptive == 'Yes':
            text_parts.append("Adaptive/IRT assessment")
        if duration:
            text_parts.append(f"Duration: {duration} minutes")

        text = ". ".join(text_parts)
        texts.append(text)

        metadatas.append({
            'url': assessment['url'],
            'alternate_urls': assessment.get('alternate_urls', []),
            'name': assessment['name'],
            'description': description,
            'duration': duration,
            'remote_support': remote,
            'adaptive_support': adaptive,
            'test_type': test_types
        })

    embeddings = []
    batch_size = 50
    total_batches = (len(texts) + batch_size - 1) // batch_size

    print(f"Processing {len(texts)} texts in {total_batches} batches...")

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]

        for text in batch:
            emb = get_embedding(text, task_type="retrieval_document")
            if emb:
                embeddings.append(emb)
            else:
                embeddings.append([0.0] * EMBEDDING_DIM)
            time.sleep(0.1)

        print(f"Processed {min(i+batch_size, len(texts))}/{len(texts)} embeddings")

    valid_indices = [i for i, emb in enumerate(embeddings) if emb and len(emb) > 0]

    if len(valid_indices) < len(embeddings):
        print(f"Warning: {len(embeddings) - len(valid_indices)} embeddings failed")
        metadatas = [metadatas[i] for i in valid_indices]
        embeddings = [embeddings[i] for i in valid_indices]

    if not embeddings:
        print("Error: No valid embeddings generated")
        return None

    dim = len(embeddings[0])
    index = faiss.IndexFlatIP(dim)

    embeddings_np = np.array(embeddings, dtype='float32')
    faiss.normalize_L2(embeddings_np)

    index.add(embeddings_np)

    faiss.write_index(index, INDEX_FILE)
    with open(METADATA_FILE, 'wb') as f:
        pickle.dump(metadatas, f)

    print(f"Added {index.ntotal} assessments to vector DB")
    print(f"Saved index to {INDEX_FILE} and metadata to {METADATA_FILE}")

    return {'index': index, 'metadata': metadatas}


if __name__ == "__main__":
    if not api_key:
        print("Error: GEMINI_API_KEY not found. Set it in .env file.")
        exit(1)

    assessments_path = 'data/assessments.json'
    if not os.path.exists(assessments_path):
        print(f"Error: {assessments_path} not found. Please run crawler.py first.")
        exit(1)

    with open(assessments_path, 'r', encoding='utf-8') as f:
        assessments = json.load(f)

    print(f"Loaded {len(assessments)} assessments from {assessments_path}")

    db = initialize_vector_db(assessments, force_rebuild=True)
    if db:
        print("Vector DB initialized successfully!")

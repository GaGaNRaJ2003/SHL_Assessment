"""
Quick setup verification script.
Checks if all required files and dependencies are in place.
"""
import os
import sys


def check_file(path, description):
    """Check if a file exists."""
    exists = os.path.exists(path)
    status = "[OK]" if exists else "[MISSING]"
    print(f"{status} {description}: {path}")
    return exists


def check_directory(path, description):
    """Check if a directory exists."""
    exists = os.path.isdir(path)
    status = "[OK]" if exists else "[MISSING]"
    print(f"{status} {description}: {path}")
    return exists


def main():
    print("="*60)
    print("SHL Assessment Recommender - Setup Verification")
    print("="*60)
    print()
    
    all_ok = True
    
    # Check directories
    print("Checking directories...")
    all_ok &= check_directory("data", "Data directory")
    all_ok &= check_directory("src", "Source directory")
    all_ok &= check_directory("app", "App directory")
    all_ok &= check_directory("notebooks", "Notebooks directory")
    all_ok &= check_directory("submission", "Submission directory")
    print()
    
    # Check source files
    print("Checking source files...")
    all_ok &= check_file("src/crawler.py", "Crawler")
    all_ok &= check_file("src/embeddings.py", "Embeddings")
    all_ok &= check_file("src/retriever.py", "Retriever")
    all_ok &= check_file("src/reranker.py", "Reranker")
    all_ok &= check_file("src/api.py", "API")
    all_ok &= check_file("src/utils.py", "Utils")
    all_ok &= check_file("app/streamlit_app.py", "Streamlit app")
    print()
    
    # Check data files
    print("Checking data files...")
    train_exists = check_file("data/train.csv", "Train CSV")
    test_exists = check_file("data/test.csv", "Test CSV")
    assessments_exists = check_file("data/assessments.json", "Assessments JSON (generated)")
    print()
    
    # Check configuration
    print("Checking configuration...")
    env_exists = check_file(".env", "Environment file (.env)")
    if not env_exists:
            print("  [WARNING] .env file not found. Create it from .env.example")
    print()
    
    # Check requirements
    print("Checking dependencies...")
    req_exists = check_file("requirements.txt", "Requirements file")
    if req_exists:
        try:
            import fastapi
            import streamlit
            import chromadb
            import google.generativeai
            print("  [OK] Key dependencies are installed")
        except ImportError as e:
            print(f"  [MISSING] Missing dependency: {e}")
            print("  Run: pip install -r requirements.txt")
            all_ok = False
    print()
    
    # Summary
    print("="*60)
    if all_ok:
        print("[SUCCESS] Setup looks good!")
        print()
        print("Next steps:")
        if not assessments_exists:
            print("1. Run: python src/crawler.py")
        if not os.path.exists("data/chroma_db"):
            print("2. Run: python src/embeddings.py")
        print("3. Start API: uvicorn src.api:app --reload")
        print("4. Start Frontend: streamlit run app/streamlit_app.py")
    else:
        print("[WARNING] Some issues found. Please fix them before proceeding.")
    print("="*60)


if __name__ == "__main__":
    main()


"""
Verify all submission requirements are met.
"""
import os
import csv
import json
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def check_api_format():
    """Verify API response format matches spec."""
    print("\n" + "="*60)
    print("API FORMAT VERIFICATION")
    print("="*60)
    
    # Check API file
    api_file = 'src/api.py'
    if not os.path.exists(api_file):
        print("❌ API file not found")
        return False
    
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'Health endpoint': '/health' in content and '@app.get' in content,
        'Recommend endpoint': '/recommend' in content and '@app.post' in content,
        'Response field name': 'recommended_assessments' in content,
        'Required fields': all(field in content for field in [
            'url', 'name', 'adaptive_support', 'description', 
            'duration', 'remote_support', 'test_type'
        ]),
        'Health returns status': '"status": "healthy"' in content or "'status': 'healthy'" in content
    }
    
    all_pass = True
    for check, passed in checks.items():
        status = "✓" if passed else "❌"
        print(f"{status} {check}")
        if not passed:
            all_pass = False
    
    return all_pass

def check_submission_csv():
    """Verify submission CSV format."""
    print("\n" + "="*60)
    print("SUBMISSION CSV VERIFICATION")
    print("="*60)
    
    csv_file = 'submission/predictions.csv'
    if not os.path.exists(csv_file):
        print("❌ Submission CSV not found")
        return False
    
    checks = {}
    
    # Check format
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        checks['Has Query column'] = 'Query' in fieldnames
        checks['Has Assessment_url column'] = 'Assessment_url' in fieldnames
        checks['Correct column order'] = list(fieldnames) == ['Query', 'Assessment_url']
        
        # Check data
        rows = list(reader)
        checks['Has data'] = len(rows) > 0
        
        # Check URLs are valid
        valid_urls = sum(1 for row in rows if row['Assessment_url'].startswith('http'))
        checks['Valid URLs'] = valid_urls == len(rows)
        
        # Check test queries covered
        with open('data/test.csv', 'r', encoding='utf-8') as tf:
            test_reader = csv.DictReader(tf)
            test_queries = set(row['Query'].strip() for row in test_reader)
        
        csv_queries = set(row['Query'].strip() for row in rows)
        checks['All test queries covered'] = test_queries.issubset(csv_queries)
    
    all_pass = True
    for check, passed in checks.items():
        status = "✓" if passed else "❌"
        print(f"{status} {check}")
        if not passed:
            all_pass = False
    
    print(f"\nTotal predictions: {len(rows)}")
    print(f"Unique queries: {len(csv_queries)}")
    print(f"Average per query: {len(rows)/len(csv_queries):.1f}")
    
    return all_pass

def check_assessments():
    """Verify assessment count."""
    print("\n" + "="*60)
    print("ASSESSMENT COUNT VERIFICATION")
    print("="*60)
    
    assessments_file = 'data/assessments.json'
    if not os.path.exists(assessments_file):
        print("❌ Assessments file not found")
        return False
    
    with open(assessments_file, 'r', encoding='utf-8') as f:
        assessments = json.load(f)
    
    count = len(assessments)
    target = 377
    
    print(f"Found: {count} assessments")
    print(f"Target: {target} assessments")
    
    if count >= target:
        print(f"✓ Requirement met ({count} >= {target})")
        return True
    else:
        print(f"❌ Requirement not met ({count} < {target})")
        return False

def check_documentation():
    """Check if documentation exists."""
    print("\n" + "="*60)
    print("DOCUMENTATION VERIFICATION")
    print("="*60)
    
    doc_file = 'submission/approach_documentation.tex'
    if os.path.exists(doc_file):
        print("✓ LaTeX documentation exists")
        return True
    else:
        print("❌ Documentation not found")
        return False

def check_frontend():
    """Check if frontend exists."""
    print("\n" + "="*60)
    print("FRONTEND VERIFICATION")
    print("="*60)
    
    frontend_file = 'app/streamlit_app.py'
    if os.path.exists(frontend_file):
        print("✓ Streamlit frontend exists")
        return True
    else:
        print("❌ Frontend not found")
        return False

def main():
    print("="*60)
    print("SUBMISSION VERIFICATION CHECKLIST")
    print("="*60)
    
    results = {
        'API Format': check_api_format(),
        'Submission CSV': check_submission_csv(),
        'Assessment Count': check_assessments(),
        'Documentation': check_documentation(),
        'Frontend': check_frontend()
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_pass = True
    for item, passed in results.items():
        status = "✓" if passed else "❌"
        print(f"{status} {item}")
        if not passed:
            all_pass = False
    
    if all_pass:
        print("\n✅ All checks passed! Ready for submission.")
    else:
        print("\n⚠️  Some checks failed. Please review above.")
    
    return all_pass

if __name__ == "__main__":
    main()


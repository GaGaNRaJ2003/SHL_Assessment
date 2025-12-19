"""
Script to generate alternate URLs for all assessments in data/assessments.json.

This ensures every assessment has both URL variants:
- /products/product-catalog/view/...
- /solutions/products/product-catalog/view/...

This fixes the recall bottleneck caused by URL variation mismatches.
"""
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.url_utils import generate_alternate_url


def add_alternate_urls_to_assessments(assessments_file: str = 'data/assessments.json'):
    """
    Add alternate URLs to all assessments.
    
    Args:
        assessments_file: Path to assessments.json file
    """
    # Load assessments
    if not os.path.exists(assessments_file):
        print(f"Error: {assessments_file} not found!")
        return
    
    print(f"Loading assessments from {assessments_file}...")
    with open(assessments_file, 'r', encoding='utf-8') as f:
        assessments = json.load(f)
    
    print(f"Found {len(assessments)} assessments")
    
    # Process each assessment
    updated_count = 0
    for i, assessment in enumerate(assessments):
        url = assessment.get('url', '')
        
        if not url:
            continue
        
        # Generate alternate URL
        alternate_url = generate_alternate_url(url)
        
        # Get existing alternate URLs
        existing_alternates = assessment.get('alternate_urls', [])
        
        # Add alternate URL if it's different and not already present
        if alternate_url != url:
            if alternate_url not in existing_alternates:
                if not existing_alternates:
                    assessment['alternate_urls'] = [alternate_url]
                else:
                    assessment['alternate_urls'].append(alternate_url)
                updated_count += 1
        
        # Also ensure we have both variants in alternate_urls
        if '/products/product-catalog/view/' in url.lower():
            solutions_variant = url.replace('/products/product-catalog/view/', '/solutions/products/product-catalog/view/')
            if solutions_variant not in existing_alternates:
                if 'alternate_urls' not in assessment:
                    assessment['alternate_urls'] = []
                if solutions_variant not in assessment['alternate_urls']:
                    assessment['alternate_urls'].append(solutions_variant)
                    updated_count += 1
        
        elif '/solutions/products/product-catalog/view/' in url.lower():
            products_variant = url.replace('/solutions/products/product-catalog/view/', '/products/product-catalog/view/')
            if products_variant not in existing_alternates:
                if 'alternate_urls' not in assessment:
                    assessment['alternate_urls'] = []
                if products_variant not in assessment['alternate_urls']:
                    assessment['alternate_urls'].append(products_variant)
                    updated_count += 1
        
        # Ensure alternate_urls is always a list (even if empty)
        if 'alternate_urls' not in assessment:
            assessment['alternate_urls'] = []
    
    # Save updated assessments
    print(f"\nUpdated {updated_count} assessments with alternate URLs")
    print(f"Saving to {assessments_file}...")
    
    # Create backup
    backup_file = assessments_file + '.backup'
    if os.path.exists(assessments_file):
        import shutil
        shutil.copy2(assessments_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    # Save updated file
    with open(assessments_file, 'w', encoding='utf-8') as f:
        json.dump(assessments, f, indent=2, ensure_ascii=False)
    
    print(f"\nSuccessfully updated {len(assessments)} assessments")
    print(f"Total assessments with alternate URLs: {sum(1 for a in assessments if a.get('alternate_urls'))}")
    
    # Show sample
    print("\nSample updated assessment:")
    sample = assessments[0] if assessments else None
    if sample:
        print(f"  Name: {sample.get('name', 'N/A')[:50]}")
        print(f"  URL: {sample.get('url', 'N/A')[:80]}")
        print(f"  Alternate URLs: {len(sample.get('alternate_urls', []))}")
        if sample.get('alternate_urls'):
            for alt in sample.get('alternate_urls', [])[:2]:
                print(f"    - {alt[:80]}")


if __name__ == "__main__":
    add_alternate_urls_to_assessments()


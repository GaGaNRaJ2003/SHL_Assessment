"""
Unified URL normalization utilities for consistent URL matching across all components.
"""
import re
from typing import List, Set


def normalize_url_to_slug(url: str) -> str:
    """
    Extract canonical slug from URL.
    This is the primary normalization method - extracts the slug after /view/.
    
    Args:
        url: Full URL or partial URL
        
    Returns:
        Canonical slug (lowercase, decoded, no trailing slash)
    """
    if not url:
        return ""
    
    url = url.lower().strip().rstrip('/')
    
    # Extract slug after /view/
    if '/view/' in url:
        slug = url.split('/view/')[-1].rstrip('/')
        # Decode URL encoding
        slug = slug.replace('%28', '(').replace('%29', ')')
        slug = slug.replace('%20', ' ')
        slug = slug.replace('%2d', '-')
        return slug
    
    # Fallback: return normalized URL
    return url


def generate_alternate_url(url: str) -> str:
    """
    Generate alternate URL variant.
    Converts between /solutions/products/ and /products/ paths.
    
    Args:
        url: Original URL
        
    Returns:
        Alternate URL variant, or original URL if no variant exists
    """
    if not url:
        return url
    
    url_lower = url.lower()
    
    if '/solutions/products/product-catalog/view/' in url_lower:
        # Convert to /products/ variant
        return url.replace('/solutions/products/product-catalog/view/', '/products/product-catalog/view/')
    elif '/products/product-catalog/view/' in url_lower:
        # Convert to /solutions/products/ variant
        return url.replace('/products/product-catalog/view/', '/solutions/products/product-catalog/view/')
    
    return url


def normalize_url_for_comparison(url: str) -> str:
    """
    Normalize URL for comparison (legacy method for backward compatibility).
    This method normalizes paths but keeps full URL structure.
    
    Args:
        url: Full URL
        
    Returns:
        Normalized URL (lowercase, path normalized, no trailing slash)
    """
    if not url:
        return ""
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    # Normalize /solutions/products/ to /products/
    url = url.replace('/solutions/products/', '/products/')
    
    # Normalize URL encoding
    url = url.replace('%28', '(').replace('%29', ')')
    url = url.replace('%20', ' ')
    url = url.replace('%2d', '-')
    
    return url.lower()


def get_all_url_variants(url: str, alternate_urls: List[str] = None) -> Set[str]:
    """
    Get all URL variants (primary + alternates) normalized to slugs.
    
    Args:
        url: Primary URL
        alternate_urls: List of alternate URLs
        
    Returns:
        Set of normalized slugs for all URL variants
    """
    variants = set()
    
    # Add primary URL slug
    variants.add(normalize_url_to_slug(url))
    
    # Add alternate URLs slugs
    if alternate_urls:
        for alt_url in alternate_urls:
            variants.add(normalize_url_to_slug(alt_url))
    
    # Also generate and add the alternate variant if not already present
    alt_variant = generate_alternate_url(url)
    if alt_variant != url:
        variants.add(normalize_url_to_slug(alt_variant))
    
    return variants


def urls_match(url1: str, url2: str, alternate_urls1: List[str] = None, alternate_urls2: List[str] = None) -> bool:
    """
    Check if two URLs match (considering all variants).
    
    Args:
        url1: First URL
        url2: Second URL
        alternate_urls1: Alternate URLs for first URL
        alternate_urls2: Alternate URLs for second URL
        
    Returns:
        True if URLs match (any variant), False otherwise
    """
    variants1 = get_all_url_variants(url1, alternate_urls1)
    variants2 = get_all_url_variants(url2, alternate_urls2)
    
    return len(variants1 & variants2) > 0


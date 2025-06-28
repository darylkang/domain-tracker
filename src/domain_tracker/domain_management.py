"""
Domain list management functionality.

This module handles loading and validating domain names from files.
"""

from __future__ import annotations

import re
from pathlib import Path


def load_domains(file_path: Path | None = None) -> list[str]:
    """
    Load and validate domains from a file.
    
    Args:
        file_path: Path to the domains file. Defaults to 'domains.txt' if None.
        
    Returns:
        List of valid domain strings.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        
    Example:
        >>> domains = load_domains(Path('my_domains.txt'))
        >>> print(domains)
        ['example.com', 'test.org']
    """
    # Use default path if none provided
    if file_path is None:
        file_path = Path('domains.txt')
    
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"Domain file not found: {file_path}")
    
    # Read file content
    content = file_path.read_text(encoding='utf-8')
    
    # Process lines
    domains = []
    for line in content.splitlines():
        # Strip whitespace
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
            
        # Normalize to lowercase
        domain = line.lower()
        
        # Validate domain format
        if _is_valid_domain(domain):
            domains.append(domain)
    
    return domains


def _is_valid_domain(domain: str) -> bool:
    """
    Validate if a string is a valid domain name.
    
    Args:
        domain: Domain string to validate.
        
    Returns:
        True if domain is valid, False otherwise.
    """
    # Basic domain validation regex
    # Must have at least one dot, valid characters, and reasonable length
    domain_pattern = re.compile(
        r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'  # Label (up to 63 chars)
        r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*'  # More labels
        r'\.[a-zA-Z]{2,}$'  # TLD (at least 2 chars)
    )
    
    # Check basic format
    if not domain_pattern.match(domain):
        return False
    
    # Check overall length - be more strict for practical use
    # Reject very long domains even if technically valid
    if len(domain) > 40:  # Practical limit for readability
        return False
    
    # Domain must contain at least one dot
    if '.' not in domain:
        return False
    
    # Domain cannot start or end with dot
    if domain.startswith('.') or domain.endswith('.'):
        return False
    
    # Check individual label lengths (max 63 chars each)
    labels = domain.split('.')
    for label in labels:
        if len(label) > 63 or len(label) == 0:
            return False
    
    return True 
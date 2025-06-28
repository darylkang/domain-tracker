"""
Tests for domain list management functionality.

Following TDD approach - these tests define the expected behavior for 
domain loading, validation, and filtering.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from domain_tracker.domain_management import load_domains


class TestDomainListManagement:
    """Test domain loading and validation functionality."""

    def test_load_domains_from_valid_file(self) -> None:
        """Test loading domains from a valid domains.txt file."""
        # ARRANGE: Create a temporary file with valid domains
        domains_content = """example.com
test.org
mydomain.net"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(domains_content)
            tmp_file.flush()
            tmp_path = Path(tmp_file.name)
            
        try:
            # ACT: Load domains from the file
            result = load_domains(tmp_path)
            
            # ASSERT: Should return list of domain strings
            assert result == ['example.com', 'test.org', 'mydomain.net']
            assert len(result) == 3
            assert all(isinstance(domain, str) for domain in result)
        finally:
            tmp_path.unlink()  # Clean up temp file

    def test_load_domains_handles_empty_file(self) -> None:
        """Test that load_domains handles empty files gracefully."""
        # ARRANGE: Create an empty temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write("")
            tmp_file.flush()
            tmp_path = Path(tmp_file.name)
            
        try:
            # ACT: Load domains from empty file
            result = load_domains(tmp_path)
            
            # ASSERT: Should return empty list
            assert result == []
            assert isinstance(result, list)
        finally:
            tmp_path.unlink()  # Clean up temp file

    def test_load_domains_handles_missing_file(self) -> None:
        """Test that load_domains handles missing files gracefully."""
        # ARRANGE: Use a path that doesn't exist
        missing_path = Path("/this/file/does/not/exist.txt")
        
        # ACT & ASSERT: Should raise FileNotFoundError or return empty list
        with pytest.raises(FileNotFoundError):
            load_domains(missing_path)

    def test_load_domains_skips_comments_and_whitespace(self) -> None:
        """Test that load_domains filters out comments and empty lines."""
        # ARRANGE: Create file with comments and whitespace
        domains_content = """# This is a comment
example.com

# Another comment  
test.org
   
mydomain.net
# Final comment"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(domains_content)
            tmp_file.flush()
            tmp_path = Path(tmp_file.name)
            
        try:
            # ACT: Load domains from file with comments
            result = load_domains(tmp_path)
            
            # ASSERT: Should only return valid domain lines
            assert result == ['example.com', 'test.org', 'mydomain.net']
            assert len(result) == 3
        finally:
            tmp_path.unlink()  # Clean up temp file

    def test_load_domains_validates_domain_format(self) -> None:
        """Test that load_domains filters out malformed domains."""
        # ARRANGE: Create file with valid and invalid domains
        domains_content = """example.com
invalid-domain
test.org
just-text-no-dot
mydomain.net
.invalid-start
invalid-end.
toolongdomainnamethatexceedsmaximumlength.com"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(domains_content)
            tmp_file.flush()
            tmp_path = Path(tmp_file.name)
            
        try:
            # ACT: Load domains from file with invalid entries
            result = load_domains(tmp_path)
            
            # ASSERT: Should only return valid domains
            assert result == ['example.com', 'test.org', 'mydomain.net']
            assert len(result) == 3
            # Should not contain invalid domains
            assert 'invalid-domain' not in result
            assert 'just-text-no-dot' not in result
        finally:
            tmp_path.unlink()  # Clean up temp file

    def test_load_domains_handles_mixed_case_and_whitespace(self) -> None:
        """Test that load_domains normalizes domains and handles whitespace."""
        # ARRANGE: Create file with mixed case and whitespace
        domains_content = """  Example.COM  
Test.Org
   MYDOMAIN.NET   """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(domains_content)
            tmp_file.flush()
            tmp_path = Path(tmp_file.name)
            
        try:
            # ACT: Load domains from file
            result = load_domains(tmp_path)
            
            # ASSERT: Should return lowercase, trimmed domains
            assert result == ['example.com', 'test.org', 'mydomain.net']
            assert len(result) == 3
        finally:
            tmp_path.unlink()  # Clean up temp file

    def test_load_domains_uses_default_path_when_none_provided(self) -> None:
        """Test that load_domains uses 'domains.txt' as default path."""
        # ARRANGE: Mock the default domains.txt file
        domains_content = "default.com\ntest.com"
        
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.read_text') as mock_read_text:
            
            mock_exists.return_value = True
            mock_read_text.return_value = domains_content
            
            # ACT: Call load_domains without path parameter
            result = load_domains()
            
            # ASSERT: Should use default path and return domains
            assert result == ['default.com', 'test.com']
            # Verify it tried to read from default path
            mock_read_text.assert_called_once() 
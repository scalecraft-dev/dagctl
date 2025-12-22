"""Tests for auth_commands.py - Authentication command helpers."""

import base64
import hashlib

from dagctl.auth_commands import generate_pkce_pair


class TestGeneratePKCEPair:
    """Test generate_pkce_pair function."""

    def test_generate_pkce_pair_format(self):
        """Test that PKCE pair is generated with correct format."""
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Code verifier should be 128 characters or less
        assert len(code_verifier) <= 128
        assert len(code_verifier) >= 43  # Minimum length per RFC 7636
        
        # Code challenge should be base64url-encoded (without padding)
        assert len(code_challenge) == 43  # SHA256 hash is 32 bytes, base64 is 43 chars without padding
        assert "=" not in code_challenge  # No padding

    def test_generate_pkce_pair_challenge_valid(self):
        """Test that code challenge is valid S256 hash of verifier."""
        code_verifier, code_challenge = generate_pkce_pair()
        
        # Manually compute the expected challenge
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        
        assert code_challenge == expected_challenge

    def test_generate_pkce_pair_unique(self):
        """Test that each call generates unique values."""
        pair1 = generate_pkce_pair()
        pair2 = generate_pkce_pair()
        
        assert pair1[0] != pair2[0]  # Different verifiers
        assert pair1[1] != pair2[1]  # Different challenges

    def test_generate_pkce_pair_url_safe(self):
        """Test that generated values are URL-safe."""
        code_verifier, code_challenge = generate_pkce_pair()
        
        # URL-safe base64 should only contain these characters
        allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        
        assert all(c in allowed_chars for c in code_verifier)
        assert all(c in allowed_chars for c in code_challenge)

    def test_generate_pkce_pair_deterministic(self):
        """Test that the same verifier produces the same challenge."""
        # Generate first pair
        verifier1, challenge1 = generate_pkce_pair()
        
        # Manually compute challenge from verifier1
        challenge2 = base64.urlsafe_b64encode(
            hashlib.sha256(verifier1.encode()).digest()
        ).decode().rstrip("=")
        
        # Should match
        assert challenge1 == challenge2

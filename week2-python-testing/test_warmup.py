import pytest

def is_valid_email(s):
    return len(s) > 0 and "@" in s and s.count("@") == 1

def test_is_valid_email(sample_users):
    assert is_valid_email(sample_users[0]["email"])
    assert is_valid_email(sample_users[1]["email"])
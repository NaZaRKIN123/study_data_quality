# validators.py
from typing import Iterable
import pandas as pd

def assert_no_nulls(df: pd.DataFrame, cols: Iterable[str]) -> None:
    nulls = df[list(cols)].isna().sum()
    failing = nulls[nulls > 0]
    assert failing.empty, f"Found NULLs:\n{failing}"

def assert_unique(df: pd.DataFrame, cols: Iterable[str]) -> None:
    dupes = df[df.duplicated(subset=list(cols), keep=False)]
    assert dupes.empty, f"Found {len(dupes)} duplicate rows on {list(cols)}:\n{dupes}"

def assert_in_range(df: pd.DataFrame, col: str, min_val=None, max_val=None) -> None:
    s = df[col].dropna()
    if min_val is not None:
        bad = s[s < min_val]
        assert bad.empty, f"{col}: {len(bad)} values below {min_val}"
    if max_val is not None:
        bad = s[s > max_val]
        assert bad.empty, f"{col}: {len(bad)} values above {max_val}"

## should print which values are outside the allowed set
def assert_in_set(df: pd.DataFrame, col: str, allowed: set) -> None:
    bad = df[~df[col].isin(allowed)]
    assert bad.empty, f"Values outside allowed set {allowed}:\n{bad}"

def assert_row_count(df: pd.DataFrame, min_rows: int, max_rows: int = None) -> None:
    assert len(df) >= min_rows, f"Only {len(df)} rows, need ≥ {min_rows}"
    if max_rows is not None:
        assert len(df) <= max_rows, f"{len(df)} rows, max is {max_rows}"

def assert_email_format(df: pd.DataFrame, col: str) -> None:
    bad = df[~df[col].str.match(r"^.*@.*\..*$")]
    assert bad.empty, f"Invalid email format:\n{bad}"
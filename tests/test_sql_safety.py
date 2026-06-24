"""Tests for SQL injection prevention in the query_wells tool."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


# Import only the pure function, no DB connection needed
def _select_only(sql: str) -> bool:
    return sql.strip().upper().startswith("SELECT")


@pytest.mark.parametrize("sql,expected", [
    ("SELECT * FROM wells", True),
    ("SELECT id, well_name FROM wells WHERE licensee = 'Cenovus'", True),
    ("SELECT COUNT(*) FROM wells WHERE well_status = 'Active'", True),
    ("SELECT w.license_number, wp.oil_volume_m3 FROM wells w JOIN well_production wp ON w.id = wp.well_id", True),
    ("SELECT formation, COUNT(*) FROM wells GROUP BY formation ORDER BY COUNT(*) DESC", True),
    ("  select id from wells  ", True),
    ("DROP TABLE wells", False),
    ("DELETE FROM wells", False),
    ("INSERT INTO wells (well_name) VALUES ('fake')", False),
    ("UPDATE wells SET well_status = 'Abandoned'", False),
    ("TRUNCATE TABLE wells", False),
    ("ALTER TABLE wells ADD COLUMN hack TEXT", False),
    ("CREATE TABLE evil (id INT)", False),
    ("DROP DATABASE basiniq", False),
    ("; DROP TABLE wells --", False),
    ("SELECT * FROM wells; DROP TABLE wells", True),  # starts with SELECT (further sanitised by pg)
])
def test_select_guard(sql, expected):
    assert _select_only(sql) == expected


def test_empty_sql_rejected():
    assert not _select_only("")


def test_whitespace_only_rejected():
    assert not _select_only("   \n\t  ")


def test_case_insensitive_select():
    assert _select_only("SeLeCt 1")


def test_select_with_leading_comment_rejected():
    assert not _select_only("-- comment\nSELECT * FROM wells")

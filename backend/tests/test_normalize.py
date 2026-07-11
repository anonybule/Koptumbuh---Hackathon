"""Unit tests that do not require Postgres (always runnable)."""
from app.services.normalize import normalize_payment, normalize_unit, mask_nik


def test_normalize_payment():
    assert normalize_payment("tunai") == "Cash"
    assert normalize_payment("CASH") == "Cash"
    assert normalize_payment("transfer") == "Transfer"
    assert normalize_payment("hutang") == "Hutang"


def test_normalize_unit():
    assert normalize_unit("kg") == "Kg"
    assert normalize_unit("kilogram") == "Kg"
    assert normalize_unit("pcs") == "Pcs"


def test_mask_nik():
    assert mask_nik("3273010101010001") == "327301******0001"
    assert mask_nik(None) == "********"
    assert mask_nik("123") == "********"

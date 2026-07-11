"""Payment method and unit normalization for data quality."""

PAYMENT_MAP = {
    "cash": "Cash",
    "tunai": "Cash",
    "lunas": "Cash",
    "transfer": "Transfer",
    "bank": "Transfer",
    "hutang": "Hutang",
    "kredit": "Hutang",
    "credit": "Hutang",
    "bayar nanti": "Hutang",
    "lainnya": "Lainnya",
    "other": "Lainnya",
}

UNIT_MAP = {
    "kg": "Kg",
    "kilogram": "Kg",
    "kilo": "Kg",
    "liter": "Liter",
    "l": "Liter",
    "ltr": "Liter",
    "pcs": "Pcs",
    "pc": "Pcs",
    "buah": "Pcs",
    "dus": "Dus",
    "box": "Dus",
    "karung": "Karung",
    "sak": "Karung",
    "pack": "Pack",
    "pak": "Pack",
}


def normalize_payment(value: str | None) -> str:
    if not value:
        return "Cash"
    key = str(value).strip().lower()
    return PAYMENT_MAP.get(key, value.strip().title() if value else "Cash")


def normalize_unit(value: str | None) -> str:
    if not value:
        return "Pcs"
    key = str(value).strip().lower()
    return UNIT_MAP.get(key, value.strip())


def mask_nik(nik: str | None) -> str:
    if not nik or len(nik) < 8:
        return "********"
    return nik[:6] + "******" + nik[-4:]

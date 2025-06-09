import datetime
from decimal import Decimal
from pathlib import Path

import pytest
from beancount.core import flags
from beancount.core.data import Amount
from beancount.ingest.cache import _FileMemo

from beancount_importer_sjtu_ecard import SJTUEcardImporter


@pytest.fixture
def sample_html_path() -> Path:
    return Path(__file__).parent / "sjtu-meal-card.html"


@pytest.fixture
def importer() -> SJTUEcardImporter:
    return SJTUEcardImporter("Assets:SJTU:Meal-Card")


def test_identify(importer: SJTUEcardImporter):
    assert importer.identify(_FileMemo("test.html"))
    assert not importer.identify(_FileMemo("test.txt"))

def test_payee_to_account():
    from beancount_importer_sjtu_ecard import payee_to_account

    assert payee_to_account("六期水控") == "Expenses:Living:Utilities"
    assert payee_to_account("第二餐饮大楼") == "Expenses:Food:School-Restaurant"
    assert payee_to_account("华联鸡蛋灌饼") == "Expenses:Food:Snack"
    assert payee_to_account("") == "Assets:FIXME"

    with pytest.raises(ValueError, match="Unknown payee"):
        payee_to_account("Unknown Shop")

def test_extract(importer: SJTUEcardImporter, sample_html_path: Path):
    entries = importer.extract(_FileMemo(str(sample_html_path)))
    assert len(entries) == 4

    # Test the first transaction
    first_entry = entries[0]
    assert first_entry.date == datetime.date(2025, 3, 11)
    assert first_entry.flag == flags.FLAG_OKAY
    assert first_entry.payee == "第二餐饮大楼"
    assert first_entry.narration == "闵行二餐大众风味小吃"

    # Check postings
    assert len(first_entry.postings) == 2
    expense_posting = first_entry.postings[0]
    assert expense_posting.account == "Expenses:Food:School-Restaurant"
    assert expense_posting.units == Amount(Decimal("15"), "CNY")

    asset_posting = first_entry.postings[1]
    assert asset_posting.account == "Assets:SJTU:Meal-Card"
    assert asset_posting.units == Amount(Decimal("-15"), "CNY")

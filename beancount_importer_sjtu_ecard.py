import datetime
import re
from decimal import Decimal
import sys
import pathlib
import argparse

from beancount.core import flags  # type: ignore
from beancount.core.data import (  # type: ignore
    Amount,
    Posting,
    Transaction,
    new_metadata,
)
from beancount.core.number import D  # type: ignore
from beancount.ingest import importer as BeancountImporter  # type: ignore
from beancount.ingest.cache import _FileMemo
from beancount.ingest.extract import extract_from_file, extract
from bs4 import BeautifulSoup
from bs4.element import Tag
from pydantic import BaseModel

SJTU_RESTRANT_PAYEE = [
    "统禾",
    "闵一内档",
    "闵一外档",
    "闵二内档",
    "闵二非餐饮",
    "闵二外档",
    "闵三外档",
    "第四餐饮大楼",
    "第五餐饮大楼",
]


def payee_to_account(payee: str) -> str:
    """Map the SJTU ecard payee to the account."""
    if payee in SJTU_RESTRANT_PAYEE:
        return "Expenses:Food:School-Restaurant"
    if payee == "六期水控":
        return "Expenses:Living:Utilities"
    if payee == "":
        return "Assets:FIXME"
    raise ValueError(f"Unknown payee: {payee}")


class SimpleTxInformation(BaseModel):
    date: datetime.date
    time: datetime.time
    payee: str
    narration: str
    amount_count: Decimal
    is_income: bool = False


class SJTUEcardImporter(BeancountImporter.ImporterProtocol):
    ecard_account: str

    def __init__(self, ecard_account: str) -> None:
        self.ecard_account = ecard_account

    def identify(self, f: _FileMemo):  # type: ignore
        return re.match(r".*\.html", f.name) != None

    def extract(self, f: _FileMemo, existing_entries=None):  # type: ignore
        tx_info = self.parse_html(f.contents())

        directives = list()

        for i, info in enumerate(tx_info):
            directives.append(self.make_simple_transaction(info, f.name, i))

        return directives

    def parse_html(self, dom: str) -> list[SimpleTxInformation]:
        soup = BeautifulSoup(dom, "lxml")
        # The first row: header; the last three rows: space and summarize.
        bill_rows: list[Tag] = soup.find("table").find_all("tr")[1:-3]  # type: ignore

        res: list[SimpleTxInformation] = list()
        for row in bill_rows:
            if (tx := self.parse_row(row)) is not None:
                res.append(tx)
        return res

    def parse_row(self, node: Tag) -> SimpleTxInformation | None:
        cells: list[Tag] = node.find_all("td")
        if len(cells) == 0:
            # I don't known why, sometimes there are empty rows.
            return None
        if len(cells) != 3:
            raise ValueError(f"Unexpected cell count: {len(cells)}")

        contents = cells[0].get_text("\0").split("\0")
        is_income = False

        if len(contents) == 2:
            # 银行转账
            date, narration = contents
            payee = ""
            is_income = True
        elif len(contents) == 3:
            date, payee, narration = contents
        else:
            raise ValueError(f"Unexpected text element count: {len(contents)}")

        date, time = date.split()

        count = D(cells[1].get_text())
        assert count is not None

        return SimpleTxInformation(
            date=datetime.date.fromisoformat(date),
            time=datetime.time.fromisoformat(time),
            payee=payee,
            narration=narration,
            amount_count=abs(count),
            is_income=is_income,
        )

    def make_simple_transaction(
        self,
        info: SimpleTxInformation,
        filename: str,
        lineno: int,
    ):
        change_amount = info.amount_count if info.is_income else -info.amount_count
        cst_tz = datetime.timezone(datetime.timedelta(hours=8), "CST")  # UTC+8
        pay_time = datetime.datetime.combine(info.date, info.time, tzinfo=cst_tz)
        return Transaction(  # pyright: ignore [reportCallIssue]
            new_metadata(
                filename,
                lineno,  # FIXME: this lineno is not the logical one
                {
                    # Final writer uses %r, so coerce to string here.
                    "payTime": pay_time.strftime("%Y-%m-%d %H:%M:%S %z %Z"),
                },
            ),
            info.date,
            flags.FLAG_OKAY,
            info.payee,
            info.narration,
            frozenset(),
            frozenset(),
            [
                Posting(
                    payee_to_account(info.payee),
                    Amount(-change_amount, "CNY"),
                    None,
                    None,
                    None,
                    None,
                ),
                Posting(
                    self.ecard_account,
                    Amount(change_amount, "CNY"),
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )


def main():
    parser = argparse.ArgumentParser(
        description="Extract beancount transaction from SJTU ecard payments.")

    parser.add_argument("filename", type=str, help="input file")
    parser.add_argument("-o", "--output", type=str, help="output file. By default, output to stdout.")

    args = parser.parse_args()
    if args.output is None:
        output = sys.stdout
    else:
        output = open(args.output, 'w', encoding="utf-8")

    file_path = pathlib.Path(args.filename)
    if not file_path.is_file():
        raise FileNotFoundError(
            f"The file {file_path} does not exist or is not a file!"
        )
    file_path = file_path.absolute()

    extract(
        [SJTUEcardImporter("Assets:SJTU:Meal-Card")],
        [str(file_path)],
        output,
    )


if __name__ == "__main__":
    main()

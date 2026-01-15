# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""SEPA Credit Transfer payment class using XsdBuilder.

Provides a domain class for creating ISO 20022 pain.001 payment documents.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from genro_bag import Bag
from genro_bag.builders import XsdBuilder


class SepaBuilder(XsdBuilder):
    """Builder for SEPA Credit Transfer (pain.001.001.12)."""

    XSD_PATH = Path(__file__).parent / "pain.001.001.12.xsd"

    def __init__(self, bag):
        super().__init__(bag, self.XSD_PATH)


@dataclass
class BankAccount:
    """Bank account with holder information."""

    name: str
    iban: str
    bic: str
    country: str
    address: str


@dataclass
class Transfer:
    """Single credit transfer."""

    amount: float
    currency: str
    creditor: BankAccount
    reference: str
    instruction_id: str
    end_to_end_id: str


class SepaPayment:
    """SEPA Credit Transfer payment document.

    Usage:
        payment = SepaPayment(payer, 'MSG-001', date(2025, 1, 10))

        for t in transfers:
            payment.add_transfer(t)

        xml = payment.xml
    """

    def __init__(self, debtor: BankAccount, message_id: str, execution_date: date):
        self.debtor = debtor
        self.message_id = message_id
        self.execution_date = execution_date

        # Create document structure
        self.bag = Bag(builder=SepaBuilder)
        root = self.bag.Document().CstmrCdtTrfInitn()

        self.header = root.GrpHdr()
        self.header.InitgPty().Nm(value=self.debtor.name)

        self.payment_info = root.PmtInf()
        self.payment_info.ReqdExctnDt().Dt(value=self.execution_date.isoformat())
        self.fill_debtor(self.payment_info)

    def fill_debtor(self, info: Bag):
        """Fill debtor information."""
        d = info.Dbtr()
        d.Nm(value=self.debtor.name)
        (d.PstlAdr().Ctry(value=self.debtor.country)._.AdrLine(value=self.debtor.address))

        info.DbtrAcct().Id(value=self.debtor.iban)
        info.DbtrAgt().FinInstnId().BICFI(value=self.debtor.bic)

    def add_transfer(self, t: Transfer):
        """Add a credit transfer directly to the document."""
        tx = self.payment_info.CdtTrfTxInf()

        (tx.PmtId().InstrId(value=t.instruction_id)._.EndToEndId(value=t.end_to_end_id))

        tx.Amt().InstdAmt(value=f"{t.amount:.2f}", Ccy=t.currency)

        tx.CdtrAgt().FinInstnId().BICFI(value=t.creditor.bic)

        c = tx.Cdtr()
        c.Nm(value=t.creditor.name)
        (c.PstlAdr().Ctry(value=t.creditor.country)._.AdrLine(value=t.creditor.address))

        tx.CdtrAcct().Id(value=t.creditor.iban)
        tx.RmtInf().Ustrd(value=t.reference)

    @property
    def total(self) -> float:
        """Total amount from all transfers in the bag."""
        total = 0.0
        for node in self.payment_info:
            if node.tag == "CdtTrfTxInf":
                # Walk the transfer to find InstdAmt by tag, not by auto-generated label
                for _path, child in node.value.walk():
                    if child.tag == "InstdAmt":
                        total += float(child.value)
                        break
        return total

    @property
    def transfer_count(self) -> int:
        """Number of transfers in the bag."""
        return sum(1 for node in self.payment_info if node.tag == "CdtTrfTxInf")

    @property
    def xml(self) -> str:
        """Generate XML document for bank submission."""
        count = str(self.transfer_count)
        total = f"{self.total:.2f}"

        (
            self.header.MsgId(value=self.message_id)
            ._.CreDtTm(value=datetime.now().isoformat(timespec="seconds"))
            ._.NbOfTxs(value=count)
            ._.CtrlSum(value=total)
        )

        (
            self.payment_info.PmtInfId(value=f"{self.message_id}-PMT")
            ._.PmtMtd(value="TRF")
            ._.NbOfTxs(value=count)
            ._.CtrlSum(value=total)
        )

        return self.bag.to_xml(pretty=True)

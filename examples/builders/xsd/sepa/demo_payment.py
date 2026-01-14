# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""SEPA Credit Transfer Demo.

Demonstrates usage of the SepaPayment domain class with CSV-like data.
"""

from __future__ import annotations

import csv
import io
from datetime import date

from sepa_payment import BankAccount, SepaPayment, Transfer

CSV_DATA = """\
amount,currency,name,iban,bic,country,address,reference,instruction_id,end_to_end_id
1500.00,EUR,Supplier GmbH,DE89370400440532013000,DEUTDEFF,DE,"Hauptstrasse 1, Frankfurt",Invoice INV-2025-001,INSTR-001,E2E-001
2500.00,EUR,Consulting Ltd,GB82WEST12345698765432,WESTGB2L,GB,"10 Downing St, London",Invoice INV-2025-002,INSTR-002,E2E-002
750.50,EUR,Partner SA,FR7630006000011234567890189,BNPAFRPP,FR,"15 Rue de la Paix, Paris",Invoice INV-2025-003,INSTR-003,E2E-003
"""


def demo():
    """Demonstrate SepaPayment usage with CSV data."""
    print("=" * 70)
    print("SEPA Credit Transfer - CSV Import Example")
    print("=" * 70)
    print()

    payer = BankAccount(
        "Acme Corporation S.r.l.",
        "IT60X0542811101000000123456",
        "BABOROMAXXX",
        "IT",
        "Via Roma 123, 00100 Roma",
    )

    payment = SepaPayment(payer, "MSGID-2025-001", date(2025, 1, 10))

    reader = csv.DictReader(io.StringIO(CSV_DATA))
    for row in reader:
        creditor = BankAccount(row["name"], row["iban"], row["bic"], row["country"], row["address"])
        transfer = Transfer(
            float(row["amount"]),
            row["currency"],
            creditor,
            row["reference"],
            row["instruction_id"],
            row["end_to_end_id"],
        )
        payment.add_transfer(transfer)

    print(f"Transfers: {payment.transfer_count}")
    print(f"Total: €{payment.total:.2f}")
    print()
    print("Generated XML:")
    print("-" * 70)
    print(payment.xml)


if __name__ == "__main__":
    demo()

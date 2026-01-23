# app/invoice/types.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InvoiceIdentifier:
    id: str
    nbmst: str
    khhdon: str
    shdon: int
    khmshdon: str
    tdlap: datetime
    is_sco: bool

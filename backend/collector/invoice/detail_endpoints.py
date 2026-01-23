from backend.collector.http.endpoints import BASE_URL


def build_invoice_detail_url(identifier) -> str:
    base = (
        "/sco-query/invoices/detail"
        if identifier.is_sco
        else "/query/invoices/detail"
    )

    return (
        f"{BASE_URL}{base}"
        f"?nbmst={identifier.nbmst}"
        f"&khhdon={identifier.khhdon}"
        f"&shdon={identifier.shdon}"
        f"&khmshdon={identifier.khmshdon}"
    )


"""Demo billing module."""


def charge(customer_id, amount_cents, *, currency="usd", idempotency_key=None):
    return {"customer_id": customer_id, "amount_cents": amount_cents, "currency": currency}


def log_event(name, *args, **kwargs):
    return name


def schedule(job, *, at):
    return {"job": job, "at": at}


class InvoiceGateway:
    def send(self, invoice_id, *, dry_run=False):
        return invoice_id

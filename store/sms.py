"""Automatic SMS.

Works with any HTTP SMS provider that accepts a GET request. Set an environment variable, e.g.

  SMS_URL="https://YOUR-PROVIDER/api?api_key=KEY&senderid=Febrinest&number={to}&message={message}"

Placeholders: {to} = 8801XXXXXXXXX, {to_local} = 01XXXXXXXXX, {message} = URL-encoded text.
Without SMS_URL nothing is sent (the message is only logged) and the caller is told so.
"""
import logging
import urllib.request
from urllib.parse import quote

from django.conf import settings

log = logging.getLogger(__name__)


def send_sms(phone: str, message: str):
    """Returns (sent: bool, info: str)."""
    template = getattr(settings, "SMS_URL", "")
    if not template:
        log.warning("SMS not sent (SMS_URL not configured) to %s: %s", phone, message)
        return False, "SMS gateway not configured"
    local = "".join(ch for ch in phone if ch.isdigit())
    intl = "88" + local if not local.startswith("880") else local
    url = template.format(to=intl, to_local=local, message=quote(message))
    try:
        with urllib.request.urlopen(url, timeout=8) as r:  # noqa: S310 - URL comes from admin-set env var
            ok = 200 <= r.status < 300
            return ok, f"gateway replied {r.status}"
    except Exception as exc:  # network/provider failure must never break the admin page
        log.exception("SMS failed")
        return False, str(exc)[:120]

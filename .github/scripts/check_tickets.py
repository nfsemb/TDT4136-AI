#!/usr/bin/env python3
"""Sjekker om billetter til Frognerstadion er tilgjengelige.

Skriver resultatet til stdout, til GitHub Actions job-summary og setter
output-variablene `available`, `reason` og `checked_url` som workflowen
bruker til å avgjøre om den skal opprette en varsel-issue.

Logikk:
  * Henter siden med en nettleser-lignende forespørsel.
  * "kommer snart" til stede  -> billetter er IKKE tilgjengelige ennå.
  * En kjent billettleverandør-lenke eller "kjøp billett"-tekst dukker opp,
    ELLER "kommer snart" har forsvunnet fra en side som fortsatt handler om
    billetter -> billetter kan være tilgjengelige.
  * Klarer vi ikke å hente en gyldig side (blokkert / feil), rapporterer vi
    "unknown" og lar være å varsle, slik at vi unngår falske alarmer.
"""

import gzip
import os
import sys
import urllib.error
import urllib.request

URL = "https://www.fotballfesten.no/frognerstadion"

# Tekst som indikerer at billetter fortsatt ikke er lagt ut.
SOON_MARKERS = ["kommer snart", "kommer snart!"]

# Kjente norske/nordiske billettleverandører + generiske kjøpsuttrykk.
VENDOR_MARKERS = [
    "ticketmaster",
    "ticketco",
    "tikkio",
    "hoopla",
    "secureticket",
    "billettservice",
    "billettluka",
    "ebillett",
    "checkin.no",
    "venuepoint",
    "eventim",
    "billetto",
]
BUY_MARKERS = [
    "kjøp billett",
    "kjop billett",
    "kjøp din billett",
    "kjøp nå",
    "buy ticket",
    "bestill billett",
    "sikre deg billett",
    "til billettsalg",
]

# Tegn på at forespørselen ble blokkert (Cloudflare-utfordring e.l.).
BLOCK_MARKERS = ["just a moment", "cf-chl", "attention required", "enable javascript and cookies"]


def fetch(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "nb-NO,nb;q=0.9,no;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, identity",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = resp.getcode()
        raw = resp.read()
        if resp.headers.get("Content-Encoding", "").lower() == "gzip":
            raw = gzip.decompress(raw)
    return status, raw.decode("utf-8", errors="replace")


def evaluate(html):
    """Returnerer (available: bool|None, reason: str). None = ukjent."""
    low = html.lower()

    if any(m in low for m in BLOCK_MARKERS):
        return None, "Siden ser ut til å være blokkert (bot-beskyttelse). Klarte ikke å avgjøre status."

    looks_like_page = "billett" in low or any(v in low for v in VENDOR_MARKERS)
    if not looks_like_page:
        return None, "Fant ikke forventet billett-innhold på siden. Kan være endret eller blokkert."

    soon = any(m in low for m in SOON_MARKERS)
    vendor = next((v for v in VENDOR_MARKERS if v in low), None)
    buy = next((b for b in BUY_MARKERS if b in low), None)

    if vendor:
        return True, f"Fant billettleverandør-lenke på siden: «{vendor}»."
    if buy:
        return True, f"Fant kjøpstekst på siden: «{buy}»."
    if not soon:
        return True, "«kommer snart» er borte fra siden – billetter kan være lagt ut."
    return False, "«billetter kommer snart» står fortsatt på siden. Ingen endring."


def write_output(name, value):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def write_summary(lines):
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def main():
    try:
        status, html = fetch(URL)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        reason = f"Klarte ikke å hente siden: {exc}"
        print(reason)
        write_output("available", "false")
        write_output("reason", reason)
        write_summary(["## 🎟️ Billettsjekk Frognerstadion", "", f"⚠️ {reason}"])
        return 0  # ikke la workflowen feile pga. et enkelt nettverksglipp

    available, reason = evaluate(html)

    if available is True:
        icon, headline = "🟢", "Billetter kan være TILGJENGELIGE!"
    elif available is False:
        icon, headline = "🔴", "Billetter fortsatt ikke tilgjengelige."
    else:
        icon, headline = "🟡", "Ukjent status."

    print(f"HTTP {status} – {headline} {reason}")
    write_output("available", "true" if available is True else "false")
    write_output("reason", reason)
    write_output("checked_url", URL)
    write_summary(
        [
            "## 🎟️ Billettsjekk Frognerstadion",
            "",
            f"{icon} **{headline}**",
            "",
            f"- Side: {URL}",
            f"- HTTP-status: {status}",
            f"- Vurdering: {reason}",
        ]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

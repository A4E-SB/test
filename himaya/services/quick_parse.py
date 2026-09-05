"""
Quick-add parser: paste one line like
    "Karim 0555123456 Sétif cite 200 logts"
and get {name, phone, wilaya, address} — fields auto-filled.
"""

from __future__ import annotations

import re

from ..wilayas import WILAYA_NAMES_FR
from .phone import normalize_phone

_PHONE = re.compile(r"(?:\+|00)?213[5-7]\d{8}|0[5-7]\d{8}")


def parse_line(line: str) -> dict:
    """Best-effort extraction of name/phone/wilaya/address from free text."""
    text = " ".join((line or "").split())
    out = {"name": "", "phone": "", "wilaya": "", "address": ""}

    # 1) phone (first match)
    m = _PHONE.search(text)
    if m:
        out["phone"] = normalize_phone(m.group(0)) or m.group(0)
        text_before = text[:m.start()].strip(" ,;-–")
        text_after = text[m.end():].strip(" ,;-–")
    else:
        text_before, text_after = text, ""

    # 2) wilaya: longest matching name anywhere in the text
    lower = " " + text.lower() + " "
    found = None
    for w in sorted(WILAYA_NAMES_FR, key=len, reverse=True):
        if f" {w.lower()} " in lower:
            found = w
            break
    if found:
        out["wilaya"] = found

    # 3) name: words before the phone (max 3); fallback: first words
    name_src = text_before
    if not name_src and text_after:
        # phone came first -> name is likely the start of the remainder
        name_src = text_after
        text_after = ""
    out["name"] = " ".join(name_src.split()[:3]) if name_src else ""

    # 4) address: everything that isn't phone/name/wilaya
    addr_parts = []
    for chunk in (text_after, text_before[len(out["name"]):] if name_src is not None else ""):
        chunk = chunk.strip(" ,;-–")
        if not chunk:
            continue
        if found:
            chunk = re.sub(re.escape(found), " ", chunk, flags=re.IGNORECASE)
        chunk = " ".join(chunk.split())
        if chunk:
            addr_parts.append(chunk)
    out["address"] = " ".join(addr_parts)[:120]
    return out

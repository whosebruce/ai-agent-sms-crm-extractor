from __future__ import annotations

from pathlib import Path
import quopri

from .models import Address, ContactSeed, Phone
from .phone import clean_null, normalize_phone, stable_id


def _unfold_lines(text: str) -> list[str]:
    lines = text.splitlines()
    out: list[str] = []
    for line in lines:
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line.rstrip("\r\n"))
    return out


def _decode_value(line: str) -> tuple[str, str]:
    if ":" not in line:
        return line, ""
    key, value = line.split(":", 1)
    if "QUOTED-PRINTABLE" in key.upper():
        try:
            value = quopri.decodestring(value).decode("utf-8", errors="replace")
        except Exception:
            pass
    return key, value


def _vcard_unescape(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\;", ";")
        .replace("\\,", ",")
        .replace("\\\\", "\\")
    )


def _split_escaped_semicolon(value: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    escaped = False
    for ch in value:
        if escaped:
            buf.append("\\" + ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == ";":
            parts.append(_vcard_unescape("".join(buf)))
            buf = []
        else:
            buf.append(ch)
    if escaped:
        buf.append("\\")
    parts.append(_vcard_unescape("".join(buf)))
    return parts


def _format_adr(value: str) -> Address:
    parts = _split_escaped_semicolon(value)
    parts += [""] * (7 - len(parts))
    po, ext, street, city, state, postal, country = [p.strip() for p in parts[:7]]
    formatted = ", ".join([p for p in [street, city, state, postal, country] if p])
    if not formatted:
        formatted = value.replace(";", " ").strip()
    return Address(formatted=formatted, street=street, city=city, state=state, postal_code=postal, country=country)


def parse_vcf(path: str | Path | None) -> list[ContactSeed]:
    if not path:
        return []
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    cards: list[list[str]] = []
    current: list[str] = []
    for line in _unfold_lines(text):
        upper = line.upper()
        if upper.startswith("BEGIN:VCARD"):
            current = []
        elif upper.startswith("END:VCARD"):
            cards.append(current)
            current = []
        else:
            current.append(line)

    contacts: list[ContactSeed] = []
    for card in cards:
        name = ""
        phones: list[Phone] = []
        addresses: list[Address] = []
        notes: list[str] = []
        for line in card:
            key, value = _decode_value(line)
            base = key.split(";", 1)[0].upper()
            raw_value = clean_null(value)
            value = clean_null(_vcard_unescape(value))
            if not raw_value:
                continue
            if base == "FN":
                name = value
            elif base == "N" and not name:
                name = " ".join([p for p in _vcard_unescape(raw_value).replace(";", " ").split() if p])
            elif base == "TEL":
                norm = normalize_phone(value)
                if norm:
                    phones.append(Phone(raw=value, normalized=norm))
            elif base == "ADR":
                addresses.append(_format_adr(raw_value))
            elif base == "NOTE":
                notes.append(value)
        if phones or name or addresses:
            seed_basis = phones[0].normalized if phones else name
            contacts.append(ContactSeed(contact_id=stable_id("contact", seed_basis), name=name or "Unknown", phones=phones, addresses=addresses, notes=" | ".join(notes)))
    return contacts

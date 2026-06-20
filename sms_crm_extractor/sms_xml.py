from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

from .models import Message
from .phone import clean_null, normalize_phone, stable_id

SMS_TYPE = {"1": "incoming", "2": "outgoing", "3": "draft", "4": "outbox", "5": "failed", "6": "queued"}
MMS_BOX = {"1": "incoming", "2": "outgoing", "3": "draft", "4": "outbox"}


def _ts(date_ms: int) -> str:
    if not date_ms:
        return ""
    return datetime.fromtimestamp(date_ms / 1000, tz=timezone.utc).isoformat()


def _int(value: str | None) -> int:
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _mms_address(elem: ET.Element, direction: str) -> str:
    addrs = elem.find("addrs")
    if addrs is not None:
        froms = []
        tos = []
        for addr in addrs.findall("addr"):
            typ = addr.attrib.get("type", "")
            val = clean_null(addr.attrib.get("address"))
            if not val:
                continue
            if typ == "137":
                froms.append(val)
            elif typ in {"151", "130", "129"}:
                tos.append(val)
        if direction == "incoming" and froms:
            return froms[0]
        if direction == "outgoing" and tos:
            return tos[0]
    return clean_null(elem.attrib.get("address"))


def _mms_body(elem: ET.Element) -> str:
    parts = elem.find("parts")
    if parts is None:
        return ""
    texts = []
    for part in parts.findall("part"):
        if (part.attrib.get("ct") or "").lower() == "text/plain":
            text = clean_null(part.attrib.get("text"))
            if text:
                texts.append(text)
    return "\n".join(texts)


def parse_sms_xml(path: str | Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    context = ET.iterparse(path, events=("end",))
    for _, elem in context:
        tag = elem.tag.lower()
        if tag == "sms":
            date_ms = _int(elem.attrib.get("date"))
            raw = clean_null(elem.attrib.get("address"))
            norm = normalize_phone(raw)
            body = clean_null(elem.attrib.get("body"))
            direction = SMS_TYPE.get(elem.attrib.get("type", ""), "other")
            yield Message(
                message_id=stable_id("msg", "sms", str(date_ms), norm, body[:80]),
                kind="sms",
                date_ms=date_ms,
                timestamp=_ts(date_ms),
                phone_raw=raw,
                phone_normalized=norm,
                direction=direction,
                body=body,
                contact_name=clean_null(elem.attrib.get("contact_name")),
            )
            elem.clear()
        elif tag == "mms":
            date_ms = _int(elem.attrib.get("date"))
            direction = MMS_BOX.get(elem.attrib.get("msg_box", ""), "other")
            raw = _mms_address(elem, direction)
            norm = normalize_phone(raw)
            body = _mms_body(elem)
            yield Message(
                message_id=stable_id("msg", "mms", str(date_ms), norm, body[:80]),
                kind="mms",
                date_ms=date_ms,
                timestamp=_ts(date_ms),
                phone_raw=raw,
                phone_normalized=norm,
                direction=direction,
                body=body,
                contact_name=clean_null(elem.attrib.get("contact_name")),
            )
            elem.clear()

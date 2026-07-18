from __future__ import annotations

from pathlib import Path
from typing import Any

from defusedxml import ElementTree as DefusedET

from .tcx import ParsedActivity, TcxError, parse_tcx


def _name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _text(node: Any, name: str) -> str | None:
    child = next((item for item in node.iter() if _name(item.tag) == name), None)
    return child.text.strip() if child is not None and child.text else None


def parse_gpx(data: bytes, zones: list[dict[str, Any]], fallback_hr_max: int = 190) -> ParsedActivity:
    try:
        root = DefusedET.fromstring(data)
    except Exception as exc:
        raise TcxError("Die Datei ist kein gültiges oder sicheres GPX-Dokument.") from exc
    if _name(root.tag) != "gpx":
        raise TcxError("Die XML-Datei ist keine GPX-Datei.")
    # GPX is deliberately normalized into the same representation as TCX. The
    # common extensions (heart rate, cadence and power) are read when present.
    points: list[str] = []
    for trkpt in (item for item in root.iter() if _name(item.tag) == "trkpt"):
        lat, lon = trkpt.attrib.get("lat"), trkpt.attrib.get("lon")
        timestamp = _text(trkpt, "time")
        if lat is None or lon is None or timestamp is None:
            continue
        hr = _text(trkpt, "hr") or _text(trkpt, "heartRate")
        cad = _text(trkpt, "cad") or _text(trkpt, "cadence")
        power = _text(trkpt, "power") or _text(trkpt, "watts")
        ele = _text(trkpt, "ele")
        points.append(
            f"<Trackpoint><Time>{timestamp}</Time><Position><LatitudeDegrees>{lat}</LatitudeDegrees>"
            f"<LongitudeDegrees>{lon}</LongitudeDegrees></Position>"
            f"<AltitudeMeters>{ele or ''}</AltitudeMeters><HeartRateBpm><Value>{hr or ''}</Value></HeartRateBpm>"
            f"<Cadence>{cad or ''}</Cadence><Extensions><Watts>{power or ''}</Watts></Extensions></Trackpoint>"
        )
    if len(points) < 2:
        raise TcxError("Die GPX-Datei enthält zu wenige Trackpunkte mit Zeitstempel.")
    tcx = ("<TrainingCenterDatabase><Activities><Activity Sport=\"cycling\"><Lap>" + "".join(points)
           + "</Lap></Activity></Activities></TrainingCenterDatabase>").encode()
    return parse_tcx(tcx, zones, fallback_hr_max)


def parse_fit(data: bytes, zones: list[dict[str, Any]], fallback_hr_max: int = 190) -> ParsedActivity:
    try:
        from fitparse import FitFile
        import datetime
        import xml.etree.ElementTree as ET
        records = []
        for message in FitFile(data).get_messages("record"):
            values = {field.name: field.value for field in message}
            timestamp = values.get("timestamp")
            if timestamp is None or values.get("position_lat") is None or values.get("position_long") is None:
                continue
            def semicircle(value: Any) -> float:
                return float(value) * 180 / 2**31
            node = ET.Element("Trackpoint")
            ET.SubElement(node, "Time").text = timestamp.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
            pos = ET.SubElement(node, "Position")
            ET.SubElement(pos, "LatitudeDegrees").text = str(semicircle(values["position_lat"]))
            ET.SubElement(pos, "LongitudeDegrees").text = str(semicircle(values["position_long"]))
            for key, tag in (("altitude", "AltitudeMeters"), ("heart_rate", "HeartRateBpm"), ("cadence", "Cadence"), ("power", "Watts")):
                value = values.get(key)
                if value is not None:
                    target = ET.SubElement(node, tag)
                    if tag == "HeartRateBpm":
                        target = ET.SubElement(target, "Value")
                    target.text = str(value)
            records.append(ET.tostring(node, encoding="unicode"))
        if len(records) < 2:
            raise TcxError("Die FIT-Datei enthält zu wenige gültige Trackpunkte.")
        tcx = ("<TrainingCenterDatabase><Activities><Activity Sport=\"cycling\"><Lap>" + "".join(records)
               + "</Lap></Activity></Activities></TrainingCenterDatabase>").encode()
        return parse_tcx(tcx, zones, fallback_hr_max)
    except TcxError:
        raise
    except Exception as exc:
        raise TcxError("Die FIT-Datei konnte nicht gelesen werden.") from exc


def parse_activity(data: bytes, filename: str, zones: list[dict[str, Any]], fallback_hr_max: int = 190) -> ParsedActivity:
    suffix = Path(filename).suffix.lower()
    if suffix == ".gpx":
        return parse_gpx(data, zones, fallback_hr_max)
    if suffix == ".fit":
        return parse_fit(data, zones, fallback_hr_max)
    if suffix != ".tcx":
        raise TcxError("Unterstützt werden nur TCX-, FIT- und GPX-Dateien.")
    return parse_tcx(data, zones, fallback_hr_max)

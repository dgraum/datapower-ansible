# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

"""Turn ping, traceroute and TCP results into one readable report.

The route is a list. A later tool can map ``traceroute.ruta`` without
reading the appliance text again. ``null`` keeps the place of a hop
that did not answer.
"""

import base64
import re


_BOILERPLATE = frozenset((
    "action request accepted.",
    "operation completed.",
    "the cli commands were accepted.",
))
_HOP_LINE = re.compile(r"^\s*(\d+)\s+(.*\S)\s*$")
_IP = re.compile(
    r"^(?:\d{1,3}(?:\.\d{1,3}){3}|[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,})$"
)
_HEADER = re.compile(
    r"traceroute to\s+(\S+)\s+\(([^)]+)\)",
    re.IGNORECASE,
)
_DP_HEADER = re.compile(
    r"Traceroute\s+(\S+)\s+\(([^)]+)\)",
    re.IGNORECASE,
)
_DP_HOP = re.compile(
    r"^\s*(\d+):\s+(\S+)\s+rtt=\s*(\d+(?:\.\d+)?)\s*ms\s*$",
    re.IGNORECASE,
)
_DP_PING_SAMPLE = re.compile(
    r"^\s*\d+:\s+rtt=\s*(\d+(?:\.\d+)?)\s*ms\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_PING_TIME = re.compile(
    r"time[=<]\s*(\d+(?:\.\d+)?)\s*ms",
    re.IGNORECASE,
)
_PING_STATS = re.compile(
    r"(\d+)\s+packets?\s+transmitted,\s+(\d+)\s+received,\s+"
    r"(\d+(?:\.\d+)?)%\s+packet\s+loss",
    re.IGNORECASE,
)
_LESS_THAN = re.compile(r"^<(\d+(?:\.\d+)?)(?:ms)?$", re.IGNORECASE)
_NUMBER_MS = re.compile(r"^(\d+(?:\.\d+)?)(?:ms)?$", re.IGNORECASE)


def _blank(value):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _text_from_payload(payload):
    if payload is None:
        return ""
    if isinstance(payload, str):
        text = payload.strip()
        if "\\n" in text and "\n" not in text:
            text = text.replace("\\n", "\n").replace("\\t", "\t")
        return text
    if isinstance(payload, dict):
        for key in ("Ping", "TraceRoute", "TCPConnectionTest", "output", "message"):
            value = payload.get(key)
            found = _text_from_payload(value)
            if found:
                return found
        for value in payload.values():
            found = _text_from_payload(value)
            if found:
                return found
        return ""
    return str(payload).strip()


def _consume_times(tokens):
    times = []
    times_ms = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.lower() == "ms":
            index += 1
            continue
        if token == "*":
            times.append("*")
            times_ms.append(None)
            index += 1
            continue
        less = _LESS_THAN.match(token)
        if less and (
            token.lower().endswith("ms")
            or (index + 1 < len(tokens) and tokens[index + 1].lower() == "ms")
        ):
            times.append("<{0} ms".format(less.group(1)))
            times_ms.append(float(less.group(1)))
            index += 1 if token.lower().endswith("ms") else 2
            continue
        number = _NUMBER_MS.match(token)
        if number and token != "*" and (
            token.lower().endswith("ms")
            or (index + 1 < len(tokens) and tokens[index + 1].lower() == "ms")
        ):
            times.append("{0} ms".format(number.group(1)))
            times_ms.append(float(number.group(1)))
            index += 1 if token.lower().endswith("ms") else 2
            continue
        if token.startswith("!"):
            times.append(token)
            times_ms.append(None)
            index += 1
            continue
        break
    return times, times_ms, tokens[index:]


def _hop(order, name, address, times, times_ms, note):
    record = {
        "orden": order,
        "nombre": name,
        "direccion": address,
        "tiempos_ms": times_ms,
        "tiempos": times,
        "sin_respuesta": name is None and address is None,
    }
    if note:
        record["anotacion"] = note
    return record


def _hop_from_host(order, host, times, times_ms, note):
    if host is None:
        return _hop(order, None, None, times, times_ms, note)
    if host.startswith("(") and host.endswith(")"):
        host = host[1:-1]
    if _IP.match(host):
        return _hop(order, None, host, times, times_ms, note)
    return _hop(order, host, None, times, times_ms, note)


def _parse_unix(order, rest):
    tokens = rest.split()
    if not tokens:
        return None
    if all(token == "*" for token in tokens):
        return _hop(order, None, None, ["*"] * len(tokens), [None] * len(tokens), None)
    name = None
    address = None
    remainder = tokens
    if len(tokens) >= 2 and tokens[1].startswith("(") and tokens[1].endswith(")"):
        name = tokens[0]
        address = tokens[1][1:-1]
        remainder = tokens[2:]
    elif _IP.match(tokens[0]) or tokens[0] == "*":
        address = None if tokens[0] == "*" else tokens[0]
        remainder = tokens[1:]
    else:
        name = tokens[0]
        remainder = tokens[1:]
    times, times_ms, leftover = _consume_times(remainder)
    if not times and leftover:
        return None
    note = " ".join(leftover) if leftover else None
    return _hop(order, name, address, times, times_ms, note)


def _parse_windows(order, rest):
    times, times_ms, leftover = _consume_times(rest.split())
    if not times or len(leftover) != 1:
        return None
    return _hop_from_host(order, leftover[0], times, times_ms, None)


def _starts_with_time(rest):
    token = rest.split(None, 1)[0]
    if token in ("*",) or token.startswith("!"):
        return True
    if _IP.match(token):
        return False
    return bool(_LESS_THAN.match(token) or _NUMBER_MS.match(token))


def _parse_hops(text):
    hops = []
    resolved_name = None
    resolved_address = None
    header = _HEADER.search(text or "") or _DP_HEADER.search(text or "")
    if header:
        resolved_name = header.group(1)
        resolved_address = header.group(2)
    for line in (text or "").splitlines():
        datapower = _DP_HOP.match(line)
        if datapower:
            elapsed = datapower.group(3)
            hops.append(_hop_from_host(
                int(datapower.group(1)),
                datapower.group(2),
                ["{0} ms".format(elapsed)],
                [float(elapsed)],
                None,
            ))
            continue
        match = _HOP_LINE.match(line)
        if not match:
            continue
        order = int(match.group(1))
        rest = match.group(2)
        if _starts_with_time(rest):
            hop = _parse_windows(order, rest) or _parse_unix(order, rest)
        else:
            hop = _parse_unix(order, rest) or _parse_windows(order, rest)
        if hop:
            hops.append(hop)
    return hops, resolved_name, resolved_address


def _same_host(left, right):
    if not left or not right:
        return False
    return left.lower().rstrip(".") == right.lower().rstrip(".")


def _destination_reached(hops, target, resolved_name, resolved_address):
    if not hops:
        return None
    last = hops[-1]
    if last["sin_respuesta"]:
        return False
    if _same_host(last.get("direccion"), target) or _same_host(last.get("nombre"), target):
        return True
    if _same_host(last.get("direccion"), resolved_address):
        return True
    if _same_host(last.get("nombre"), resolved_name):
        return True
    if target and _IP.match(target) and last.get("direccion"):
        return False
    return None


def _ping_reading(text):
    samples = [float(item) for item in _DP_PING_SAMPLE.findall(text or "")]
    folded = (text or "").lower()
    stats = _PING_STATS.search(text or "")
    packets = {
        "enviados": int(stats.group(1)) if stats else None,
        "recibidos": int(stats.group(2)) if stats else None,
        "perdida_pct": float(stats.group(3)) if stats else None,
    }
    sample = _PING_TIME.search(text or "")
    elapsed = float(sample.group(1)) if sample else None
    if samples:
        elapsed = samples[0]
        if packets["recibidos"] is None:
            packets["recibidos"] = len(samples)
    if packets["perdida_pct"] is not None:
        reachable = packets["recibidos"] not in (None, 0) and packets["perdida_pct"] < 100
    elif any(phrase in folded for phrase in (
        "100% packet loss",
        "unreachable",
        "no answer",
        "unknown host",
        "could not",
        "timed out",
        "timeout",
        "network is down",
        "ping failed",
    )) and not samples:
        reachable = False
    elif samples or any(phrase in folded for phrase in (
        "is alive",
        "reply from",
        "ping successful",
        "bytes from",
        "ttl=",
        "time=",
        "time<",
    )):
        reachable = True
    else:
        reachable = None
    return reachable, elapsed, packets, samples


def _meaningful(text):
    cleaned = (text or "").strip()
    if not cleaned or cleaned.lower() in _BOILERPLATE:
        return ""
    return cleaned


def _screen_text(screen):
    """Join a CLI screen. Each entry is decoded when it is base64."""
    if isinstance(screen, str):
        screen = [screen]
    if not isinstance(screen, list):
        return ""
    parts = []
    for item in screen:
        if not isinstance(item, str) or not item.strip():
            continue
        decoded = _maybe_b64(item)
        if decoded.strip():
            parts.append(decoded.strip())
    return "\n".join(parts)


def _maybe_b64(value):
    compact = "".join(value.split())
    if not re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", compact) or len(compact) % 4:
        return value
    try:
        return base64.b64decode(compact, validate=True).decode("latin-1")
    except (ValueError, TypeError, UnicodeDecodeError):
        return value


def _tcp_open(text):
    lines = [
        line for line in (text or "").splitlines()
        if re.search(r"tcp|refus|connect", line, re.IGNORECASE)
    ]
    folded = "\n".join(lines).lower() if lines else _meaningful(text).lower()
    if not folded:
        return None
    if any(phrase in folded for phrase in (
        "refused",
        "failed",
        "timed out",
        "timeout",
        "unreachable",
        "could not",
    )):
        return False
    if any(phrase in folded for phrase in (
        "successful",
        "succeeded",
        "connection established",
        "connected",
    )):
        return True
    return None


def _probe(publicado, cola, solicitada):
    if not solicitada:
        return {
            "solicitada": False,
            "estado": "no_solicitada",
            "accion": None,
            "texto": "",
            "crudo": None,
        }
    publicado = publicado if isinstance(publicado, dict) else {}
    cola = cola if isinstance(cola, dict) else {}
    if cola.get("skipped"):
        cola = {}
    accion = cola.get("action_id") or publicado.get("action_id") or None
    status = cola.get("status") if isinstance(cola.get("status"), str) else ""
    crudo = cola.get("result") if cola.get("result") not in (None, "") else None
    texto = _text_from_payload(crudo)
    if not texto:
        for candidate in (cola.get("msg"), publicado.get("msg")):
            if not isinstance(candidate, str):
                continue
            cleaned = _meaningful(candidate)
            if not cleaned:
                continue
            texto = _text_from_payload(cleaned)
            if crudo is None:
                crudo = cleaned
            break
    if publicado.get("failed") and not status:
        estado = "rechazada"
    elif cola.get("failed") or status in ("error", "failed", "aborted"):
        estado = "fallida"
    elif status == "completed":
        estado = "completada"
    elif status == "processed":
        estado = "procesada"
    elif texto:
        estado = "inmediata"
    elif accion:
        estado = "aceptada"
    else:
        estado = "sin_respuesta"
    return {
        "solicitada": True,
        "estado": estado,
        "accion": accion,
        "texto": texto,
        "crudo": crudo,
    }


def _apply_screen(view, probe):
    """Use a CLI screen when the caller passed one."""
    if not isinstance(probe, dict) or "pantalla" not in probe:
        view["fuente"] = "accion"
        return view
    view["fuente"] = "cli"
    screen_text = _screen_text(probe.get("pantalla"))
    if screen_text and view["estado"] not in ("rechazada", "fallida"):
        view["texto"] = screen_text
        view["crudo"] = probe.get("pantalla")
        view["estado"] = "completada"
    return view


def _sentence_ping(host, view, reachable):
    if view["estado"] == "rechazada":
        return "El equipo rechazó el ping hacia {0}.".format(host)
    if view["estado"] == "fallida":
        return "El ping hacia {0} no terminó.".format(host)
    if reachable is True:
        return "El equipo recibió respuesta de ping desde {0}.".format(host)
    if reachable is False:
        return "El equipo no recibió respuesta de ping desde {0}.".format(host)
    return "El ping hacia {0} no devolvió un resultado interpretable.".format(host)


def _sentence_trace(host, view, hops, reached):
    if view["estado"] == "rechazada":
        return "El equipo rechazó la traza hacia {0}.".format(host)
    if view["estado"] == "fallida":
        return "La traza hacia {0} no terminó.".format(host)
    count = len(hops)
    if not count:
        return "La traza hacia {0} no devolvió saltos interpretables.".format(host)
    if reached is True:
        return "La ruta llega a {0} en {1} saltos.".format(host, count)
    if reached is False:
        answered = [hop for hop in hops if not hop["sin_respuesta"]]
        if answered:
            last = answered[-1]
            place = last.get("direccion") or last.get("nombre")
            return (
                "La ruta hacia {0} se pierde en el salto {1}. "
                "El último salto con respuesta fue {2}."
            ).format(host, hops[-1]["orden"], place)
        return "La ruta hacia {0} no obtuvo respuesta de ningún salto.".format(host)
    return (
        "La ruta hacia {0} tiene {1} saltos. "
        "El texto no confirma si el último salto es el destino."
    ).format(host, count)


def _sentence_tcp(host, port, view, open_port):
    if not view["solicitada"]:
        return "No se solicitó prueba TCP."
    if view["estado"] == "rechazada":
        return "El equipo rechazó la prueba TCP hacia {0}:{1}.".format(host, port)
    if view["estado"] == "fallida":
        return "La prueba TCP hacia {0}:{1} no terminó.".format(host, port)
    if open_port is True:
        return "El puerto {0} en {1} acepta conexión TCP.".format(port, host)
    if open_port is False:
        return "El puerto {0} en {1} no acepta conexión TCP.".format(port, host)
    return "La prueba TCP hacia {0}:{1} no devolvió un resultado interpretable.".format(host, port)


def reachability_report(payload):
    """Build the reachability report from posted actions and queue reads."""
    data = payload if isinstance(payload, dict) else {}
    origin = data.get("origen") if isinstance(data.get("origen"), dict) else {}
    target = data.get("destino") if isinstance(data.get("destino"), dict) else {}
    host = _blank(target.get("host")) or ""
    port = target.get("puerto")
    if port in ("", None):
        port = None
    ping_in = data.get("ping") if isinstance(data.get("ping"), dict) else {}
    trace_in = data.get("traceroute") if isinstance(data.get("traceroute"), dict) else {}
    tcp_in = data.get("tcp") if isinstance(data.get("tcp"), dict) else {}

    ping = _apply_screen(_probe(ping_in.get("publicado"), ping_in.get("cola"), True), ping_in)
    trace = _apply_screen(_probe(trace_in.get("publicado"), trace_in.get("cola"), True), trace_in)
    tcp = _apply_screen(
        _probe(tcp_in.get("publicado"), tcp_in.get("cola"), bool(tcp_in.get("solicitada"))),
        tcp_in,
    )

    reachable, elapsed, packets, samples = _ping_reading(ping["texto"])
    ping["alcanzable"] = reachable
    ping["tiempo_ms"] = elapsed
    ping["muestras_ms"] = samples
    ping["paquetes"] = packets

    hops, resolved_name, resolved_address = _parse_hops(trace["texto"])
    reached = _destination_reached(hops, host, resolved_name, resolved_address)
    trace["destino_alcanzado"] = reached
    trace["destino_resuelto"] = {
        "nombre": resolved_name,
        "direccion": resolved_address,
    }
    trace["saltos"] = hops
    trace["ruta"] = [hop.get("direccion") for hop in hops]

    open_port = _tcp_open(tcp["texto"]) if tcp["solicitada"] else None
    tcp["abierto"] = open_port

    return {
        "esquema": "gr.idg.reachability/v1",
        "resumen": {
            "ping": _sentence_ping(host, ping, reachable),
            "traceroute": _sentence_trace(host, trace, hops, reached),
            "tcp": _sentence_tcp(host, port, tcp, open_port),
        },
        "origen": {
            "inventario": _blank(origin.get("inventario")),
            "direccion": _blank(origin.get("direccion")),
        },
        "destino": {
            "host": host or None,
            "puerto": port,
            "version_ip": _blank(target.get("version_ip")),
            "direccion_local": _blank(target.get("direccion_local")),
        },
        "ping": ping,
        "traceroute": trace,
        "tcp": tcp,
    }


class FilterModule(object):
    def filters(self):
        return {"reachability_report": reachability_report}

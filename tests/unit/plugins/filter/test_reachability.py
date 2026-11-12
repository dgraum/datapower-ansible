# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import base64
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from ansible_collections.gr.idg.plugins.filter.reachability import reachability_report


TRACE = "\n".join((
    "traceroute to host.example (10.20.30.40), 30 hops max, 60 byte packets",
    " 1  borde (10.0.0.1)  0.4 ms  0.5 ms  0.4 ms",
    " 2  * * *",
    " 3  10.20.30.40  5 ms * 6 ms",
))


def _report():
    return reachability_report({
        "origen": {"inventario": "idg01", "direccion": "192.0.2.10"},
        "destino": {
            "host": "host.example",
            "puerto": 443,
            "version_ip": "",
            "direccion_local": "",
        },
        "ping": {
            "publicado": {"msg": "Action request accepted.", "action_id": "Ping-1"},
            "cola": {
                "status": "completed",
                "action_id": "Ping-1",
                "result": "64 bytes from 10.20.30.40: icmp_seq=1 ttl=54 time=12.5 ms",
            },
        },
        "traceroute": {
            "publicado": {"action_id": "Trace-1"},
            "cola": {"status": "completed", "result": {"TraceRoute": TRACE}},
        },
        "tcp": {
            "solicitada": True,
            "publicado": {"action_id": "Tcp-1"},
            "cola": {"status": "completed", "result": "TCP connection successful"},
        },
    })


def test_route_keeps_order_and_a_gap():
    report = _report()
    assert report["esquema"] == "gr.idg.reachability/v1"
    assert report["traceroute"]["ruta"] == ["10.0.0.1", None, "10.20.30.40"]
    assert report["traceroute"]["destino_alcanzado"] is True
    assert report["traceroute"]["destino_resuelto"]["direccion"] == "10.20.30.40"
    hops = report["traceroute"]["saltos"]
    assert hops[0]["nombre"] == "borde"
    assert hops[0]["tiempos_ms"] == [0.4, 0.5, 0.4]
    assert hops[1]["sin_respuesta"] is True
    assert hops[2]["tiempos"] == ["5 ms", "*", "6 ms"]
    assert report["ping"]["alcanzable"] is True
    assert report["ping"]["tiempo_ms"] == 12.5
    assert report["tcp"]["abierto"] is True
    assert "llega a" in report["resumen"]["traceroute"]
    assert report["destino"]["version_ip"] is None


def test_numeric_target_that_is_not_the_last_hop():
    report = reachability_report({
        "destino": {"host": "10.9.9.9"},
        "ping": {"publicado": {}, "cola": {}},
        "traceroute": {
            "publicado": {},
            "cola": {"status": "completed", "result": " 1  10.0.0.1  1 ms\n 2  10.0.0.2  2 ms\n"},
        },
        "tcp": {"solicitada": False},
    })
    assert report["traceroute"]["destino_alcanzado"] is False
    assert report["tcp"]["estado"] == "no_solicitada"
    assert report["tcp"]["abierto"] is None
    assert report["resumen"]["tcp"] == "No se solicitó prueba TCP."


def test_windows_tracert_and_loss():
    report = reachability_report({
        "destino": {"host": "10.0.0.8"},
        "ping": {
            "publicado": {"msg": "3 packets transmitted, 0 received, 100% packet loss"},
            "cola": {"skipped": True},
        },
        "traceroute": {
            "publicado": {},
            "cola": {
                "status": "processed",
                "result": "  1    <1 ms    <1 ms    <1 ms  10.0.0.1\n",
            },
        },
        "tcp": {
            "solicitada": True,
            "publicado": {},
            "cola": {"failed": True, "msg": "Action Tcp-9 was not found."},
        },
    })
    hop = report["traceroute"]["saltos"][0]
    assert hop["direccion"] == "10.0.0.1"
    assert hop["tiempos_ms"] == [1.0, 1.0, 1.0]
    assert report["ping"]["alcanzable"] is False
    assert report["ping"]["paquetes"]["enviados"] == 3
    assert report["ping"]["estado"] == "inmediata"
    assert report["tcp"]["estado"] == "fallida"
    assert report["tcp"]["abierto"] is None


def test_acceptance_alone_is_not_a_measurement():
    report = reachability_report({
        "destino": {"host": "10.0.0.8"},
        "ping": {
            "publicado": {"msg": "Action request accepted.", "action_id": "Ping-2"},
            "cola": {},
        },
        "traceroute": {"publicado": {}, "cola": {}},
        "tcp": {"solicitada": False},
    })
    assert report["ping"]["estado"] == "aceptada"
    assert report["ping"]["alcanzable"] is None
    assert report["ping"]["texto"] == ""


def test_cli_screen_is_the_route_and_completion_is_empty():
    encoded = base64.b64encode(TRACE.encode("utf-8")).decode("ascii")
    report = reachability_report({
        "destino": {"host": "host.example"},
        "ping": {
            "publicado": {"msg": "Operation completed."},
            "cola": {},
        },
        "traceroute": {
            "publicado": {"msg": "The CLI commands were accepted."},
            "pantalla": [encoded],
        },
        "tcp": {"solicitada": False},
    })
    assert report["ping"]["texto"] == ""
    assert report["ping"]["alcanzable"] is None
    assert report["traceroute"]["fuente"] == "cli"
    assert report["traceroute"]["ruta"] == ["10.0.0.1", None, "10.20.30.40"]
    assert report["traceroute"]["destino_alcanzado"] is True


def test_datapower_console_traceroute():
    screen = (
        "\xff\xfc\x01Traceroute host.example (198.51.100.20)\n"
        " 1:      192.0.2.1  rtt= 0 ms\n"
        " 2:      198.51.100.20  rtt= 1 ms\n"
        "Goodbye.\n"
    )
    encoded = base64.b64encode(screen.encode("latin-1")).decode("ascii")
    report = reachability_report({
        "destino": {"host": "host.example"},
        "ping": {"publicado": {}, "cola": {}},
        "traceroute": {
            "publicado": {"msg": "The CLI commands were accepted."},
            "pantalla": [encoded],
        },
        "tcp": {"solicitada": False},
    })
    assert report["traceroute"]["ruta"] == ["192.0.2.1", "198.51.100.20"]
    assert report["traceroute"]["saltos"][0]["tiempos_ms"] == [0.0]
    assert report["traceroute"]["saltos"][1]["tiempos_ms"] == [1.0]
    assert report["traceroute"]["destino_alcanzado"] is True
    assert report["traceroute"]["destino_resuelto"]["direccion"] == "198.51.100.20"


def test_cli_ping_samples_and_refused_tcp():
    ping = base64.b64encode(
        "Ping host.example (198.51.100.20)\n1: rtt=0 ms\n2: rtt=1 ms\n".encode("latin-1")
    ).decode("ascii")
    refused = base64.b64encode(
        "TCP connection to host.example port 44334 failed (connection refused)\n".encode("ascii")
    ).decode("ascii")
    report = reachability_report({
        "destino": {"host": "host.example", "puerto": 44334},
        "ping": {"publicado": {}, "pantalla": [ping]},
        "traceroute": {"publicado": {}, "pantalla": []},
        "tcp": {"solicitada": True, "publicado": {}, "pantalla": [refused]},
    })
    assert report["ping"]["fuente"] == "cli"
    assert report["ping"]["alcanzable"] is True
    assert report["ping"]["muestras_ms"] == [0.0, 1.0]
    assert report["ping"]["paquetes"]["recibidos"] == 2
    assert report["tcp"]["abierto"] is False
    assert "no acepta" in report["resumen"]["tcp"]

# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse


DEFAULT_SCHEME_PORTS = {
    'http': 80,
    'https': 443,
}


def parse_target_url(target_url: str) -> dict[str, Any]:
    parsed = urlparse(target_url.strip())
    if not parsed.scheme:
        parsed = urlparse('https://' + target_url.strip())

    scheme = (parsed.scheme or 'https').lower()
    port = parsed.port
    if port is None:
        port = DEFAULT_SCHEME_PORTS.get(scheme, 443)

    path = normalize_path(parsed.path or '/')
    return {
        'scheme': scheme,
        'hostname': parsed.hostname or '',
        'port': int(port),
        'path': path,
        'raw': target_url,
    }


def normalize_path(path: str) -> str:
    if not path:
        return '/'
    if not path.startswith('/'):
        path = '/' + path
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    return path


def socket_key(local_ip: str, local_port: int) -> str:
    return '{0}:{1}'.format(local_ip, int(local_port))


def path_matches(target_path: str, candidate_path: str | None) -> bool:
    if not candidate_path:
        return False
    target = normalize_path(target_path)
    candidate = normalize_path(candidate_path)
    if not target or target == '/':
        return True
    return candidate == target or candidate.startswith(target + '/') or target.startswith(candidate + '/')


def normalize_active_service(item: dict) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    service_name = item.get('ServiceName')
    service_class = item.get('ServiceClass')
    local_ip = item.get('LocalIP')
    local_port = item.get('LocalPort')
    if not service_name or not service_class or local_ip is None or local_port is None:
        return None
    return {
        'service_name': service_name,
        'service_class': service_class,
        'local_ip': str(local_ip),
        'local_port': int(local_port),
    }


def _reference_value(item: Any) -> str | None:
    if isinstance(item, dict):
        return item.get('value') or item.get('name')
    return None


def _walk_collect_strings(value: Any, strings: list[str]) -> None:
    if isinstance(value, str):
        if value.strip():
            strings.append(value)
        return
    if isinstance(value, dict):
        for key, val in value.items():
            if key in ('href', '_links'):
                continue
            _walk_collect_strings(val, strings)
        return
    if isinstance(value, list):
        for item in value:
            _walk_collect_strings(item, strings)


def _path_candidates_from_strings(strings: list[str]) -> list[str]:
    paths: list[str] = []
    for raw in strings:
        if not isinstance(raw, str):
            continue
        text = raw.strip()
        if not text:
            continue
        if text.startswith('/'):
            paths.append(normalize_path(text.split('?', 1)[0]))
            continue
        if '://' in text:
            parsed = urlparse(text)
            if parsed.path:
                paths.append(normalize_path(parsed.path))
    return paths


def match_paths_in_service_config(service: dict, descendants: list, target_path: str) -> str | None:
    strings: list[str] = []
    _walk_collect_strings(service, strings)
    for entry in descendants or []:
        if isinstance(entry, dict):
            _walk_collect_strings(entry, strings)

    for candidate in _path_candidates_from_strings(strings):
        if path_matches(target_path, candidate):
            return candidate
    return None


def match_wsgateway_operation(
    operations: list[dict],
    service_name: str,
    target_path: str,
) -> str | None:
    for op in operations or []:
        ws_gateway = op.get('ws_gateway') or op.get('WSGateway')
        if isinstance(ws_gateway, dict):
            ws_gateway = ws_gateway.get('value')
        if ws_gateway != service_name:
            continue
        op_url = op.get('url')
        if path_matches(target_path, op_url):
            return normalize_path(op_url or target_path)
    return None


def _parse_ref(ref: Any, fallback_type: str | None = None) -> dict[str, str] | None:
    if not isinstance(ref, dict):
        return None
    href = ref.get('href')
    if isinstance(href, str):
        href = href.strip()
    ref_name = ref.get('value') or ref.get('name')
    parts = [p for p in href.split('/') if p] if href else []
    if href and len(parts) >= 2:
        obj_type = parts[-2]
        obj_name = str(ref_name or parts[-1])
        return {'type': obj_type, 'name': obj_name}
    if fallback_type and ref_name:
        return {'type': fallback_type, 'name': str(ref_name)}
    return None


HANDLER_CLASS_TO_TRANSPORT = {
    'HTTPSourceProtocolHandler': 'http',
    'HTTPSSourceProtocolHandler': 'https',
    'FTPSourceProtocolHandler': 'ftp',
    'FTPSSourceProtocolHandler': 'ftps',
    'MQSourceProtocolHandler': 'mq',
}

HANDLER_OBJECT_TYPES = frozenset(HANDLER_CLASS_TO_TRANSPORT.keys())


def _index_descendants(descendants: list) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for entry in descendants or []:
        if not isinstance(entry, dict):
            continue
        type_keys = [k for k in entry.keys() if k != '_links']
        if not type_keys:
            continue
        obj_type = type_keys[0]
        obj = entry.get(obj_type, {}) or {}
        obj_name = obj.get('name')
        if obj_name:
            indexed['{0}:{1}'.format(obj_type, obj_name)] = obj
    return indexed


def _transport_from_handler_class(handler_class: str | None) -> str:
    if not handler_class:
        return 'unknown'
    return HANDLER_CLASS_TO_TRANSPORT.get(handler_class, 'unknown')


def _infer_transport_from_port(local_port: int) -> str:
    if int(local_port) == 443:
        return 'https'
    if int(local_port) == 80:
        return 'http'
    return 'unknown'


def _infer_transport_from_service_name(service_name: str | None) -> str:
    if not service_name:
        return 'unknown'
    upper = service_name.upper()
    if upper.startswith('HTTPS'):
        return 'https'
    if upper.startswith('HTTP'):
        return 'http'
    return 'unknown'


def _handler_port(handler_obj: dict) -> int | None:
    port = handler_obj.get('LocalPort')
    if port is None:
        return None
    try:
        return int(port)
    except (TypeError, ValueError):
        return None


def _handler_address(handler_obj: dict) -> str:
    return str(handler_obj.get('LocalAddress') or handler_obj.get('IPAddress') or '')


def _find_handler_in_descendants(
    descendants: list,
    local_port: int,
    local_ip: str = '',
) -> tuple[str | None, str | None, dict[str, Any]]:
    """Find a front handler object in descendants matching the active socket port."""
    indexed = _index_descendants(descendants)
    candidates: list[tuple[str, str, dict]] = []
    for key, obj in indexed.items():
        obj_type = key.split(':', 1)[0]
        if obj_type not in HANDLER_OBJECT_TYPES:
            continue
        port = _handler_port(obj)
        if port is None or port != int(local_port):
            continue
        if local_ip:
            addr = _handler_address(obj)
            if addr and addr != str(local_ip):
                continue
        obj_name = obj.get('name') or key.split(':', 1)[-1]
        candidates.append((obj_type, str(obj_name), obj))

    if not candidates:
        return None, None, {}

    # Prefer TLS handler when multiple handlers share the same port.
    candidates.sort(key=lambda item: (0 if item[0] == 'HTTPSSourceProtocolHandler' else 1, item[1]))
    obj_type, obj_name, obj = candidates[0]
    return obj_type, obj_name, obj


def _resolve_handler(
    service: dict,
    descendants: list,
    local_ip: str,
    local_port: int,
) -> tuple[str | None, str | None, dict[str, Any], str]:
    """
    Returns handler_class, handler_name, handler_obj, resolution_method.
    """
    indexed = _index_descendants(descendants)

    front_ref = _parse_ref(service.get('FrontProtocol'), 'HTTPSourceProtocolHandler')
    if front_ref:
        handler_obj = indexed.get('{0}:{1}'.format(front_ref['type'], front_ref['name']), {})
        if handler_obj:
            return front_ref['type'], front_ref['name'], handler_obj, 'front_protocol'

    if front_ref:
        return front_ref['type'], front_ref['name'], {}, 'front_protocol'

    obj_type, obj_name, handler_obj = _find_handler_in_descendants(
        descendants,
        local_port,
        local_ip,
    )
    if obj_type and obj_name:
        return obj_type, obj_name, handler_obj, 'descendant_port_match'

    return None, None, {}, 'none'


def extract_frontside_socket(
    service: dict,
    descendants: list,
    *,
    service_name: str | None = None,
    local_ip: str = '',
    local_port: int = 0,
    url_scheme: str | None = None,
    wsg_operation: dict | None = None,
) -> dict[str, Any]:
    """
    Resolve front-side handler and socket transport (http/https/...) from service config.
    """
    handler_class, handler_name, handler_obj, handler_resolution = _resolve_handler(
        service,
        descendants,
        local_ip,
        local_port,
    )

    transport = _transport_from_handler_class(handler_class)
    inferred = False
    inference_source = 'handler' if transport != 'unknown' else 'none'

    if transport == 'unknown':
        transport = _infer_transport_from_service_name(service_name)
        if transport != 'unknown':
            inferred = True
            inference_source = 'service_name'

    if transport == 'unknown' and url_scheme in ('http', 'https'):
        transport = url_scheme.lower()
        inferred = True
        inference_source = 'url_scheme'

    if transport == 'unknown':
        port_guess = _infer_transport_from_port(local_port)
        if port_guess != 'unknown':
            transport = port_guess
            inferred = True
            inference_source = 'port'

    handler_port = _handler_port(handler_obj) if handler_obj else None

    scheme_match = None
    if url_scheme and transport != 'unknown':
        scheme_match = url_scheme.lower() == transport

    endpoint_ip = local_ip or _handler_address(handler_obj)
    endpoint_port = local_port or handler_port or 0

    exposed_endpoint = ''
    if transport != 'unknown' and endpoint_ip and endpoint_port:
        exposed_endpoint = '{0}://{1}:{2}'.format(transport, endpoint_ip, endpoint_port)

    result = {
        'front_protocol_handler': handler_name,
        'front_protocol_handler_class': handler_class,
        'handler_resolution': handler_resolution,
        'socket_transport': transport,
        'socket_transport_inferred': inferred,
        'socket_transport_inference_source': inference_source,
        'handler_local_port': handler_port,
        'handler_local_address': _handler_address(handler_obj) or None,
        'url_scheme_hint': url_scheme or '',
        'scheme_match': scheme_match,
        'exposed_endpoint': exposed_endpoint,
    }

    if wsg_operation:
        result['wsg_frontside_soap'] = wsg_operation.get('frontside_protocol')
        result['wsg_backside_soap'] = wsg_operation.get('backside_protocol')

    return result


def enrich_match_with_frontside(
    match: dict[str, Any],
    service_obj: dict,
    descendants: list,
    *,
    url_scheme: str | None = None,
    wsg_operation: dict | None = None,
) -> dict[str, Any]:
    frontside = extract_frontside_socket(
        service_obj,
        descendants,
        service_name=match.get('service_name'),
        local_ip=match.get('local_ip', ''),
        local_port=int(match.get('local_port', 0)),
        url_scheme=url_scheme,
        wsg_operation=wsg_operation,
    )
    merged = {**match, **frontside}
    base = merged.get('exposed_endpoint', '')
    path = match.get('matched_path') or ''
    if base and path and path != '/':
        merged['exposed_endpoint'] = base.rstrip('/') + normalize_path(path)
    return merged


def build_match_record(
    domain: str,
    service: dict[str, Any],
    matched_path: str,
    match_method: str,
) -> dict[str, Any]:
    return {
        'domain': domain,
        'service_name': service['service_name'],
        'service_class': service['service_class'],
        'local_ip': service['local_ip'],
        'local_port': service['local_port'],
        'socket_key': socket_key(service['local_ip'], service['local_port']),
        'matched_path': matched_path,
        'match_method': match_method,
    }


def detect_socket_conflicts(matches: list[dict[str, Any]]) -> tuple[bool, list[dict[str, Any]]]:
    by_socket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for match in matches:
        by_socket[match['socket_key']].append(match)

    conflicts: list[dict[str, Any]] = []
    for key, entries in by_socket.items():
        domains = {item['domain'] for item in entries}
        if len(domains) > 1:
            conflicts.append({
                'socket_key': key,
                'domains': sorted(domains),
                'services': entries,
            })

    return (len(conflicts) > 0, conflicts)


def cluster_fingerprint(match: dict[str, Any]) -> str:
    """Logical service identity across cluster nodes (IP excluded; each node has its own local IP)."""
    return '|'.join([
        match.get('domain', ''),
        match.get('service_name', ''),
        match.get('service_class', ''),
        str(match.get('local_port', '')),
    ])


index_descendants = _index_descendants
parse_ref = _parse_ref


def service_name_pattern(service_name: str) -> re.Pattern[str]:
    escaped = re.escape(service_name)
    return re.compile(r'(?<![A-Za-z0-9_\-])' + escaped + r'(?![A-Za-z0-9_\-])')


DEFAULT_GTID_PATTERNS = [
    re.compile(r'gtid\(([^)]+)\)', re.IGNORECASE),
    re.compile(r'tid\(([^)]+)\)', re.IGNORECASE),
    re.compile(r'GTID\[([^\]]+)\]', re.IGNORECASE),
    re.compile(r'TID\[([^\]]+)\]', re.IGNORECASE),
]


def extract_gtids(text: str, patterns: list[re.Pattern[str]] | None = None) -> set[str]:
    found: set[str] = set()
    for pattern in patterns or DEFAULT_GTID_PATTERNS:
        for match in pattern.findall(text):
            token = str(match).strip()
            if token:
                found.add(token)
    return found

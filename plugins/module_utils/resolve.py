# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

"""Resolve a URL to the DataPower service that owns it."""

from urllib.parse import quote, urlencode

from ansible_collections.gr.idg.plugins.module_utils.client import (
    camel_to_snake,
    clean_payload,
)
from ansible_collections.gr.idg.plugins.module_utils.endpoint_resolver import (
    build_match_record,
    detect_socket_conflicts,
    enrich_match_with_frontside,
    index_descendants,
    match_paths_in_service_config,
    match_wsgateway_operation,
    normalize_active_service,
    parse_ref,
    parse_target_url,
)


def _get(client, uri):
    response = client.request("GET", uri)
    if response.data is None:
        response.data = {}
    return response


def _wsgateway_operations_format(wsgateway_ops):
    result = {}
    for key in wsgateway_ops.keys():
        nkey = camel_to_snake(key)
        if key == 'WSGateway':
            result[nkey] = wsgateway_ops.get(key).get('value')
        else:
            val = wsgateway_ops.get(key)
            result[nkey] = val if val and val != 'none' else None
    return result


def _enabled_domains(client, skip_domains, explicit_domains):
    if explicit_domains:
        return list(explicit_domains)

    resp = _get(client, "/mgmt/status/default/DomainStatus")
    api_subject = 'DomainStatus'
    if resp.status != 200 or api_subject not in resp.data:
        return []

    domains = resp.data[api_subject]
    if isinstance(domains, dict):
        domains = [domains]

    enabled = []
    skip = set(skip_domains or [])
    for item in domains:
        name = item.get('Domain')
        if not name or name in skip:
            continue
        admin_state = item.get('mAdminState')
        if admin_state and admin_state != 'enabled':
            continue
        enabled.append(name)
    return enabled


def _active_services(client, domain_name):
    api_subject = 'ServicesStatus'
    uri = '/mgmt/status/{0}/{1}'.format(quote(domain_name, safe=''), api_subject)
    resp = _get(client, uri)
    if resp.status != 200 or api_subject not in resp.data:
        return []

    cleaned = clean_payload(resp.data)
    payload = cleaned.get(api_subject)
    if isinstance(payload, dict):
        payload = [payload]

    services = []
    for item in payload or []:
        normalized = normalize_active_service(item)
        if normalized:
            services.append(normalized)
    return services


def _wsgateway_operations(client, domain_name):
    api_subject = 'WSOperationsStatusSimpleIndex'
    uri = '/mgmt/status/{0}/{1}'.format(quote(domain_name, safe=''), api_subject)
    resp = _get(client, uri)
    if resp.status != 200 or api_subject not in resp.data:
        return []
    return list(map(_wsgateway_operations_format, resp.data[api_subject]))


def _service_config(client, domain_name, service_class, service_name, depth):
    query = urlencode({'view': 'recursive', 'depth': depth})
    uri = '/mgmt/config/{0}/{1}/{2}?{3}'.format(
        quote(domain_name, safe=''),
        quote(service_class, safe=''),
        quote(service_name, safe=''),
        query,
    )
    resp = _get(client, uri)
    if resp.status != 200 or service_class not in resp.data:
        return {}, []

    cleaned = clean_payload(resp.data)
    service = cleaned.get(service_class) if isinstance(cleaned, dict) else {}
    embedded = cleaned.get('_embedded') if isinstance(cleaned, dict) else {}
    descendants = embedded.get('descendants') if isinstance(embedded, dict) else []
    return service if isinstance(service, dict) else {}, descendants if isinstance(descendants, list) else []


def _refine_candidate(client, domain_name, service, parsed):
    target_path = parsed['path']
    has_path = target_path not in ('', '/')

    if service['service_class'] == 'WSGateway':
        if has_path:
            operations = _wsgateway_operations(client, domain_name)
            matched_path = match_wsgateway_operation(
                operations,
                service['service_name'],
                target_path,
            )
            if matched_path:
                return build_match_record(domain_name, service, matched_path, 'wsgateway_operations')
        return build_match_record(domain_name, service, target_path, 'active_port_only')

    if has_path:
        service_obj, descendants = _service_config(
            client,
            domain_name,
            service['service_class'],
            service['service_name'],
            depth=4,
        )
        matched_path = match_paths_in_service_config(service_obj, descendants, target_path)
        if matched_path:
            return build_match_record(domain_name, service, matched_path, 'service_config_path')

    return build_match_record(domain_name, service, target_path, 'active_port_only')


def _find_wsgateway_operation(operations, service_name, target_path):
    for op in operations or []:
        ws_gateway = op.get('ws_gateway') or op.get('WSGateway')
        if isinstance(ws_gateway, dict):
            ws_gateway = ws_gateway.get('value')
        if ws_gateway != service_name:
            continue
        if target_path in ('', '/') or match_wsgateway_operation([op], service_name, target_path):
            return op
    return None


def _fetch_handler_if_missing(client, domain_name, handler_class, handler_name):
    if not handler_class or not handler_name:
        return {}
    uri = '/mgmt/config/{0}/{1}/{2}'.format(
        quote(domain_name, safe=''),
        quote(handler_class, safe=''),
        quote(handler_name, safe=''),
    )
    resp = _get(client, uri)
    if resp.status != 200 or handler_class not in resp.data:
        return {}
    cleaned = clean_payload(resp.data)
    obj = cleaned.get(handler_class)
    return obj if isinstance(obj, dict) else {}


def _enrich_matches(client, matches, parsed):
    if not matches:
        return matches

    wsg_ops_cache = {}
    enriched = []
    url_scheme = parsed.get('scheme')

    for match in matches:
        domain_name = match['domain']
        service_class = match['service_class']
        service_name = match['service_name']

        service_obj, descendants = _service_config(
            client,
            domain_name,
            service_class,
            service_name,
            depth=5,
        )

        wsg_operation = None
        if service_class == 'WSGateway':
            if domain_name not in wsg_ops_cache:
                wsg_ops_cache[domain_name] = _wsgateway_operations(client, domain_name)
            wsg_operation = _find_wsgateway_operation(
                wsg_ops_cache[domain_name],
                service_name,
                parsed.get('path', '/'),
            )

        front_ref = parse_ref(service_obj.get('FrontProtocol') if service_obj else None)
        if front_ref:
            indexed_key = '{0}:{1}'.format(front_ref['type'], front_ref['name'])
            if indexed_key not in index_descendants(descendants):
                handler_obj = _fetch_handler_if_missing(
                    client,
                    domain_name,
                    front_ref['type'],
                    front_ref['name'],
                )
                if handler_obj:
                    descendants = list(descendants or []) + [{front_ref['type']: handler_obj}]

        enriched.append(
            enrich_match_with_frontside(
                match,
                service_obj or {},
                descendants,
                url_scheme=url_scheme,
                wsg_operation=wsg_operation,
            )
        )

    return enriched


def resolve_endpoint(client, target_url, skip_domains, explicit_domains):
    parsed = parse_target_url(target_url)
    port_matches = []

    for domain_name in _enabled_domains(client, skip_domains, explicit_domains):
        for service in _active_services(client, domain_name):
            if service['local_port'] != parsed['port']:
                continue
            port_matches.append((domain_name, service))

    if not port_matches:
        ambiguous, conflicts = False, []
        return parsed, [], ambiguous, conflicts

    refined = []
    for domain_name, service in port_matches:
        match = _refine_candidate(client, domain_name, service, parsed)
        if match:
            refined.append(match)

    ambiguous, conflicts = detect_socket_conflicts(refined)
    enriched = _enrich_matches(client, refined, parsed)
    return parsed, enriched, ambiguous, conflicts

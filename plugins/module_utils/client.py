# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote

"""REST helpers for IBM DataPower.

Comparison uses the cleaned document. Redaction is applied only to values
that leave the module.
"""

HTTP_AGENT = "ansible-collection-gr.idg/1.0.0"
REDACTED = "VALUE_SPECIFIED_IN_NO_LOG_PARAMETER"
DEFAULT_DOMAIN = "default"
PROTECTED_STORES = frozenset(("cert", "sharedcert"))
SECRET_KEYS = frozenset((
    "password",
    "passphrase",
    "secret",
    "privatekey",
    "private_key",
    "sslkey",
    "credential",
))
STRIP_OUTPUT = frozenset(("_links", "href"))
STRIP_COMPARE = frozenset(("_links", "href", "state"))


class IDGError(Exception):
    """A REST call failed. The message is safe to pass to fail_json."""

    def __init__(self, message, status=None, data=None):
        super(IDGError, self).__init__(message)
        self.status = status
        self.data = data


class Response(object):
    """One HTTP response. ``data`` is parsed JSON or None."""

    def __init__(self, status, data):
        self.status = int(status)
        self.data = data

    @property
    def ok(self):
        return self.status in (200, 201, 202)


def unescape_payload(text):
    """Undo XML escapes DataPower sometimes leaves inside JSON."""
    if not isinstance(text, str):
        return text
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )


def parse_body(body):
    """Parse a response body. Dicts and lists pass through."""
    if body is None or body == b"" or body == "":
        return None
    if isinstance(body, (dict, list)):
        return body
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    text = unescape_payload(body).strip()
    if not text:
        return None
    return json.loads(text)


def error_text(data):
    """Short error string. Secret keys are redacted before the text is built."""
    if isinstance(data, (dict, list)):
        data = redact(data)
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, list):
            return " ".join(str(part) for part in err[:2])
        if isinstance(err, str):
            return err
        if err is not None:
            return str(err)
    return ""


def is_absent(status, data):
    """A missing object is a 404 or the Resource not found text."""
    if status == 404:
        return True
    return "Resource not found" in (error_text(data) or "")


def order_name_first(value):
    """Put ``name`` first and send booleans as on/off.

    Export and LoadConfiguration reject a body whose ``name`` is not first.
    """
    if isinstance(value, list):
        return [order_name_first(item) for item in value]
    if isinstance(value, dict):
        ordered = {}
        if "name" in value:
            ordered["name"] = order_name_first(value["name"])
        for key, item in value.items():
            if key == "name":
                continue
            ordered[key] = order_name_first(item)
        return ordered
    if isinstance(value, bool):
        return "on" if value else "off"
    return value


def strip_keys(value, keys):
    if isinstance(value, list):
        return [strip_keys(item, keys) for item in value]
    if isinstance(value, dict):
        return {
            key: strip_keys(item, keys)
            for key, item in value.items()
            if key not in keys
        }
    return value


def clean_payload(value):
    """Drop documentation links. The remaining keys can be sent again."""
    return strip_keys(value, STRIP_OUTPUT)


def clean_for_compare(value):
    """Drop links and the operational ``state`` key before an equality check."""
    return strip_keys(value, STRIP_COMPARE)


def same_config(current, desired):
    """Compare cleaned JSON. Call this before redaction."""
    return clean_for_compare(current) == clean_for_compare(desired)


def redact(value):
    """Replace secret keys. Does not change the object used for comparison."""
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if str(key).lower() in SECRET_KEYS:
                cleaned[key] = REDACTED
            else:
                cleaned[key] = redact(item)
        return cleaned
    return value


def redact_text(text):
    if not isinstance(text, str) or not text:
        return text
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return text
    return json.dumps(redact(parsed))


def action_id_from_body(data):
    """Read the action id from ``_links.location``. Does not follow the link."""
    if not isinstance(data, dict):
        return None
    links = data.get("_links") or {}
    location = links.get("location") or {}
    href = location.get("href") if isinstance(location, dict) else None
    if isinstance(href, str) and href.strip():
        return href.rstrip("/").rsplit("/", 1)[-1]
    return None


def action_suffix():
    """Unique suffix for this request. Computed at call time, not at import."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def camel_to_snake(name):
    text = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", str(name))
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", text).lower()


def snake_record(value):
    if isinstance(value, list):
        return [snake_record(item) for item in value]
    if isinstance(value, dict):
        return {
            camel_to_snake(key): snake_record(item)
            for key, item in value.items()
        }
    return value


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def quote_path(*parts):
    """Build a REST path. A period in a name stays literal.

    DataPower publishes that form in its own links, for example
    ``/mgmt/config/default/Domain/payments.example``.
    A directory resource such as ``/mgmt/domains/config/`` still needs
    the trailing slash; this function does not add it.
    """
    segments = []
    for part in parts:
        text = str(part).strip("/")
        if not text:
            continue
        segments.append(quote(text, safe=""))
    return "/" + "/".join(segments)


def write_private(path, data):
    """Write bytes with mode 0600. Used for a local export package."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    descriptor = os.open(path, flags, 0o600)
    try:
        if isinstance(data, str):
            data = data.encode("utf-8")
        os.write(descriptor, data)
    finally:
        os.close(descriptor)
    os.chmod(path, 0o600)


def status_message(data, operation=None):
    if isinstance(data, str):
        return data
    if not isinstance(data, dict):
        return None
    if operation and isinstance(data.get(operation), str):
        return data.get(operation)
    for key, value in data.items():
        if key != "_links" and isinstance(value, str):
            return value
    return None


class IDGClient(object):
    """Talks to one transport.

    ``request_fn(method, path, body, headers)`` returns ``(status, body)``.
    The body may be text, bytes, or an already parsed object.
    """

    def __init__(self, request_fn):
        self._request_fn = request_fn

    def request(self, method, path, body=None, headers=None, as_json=True):
        payload = body
        if body is not None and method in ("POST", "PUT"):
            payload = order_name_first(body)
        status, raw = self._request_fn(method, path, payload, headers)
        try:
            data = parse_body(raw)
        except (ValueError, TypeError):
            if as_json:
                raise IDGError(
                    "Response from {0} was not valid JSON.".format(path),
                    status=status,
                )
            if isinstance(raw, bytes):
                data = raw.decode("latin-1")
            else:
                data = raw
        return Response(status, data)

    def get(self, path, headers=None):
        response = self.request("GET", path, headers=headers)
        if response.status != 200:
            detail = error_text(response.data) or "GET failed."
            raise IDGError(detail, status=response.status, data=response.data)
        return response

    def get_or_none(self, path, headers=None):
        response = self.request("GET", path, headers=headers)
        if is_absent(response.status, response.data):
            return None
        if response.status != 200:
            detail = error_text(response.data) or "GET failed."
            raise IDGError(detail, status=response.status, data=response.data)
        return response.data

    def read_class(self, path, class_name):
        """GET one class. A missing class fails with that class name."""
        try:
            response = self.get(path)
        except IDGError as exc:
            if is_absent(exc.status or 0, exc.data):
                raise IDGError(
                    "Class {0} is not available on this firmware.".format(class_name),
                    status=exc.status,
                    data=exc.data,
                )
            raise
        data = response.data if isinstance(response.data, dict) else {}
        if class_name not in data:
            raise IDGError(
                "Class {0} is not available on this firmware.".format(class_name)
            )
        return clean_payload(data[class_name]), clean_payload(data)

    def post_action(self, domain, body, headers=None):
        """Publish one action and return its id. Does not poll the queue."""
        path = quote_path("mgmt", "actionqueue", domain)
        response = self.request("POST", path, body, headers=headers)
        if response.status not in (200, 202):
            detail = error_text(response.data) or "The action was not accepted."
            raise IDGError(detail, status=response.status, data=response.data)
        return {
            "action_id": action_id_from_body(response.data),
            "msg": status_message(response.data) or "Action request accepted.",
            "changed": True,
        }

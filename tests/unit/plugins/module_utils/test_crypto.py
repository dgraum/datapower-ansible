# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import ast
import base64
import json
from pathlib import Path

from ansible_collections.gr.idg.plugins.module_utils.client import IDGError
from ansible_collections.gr.idg.plugins.module_utils.ops import (
    ensure_crypto_certificate,
    ensure_crypto_key,
    read_certificate_detail,
)


class FakeClient(object):
    def __init__(self, status, data, current=None):
        self.status = status
        self.data = data
        self.current = current
        self.calls = []

    def get_or_none(self, path):
        self.calls.append(("GET", path, None))
        return self.current

    def request(self, method, path, body=None, headers=None, as_json=True):
        self.calls.append((method, path, body))

        class Response(object):
            pass

        response = Response()
        response.status = self.status
        response.data = self.data
        return response


def test_certificate_detail_keeps_identity_and_drops_the_key():
    body = {
        "_links": {"self": {"href": "/mgmt/actionqueue/pagos"}},
        "ViewCertificateDetails": "Operation completed.",
        "CryptoCertificate": {
            "CertificateObject": "portal-cert",
            "Domain": "pagos",
            "CertificateDetails": {
                "fingerprint-sha1": "AA:BB",
                "Version": 3,
                "SerialNumber": "9193",
                "SignatureAlgorithm": "sha256WithRSAEncryption",
                "Issuer": "CN=ca",
                "NotBefore": "2019-04-03T18:48:46Z",
                "NotAfter": "2029-03-31T18:48:46Z",
                "Subject": "CN=portal",
                "SubjectPublicKeyAlgorithm": "rsaEncryption",
                "SubjectPublicKeyBitLength": 2048,
                "KeyValue": {
                    "RSAKeyValue": {
                        "Modulus": "secret-modulus",
                        "Exponent": "AQAB",
                    }
                },
                "Extensions": {
                    "Extension": [
                        {
                            "critical": "false",
                            "name": "basicConstraints",
                            "oid": "2.5.29.19",
                        }
                    ]
                },
            },
        },
    }
    client = FakeClient(200, body)
    result = read_certificate_detail(
        client, {"domain": "pagos", "name": "portal-cert"}
    )
    encoded = json.dumps(result)
    assert "secret-modulus" not in encoded
    assert "AQAB" not in encoded
    assert result["changed"] is False
    assert result["detail"]["subject"] == "CN=portal"
    assert result["detail"]["issuer"] == "CN=ca"
    assert result["detail"]["not_after"] == "2029-03-31T18:48:46Z"
    assert result["detail"]["fingerprint_sha1"] == "AA:BB"
    assert result["detail"]["subject_public_key_bit_length"] == 2048
    assert result["detail"]["extensions"]["extension"][0]["name"] == "basicConstraints"
    assert client.calls[0][0] == "POST"
    assert client.calls[0][1] == "/mgmt/actionqueue/pagos"
    assert client.calls[0][2] == {
        "ViewCertificateDetails": {"CertificateObject": "portal-cert"}
    }


def test_certificate_detail_fails_when_the_body_has_no_record():
    client = FakeClient(200, {"ViewCertificateDetails": "Operation completed."})
    try:
        read_certificate_detail(client, {"domain": "pagos", "name": "portal-cert"})
    except IDGError as exc:
        assert "not returned" in str(exc)
    else:
        raise AssertionError("missing certificate detail must fail")


def test_crypto_key_posts_a_crypto_key():
    client = FakeClient(201, {"CryptoKey": {"name": "portal-key"}})
    result = ensure_crypto_key(
        client,
        {
            "domain": "pagos",
            "name": "portal-key",
            "state": "present",
            "admin_state": "enabled",
            "file_name": "cert:///portal-key.pem",
            "password_alias": "portal",
        },
        False,
    )
    assert result["changed"] is True
    method, path, body = client.calls[-1]
    assert method == "POST"
    assert path == "/mgmt/config/pagos/CryptoKey"
    assert body["CryptoKey"]["Filename"] == "cert:///portal-key.pem"
    assert body["CryptoKey"]["Alias"] == {"value": "portal"}
    assert "IgnoreExpiration" not in body["CryptoKey"]


def _sample_cert_pem():
    from datetime import datetime, timedelta, timezone

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "portal")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(7)
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    return key, cert.public_bytes(serialization.Encoding.PEM)


def test_file_detail_reads_a_certificate_and_drops_the_key():
    from cryptography.hazmat.primitives import serialization

    key, pem = _sample_cert_pem()
    secret = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    blob = secret + b"\n" + pem
    client = FakeClient(200, None)
    client.current = {
        "file": {
            "name": "portal.pem",
            "content": base64.b64encode(blob).decode("ascii"),
        }
    }
    result = ensure_crypto_certificate(
        client,
        {
            "domain": "pagos",
            "state": "detail",
            "file_name": "cert:///portal.pem",
        },
        False,
    )
    encoded = json.dumps(result)
    assert result["changed"] is False
    assert result["certificate"] is True
    assert result["kind"] == "certificate"
    assert "CN=portal" in result["detail"]["subject"]
    assert "BEGIN" not in encoded
    assert "PRIVATE" not in encoded
    assert client.calls == [("GET", "/mgmt/filestore/pagos/cert/portal.pem", None)]


def test_file_detail_reports_a_key_without_its_bytes():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    client = FakeClient(200, None)
    client.current = {
        "file": {"name": "portal-key.pem", "content": base64.b64encode(pem).decode("ascii")}
    }
    result = ensure_crypto_certificate(
        client,
        {
            "domain": "pagos",
            "state": "detail",
            "file_name": "cert:///portal-key.pem",
        },
        False,
    )
    encoded = json.dumps(result)
    assert result["certificate"] is False
    assert result["kind"] == "key"
    assert "detail" not in result
    assert "PRIVATE" not in encoded
    assert client.calls[0][0] == "GET"


def _key_document():
    return {
        "CryptoKey": {
            "name": "portal-key",
            "mAdminState": "disabled",
            "Filename": "cert:/portal-key.pem",
            "Alias": {"value": "portal", "href": "/mgmt/config/pagos/PasswordAlias/portal"},
            "External": "off",
            "state": "up",
            "PasswordAlias": {"value": "portal", "href": "/alias"},
        }
    }


def test_retarget_keeps_the_key_and_changes_the_filename():
    client = FakeClient(200, {})
    client.current = _key_document()
    result = ensure_crypto_key(
        client,
        {
            "domain": "pagos",
            "name": "portal-key",
            "state": "retarget",
            "admin_state": "enabled",
            "file_name": "cert:///portal-key-2026.pem",
        },
        False,
    )
    assert result["changed"] is True
    assert result["previous"]["alias"] == "portal"
    assert result["previous"]["admin_state"] == "disabled"
    method, path, body = client.calls[-1]
    assert method == "PUT"
    assert path == "/mgmt/config/pagos/CryptoKey/portal-key"
    written = body["CryptoKey"]
    assert written["Filename"] == "cert:///portal-key-2026.pem"
    assert written["mAdminState"] == "disabled"
    assert written["Alias"] == {"value": "portal"}
    assert written["External"] == "off"
    assert "state" not in written
    assert "PasswordAlias" not in written
    assert "href" not in json.dumps(written)


def test_retarget_matches_a_normalized_path_without_writing():
    client = FakeClient(200, {})
    client.current = _key_document()
    client.current["CryptoKey"]["Filename"] = "cert:/portal-key-2026.pem"
    result = ensure_crypto_key(
        client,
        {
            "domain": "pagos",
            "name": "portal-key",
            "state": "retarget",
            "file_name": "cert:///portal-key-2026.pem",
            "password_alias": "portal",
        },
        False,
    )
    assert result["changed"] is False
    assert [call[0] for call in client.calls] == ["GET"]


def test_retarget_check_mode_does_not_write():
    client = FakeClient(200, {})
    client.current = _key_document()
    result = ensure_crypto_key(
        client,
        {
            "domain": "pagos",
            "name": "portal-key",
            "state": "retarget",
            "file_name": "cert:///portal-key-2026.pem",
            "password_alias": "next",
        },
        True,
    )
    assert result["changed"] is True
    assert result["diff"]["after"]["Alias"] == {"value": "next"}
    assert [call[0] for call in client.calls] == ["GET"]


def test_retarget_clears_an_empty_alias_and_does_not_create():
    client = FakeClient(200, {})
    client.current = None
    try:
        ensure_crypto_key(
            client,
            {
                "domain": "pagos",
                "name": "portal-key",
                "state": "retarget",
                "file_name": "cert:///portal-key.pem",
            },
            False,
        )
    except IDGError as exc:
        assert "does not exist" in str(exc)
    else:
        raise AssertionError("retarget must not create a key")
    assert [call[0] for call in client.calls] == ["GET"]

    client.current = _key_document()
    result = ensure_crypto_key(
        client,
        {
            "domain": "pagos",
            "name": "portal-key",
            "state": "retarget",
            "file_name": "cert:///portal-key-2026.pem",
            "password_alias": "",
        },
        False,
    )
    written = client.calls[-1][2]["CryptoKey"]
    assert result["changed"] is True
    assert "Alias" not in written


def test_certificate_retarget_keeps_alias_and_expiration():
    client = FakeClient(200, {})
    client.current = {
        "CryptoCertificate": {
            "name": "portal-cert",
            "mAdminState": "disabled",
            "Filename": "cert:///portal.pem",
            "IgnoreExpiration": "on",
            "Alias": {"value": "portal"},
        }
    }
    result = ensure_crypto_certificate(
        client,
        {
            "domain": "pagos",
            "name": "portal-cert",
            "state": "retarget",
            "admin_state": "enabled",
            "file_name": "sharedcert:///portal-2026.pem",
            "ignore_expiration": False,
            "password_alias": "other",
        },
        False,
    )
    written = client.calls[-1][2]["CryptoCertificate"]
    assert result["changed"] is True
    assert written["Filename"] == "sharedcert:///portal-2026.pem"
    assert written["mAdminState"] == "disabled"
    assert written["IgnoreExpiration"] == "on"
    assert written["Alias"] == {"value": "portal"}


def test_certificate_present_sends_ignore_expiration():
    client = FakeClient(201, {})
    ensure_crypto_certificate(
        client,
        {
            "domain": "pagos",
            "name": "portal-cert",
            "state": "present",
            "admin_state": "enabled",
            "file_name": "cert:///portal.pem",
            "ignore_expiration": False,
        },
        False,
    )
    body = client.calls[-1][2]
    assert client.calls[-1][1] == "/mgmt/config/pagos/CryptoCertificate"
    assert body["CryptoCertificate"]["IgnoreExpiration"] == "off"


def _state_choices(module_name):
    root = Path(__file__).resolve().parents[4]
    tree = ast.parse((root / "plugins" / "modules" / module_name).read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name != "AnsibleModule":
            continue
        for keyword in node.keywords:
            if keyword.arg != "argument_spec":
                continue
            spec = ast.literal_eval(keyword.value)
            return spec["state"]["choices"]
    raise AssertionError("argument_spec was not found")


def test_retarget_is_an_accepted_state():
    assert "retarget" in _state_choices("crypto_certificate.py")
    assert "retarget" in _state_choices("crypto_key.py")

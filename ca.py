import datetime
import ipaddress
import os
import sys
from pathlib import Path

# Pillar 8: UTF-8 Console Safety Guard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import BASE_DIR
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

CERT_DIR = BASE_DIR / "certs"
CA_KEY_PATH = CERT_DIR / "ca.key"
CA_CERT_PATH = CERT_DIR / "ca.crt"

def ensure_ca():
    """Generates a root CA certificate if it doesn't already exist."""
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    if CA_KEY_PATH.exists() and CA_CERT_PATH.exists():
        with open(CA_KEY_PATH, "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(CA_CERT_PATH, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())
        return ca_key, ca_cert

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(CA_KEY_PATH, "wb") as f:
        f.write(
            ca_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "KR"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "EdgeSidecar"),
        x509.NameAttribute(NameOID.COMMON_NAME, "EdgeSidecar Root CA"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    with open(CA_CERT_PATH, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    return ca_key, ca_cert

_cert_cache = {}

def get_certificate_for_host(hostname: str, ca_key, ca_cert):
    """Generates an on-the-fly certificate signed by the Root CA for the given hostname."""
    if hostname in _cert_cache:
        return _cert_cache[hostname]

    host_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.timezone.utc)

    san_list = []
    try:
        ip = ipaddress.ip_address(hostname)
        san_list.append(x509.IPAddress(ip))
    except ValueError:
        san_list.append(x509.DNSName(hostname))

    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ]))
        .issuer_name(ca_cert.subject)
        .public_key(host_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    cert_pem = builder.public_bytes(serialization.Encoding.PEM)
    key_pem = host_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    _cert_cache[hostname] = (cert_pem, key_pem)
    return cert_pem, key_pem

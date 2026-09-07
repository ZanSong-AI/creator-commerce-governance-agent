#!/usr/bin/env python3
"""Attach test-only C2PA manifests to selected synthetic MP4 fixtures.

The private key is generated under `.runtime/` and is never committed. The resulting
media is a provenance interoperability fixture, not a public-trust identity claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import c2pa
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier

C2PA_CLAIM_SIGNING = ObjectIdentifier("1.3.6.1.4.1.62558.2.1")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_test_credential(runtime: Path) -> tuple[ec.EllipticCurvePrivateKey, str]:
    runtime.mkdir(parents=True, exist_ok=True)
    root_key = ec.generate_private_key(ec.SECP256R1())
    root_name = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Creator Commerce Governance Test Only"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Local C2PA Test Root"),
        ]
    )
    now = datetime.now(UTC)
    root_certificate = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()), critical=False)
        .sign(root_key, hashes.SHA256())
    )
    key = ec.generate_private_key(ec.SECP256R1())
    signer_name = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Creator Commerce Governance Test Only"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Local C2PA Test Signer"),
        ]
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(signer_name)
        .issuer_name(root_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(True, False, False, False, False, False, False, False, False),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([C2PA_CLAIM_SIGNING, ExtendedKeyUsageOID.EMAIL_PROTECTION]),
            critical=False,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()),
            critical=False,
        )
        .sign(root_key, hashes.SHA256())
    )
    key_path = runtime / "test-signer-private-key.pem"
    certificate_path = runtime / "test-signer-certificate.pem"
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    leaf_pem = certificate.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    root_pem = root_certificate.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    certificate_path.write_text(leaf_pem + root_pem, encoding="utf-8")
    (runtime / "test-root-trust-anchor.pem").write_text(root_pem, encoding="utf-8")
    return key, leaf_pem + root_pem


def sign_asset(source: Path, target: Path, title: str, key: ec.EllipticCurvePrivateKey, cert: str) -> None:
    if target.exists():
        target.unlink()
    manifest = {
        "claim_generator_info": [{"name": "creator-commerce-governance-agent", "version": "0.1.0"}],
        "format": "video/mp4",
        "title": title,
        "ingredients": [],
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": (
                                "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
                            ),
                        }
                    ]
                },
            }
        ],
    }

    def callback(data: bytes) -> bytes:
        return key.sign(data, ec.ECDSA(hashes.SHA256()))

    with (
        c2pa.Context() as context,
        c2pa.Signer.from_callback(callback, c2pa.C2paSigningAlg.ES256, cert, None) as signer,
        c2pa.Builder(manifest, context) as builder,
    ):
        builder.sign_file(str(source), str(target), signer)


def tamper_media(path: Path) -> None:
    data = bytearray(path.read_bytes())
    marker = data.find(b"mdat")
    if marker < 0 or marker + 128 >= len(data):
        raise RuntimeError("Could not locate MP4 mdat box for the invalid-manifest fixture")
    position = marker + 96
    data[position] ^= 0x01
    path.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key, certificate = create_test_credential(args.runtime.resolve())
    signed = invalid = 0
    for case in manifest["cases"]:
        state = case["c2pa_fixture_state"]
        if state == "absent":
            continue
        source = manifest_path.parents[2] / case["asset_path"]
        temporary = source.with_suffix(".c2pa.tmp.mp4")
        sign_asset(source, temporary, case["stable_key"], key, certificate)
        if state == "invalid":
            tamper_media(temporary)
            invalid += 1
        shutil.move(str(temporary), str(source))
        case["asset_sha256"] = sha256(source)
        signed += 1
    manifest["c2pa_test_fixture"] = {
        "sdk": f"c2pa-python {getattr(c2pa, '__version__', 'unknown')}",
        "private_key_committed": False,
        "public_trust_claim": False,
        "signed_assets": signed,
        "intentionally_tampered_assets": invalid,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest["c2pa_test_fixture"]))


if __name__ == "__main__":
    main()

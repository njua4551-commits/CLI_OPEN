"""Filters for potential credentials and untrusted memory framing."""
import json
import re

SECRETS = (
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?-----"),
    re.compile(r"\b(?:sk|rk|ghp|gho|ghs|ghu|ghr|xox[baprs])[-_][A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
)
CREDENTIAL_NAME = re.compile(r"secret|credential|password|private.?key", re.IGNORECASE)
PRIVATE_NAMES = {".aws", ".git", ".ssh", ".netrc", "_netrc", ".npmrc", ".pypirc", ".pgpass",
                 ".docker", "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"}
PRIVATE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".kdbx")
ENV_NAME = re.compile(r"(?:^|\.)env(?:\.|$)")
MARKER = "UNTRUSTED_PROJECT_MEMORY_CONTEXT"


def looks_secret(value):
    return any(pattern.search(value) for pattern in SECRETS)


def sensitive_path(value):
    parts = value.casefold().split("/")
    return (
        looks_secret(value) or CREDENTIAL_NAME.search(value) is not None
        or any(part in PRIVATE_NAMES or ENV_NAME.search(part)
               or part.endswith(PRIVATE_SUFFIXES) for part in parts)
    )


def encode_context(value):
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    for prefix in ("[", "[/"):
        marker = prefix + MARKER
        encoded = encoded.replace(marker, "\\u005b" + marker[1:])
    return encoded

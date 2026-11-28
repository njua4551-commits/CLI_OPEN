"""Trusted file bounds and lexical path policy for review and validation."""

MAX_FILE = 262_144


def canonical_relative(name):
    return isinstance(name, str) and all(part not in ("", ".", "..") for part in name.split("/"))

"""Decode gateway JSON while rejecting non-finite numeric values."""
import json
import math


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("invalid JSON number")
    return number


def reject_constant(_):
    raise ValueError("invalid JSON constant")


def load(data):
    return json.loads(data, parse_float=finite_float, parse_constant=reject_constant)

"""Run two bounded, synthetic tool-calling requests on the approved free endpoint."""
import json
import os
import urllib.error
import urllib.request
from decimal import Decimal

BASE = "https://openrouter.ai/api/v1/"
MODEL = "liquid/lfm-3-1.7b:free"
PROVIDER = "liquid"
FIXTURE = "SYNTHETIC_RESULT_42"
TOOL = {
    "type": "function",
    "function": {
        "name": "read_fixture",
        "description": "Return the value of a fixed synthetic fixture.",
        "parameters": {
            "type": "object",
            "properties": {"id": {"type": "string", "enum": ["fixture_42"]}},
            "required": ["id"],
            "additionalProperties": False,
        },
    },
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY ausente")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def api(path, payload=None):
        request = urllib.request.Request(
            BASE + path,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        )
        try:
            with opener.open(request, timeout=35) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise SystemExit(f"{path}: HTTP {error.code}") from None
        except urllib.error.URLError:
            raise SystemExit(f"{path}: error de conexión") from None

    endpoints = api(f"models/{MODEL}/endpoints")["data"]["endpoints"]
    eligible = [
        entry for entry in endpoints
        if entry.get("tag") == PROVIDER
        and "tools" in entry.get("supported_parameters", [])
        and {"prompt", "completion"} <= entry["pricing"].keys()
        and all(Decimal(str(price)) == 0 for price in entry["pricing"].values())
    ]
    if len(eligible) != 1:
        raise SystemExit("Endpoint gratuito con herramientas sin confirmar")

    messages = [{
        "role": "user",
        "content": "Call read_fixture exactly once with id fixture_42. After its reply, return only the value.",
    }]

    def complete(**extra):
        response = api("chat/completions", {
            "model": MODEL,
            "max_tokens": 240,
            "messages": messages,
            "tools": [TOOL],
            "provider": {
                "only": [PROVIDER],
                "allow_fallbacks": False,
                "require_parameters": True,
                "max_price": {"prompt": 0, "completion": 0, "request": 0},
            },
            **extra,
        })
        cost = response.get("usage", {}).get("cost")
        if cost is None or Decimal(str(cost)) != 0 or response.get("model") != MODEL:
            raise SystemExit("Costo cero o identidad del modelo sin confirmar")
        if response.get("provider", "").casefold() != PROVIDER:
            raise SystemExit("Proveedor inesperado")
        print(f"{MODEL}, proveedor {PROVIDER}, costo USD {cost}", flush=True)
        return response["choices"][0]["message"]

    message = complete(tool_choice="required")
    calls = message.get("tool_calls") or []
    if (
        len(calls) != 1 or calls[0]["function"]["name"] != "read_fixture"
        or json.loads(calls[0]["function"]["arguments"]) != {"id": "fixture_42"}
    ):
        raise SystemExit("Llamada a herramienta inválida")
    messages.extend([
        {"role": "assistant", "content": message.get("content"), "tool_calls": calls},
        {"role": "tool", "tool_call_id": calls[0]["id"], "content": FIXTURE},
    ])
    answer = complete()
    if (answer.get("content") or "").strip() != FIXTURE or answer.get("tool_calls"):
        raise SystemExit("Resultado sintético inválido")
    print("PASS herramienta y resultado sintético")


if __name__ == "__main__":
    main()

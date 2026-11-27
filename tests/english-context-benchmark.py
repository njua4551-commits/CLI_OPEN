"""Compare fixed synthetic inputs using the pinned OpenCode Token.estimate formula."""
import json
from pathlib import Path
import runpy
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "b96229d7d3a3b00a2fe5a147444f2a73c48cfa1b"
CONTEXT = "implementacion/supervisor/context.py"
CONFIG = "implementacion/contexto/opencode.json"
REQUEST = "Revisa el inicio de sesión en src/login.py."
MEMORY = {
    "authority": "none", "source": "project-memory",
    "entries": [{"id": "0123456789abcdef", "text": "Revisar el inicio de sesión."}],
}
TOOLS = [{"name": "read", "description": "Read a file page by path, offset, and limit."}]


def baseline(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)


def measure(text):
    # OpenCode rounds JavaScript String.length / 4. String.length counts UTF-16 code units.
    return {"bytes": len(text.encode()), "estimated_tokens": (len(text.encode("utf-16-le")) // 2 + 2) // 4}


def sample(config, context):
    agent = json.loads(config)["agents"]["contexto-selectivo"]
    encode = context["encode"]
    full_prompt = context["incorporate_prompt"](REQUEST, {**MEMORY, "paths": ["src/login.py"]})
    envelope = encode(context["validate_envelope"]({**MEMORY, "paths": ["src/login.py"]}))
    assert full_prompt.endswith("\n\n" + REQUEST)
    assert context["validate_envelope"](MEMORY) == MEMORY
    parts = {
        "input": REQUEST,
        "instructions": agent["system"],
        "agent_description": agent["description"],
        "tool_descriptions": encode(TOOLS),
        "context": full_prompt.removesuffix(REQUEST).replace(envelope, "", 1),
        "memory_and_paths": envelope,
    }
    return {**{key: measure(value) for key, value in parts.items()}, "total": measure("".join(parts.values()))}


if __name__ == "__main__":
    old_context = {}
    exec(compile(baseline(CONTEXT), f"{BASE}:{CONTEXT}", "exec"), old_context)
    before = sample(baseline(CONFIG), old_context)
    after = sample((ROOT / CONFIG).read_text(), runpy.run_path(str(ROOT / CONTEXT)))
    percent = {key: {metric: round(100 * (after[key][metric] / value - 1), 2)
                     for metric, value in metrics.items()}
               for key, metrics in before.items()}
    print(json.dumps({"baseline": BASE, "before": before, "after": after, "change_percent": percent}, indent=2))

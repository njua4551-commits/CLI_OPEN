"""Read-only Linux diagnostics over a private MCP stdio connection."""
import json
import os
import platform
import sys

PROTOCOL = "2025-11-25"
MAX_LINE = 8192
MAX_PROCESSES = 4096
EMPTY_OBJECT = {"type": "object", "properties": {}, "additionalProperties": False}


def cpu():
    return {"logical_cpus": os.cpu_count(), "load_average": list(os.getloadavg())}


def memory():
    selected = {"MemTotal": "total_bytes", "MemAvailable": "available_bytes"}
    result = {}
    with open("/proc/meminfo", "rb") as source:
        for line in source.read(8192).splitlines():
            key, _, value = line.decode("ascii").partition(":")
            if key in selected:
                amount, unit = value.split()
                if unit != "kB":
                    raise ValueError("unexpected memory unit")
                result[selected[key]] = int(amount) * 1024
    if len(result) != len(selected):
        raise ValueError("incomplete memory information")
    return result


def storage():
    stats = os.statvfs("/")
    return {
        "scope": "root_filesystem",
        "total_bytes": stats.f_blocks * stats.f_frsize,
        "available_bytes": stats.f_bavail * stats.f_frsize,
    }


def processes():
    count = 0
    with os.scandir("/proc") as entries:
        for index, entry in enumerate(entries):
            if index == MAX_PROCESSES:
                return {"visible_processes": count, "truncated": True}
            count += entry.name.isdecimal()
    return {"visible_processes": count, "truncated": False}


def environment():
    return {
        "system": platform.system(),
        "architecture": platform.machine(),
        "wsl_kernel": "microsoft" in platform.release().casefold(),
        "profile": "DIAG",
    }


TOOLS = {
    "cpu": ("Summarize visible logical CPUs and load averages.", cpu),
    "memory": ("Summarize visible RAM totals in bytes.", memory),
    "storage": ("Summarize the root filesystem in bytes.", storage),
    "processes": ("Count visible processes within a bounded scan.", processes),
    "environment": ("Identify the runtime platform and profile.", environment),
}


INTEGER = {"type": "integer", "minimum": 0}
OUTPUT_FIELDS = {
    "cpu": {
        "logical_cpus": {"type": ["integer", "null"], "minimum": 1},
        "load_average": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
    },
    "memory": {"total_bytes": INTEGER, "available_bytes": INTEGER},
    "storage": {
        "scope": {"const": "root_filesystem"}, "total_bytes": INTEGER, "available_bytes": INTEGER,
    },
    "processes": {"visible_processes": INTEGER, "truncated": {"type": "boolean"}},
    "environment": {
        "system": {"type": "string"}, "architecture": {"type": "string"},
        "wsl_kernel": {"type": "boolean"}, "profile": {"const": "DIAG"},
    },
}


def output_schema(name):
    fields = OUTPUT_FIELDS[name]
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def response(identifier, *, result=None, error=None):
    reply = {"jsonrpc": "2.0", "id": identifier}
    if error is None:
        reply["result"] = result
    else:
        code, message = error
        reply["error"] = {"code": code, "message": message}
    encoded = json.dumps(reply, ensure_ascii=True, allow_nan=False).encode("ascii")
    if len(encoded) > MAX_LINE:
        return response(identifier, error=(-32603, "Response too large"))
    sys.stdout.buffer.write(encoded + b"\n")
    sys.stdout.buffer.flush()


def audit(name, outcome):
    # Names come from the fixed catalog. Requests and diagnostic values are excluded.
    print(f"diag tool={name} outcome={outcome}", file=sys.stderr, flush=True)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def serve():
    initialized = False
    ready = False
    for line in iter(lambda: sys.stdin.buffer.readline(MAX_LINE + 1), b""):
        if len(line) > MAX_LINE:
            # A framing violation closes the connection without buffering the rest.
            response(None, error=(-32600, "Request too large"))
            return 1
        try:
            request = json.loads(line.decode("utf-8"), object_pairs_hook=unique_object)
        except (ValueError, RecursionError):
            response(None, error=(-32700, "Parse error"))
            continue
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            response(None, error=(-32600, "Invalid request"))
            continue
        method = request.get("method")
        params = request.get("params", {})
        identifier = request.get("id")
        if not isinstance(method, str):
            response(None, error=(-32600, "Invalid request"))
            continue
        if "id" not in request:
            if initialized and method == "notifications/initialized":
                ready = True
            continue
        if not (type(identifier) is int and -(2**53) < identifier < 2**53
                or isinstance(identifier, str) and len(identifier) <= 128):
            response(None, error=(-32600, "Invalid request id"))
            continue
        if not isinstance(params, dict):
            response(identifier, error=(-32602, "Invalid parameters"))
        elif method == "initialize" and not initialized:
            if not isinstance(params.get("protocolVersion"), str):
                response(identifier, error=(-32602, "Protocol version required"))
                continue
            initialized = True
            response(identifier, result={
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "cli-open-diag", "version": "1.0.0"},
            })
        elif method == "ping" and not params:
            response(identifier, result={})
        elif not ready:
            response(identifier, error=(-32002, "Server not initialized"))
        elif method == "tools/list" and not params:
            response(identifier, result={"tools": [
                {"name": name, "description": description, "inputSchema": EMPTY_OBJECT,
                 "outputSchema": output_schema(name),
                 "annotations": {"readOnlyHint": True, "openWorldHint": False}}
                for name, (description, _) in TOOLS.items()
            ]})
        elif method == "tools/call":
            call_tool(identifier, params)
        elif method == "tools/list":
            response(identifier, error=(-32602, "Invalid parameters"))
        else:
            response(identifier, error=(-32601, "Method not found"))
    return 0


def call_tool(identifier, params):
    name = params.get("name")
    if not isinstance(name, str) or name not in TOOLS:
        audit("unknown", "denied")
        response(identifier, error=(-32602, "Unknown tool"))
        return
    if params.keys() - {"name", "arguments"} or params.get("arguments", {}) != {}:
        audit(name, "denied")
        response(identifier, error=(-32602, "Tool accepts no arguments"))
        return
    try:
        values = TOOLS[name][1]()
        text = json.dumps(values, ensure_ascii=True, allow_nan=False)
    except (OSError, ValueError):
        audit(name, "unavailable")
        response(identifier, result={"isError": True, "content": [
            {"type": "text", "text": "Diagnostic unavailable"},
        ]})
        return
    audit(name, "ok")
    response(identifier, result={
        "structuredContent": values, "content": [{"type": "text", "text": text}],
    })


if __name__ == "__main__":
    if platform.system() != "Linux":
        print("DIAG backend unavailable for this operating system", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(serve())

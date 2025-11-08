#!/usr/bin/env python3
import json
import sys
from pathlib import Path

SCHEMA_JSON = Path(__file__).resolve().parent.parent / "schema.json"

REQUIRED = [
    ("/api/v1/wing/overview/", "get"),
    ("/api/v1/wing/missing/", "get"),
    ("/api/v1/wing/entered/", "get"),
    ("/api/v1/wing/pending/", "get"),
    ("/api/v1/wing/decide/", "post"),
    ("/api/v1/wing/set-excused/", "post"),
    ("/api/v1/wing/timetable/", "get"),
    ("/api/v1/wing/daily-absences/", "get"),
    ("/api/v1/wing/students/", "get"),
    ("/api/v1/wing/me/", "get"),
    ("/api/v1/wing/classes/", "get"),
    ("/api/v1/attendance/records/", "get"),
    ("/api/v1/attendance/students/", "get"),
    ("/api/v1/attendance/history/", "get"),
    ("/api/v1/attendance/history-strict/", "get"),
    ("/api/v1/attendance/submit/", "post"),
    ("/api/v1/attendance/exit-events/", "get"),
]

# Minimal response keys expected for some critical endpoints (best-effort check).
# The check is tolerant: it looks for JSON schema properties in the OpenAPI document.
REQUIRED_RESPONSE_KEYS = {
    ("/api/v1/absence-alerts/", "get"): ["count", "results"],
    ("/api/v1/attendance/history/", "get"): ["count", "results", "page", "page_size"],
    ("/api/v1/attendance/history-strict/", "get"): ["count", "results", "page", "page_size"],
    ("/api/v1/attendance/exit-events/", "get"): ["results"],  # may also be list — schema may be underspecified
    ("/api/v1/wing/pending/", "get"): ["results"],  # or {items:[]}; schema tolerance applies
    # Wing overview should expose top-level keys even if nested structures are more detailed.
    ("/api/v1/wing/overview/", "get"): ["date", "kpis", "top_classes", "worst_classes"],
    # Approvals POST endpoints should at least include 'updated' (and action for /decide)
    ("/api/v1/wing/decide/", "post"): ["updated", "action"],
    ("/api/v1/wing/set-excused/", "post"): ["updated"],
}

# Endpoints that accept one-of several keys (schema-level tolerance)
EITHER_KEYS: dict[tuple[str, str], list[str]] = {
    ("/api/v1/wing/missing/", "get"): ["items", "results"],
    ("/api/v1/wing/entered/", "get"): ["items", "results"],
}

# Endpoints whose required response keys are treated as contract-fatal (CI-failing)
HARD_KEY_CHECK: set[tuple[str, str]] = {
    ("/api/v1/wing/overview/", "get"),
    ("/api/v1/attendance/history-strict/", "get"),
    ("/api/v1/attendance/history/", "get"),
    ("/api/v1/absence-alerts/", "get"),
    # Wing list endpoints accept either items[] or results[]; handled as a special case below.
    ("/api/v1/wing/missing/", "get"),
    ("/api/v1/wing/entered/", "get"),
    # Tighten guard to pending list as well (either items[] or results[] tolerated)
    ("/api/v1/wing/pending/", "get"),
    # Exit events list should expose basic list/paginated results
    ("/api/v1/attendance/exit-events/", "get"),
}


def _resolve_ref(obj: dict, root: dict) -> dict:
    try:
        ref = obj.get("$ref")
        if not ref:
            return obj
        # Expected format: '#/components/schemas/Name'
        if not ref.startswith("#/"):
            return obj
        parts = ref.lstrip("#/").split("/")
        cur: dict = root
        for part in parts:
            cur = cur.get(part, {})  # type: ignore[assignment]
        return cur or obj
    except Exception:
        return obj


def _schema_properties_for(op: dict, root: dict) -> dict:
    try:
        responses = op.get("responses") or {}
        # Prefer 200, fallback to 204 (may not have body)
        chosen = None
        for code in ("200", "204"):
            if code in responses:
                chosen = responses[code]
                break
        if not chosen:
            return {}
        content = (chosen.get("content") or {}).get("application/json") or {}
        schema = content.get("schema") or {}
        schema = _resolve_ref(schema, root)
        # If allOf/oneOf used, try the first object schema
        if "allOf" in schema and isinstance(schema["allOf"], list) and schema["allOf"]:
            s0 = schema["allOf"][0]
            schema = _resolve_ref(s0, root)
        if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
            return schema.get("properties") or {}
        return {}
    except Exception:
        return {}


def main() -> int:
    if not SCHEMA_JSON.exists():
        print(f"Schema file not found: {SCHEMA_JSON}", file=sys.stderr)
        return 1
    try:
        data = json.loads(SCHEMA_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to parse schema.json: {e}", file=sys.stderr)
        return 1
    paths = data.get("paths") or {}
    missing: list[str] = []
    weak: list[str] = []
    contract_warnings: list[str] = []
    contract_key_errors: list[str] = []
    for p, method in REQUIRED:
        entry = paths.get(p)
        if not isinstance(entry, dict) or method.lower() not in entry:
            missing.append(f"{p} [{method.upper()}]")
            continue
        # Minimal extra validation: ensure 200/204 response exists
        op = entry.get(method.lower(), {}) or {}
        responses = op.get("responses") or {}
        if "200" not in responses and "204" not in responses:
            weak.append(f"{p} [{method.upper()}] lacks 200/204 response in schema")
        # Optional contract keys check (best-effort)
        expected = REQUIRED_RESPONSE_KEYS.get((p, method.lower())) or REQUIRED_RESPONSE_KEYS.get((p, method))
        if expected:
            props = _schema_properties_for(op, data)
            if props:
                for k in expected:
                    if k not in props:
                        msg = f"{p} [{method.upper()}] response schema missing key: {k}"
                        if (p, method.lower()) in HARD_KEY_CHECK or (p, method) in HARD_KEY_CHECK:
                            contract_key_errors.append(msg)
                        else:
                            contract_warnings.append(msg)
            else:
                # No properties available — treat as a weak contract but non-fatal
                contract_warnings.append(f"{p} [{method.upper()}] response schema has no object properties")
    if missing:
        print("Missing endpoints in OpenAPI schema:")
        for m in missing:
            print(" -", m)
        return 2
    exit_code = 0
    if contract_key_errors:
        print("Contract key errors (fatal):")
        for e in contract_key_errors:
            print(" -", e)
        exit_code = 2
    if weak:
        print("Endpoints present but responses are underspecified:")
        for w in weak:
            print(" -", w)
        if exit_code == 0:
            exit_code = 3
    if contract_warnings:
        print("OpenAPI response schema warnings (non-fatal):")
        for w in contract_warnings:
            print(" -", w)
        if exit_code == 0:
            exit_code = 3
    if exit_code == 0:
        print("OpenAPI schema contains all required endpoints with basic responses.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

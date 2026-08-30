from __future__ import annotations

"""Gemini runner with short timeouts and auditable local JSON syntax repair.

The model, prompt, schema, and semantic validation are unchanged. If Gemini emits
syntactically invalid JSON, the raw text is repaired locally, then passed through
the same strict validate_payload() function used by the production runner.
"""

import hashlib
import json
import random
import time
from typing import Any

from json_repair import loads as repair_loads
import run_openrouter_v2 as base

_original_post_json = base.post_json


def _fast_post_json(payload, key, timeout=35):
    return _original_post_json(payload, key, timeout=35)


def _parse_with_audit(content: str, outcome_keys: list[str]) -> tuple[dict[str, Any], bool, str]:
    raw_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    repaired = False
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        obj = repair_loads(content, return_objects=True)
        repaired = True
    parsed = base.validate_payload(obj, outcome_keys)
    return parsed, repaired, raw_hash


def run_one_resilient(row, model, schema, outcome_keys, provider, key, max_retries):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": row["prompt"]}],
        "response_format": base.response_format(schema),
        "max_tokens": 450,
        "provider": {"require_parameters": True, "data_collection": "deny"},
    }
    if provider:
        body["provider"].update({"only": [provider], "allow_fallbacks": False})

    last = None
    for attempt in range(max_retries + 1):
        try:
            t = time.perf_counter()
            resp = base.post_json(body, key)
            lat = time.perf_counter() - t
            content = resp["choices"][0]["message"]["content"]
            parsed, repaired, raw_hash = _parse_with_audit(content, outcome_keys)
            usage = resp.get("usage") or {}
            return {
                "anon_id": row["anon_id"],
                "condition": row["condition"],
                "survey": row.get("survey"),
                "model_requested": model,
                "model_returned": resp.get("model"),
                "provider_returned": resp.get("provider"),
                "response_id": resp.get("id"),
                "latency_seconds": lat,
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "response": parsed,
                "attempts": attempt + 1,
                "json_syntax_repaired": repaired,
                "raw_content_sha256": raw_hash,
                "saved_at_unix": time.time(),
            }
        except Exception as e:
            last = repr(e)
            if attempt < max_retries:
                time.sleep(min(8, 2**attempt + random.random()))

    return {
        "anon_id": row["anon_id"],
        "condition": row["condition"],
        "survey": row.get("survey"),
        "model_requested": model,
        "error": last,
        "attempts": max_retries + 1,
        "saved_at_unix": time.time(),
    }


base.post_json = _fast_post_json
base.run_one = run_one_resilient


if __name__ == "__main__":
    base.main()

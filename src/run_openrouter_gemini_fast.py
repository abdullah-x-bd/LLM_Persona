from __future__ import annotations

"""Gemini-specific OpenRouter runner with a shorter per-request network timeout.

This preserves all checkpointing, validation, deduplication, and retry semantics from
run_openrouter_v2 while preventing a single unresponsive Gemini request from holding
a matrix worker for many minutes.
"""

import run_openrouter_v2 as base

_original_post_json = base.post_json


def _fast_post_json(payload, key, timeout=35):
    return _original_post_json(payload, key, timeout=35)


base.post_json = _fast_post_json


if __name__ == "__main__":
    base.main()

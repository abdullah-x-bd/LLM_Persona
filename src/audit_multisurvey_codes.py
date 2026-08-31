from __future__ import annotations
import argparse, json
from pathlib import Path
from multisurvey_runtime import decrypt_public_bundle, rows_from_bytes

def audit(bundle: Path, survey: str) -> dict:
    rows = rows_from_bytes(decrypt_public_bundle(bundle, survey, 'codes'))
    if not rows:
        raise RuntimeError('empty code bundle')
    keys = sorted(set().union(*(r.keys() for r in rows)))
    coverage = {k: sum(k in r and r[k] is not None for r in rows) for k in keys}
    # Only schema-level information. Never print respondent values.
    return {
        'survey': survey,
        'rows': len(rows),
        'unique_anon_ids': len({r.get('anon_id') for r in rows}),
        'keys': keys,
        'coverage': coverage,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bundle', required=True)
    ap.add_argument('--survey', required=True)
    args = ap.parse_args()
    print(json.dumps(audit(Path(args.bundle), args.survey), indent=2, sort_keys=True))

if __name__ == '__main__':
    main()

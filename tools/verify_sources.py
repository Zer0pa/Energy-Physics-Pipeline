"""Source-manifest verification wave.

Reads `sources_log/seed.jsonl` (placeholder sha256 = "sha256:0000…"), fetches each URL,
computes the real sha256 of the response body, and writes a verified copy to
`sources_log/seed_verified.jsonl`.

Per PRD: every external lookup logs a `SourceManifest`. The seed file was produced
manually with placeholder digests; this wave replaces them with real digests so the
KG license-grant trail is content-addressable.

No bulk data is stored — only the sha256 of the response body. Body is discarded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "sources_log" / "seed.jsonl"
VERIFIED = ROOT / "sources_log" / "seed_verified.jsonl"
SUMMARY = ROOT / "sources_log" / "verification_summary.md"

USER_AGENT = "Zer0pa-Energy-Source-Verifier/0.1 (research; contact: architects@zer0pa.ai)"
TIMEOUT_S = 12


def fetch_sha256(url: str) -> tuple[str | None, str]:
    """Return (sha256, status). status is 'ok' or an error string."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310
            body = resp.read()
            sha = hashlib.sha256(body).hexdigest()
            return sha, "ok"
    except urllib.error.HTTPError as e:
        return None, f"http {e.code}"
    except urllib.error.URLError as e:
        return None, f"url {type(e.reason).__name__}"
    except TimeoutError:
        return None, "timeout"
    except Exception as e:  # noqa: BLE001
        return None, f"{type(e).__name__}: {str(e)[:80]}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=0, help="cap number of entries (0 = all)")
    p.add_argument("--dry-run", action="store_true", help="report only; do not write")
    args = p.parse_args()

    if not SEED.exists():
        print(f"ERROR: {SEED} not found", file=sys.stderr)
        return 2

    entries: list[dict] = []
    with SEED.open() as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))

    if args.limit:
        entries = entries[: args.limit]

    print(f"verifying {len(entries)} source manifests...")
    out: list[dict] = []
    successes = failures = 0
    failure_reasons: dict[str, int] = {}

    for i, e in enumerate(entries, 1):
        url = e.get("uri", "")
        # H8: explicit non_authority flag means "this entry is acknowledged
        # unresolved; do not attempt fetch and do not count as a failure".
        if e.get("non_authority"):
            print(f"  [{i:3}/{len(entries)}] {e.get('source_id', '?'):<26} SKIP (non-authority)")
            verified = dict(e)
            verified.setdefault("rights_notes", "")
            verified["rights_notes"] = (verified["rights_notes"] or "") + " | verification skipped: non_authority flag"
            out.append(verified)
            continue
        if not url:
            print(f"  [{i:3}/{len(entries)}] skip: no URI in entry {e.get('source_id', '?')}")
            continue
        if not (url.startswith("http://") or url.startswith("https://") or url.startswith("ftp://")):
            print(f"  [{i:3}/{len(entries)}] {e.get('source_id', '?'):<26} SKIP (non-fetchable URI)")
            verified = dict(e)
            verified["rights_notes"] = (verified.get("rights_notes") or "") + " | verification skipped: non-fetchable URI"
            out.append(verified)
            continue
        sha, status = fetch_sha256(url)
        verdict = "OK" if status == "ok" else f"FAIL ({status})"
        print(f"  [{i:3}/{len(entries)}] {e.get('source_id', '?'):<26} {verdict}")
        if status == "ok":
            successes += 1
            verified = dict(e)
            verified["checksum"] = f"sha256:{sha}"
            verified["retrieval_method"] = "api"
            verified["retrieved_at"] = datetime.now(timezone.utc).isoformat()
            verified["rights_notes"] = (e.get("rights_notes") or "") + " | verified via verify_sources.py"
            out.append(verified)
        else:
            failures += 1
            failure_reasons[status] = failure_reasons.get(status, 0) + 1
            verified = dict(e)
            verified["rights_notes"] = (e.get("rights_notes") or "") + f" | verification {status}"
            out.append(verified)
        time.sleep(0.05)  # be polite

    skipped = len(out) - successes - failures
    print()
    print(
        f"results: {successes} ok, {failures} fail, {skipped} skipped (non-authority / non-fetchable) "
        f"({len(out)} total)"
    )
    if failure_reasons:
        print("failure breakdown:")
        for k, v in sorted(failure_reasons.items(), key=lambda kv: -kv[1]):
            print(f"  {v:3}  {k}")

    if args.dry_run:
        return 0

    with VERIFIED.open("w") as fp:
        for v in out:
            fp.write(json.dumps(v, ensure_ascii=False) + "\n")
    print(f"\nwrote {VERIFIED.relative_to(ROOT)} ({len(out)} entries)")

    # Summary markdown
    with SUMMARY.open("w") as fp:
        fp.write("# Source Manifest Verification Summary\n\n")
        fp.write(f"Run at: {datetime.now(timezone.utc).isoformat()}\n\n")
        fp.write(f"- Total entries: {len(entries)}\n")
        fp.write(f"- Verified (real sha256): {successes}\n")
        fp.write(f"- Failed: {failures}\n\n")
        if failure_reasons:
            fp.write("## Failure breakdown\n\n")
            for k, v in sorted(failure_reasons.items(), key=lambda kv: -kv[1]):
                fp.write(f"- `{k}` × {v}\n")
        fp.write("\n## Per-entry results\n\n")
        fp.write("| source_id | URI | verdict |\n|---|---|---|\n")
        for o in out:
            sid = o.get("source_id", "?")
            uri = o.get("uri", "")
            ck = o.get("checksum", "")
            verdict = "OK" if ck.startswith("sha256:") and "0000" not in ck else "FAIL"
            fp.write(f"| `{sid}` | <{uri}> | {verdict} |\n")
    print(f"wrote {SUMMARY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

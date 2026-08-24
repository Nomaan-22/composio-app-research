"""
100-app production runner.

Copy this file into src/orchestrate.py and app_list.py into src/app_list.py.
It reuses research_app() from research_one_v5.py without modifying V5.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path

from src.app_list import APPS, AppTarget
from src.research_one_v5 import research_app

RESULTS_DIR = Path(__file__).resolve().parent / "results"
FAILURES_FILE = RESULTS_DIR / "_failures.json"

# Hard wall-clock cap per app, independent of anything research_one_v5.py
# does internally. This is what actually would have saved the Stripe smoke
# test: research_one_v5 now has its own timeouts on every network/Gemini
# call, but this is a second, outer backstop in case some future code path
# (a new SDK version, a different tool call, whatever) hangs in a way the
# inner timeouts don't catch. One app timing out here is logged as a
# failure and the batch moves on — it never blocks apps 4 through 100.
PER_APP_TIMEOUT_SECONDS = 240


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def result_file(app: AppTarget) -> Path:
    return RESULTS_DIR / f"{slugify(app.app)}.json"


def load_failures() -> list[dict]:
    if not FAILURES_FILE.exists():
        return []
    try:
        return json.loads(FAILURES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def save_failures(items: list[dict]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FAILURES_FILE.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_completed(app: AppTarget) -> bool:
    path = result_file(app)
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "completed"
    except (OSError, json.JSONDecodeError):
        return False


_app_executor = ThreadPoolExecutor(max_workers=1)


def _run_research_with_hard_timeout(app: AppTarget, timeout: float):
    future = _app_executor.submit(
        research_app,
        app_name=app.app,
        website=app.website,
        category=app.category,
        max_repair_attempts=2,
    )
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        # Note: the underlying thread is NOT forcibly killed (Python has no
        # clean way to do that) — it keeps running in the background and
        # will eventually finish or error out on its own. That's fine here:
        # we've already moved on to the next app, and a stray background
        # thread finishing late just gets its result discarded.
        raise TimeoutError(
            f"{app.app} exceeded the {timeout:.0f}s hard per-app timeout"
        )


def run_with_retries(app: AppTarget, max_attempts: int = 2):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return _run_research_with_hard_timeout(
                app, timeout=PER_APP_TIMEOUT_SECONDS
            )
        except Exception as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            delay = 2.0 * (2 ** (attempt - 1))
            print(
                f"[retry] {app.app}: attempt {attempt}/{max_attempts} failed: "
                f"{type(exc).__name__}: {exc}"
            )
            print(f"[retry] sleeping {delay:.1f}s")
            time.sleep(delay)
    raise RuntimeError(
        f"{app.app} failed after {max_attempts} attempts: {last_error}"
    ) from last_error


def save_result(
    app: AppTarget,
    result,
    repair_attempts: int,
    validated: bool,
    elapsed: float,
) -> None:
    payload = {
        "status": "completed",
        # "validated" distinguishes an app that actually passed deterministic
        # evidence validation from one that ran out of repair attempts (or
        # tripped the stagnation guard) and was saved anyway with whatever
        # Gemini's last attempt produced. Both count as "completed" — the
        # pipeline didn't crash — but only "validated": true results should
        # go into the headline pattern-analysis numbers without an asterisk.
        "validated": validated,
        "app": app.app,
        "website": app.website,
        "category": app.category,
        "completed_at": now_utc(),
        "elapsed_seconds": round(elapsed, 2),
        "repair_attempts": repair_attempts,
        "research_result": result.model_dump(),
    }
    result_file(app).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def save_failure(app: AppTarget, exc: Exception, elapsed: float) -> None:
    items = [x for x in load_failures() if x.get("app") != app.app]
    items.append({
        "status": "failed",
        "app": app.app,
        "website": app.website,
        "category": app.category,
        "failed_at": now_utc(),
        "elapsed_seconds": round(elapsed, 2),
        "error_type": type(exc).__name__,
        "error": str(exc),
    })
    save_failures(items)


def select_apps(args) -> list[AppTarget]:
    if args.app:
        wanted = {x.casefold() for x in args.app}
        selected = [a for a in APPS if a.app.casefold() in wanted]
        missing = wanted - {a.app.casefold() for a in selected}
        if missing:
            raise SystemExit("Unknown app(s): " + ", ".join(sorted(missing)))
        return selected

    if args.smoke:
        return [a for a in APPS if a.app in {"Salesforce", "Slack", "Stripe"}]

    if args.retry_failed:
        failed = {x.get("app") for x in load_failures()}
        return [a for a in APPS if a.app in failed]

    return APPS[:args.limit] if args.limit else APPS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true",
                        help="Run Salesforce, Slack and Stripe.")
    parser.add_argument("--app", action="append",
                        help="Run a named app; repeat for multiple apps.")
    parser.add_argument("--limit", type=int,
                        help="Run the first N apps.")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Run only apps in results/_failures.json.")
    parser.add_argument("--force", action="store_true",
                        help="Re-run apps whose checkpoint already exists.")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    selected = select_apps(args)

    print("=" * 70)
    print("COMPOSIO 100-APP RESEARCH ORCHESTRATOR")
    print("=" * 70)
    print(f"Assignment apps: {len(APPS)}")
    print(f"Selected now:    {len(selected)}")
    print(f"Results:         {RESULTS_DIR}")
    print("=" * 70)

    completed = skipped = failed = repairs = not_validated = 0

    for i, app in enumerate(selected, 1):
        if not args.force and is_completed(app):
            skipped += 1
            print(f"[{i}/{len(selected)}] SKIP {app.app} (checkpoint exists)")
            continue

        print(f"\n[{i}/{len(selected)}] START {app.app} | {app.category}")
        start = time.perf_counter()

        try:
            result, repair_attempts, validated = run_with_retries(app)
            elapsed = time.perf_counter() - start
            save_result(app, result, repair_attempts, validated, elapsed)
            completed += 1
            repairs += repair_attempts
            if not validated:
                not_validated += 1
            print(
                f"[done] {app.app}: {elapsed:.1f}s, "
                f"repairs={repair_attempts}, validated={validated}"
            )
        except Exception as exc:
            elapsed = time.perf_counter() - start
            save_failure(app, exc, elapsed)
            failed += 1
            print(f"[FAILED] {app.app}: {type(exc).__name__}: {exc}")
            # Continue to the next app; one failure never kills the batch.

        print(
            f"[progress] completed={completed}, skipped={skipped}, "
            f"failed={failed}, repairs={repairs}"
        )

    print("\n" + "=" * 70)
    print("RUN COMPLETE")
    print(f"Completed:      {completed}")
    print(f"  Not fully validated (saved, needs review): {not_validated}")
    print(f"Skipped:        {skipped}")
    print(f"Failed:         {failed}")
    print(f"Repairs used:   {repairs}")
    print("=" * 70)


if __name__ == "__main__":
    main()
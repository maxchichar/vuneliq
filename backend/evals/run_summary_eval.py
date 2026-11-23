"""Live evaluation of /ai/summarize behaviour against the configured provider.

This calls the real provider and spends tokens. Run it only with an authorized key:

    cd backend && python -m evals.run_summary_eval

Each case passes only if the service accepts the output (non-empty, size-bounded, no numbers
missing from the source) and the deterministic content checks hold. Exit code 1 on any failure.
"""
import json
import sys
from pathlib import Path

from app.modules.ai.providers import AIProviderError
from app.modules.ai.services import summarize_impact

CASES = Path(__file__).with_name("summary_cases.json")


def main() -> int:
    cases = json.loads(CASES.read_text())
    failures = 0
    for case in cases:
        try:
            result = summarize_impact(case["text"])
        except AIProviderError as exc:
            print(f"FAIL {case['id']}: rejected by guardrails ({exc})")
            failures += 1
            continue
        if result.is_mock:
            print("Mock provider is active (AI_API_KEY empty); nothing to evaluate.")
            return 2
        lower = result.summary.lower()
        problems = []
        if not any(word.lower() in lower for word in case.get("must_mention_any", [])):
            problems.append(f"missing any of {case['must_mention_any']}")
        for banned in case.get("must_not_contain", []):
            if banned.lower() in lower:
                problems.append(f"contains banned text {banned!r}")
        status = "FAIL" if problems else "PASS"
        failures += bool(problems)
        print(f"{status} {case['id']}: {result.summary!r} {'; '.join(problems)}")
    print(f"\n{len(cases) - failures}/{len(cases)} cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

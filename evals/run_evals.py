import json
from pathlib import Path

import requests


CASES_FILE = Path(__file__).with_name("cases.json")
ENDPOINT = "http://127.0.0.1:8000/enrich"


def main():
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))

    passed = 0
    failures = []

    for number, case in enumerate(cases, start=1):
        print(f"Running {number}/8: {case['name']}")

        try:
            response = requests.post(
                ENDPOINT,
                json=case["input"],
                timeout=180,
            )
            response.raise_for_status()
            result = response.json()

            actual = result["category"]
            expected = case["expected_category"]

            if actual == expected:
                passed += 1
                print(f"  PASS: {actual}")
            else:
                failures.append(
                    {
                        "name": case["name"],
                        "expected": expected,
                        "actual": actual,
                    }
                )
                print(f"  FAIL: expected {expected}, got {actual}")

        except Exception as error:
            failures.append(
                {
                    "name": case["name"],
                    "expected": case["expected_category"],
                    "error": str(error),
                }
            )
            print(f"  ERROR: {error}")

    total = len(cases)
    percentage = round((passed / total) * 100, 1)

    print()
    print(f"Score: {passed}/{total} ({percentage}%)")

    if failures:
        print("Failed cases:")
        print(json.dumps(failures, indent=2))
    else:
        print("All evaluation cases passed.")


if __name__ == "__main__":
    main()
"""
eval.py — Runs all test cases against the classifier and prints a graded report.

Usage:
    python eval.py

Requires ANTHROPIC_API_KEY to be set in your environment.
Outputs a table of results + aggregate accuracy, and saves eval_results.json.
"""

import json
import time
from classifier import classify
from schema import ClassificationResult


def load_cases(path: str = "test_cases.json") -> list[dict]:
    with open(path) as f:
        return json.load(f)


def grade(result: ClassificationResult, expected: dict) -> dict:
    category_correct = result.category.value == expected["expected_category"]
    language_correct = result.language_detected.value == expected["expected_language"]
    return {
        "category_correct": category_correct,
        "language_correct": language_correct,
        "confidence": result.confidence,
        "uncertainty_flag": result.uncertainty_flag,
        "reasoning_preview": result.reasoning[:80] + ("..." if len(result.reasoning) > 80 else ""),
        "suggested_response_hint": result.suggested_response_hint,
    }


def run_evals():
    cases = load_cases()
    results = []
    passed = 0
    lang_passed = 0
    total = len(cases)

    print(f"\n{'─'*90}")
    print(f"{'ID':<4} {'Difficulty':<12} {'Expected':<14} {'Got':<14} {'Conf':<6} {'Cat✓':<6} {'Lang✓':<6}")
    print(f"{'─'*90}")

    for case in cases:
        cid = case["id"]
        try:
            result = classify(case["text"])
            grades = grade(result, case)
            cat_ok = grades["category_correct"]
            lang_ok = grades["language_correct"]
            if cat_ok:
                passed += 1
            if lang_ok:
                lang_passed += 1

            status_cat = "✅" if cat_ok else "❌"
            status_lang = "✅" if lang_ok else "❌"

            print(
                f"{cid:<4} {case['difficulty']:<12} {case['expected_category']:<14} "
                f"{result.category.value:<14} {result.confidence:<6.2f} {status_cat:<6} {status_lang:<6}"
            )

            if not cat_ok:
                print(f"     NOTE: {case['note']}")
                print(f"     Reasoning: {grades['reasoning_preview']}")
                print(f"     Hint: {grades['suggested_response_hint']}")

            results.append({
                "id": cid,
                "text": case["text"],
                "expected_category": case["expected_category"],
                "expected_language": case["expected_language"],
                "difficulty": case["difficulty"],
                "note": case["note"],
                "got_category": result.category.value,
                "got_language": result.language_detected.value,
                "confidence": result.confidence,
                "uncertainty_flag": result.uncertainty_flag,
                "reasoning": result.reasoning,
                "suggested_response_hint": result.suggested_response_hint,
                "category_correct": cat_ok,
                "language_correct": lang_ok,
                "error": None,
            })

        except Exception as e:
            print(f"{cid:<4} {'ERROR':<12} {case['expected_category']:<14} {'FAILED':<14} {'—':<6} ❌     ❌")
            print(f"     Error: {e}")
            results.append({
                "id": cid,
                "text": case["text"],
                "expected_category": case["expected_category"],
                "difficulty": case["difficulty"],
                "note": case["note"],
                "error": str(e),
                "category_correct": False,
                "language_correct": False,
            })

        time.sleep(0.5)  # Rate-limit buffer

    print(f"{'─'*90}")
    cat_acc = passed / total * 100
    lang_acc = lang_passed / total * 100
    print(f"\nCategory accuracy : {passed}/{total} = {cat_acc:.1f}%")
    print(f"Language accuracy : {lang_passed}/{total} = {lang_acc:.1f}%")

    # Breakdown by difficulty
    for diff in ["easy", "medium", "ambiguous", "adversarial"]:
        subset = [r for r in results if r.get("difficulty") == diff]
        if subset:
            correct = sum(1 for r in subset if r.get("category_correct"))
            print(f"  {diff:<12}: {correct}/{len(subset)}")

    print()

    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Full results saved to eval_results.json\n")


if __name__ == "__main__":
    run_evals()

import os
import sys
import json
from datetime import datetime

# keep the rupee sign and dashes printable on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
FINDINGS_PATH = os.path.join(HERE, "findings.json")
SAMPLE_PATH = os.path.join(HERE, "sample_output.txt")

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")   # free-tier model

# The role, the structure and the "no invented numbers" rule live here,
# in the system instruction, not in the user prompt.
SYSTEM_INSTRUCTION = (
    "You are a senior data analyst writing for Mamaearth's regional ops and finance heads. "
    "Write a business narrative of about 250 words with exactly three labeled sections: "
    "Situation, Complication, Resolution. "
    "Every number in your output must come from the findings supplied by the user and must "
    "appear with exactly the same value. Do not invent, estimate, or add any statistic that is "
    "not in the findings. Use plain language a non-technical reader can act on."
)


def month_name(ym):
    return datetime.strptime(ym, "%Y-%m").strftime("%B %Y")


def build_user_prompt(findings):
    """Interpolate the findings into the prompt, nothing is hardcoded."""
    return (
        "Write the Situation-Complication-Resolution narrative from these verified findings "
        "(amounts are in Indian Rupees):\n\n"
        f"{json.dumps(findings, indent=2)}\n\n"
        "Cover: the cleaned vs raw revenue and what explains the gap, the return rate by payment "
        "method, the highest-risk segment, and the true peak month versus the month that only "
        "looked highest because of bulk orders. End with concrete actions for ops and finance."
    )


def generate_scr_narrative_offline(findings):
    """No network, no key: the same three sections from a fixed template."""
    pay = findings["return_rate_by_payment"]
    seg = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    infl = findings["outlier_inflated_month"]

    narrative = f"""SITUATION
After cleaning the order data, total revenue stands at Rs {findings['cleaned_total_revenue_inr']:,.2f}. The raw figure was Rs {findings['raw_total_revenue_inr']:,.2f}; the Rs {findings['duplicate_reconciliation_delta_inr']:,.2f} difference comes entirely from duplicate orders caused by a double-submit bug, not from any real loss of sales. {month_name(peak['month'])} is the genuine peak month at Rs {peak['revenue_inr']:,.2f}.

COMPLICATION
Returns are not spread evenly. Cash on delivery orders are returned at {pay['COD']}%, against {pay['UPI']}% for UPI and {pay['CARD']}% for card. The problem is concentrated further: {seg['payment_method']} orders in Tier-{seg['city_tier']} cities are returned at {seg['return_rate_pct']}%, the highest of any segment. The revenue trend also misleads at first glance: {month_name(infl['month'])} appears to lead at Rs {infl['apparent_revenue_inr']:,.2f}, but that is inflated by two bulk orders and falls to Rs {infl['corrected_revenue_inr']:,.2f} once they are excluded.

RESOLUTION
Ops should target {seg['payment_method']} orders in Tier-{seg['city_tier']} cities first, for example with order confirmation calls, or by nudging those customers toward prepaid payment. Finance should report revenue on the de-duplicated base of Rs {findings['cleaned_total_revenue_inr']:,.2f}, flag bulk orders separately so they do not distort monthly trends, and plan inventory and campaigns around {month_name(peak['month'])} as the real peak.
"""
    return {"status": "success", "narrative": narrative, "tokens": None}


def generate_scr_narrative(findings):
    """Gemini first; offline template if there is no key or the call fails."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[narrator] No API key set -> using the offline path.")
        return generate_scr_narrative_offline(findings)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=build_user_prompt(findings),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                # temperature 0.0: this is a factual business report, so we want
                # the same careful, repeatable wording, not creative variation.
                temperature=0.0,
                max_output_tokens=1024,
                thinking_config=types.ThinkingConfig(thinking_budget=0),  # keep the budget for the text
                http_options=types.HttpOptions(timeout=30000),            # 30 s (milliseconds)
            ),
        )
        usage = getattr(response, "usage_metadata", None)
        result = {
            "status": "success",
            "narrative": response.text,
            "tokens": getattr(usage, "total_token_count", None),
        }
    except Exception as err:
        result = {"status": "error", "narrative": None, "message": str(err)}

    if result["status"] == "error":
        print(f"[narrator] Gemini call failed ({result['message'][:150]}) -> using the offline path.")
        return generate_scr_narrative_offline(findings)
    return result


def check_numbers(narrative, findings):
    """Assert the five required figures appear in the text (commas ignored)."""
    text = narrative.replace(",", "")
    peak = findings["true_peak_month"]
    checks = [
        ("Cleaned total revenue", f"{findings['cleaned_total_revenue_inr']:.1f}", True),
        ("COD return rate", f"{findings['return_rate_by_payment']['COD']}", True),
        ("COD + Tier-2 risk segment rate", f"{findings['highest_risk_segment']['return_rate_pct']}", True),
        ("Duplicate reconciliation delta", f"{findings['duplicate_reconciliation_delta_inr']:.1f}", True),
    ]
    results = []
    for label, needle, _ in checks:
        results.append((label, needle, needle in text))
    month_word = datetime.strptime(peak["month"], "%Y-%m").strftime("%B")
    peak_ok = (month_word in text) and (f"{peak['revenue_inr']:.1f}" in text)
    results.append((f"Peak month ({month_word}) + revenue", f"{month_word} & {peak['revenue_inr']:.1f}", peak_ok))

    for label, needle, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {needle}")
    all_ok = all(ok for _, _, ok in results)
    print("  Overall:", "ALL 5 FIGURES PRESENT" if all_ok else "MISSING FIGURES")
    return all_ok


if __name__ == "__main__":
    with open(FINDINGS_PATH, encoding="utf-8") as f:
        findings = json.load(f)

    result = generate_scr_narrative(findings)
    online = result["tokens"] is not None
    source = f"Gemini ({MODEL})" if online else "offline template (no live Gemini call)"

    print("\n" + "=" * 60)
    print("SCR NARRATIVE  |  source:", source)
    print("=" * 60)
    print(result["narrative"])
    if online:
        print("Tokens used:", result["tokens"])

    # A live Gemini run always refreshes sample_output.txt; the offline path only
    # creates it if missing, so it never overwrites a real Gemini sample.
    if online or not os.path.exists(SAMPLE_PATH):
        with open(SAMPLE_PATH, "w", encoding="utf-8") as f:
            f.write(f"# source: {source}\n\n{result['narrative']}")
        print(f"(saved to narrator/sample_output.txt)")

    print("\n" + "=" * 60)
    print("NUMERIC ACCURACY CHECK on narrator/sample_output.txt")
    print("=" * 60)
    with open(SAMPLE_PATH, encoding="utf-8") as f:
        saved_text = f.read()
    check_numbers(saved_text, findings)

    print("\nNUMERIC ACCURACY CHECK on this run's narrative")
    check_numbers(result["narrative"], findings)

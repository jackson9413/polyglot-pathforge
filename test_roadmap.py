"""Smoke test for polyglot-pathforge — runs 5 learner-brief scenarios through build_roadmap()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import build_roadmap, to_markdown

SCENARIOS = [
    {
        "name": "Spanish beginner → B1 conversation (Mexico trip)",
        "brief": (
            "I'm learning Spanish. Absolute beginner, never studied before. "
            "My native is English. I want to reach B1 conversation level in 12 months "
            "so I can chat with my in-laws when I visit Mexico. "
            "About 7 hours per week, conversational speaking style, "
            "taking a weekly italki lesson. I have a commute so podcasts work. "
            "No immersion access locally — no native speakers nearby."
        ),
    },
    {
        "name": "Mandarin intermediate → B2 (career, structured)",
        "brief": (
            "Studying Mandarin Chinese. Native English. Currently at B1 — can hold a conversation "
            "and read short articles. Targeting C1 in 24 months for a Beijing office move. "
            "12 hours/week, structured grammar-first style with heavy Anki use. "
            "Low budget — no paid tutor. Have access to native speakers via Slack community."
        ),
    },
    {
        "name": "German tight deadline (3-month tourist)",
        "brief": (
            "Want to learn German for a 2-week trip to Berlin next summer. "
            "Zero background, English native. 3 months, casual 3 hours per week. "
            "Travel phrases only, no immersion access."
        ),
    },
    {
        "name": "French heritage (family exposure, receptive ahead of productive)",
        "brief": (
            "I want to learn French. I grew up hearing French from my grandparents so I can "
            "understand a lot but I can't speak it. Want to reach B2 conversation in 18 months. "
            "8 hours/week, conversational style, immersion via family calls."
        ),
    },
    {
        "name": "Low-volume busy (5h/wk, no tutor, low budget)",
        "brief": (
            "Want to learn Japanese. Absolute beginner, English native. "
            "Target A2 in 12 months. Only 5 hours/week, full-time job. "
            "No tutor, low budget. Like anime and J-dramas. "
            "No native speakers nearby."
        ),
    },
]


def main():
    print(f"\n{'=' * 70}\npolyglot-pathforge — smoke test\n{'=' * 70}\n")
    for i, sc in enumerate(SCENARIOS, 1):
        print(f"\n[{i}] {sc['name']}\n")
        r = build_roadmap(sc["brief"])
        if "error" in r:
            print(f"  ERROR: {r['error']}")
            continue
        p = r["profile"]
        print(f"  target       : {p['target_language']} ({p['target_meta']['family']}, "
              f"diff {p['target_meta']['difficulty']}/4, script {p['target_meta']['script']})")
        print(f"  native       : {p.get('native_language') or '—'}")
        print(f"  current level: {p['current_level'].upper()} (conf {p['level_confidence']})")
        print(f"  target level : {p['target_level'].upper()}")
        print(f"  weekly hours : {p['weekly_hours']:.1f} h/wk")
        print(f"  horizon      : {p['horizon_months']} mo")
        print(f"  goals        : {', '.join(p['goals']) or '—'}")
        print(f"  style        : {', '.join(p['styles']) or '—'}")
        print(f"  constraints  : {', '.join(p['constraints']) or '—'}")
        print(f"  motivation   : {p['motivation']['label']}")
        print(f"  prior expos. : {', '.join(p['prior_exposure']) or '—'}")
        print(f"  family known : {', '.join(p['family_known']) or '—'}")
        print(f"  phases       : {len(r['phases'])}")
        print(f"  vocab waves  : {len(r['vocab_waves'])} (cumulative target {r['vocab_waves'][-1]['approx_items_touched']} words)")
        print(f"  immersion    : {len(r['immersion'])} tactics, ~{sum(t['weekly_minutes'] for t in r['immersion'])} min/wk")
        print(f"  feasibility  : {r['feasibility'].upper()} ({r['weeks_needed']} wk needed vs {r['weeks_available']} wk available)")
        print(f"  risk flags   : {len(r['risk_flags'])} "
              f"(H {sum(1 for f in r['risk_flags'] if f['severity']=='high')}, "
              f"M {sum(1 for f in r['risk_flags'] if f['severity']=='medium')}, "
              f"L {sum(1 for f in r['risk_flags'] if f['severity']=='low')})")
        print(f"  readiness    : {r['readiness_score']}/100 → {r['readiness_verdict'].replace('_',' ').upper()}")
        for axis, val in r["readiness_axes"].items():
            print(f"    - {axis:25s}: {val}/100")
        print(f"\n  risk-flag summary:")
        for f in r["risk_flags"][:5]:
            print(f"    [{f['severity'].upper():6s}] {f['label'][:80]}{'...' if len(f['label']) > 80 else ''}")
    print(f"\n{'=' * 70}\nAll 5 scenarios completed.\n{'=' * 70}\n")


if __name__ == "__main__":
    main()
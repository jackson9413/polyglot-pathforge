# polyglot-pathforge

> Local-first self-directed language-learning roadmap workbench. Paste a learner brief, get back a phase-by-phase roadmap tuned to the target language, current level, time budget, and goals — plus immersion tactics, SRS vocab waves, cultural landmarks, risk flags, and a 0–100 path-readiness score.

**No API keys. No LLM. Single-file Flask + SQLite + vanilla JS.** Runs entirely on your machine.

## Why this exists

There are thousands of "learn Spanish in 30 days" blog posts and a handful of SRS apps. None of them answer the actual question a serious self-directed learner has:

> *"Given where I am, what I'm aiming for, and how much time I have — what's the actual structure of my path, and is it realistic?"*

`polyglot-pathforge` takes your learner brief, classifies it (target language + family + script + tone + difficulty, current CEFR level, weekly hours, horizon, goals, style, constraints, motivation), and produces:

1. **A phase roadmap** — phase-by-phase milestones from your current CEFR to your target CEFR. Each phase lists grammar topics, vocab target, est. weeks / hours, and a measurable milestone (e.g., "hold a 5-minute conversation").
2. **A weekly hour split** — minutes/week across input / output / study / review, biased by your stated style (conversational → more speaking, immersion → more listening, anki → more SRS).
3. **Immersion tactics** — 8 ranked tactics (input ladder, shadowing, sentence mining, output journal, tandem, italki, subtitled media, news scan, book ladder, think-in-target, music study, dictation) chosen by current level + style + goals.
4. **SRS vocab waves** — 5-wave spaced-repetition schedule (acquire / recall / reinforce / consolidate / long-term) with interval and review share per wave.
6. **Cultural landmarks** — literature, film, and music picks curated for the target language's family.
7. **Risk flags** — ambition-mismatch, new-script, tonal, many-cases, low-volume, time-constrained, self-study-gap, no-native-input, weak-motivation, tight-deadline, family-boost, heritage-low, rtl-script, same-family-native, with high/medium/low severity.
8. **Path-readiness score (0–100)** — across 6 weighted axes: profile completeness, time feasibility, plan density, style fit, goal alignment, risk hygiene.

## Quickstart

```bash
# 1. install
pip install flask

# 2. run
python app.py

# 3. open
open http://127.0.0.1:5130
```

That's it. The SQLite session log is created at `polyglot_pathforge.db` on first launch.

## How to use it

1. **Write or paste a learner brief.** The more you share, the tighter the plan. Useful fields:
   - target language ("learning Spanish", "studying Japanese")
   - native language ("my native is English")
   - current level (absolute beginner / A1 / B1 / "I can hold a conversation")
   - target level (CEFR letter or "reach B1", "until I'm conversational")
   - weekly hours ("7 hours/week", "30 min/day", "casual")
   - horizon ("12 months", "by next summer")
   - goals (travel / conversation / relocation / career / exam / family / media / reading / heritage)
   - style (structured / conversational / immersion / anki / music / video / reading / tutor)
   - constraints (no tutor / low budget / busy / no apps / commute / kids / deadline / no immersion)
2. **Hit "Forge roadmap →"** — get the full plan.
3. **Save / export** — session log with 1-5 star rating + notes, Markdown + JSON export.

## What's covered

**36 languages** across 15 families: Spanish, Portuguese, French, Italian, Romanian, German, Dutch, Swedish, Norwegian, Danish, Russian, Polish, Czech, Ukrainian, Mandarin, Cantonese, Korean, Japanese, Arabic, Hebrew, Hindi, Urdu, Farsi, Greek, Turkish, Finnish, Hungarian, Vietnamese, Thai, Indonesian, Malay, Swahili, plus Chinese variants and Persian/Farsi synonyms.

**Difficulty band (1-4, FSI-style)** drives est. weeks per phase and grammar pacing.

**6 CEFR-aligned phase blocks** (`a0_a1`, `a1_a2`, `a2_b1`, `b1_b2`, `b2_c1`, `c1_c2`) with 11 total phases — each with grammar topic list, vocab target, focus, and milestone.

**12 immersion tactics** with weekly-minute estimates, level floors, and category tags (listening / speaking / writing / reading / input / tutoring / vocab).

**5 SRS waves** (acquire → recall → reinforce → consolidate → long-term) at 1d / 2d / 5d / 14d / 45d intervals.

**15 cultural-landmark picks** (literature, film, music) per language family.

**14 risk-flag patterns** (ambition-mismatch, new-script, tonal, many-cases, low-volume, time-constrained, self-study-gap, no-native-input, low-budget, weak-motivation, tight-deadline, family-boost, heritage-low, rtl-script, same-family-native).

**6 weighted readiness axes** (profile completeness 15% / time feasibility 20% / plan density 15% / style fit 15% / goal alignment 15% / risk hygiene 20%) with 5 verdict bands.

## Architecture

- `app.py` — single-file Flask backend with 36-language taxonomy, level/goal/constraint/style/horizon/motivation detectors, CEFR-phase library, SRS wave library, immersion-tactic library, cultural-landmark library, risk-flag engine, 0–100 readiness engine, SQLite session log, Markdown + JSON export.
- `templates/index.html` — single-page UI with brief input + result rendering.
- `static/style.css` — dark theme styling.
- `static/app.js` — frontend logic, save/load/delete sessions, download Markdown/JSON, copy to clipboard.
- `test_roadmap.py` — 5-scenario smoke test (Spanish beginner→B1, Mandarin intermediate→B2, German tight deadline, French heritage, low-volume busy).

## Tested scenarios

```bash
python test_roadmap.py
```

Runs 5 brief scenarios end-to-end through `build_roadmap()`:
1. Spanish beginner → B1 conversation (Mexico trip, 12 mo, 7h/wk, italki + commute)
2. Mandarin intermediate → B2 (career, 18 mo, 12h/wk, structured + anki)
3. German tight deadline (3 mo, casual tourist)
4. French heritage (receptive ahead of productive, no formal study)
5. Low-volume busy (5h/wk, no tutor, low budget)

Each scenario prints detected profile, phase count, vocab waves, immersion tactic count, risk-flag count, and the path-readiness score + verdict.

## Different from other tools in the rotation

This is **NOT** another finance / portfolio / job-tracker / study-deck / lease-decode / meal-planner.

This fills the MISSING **language learning self-direction moment**: "I'm a self-directed learner who wants a real roadmap that knows my language, my level, my time, my style, my constraints — not a 30-day YouTube checklist."

## License

MIT.
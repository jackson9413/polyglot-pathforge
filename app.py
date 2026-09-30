"""
polyglot-pathforge — local-first self-directed language learning roadmap workbench.

Paste a learner brief (target language, native language, current level, goal,
time horizon, weekly hours, learning style, motivation, prior exposure,
constraints), get back: detected learner profile, a phase-by-phase roadmap
(milestone ladder from A0→target with hand-curated grammar topics, vocab
waves with spaced-repetition review schedule, immersion tactics, cultural
landmarks), risk flags, and a 0-100 path-readiness score.

Single-file Flask app, SQLite session log, no API keys, no LLM.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, render_template, request

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "polyglot_pathforge.db"

app = Flask(__name__, template_folder="templates", static_folder="static")


# ----------------------------- language taxonomy -----------------------------------
# Curated language families with structural characteristics, difficulty band
# (FSI-style 1=easy for English speaker to 4=hard), and family label.

LANGUAGES: dict[str, dict[str, Any]] = {
    # Romance
    "spanish": {"family": "romance", "difficulty": 1, "script": "latin", "tonal": False,
                "genders": True, "articles": "def+indef", "cases": 0,
                "vowel_count": 5, "writing_dir": "ltr"},
    "portuguese": {"family": "romance", "difficulty": 1, "script": "latin", "tonal": False,
                   "genders": True, "articles": "def+indef", "cases": 0, "vowel_count": 5, "writing_dir": "ltr"},
    "french": {"family": "romance", "difficulty": 1, "script": "latin", "tonal": False,
               "genders": True, "articles": "def+indef", "cases": 0, "vowel_count": 17, "writing_dir": "ltr"},
    "italian": {"family": "romance", "difficulty": 1, "script": "latin", "tonal": False,
                "genders": True, "articles": "def+indef", "cases": 0, "vowel_count": 7, "writing_dir": "ltr"},
    "romanian": {"family": "romance", "difficulty": 1, "script": "latin", "tonal": False,
                 "genders": True, "articles": "def+indef", "cases": 0, "vowel_count": 7, "writing_dir": "ltr"},
    # Germanic
    "german": {"family": "germanic", "difficulty": 2, "script": "latin", "tonal": False,
               "genders": True, "articles": "def+indef", "cases": 4, "vowel_count": 8, "writing_dir": "ltr"},
    "dutch": {"family": "germanic", "difficulty": 1, "script": "latin", "tonal": False,
              "genders": True, "articles": "def+indef", "cases": 0, "vowel_count": 11, "writing_dir": "ltr"},
    "swedish": {"family": "germanic", "difficulty": 1, "script": "latin", "tonal": False,
                "genders": True, "articles": "def+indef", "cases": 0, "vowel_count": 17, "writing_dir": "ltr"},
    "norwegian": {"family": "germanic", "difficulty": 1, "script": "latin", "tonal": False,
                  "genders": True, "articles": "def+indef", "cases": 0, "vowel_count": 17, "writing_dir": "ltr"},
    "danish": {"family": "germanic", "difficulty": 1, "script": "latin", "tonal": False,
               "genders": True, "articles": "def+indef", "cases": 0, "vowel_count": 17, "writing_dir": "ltr"},
    # Slavic
    "russian": {"family": "slavic", "difficulty": 3, "script": "cyrillic", "tonal": False,
                "genders": True, "articles": "none", "cases": 6, "vowel_count": 10, "writing_dir": "ltr"},
    "polish": {"family": "slavic", "difficulty": 3, "script": "latin", "tonal": False,
               "genders": True, "articles": "none", "cases": 7, "vowel_count": 9, "writing_dir": "ltr"},
    "czech": {"family": "slavic", "difficulty": 3, "script": "latin", "tonal": False,
              "genders": True, "articles": "none", "cases": 7, "vowel_count": 10, "writing_dir": "ltr"},
    "ukrainian": {"family": "slavic", "difficulty": 3, "script": "cyrillic", "tonal": False,
                  "genders": True, "articles": "none", "cases": 7, "vowel_count": 6, "writing_dir": "ltr"},
    # East Asian
    "mandarin": {"family": "sinitic", "difficulty": 4, "script": "hanzi", "tonal": True,
                 "genders": False, "articles": "none", "cases": 0, "vowel_count": 6, "writing_dir": "ltr"},
    "chinese": {"family": "sinitic", "difficulty": 4, "script": "hanzi", "tonal": True,
                "genders": False, "articles": "none", "cases": 0, "vowel_count": 6, "writing_dir": "ltr"},
    "cantonese": {"family": "sinitic", "difficulty": 4, "script": "hanzi", "tonal": True,
                  "genders": False, "articles": "none", "cases": 0, "vowel_count": 6, "writing_dir": "ltr"},
    "japanese": {"family": "japonic", "difficulty": 4, "script": "mixed_jp", "tonal": True,
                 "genders": False, "articles": "none", "cases": 0, "vowel_count": 5, "writing_dir": "ltr"},
    "korean": {"family": "koreanic", "difficulty": 3, "script": "hangul", "tonal": False,
               "genders": False, "articles": "none", "cases": 0, "vowel_count": 10, "writing_dir": "ltr"},
    # Semitic
    "arabic": {"family": "semitic", "difficulty": 4, "script": "arabic", "tonal": False,
               "genders": True, "articles": "def_only", "cases": 3, "vowel_count": 8, "writing_dir": "rtl"},
    "hebrew": {"family": "semitic", "difficulty": 3, "script": "hebrew", "tonal": False,
               "genders": True, "articles": "def_only", "cases": 0, "vowel_count": 5, "writing_dir": "rtl"},
    # Indo-Iranian
    "hindi": {"family": "indo_iranian", "difficulty": 2, "script": "devanagari", "tonal": False,
              "genders": True, "articles": "none", "cases": 2, "vowel_count": 11, "writing_dir": "ltr"},
    "urdu": {"family": "indo_iranian", "difficulty": 2, "script": "arabic", "tonal": False,
             "genders": True, "articles": "none", "cases": 2, "vowel_count": 10, "writing_dir": "rtl"},
    "farsi": {"family": "indo_iranian", "difficulty": 2, "script": "arabic", "tonal": False,
              "genders": False, "articles": "none", "cases": 0, "vowel_count": 6, "writing_dir": "rtl"},
    "persian": {"family": "indo_iranian", "difficulty": 2, "script": "arabic", "tonal": False,
                "genders": False, "articles": "none", "cases": 0, "vowel_count": 6, "writing_dir": "rtl"},
    # Hellenic / Turkic / Uralic / Other
    "greek": {"family": "hellenic", "difficulty": 3, "script": "greek", "tonal": False,
              "genders": True, "articles": "def", "cases": 4, "vowel_count": 5, "writing_dir": "ltr"},
    "turkish": {"family": "turkic", "difficulty": 3, "script": "latin", "tonal": False,
                "genders": False, "articles": "none", "cases": 6, "vowel_count": 8, "writing_dir": "ltr"},
    "finnish": {"family": "uralic", "difficulty": 3, "script": "latin", "tonal": False,
                "genders": False, "articles": "none", "cases": 15, "vowel_count": 8, "writing_dir": "ltr"},
    "hungarian": {"family": "uralic", "difficulty": 3, "script": "latin", "tonal": False,
                  "genders": False, "articles": "none", "cases": 18, "vowel_count": 14, "writing_dir": "ltr"},
    "vietnamese": {"family": "austroasiatic", "difficulty": 3, "script": "latin", "tonal": True,
                   "genders": False, "articles": "none", "cases": 0, "vowel_count": 11, "writing_dir": "ltr"},
    "thai": {"family": "tai_kadai", "difficulty": 3, "script": "thai", "tonal": True,
             "genders": False, "articles": "none", "cases": 0, "vowel_count": 9, "writing_dir": "ltr"},
    "indonesian": {"family": "austronesian", "difficulty": 1, "script": "latin", "tonal": False,
                   "genders": False, "articles": "none", "cases": 0, "vowel_count": 5, "writing_dir": "ltr"},
    "malay": {"family": "austronesian", "difficulty": 1, "script": "latin", "tonal": False,
              "genders": False, "articles": "none", "cases": 0, "vowel_count": 5, "writing_dir": "ltr"},
    "swahili": {"family": "niger_congo", "difficulty": 2, "script": "latin", "tonal": False,
                "genders": True, "articles": "none", "cases": 0, "vowel_count": 5, "writing_dir": "ltr"},
    # English as a native-language anchor (commonly claimed default)
    "english": {"family": "germanic", "difficulty": 1, "script": "latin", "tonal": False,
                "genders": False, "articles": "none", "cases": 0, "vowel_count": 6, "writing_dir": "ltr"},
}


LEVEL_KEYWORDS = {
    "a0": ["zero", "absolute beginner", "no background", "never studied", "don't know",
           "do not know", "no prior", "from scratch", "starting from zero"],
    "a1": ["a1", "beginner", "know some basics", "couple words", "very basic",
           "know a few", "survival", "abc", "alphabet only", "just started"],
    "a2": ["a2", "elementary", "basic phrases", "can order food", "simple sentences",
           "know some grammar", "basic conversations", "false beginner"],
    "b1": ["b1", "intermediate", "can hold conversation", "talk about hobbies",
           "understand slow speech", "survive travel", "solid basics"],
    "b2": ["b2", "upper intermediate", "can argue", "read short articles",
           "watch shows with subs", "express opinions", "comfortable"],
    "c1": ["c1", "advanced", "read novels", "fluent-ish", "long conversations",
           "subtle meaning", "professional working"],
    "c2": ["c2", "near-native", "mastery", "professional fluency", "nuanced",
           "native-like", "literary"],
}


GOAL_KEYWORDS = {
    "travel": ["travel", "trip", "vacation", "tourist", "holiday", "backpack",
               "abroad", "tour"],
    "conversation": ["conversation", "chat", "talk to people", "social", "small talk",
                     "speak with", "make friends"],
    "relocation": ["relocate", "moving to", "live in", "moving abroad", "expat",
                   "settle in", "live abroad", "long-term stay"],
    "family": ["family", "partner", "in-laws", "inlaws", "spouse", "kids", "children",
               "heritage", "grandparents", "ancestors"],
    "academic": ["academic", "university", "study abroad", "research", "thesis",
                 "dissertation", "graduate school", "phd", "degree"],
    "career": ["career", "job", "work", "client", "business", "promotion",
               "office", "colleague", "negotiate", "interview"],
    "reading": ["read", "literature", "novels", "books", "poetry", "comics", "manga",
                "lyrics"],
    "media": ["watch", "show", "movie", "film", "anime", "k-drama", "tv", "series",
              "podcast", "music", "songs"],
    "heritage": ["heritage", "roots", "ancestors", "grandparents", "family language",
                 "cultural"],
    "relationship": ["relationship", "partner", "dating", "marriage", "in-laws"],
    "exam": ["exam", "test", "certification", "delf", "dele", "jlpt", "hsk",
             "goethe", "torfl", "ielts"],
}


CONSTRAINT_KEYWORDS = {
    "no_tutor": ["no tutor", "self-study", "self study", "no teacher", "solo",
                 "on my own", "by myself"],
    "low_budget": ["free", "no budget", "low budget", "cheap", "minimal cost",
                   "no money"],
    "busy": ["busy", "no time", "limited time", "tight schedule", "full-time job",
             "10 minutes", "5 minutes"],
    "no_apps": ["no apps", "don't like apps", "no subscription", "no paid",
                "no rosetta stone", "no duolingo"],
    "commute": ["commute", "driving", "subway", "transit", "on the bus"],
    "kids": ["kids", "children", "toddler", "parent", "family time"],
    "deadline": ["deadline", "by next", "before", "in 3 months", "in 6 months",
                 "soon"],
    "no_immersion": ["no immersion", "no native", "no speakers nearby",
                     "isolated", "no community"],
    "have_immersion": ["partner speaks", "live in country", "surrounded by",
                       "community of speakers", "tandem"],
}


STYLE_KEYWORDS = {
    "structured": ["structured", "textbook", "grammar-first", "systematic", "rules",
                   "formal", "classroom"],
    "conversational": ["conversational", "speaking", "talking", "chat", "fluency first"],
    "immersion": ["immersion", "native media", "subtitles", "input-heavy",
                  "comprehensible input"],
    "anki": ["anki", "flashcard", "spaced repetition", "srs", "memorization"],
    "music": ["music", "songs", "lyrics", "k-pop", "rap", "singing"],
    "video": ["video", "youtube", "tiktok", "show", "movie", "film"],
    "reading": ["reading", "books", "novels", "articles", "news"],
    "game": ["game", "gaming", "video game", "rpg"],
    "tutor": ["tutor", "teacher", "class", "italki", "lesson"],
}


# ------------------------------ CEFR / grammar library ----------------------------
# Phases by level for a typical roadmap; the deeper the target level, the more phases.

CEFR_PHASES: dict[str, list[dict[str, Any]]] = {
    "a0_a1": [
        {"name": "Phase 1: Sounds", "focus": "sound inventory + script",
         "weeks_lo": 1, "weeks_hi": 2,
         "grammar": ["alphabet / script", "pronunciation drills", "greetings & courtesy",
                     "yes/no + numbers 0-20", "introduce yourself"],
         "vocab_target": 300, "milestone": "Survival introductions"},
        {"name": "Phase 2: Survival phrases", "focus": "high-frequency chunks",
         "weeks_lo": 2, "weeks_hi": 4,
         "grammar": ["present tense (1st person)", "wh-questions", "negation basics",
                     "common verbs: to be / to have / to want / to go"],
         "vocab_target": 600, "milestone": "Order food, ask directions, basic small talk"},
        {"name": "Phase 3: Daily life", "focus": "narrative present + daily routine",
         "weeks_lo": 3, "weeks_hi": 5,
         "grammar": ["regular plurals", "articles (if any)", "time / days / months",
                     "frequency adverbs"],
         "vocab_target": 1000, "milestone": "Describe a typical day"},
    ],
    "a1_a2": [
        {"name": "Phase 4: Past & future", "focus": "narrative tenses",
         "weeks_lo": 3, "weeks_hi": 6,
         "grammar": ["past tense (regular + top 20 irregular)", "future (going to / will)",
                     "prepositions of time & place", "modal: can / must / want to"],
         "vocab_target": 1500, "milestone": "Tell a story from last weekend"},
        {"name": "Phase 5: Connected speech", "focus": "real-world input tolerance",
         "weeks_lo": 4, "weeks_hi": 6,
         "grammar": ["object pronouns", "reflexive verbs (if any)", "comparative + superlative",
                     "conjunctions (because / but / so / when)"],
         "vocab_target": 2000, "milestone": "Hold a 5-minute conversation"},
    ],
    "a2_b1": [
        {"name": "Phase 6: Subjunctive mood / conditionals", "focus": "opinion + hypothetical",
         "weeks_lo": 4, "weeks_hi": 7,
         "grammar": ["present perfect", "imperfect / continuous aspect (if any)",
                     "basic conditionals (real + unreal)", "relative clauses",
                     "indirect speech"],
         "vocab_target": 3000, "milestone": "Argue preferences, follow a TV show with subs"},
        {"name": "Phase 7: Idiom + listening stamina", "focus": "natural input",
         "weeks_lo": 4, "weeks_hi": 8,
         "grammar": ["passive voice", "reported speech", "all conjunctions + discourse markers",
                     "discourse: actually / basically / I mean / you know"],
         "vocab_target": 4000, "milestone": "Read short articles, watch news with subs"},
    ],
    "b1_b2": [
        {"name": "Phase 8: Nuance + register", "focus": "subtle meaning",
         "weeks_lo": 5, "weeks_hi": 10,
         "grammar": ["subjunctive / formal register", "advanced conditionals",
                     "concessive clauses (although / even though)", "phrasal verbs / idioms",
                     "register shift: tu/usted, casual vs honorific speech"],
         "vocab_target": 5500, "milestone": "Read a novel, follow a film without subs"},
        {"name": "Phase 9: Argumentation + cultural layer", "focus": "rhetoric + culture",
         "weeks_lo": 6, "weeks_hi": 10,
         "grammar": ["rhetorical devices", "hedging & emphasis", "literary tense (if any)",
                     "dialects / slang awareness", "professional / formal email patterns"],
         "vocab_target": 7000, "milestone": "Debate, write essays, near-native comprehension"},
    ],
    "b2_c1": [
        {"name": "Phase 10: Style & idiom depth", "focus": "advanced style",
         "weeks_lo": 6, "weeks_hi": 12,
         "grammar": ["all remaining tenses / aspects / moods", "word formation patterns",
                     "loanwords & false friends across family languages",
                     "literary devices & registers"],
         "vocab_target": 9000, "milestone": "Read academic prose, write professional letters"},
    ],
    "c1_c2": [
        {"name": "Phase 11: Native-like fluency", "focus": "native idiom & culture",
         "weeks_lo": 8, "weeks_hi": 16,
         "grammar": ["rare / literary grammar", "regional dialect awareness",
                     "puns / wordplay", "stylistic imitation of native authors"],
         "vocab_target": 12000, "milestone": "Native-like comprehension & self-expression"},
    ],
}


# Spaced-repetition vocab wave schedule (each wave expands to a longer interval).
SRS_WAVES: list[dict[str, Any]] = [
    {"name": "Wave 1: Acquire", "interval_days": 1, "review_share": 1.0,
     "note": "first encounter — context + sound + image + 1 example"},
    {"name": "Wave 2: Recall", "interval_days": 2, "review_share": 0.8,
     "note": "active recall + cloze + production"},
    {"name": "Wave 3: Reinforce", "interval_days": 5, "review_share": 0.5,
     "note": "use in a sentence + hear in input"},
    {"name": "Wave 4: Consolidate", "interval_days": 14, "review_share": 0.3,
     "note": "encounter in media or conversation"},
    {"name": "Wave 5: Long-term", "interval_days": 45, "review_share": 0.15,
     "note": "re-encounter every ~6 weeks to prevent decay"},
]


# Immersion tactics library (curated).
IMMERSION_TACTICS: list[dict[str, Any]] = [
    {"name": "Input ladder", "category": "listening",
     "description": "Comprehensible input at 80-90% known: graded reader → YouTube with subs → podcasts → native TV → films without subs.",
     "weekly_minutes": 90, "level_floor": "a1"},
    {"name": "Shadowing", "category": "speaking",
     "description": "Listen to a 5-10s clip, pause, repeat mimicking intonation + rhythm. Record & compare.",
     "weekly_minutes": 30, "level_floor": "a1"},
    {"name": "Sentence mining", "category": "vocab",
     "description": "Save real sentences from native input; annotate grammar; cloze-delete key words; review via SRS.",
     "weekly_minutes": 45, "level_floor": "a1"},
    {"name": "Output journal", "category": "writing",
     "description": "Write 5-10 sentences about your day in target language. Submit to tutor or community for correction.",
     "weekly_minutes": 30, "level_floor": "a2"},
    {"name": "Tandem / language exchange", "category": "speaking",
     "description": "Weekly 30-min voice call with a native speaker learning your language (tandem.net, HelloTalk).",
     "weekly_minutes": 30, "level_floor": "a2"},
    {"name": "Italki lesson", "category": "tutoring",
     "description": "1-on-1 lesson with a community tutor (~$10-20/hr). Two short lessons > one long one.",
     "weekly_minutes": 60, "level_floor": "a0"},
    {"name": "Subtitled media immersion", "category": "listening",
     "description": "Watch 1 episode of a native show per week with target-language subs (not English).",
     "weekly_minutes": 90, "level_floor": "a2"},
    {"name": "News scan", "category": "reading",
     "description": "Skim 2-3 native news articles daily. Highlight unknown words; review weekly.",
     "weekly_minutes": 30, "level_floor": "b1"},
    {"name": "Book ladder", "category": "reading",
     "description": "Read graded readers → short stories → full novels in target language. Keep a vocabulary log.",
     "weekly_minutes": 120, "level_floor": "b1"},
    {"name": "Think in target", "category": "speaking",
     "description": "Narrate your thoughts in target language during daily activities (cooking, walking, commuting).",
     "weekly_minutes": 60, "level_floor": "a2"},
    {"name": "Music lyric study", "category": "input",
     "description": "Pick 2 songs/week; read lyrics while listening; translate and sing-along.",
     "weekly_minutes": 30, "level_floor": "a0"},
    {"name": "Dictation drills", "category": "writing",
     "description": "Listen to a 30s clip and write down what you hear. Compare to transcript.",
     "weekly_minutes": 20, "level_floor": "a2"},
]


# Cultural landmark suggestions per family.
CULTURAL_LANDMARKS: dict[str, list[dict[str, str]]] = {
    "romance": [
        {"item": "Read a Don Quixote excerpt (es) / Les Misérables excerpt (fr)", "type": "literature"},
        {"item": "Watch a Studio Ghibli dub in target language (jp dub tracks for romance? use local production)", "type": "film"},
        {"item": "Follow a regional podcast (Radio Ambulante, France Inter)", "type": "media"},
    ],
    "germanic": [
        {"item": "Read a Brothers Grimm fairy tale in original (de)", "type": "literature"},
        {"item": "Watch a Nordic Noir series (sk/se/no/da)", "type": "film"},
        {"item": "Listen to a Krautrock or Nordic music deep dive", "type": "music"},
    ],
    "slavic": [
        {"item": "Read Chekhov short stories (ru), Szymborska poems (pl)", "type": "literature"},
        {"item": "Watch a Tarkovsky film (ru) or a Wajda classic (pl)", "type": "film"},
        {"item": "Listen to a Slavic-folk or contemporary indie record", "type": "music"},
    ],
    "sinitic": [
        {"item": "Read a Lao She novella or modern 鲁迅 (lu xun) short", "type": "literature"},
        {"item": "Watch a Zhang Yimou or Jia Zhangke film", "type": "film"},
        {"item": "Follow a Taiwan/HK pop release + Mainland indie", "type": "music"},
    ],
    "japonic": [
        {"item": "Read a Murakami short or a Soseki excerpt", "type": "literature"},
        {"item": "Watch a Studio Ghibli or Kore-eda film without subs", "type": "film"},
        {"item": "Listen to city pop / Shibuya-kei / Vocaloid", "type": "music"},
    ],
    "koreanic": [
        {"item": "Read a Shin Kyung-sook novel excerpt (ko)", "type": "literature"},
        {"item": "Watch a Bong Joon-ho or Park Chan-wook film", "type": "film"},
        {"item": "Follow a K-indie band or trot revival", "type": "music"},
    ],
    "semitic": [
        {"item": "Read a Naguib Mahfouz novel (ar) or Amos Oz memoir (he)", "type": "literature"},
        {"item": "Watch a Nabil Ayouch or Elia Suleiman film", "type": "film"},
        {"item": "Listen to Oum Kalthoum or Fairuz (ar), Idan Raichel (he)", "type": "music"},
    ],
    "indo_iranian": [
        {"item": "Read a Rumi poem (fa) or a Premchand story (hi)", "type": "literature"},
        {"item": "Watch a Satyajit Ray film (hi) or a Majidi film (fa)", "type": "film"},
        {"item": "Listen to Bollywood or qawwali (hi) or Persian classical (fa)", "type": "music"},
    ],
    "hellenic": [
        {"item": "Read a Kazantzakis excerpt (el)", "type": "literature"},
        {"item": "Watch a Theo Angelopoulos film (el)", "type": "film"},
        {"item": "Listen to rebetiko or contemporary Greek indie", "type": "music"},
    ],
    "turkic": [
        {"item": "Read a Orhan Pamuk novel (tr)", "type": "literature"},
        {"item": "Watch a Nuri Bilge Ceylan film (tr)", "type": "film"},
        {"item": "Listen to Anatolian rock or modern Turkish pop", "type": "music"},
    ],
    "uralic": [
        {"item": "Read a Kalevala excerpt (fi) or a contemporary Hungarian novel", "type": "literature"},
        {"item": "Watch a Finnish or Hungarian indie film", "type": "film"},
        {"item": "Listen to Sibelius + Finnish tango or Hungarian folk", "type": "music"},
    ],
    "austroasiatic": [
        {"item": "Read a contemporary Vietnamese author (Nguyễn Nhật Ánh)", "type": "literature"},
        {"item": "Watch a Tran Anh Hung film (vi)", "type": "film"},
        {"item": "Listen to V-pop or Vietnamese indie", "type": "music"},
    ],
    "tai_kadai": [
        {"item": "Read a Thai literary excerpt or contemporary novel", "type": "literature"},
        {"item": "Watch a Apichatpong Weerasethakul film (th)", "type": "film"},
        {"item": "Listen to Thai indie or luk thung", "type": "music"},
    ],
    "austronesian": [
        {"item": "Read a Pramoedya Ananta Toer excerpt (id)", "type": "literature"},
        {"item": "Watch a Joko Anwar or Garin Nugroho film", "type": "film"},
        {"item": "Listen to Indonesian indie (id) or contemporary pop", "type": "music"},
    ],
    "niger_congo": [
        {"item": "Read a Ngugi wa Thiong'o excerpt (sw/ki)", "type": "literature"},
        {"item": "Watch a recent East African film", "type": "film"},
        {"item": "Listen to Bongo Flava or Taarab", "type": "music"},
    ],
}


# ------------------------------ detection helpers -------------------------------

def detect_language(text: str) -> dict[str, Any]:
    """Detect target language by name from text. Filters out languages claimed as native."""
    text_l = text.lower()
    # identify which languages are explicitly called 'native' so we can exclude them
    native_excludes: set[str] = set()
    m = re.search(r"native\s+(?:is|language\s+is)\s+([a-zA-Z]+)", text_l)
    if m:
        cand = m.group(1).strip()
        if cand in LANGUAGES:
            native_excludes.add(cand)
    m = re.search(r"speak\s+(\w+)\s+(?:at\s+home|natively)", text_l)
    if m:
        cand = m.group(1).strip()
        if cand in LANGUAGES:
            native_excludes.add(cand)
    # also detect 'my L1' or 'my mother tongue'
    m = re.search(r"(?:L1|mother tongue|first language)\s+(?:is\s+)?([a-zA-Z]+)", text_l)
    if m:
        cand = m.group(1).strip()
        if cand in LANGUAGES:
            native_excludes.add(cand)
    hits = []
    for lang_name, meta in LANGUAGES.items():
        if lang_name in native_excludes:
            continue
        if re.search(rf"\b{re.escape(lang_name)}\b", text_l):
            hits.append((lang_name, meta))
    variants = {
        "chinese (mandarin)": "mandarin", "mandarin chinese": "mandarin",
        "chinese (cantonese)": "cantonese", "cantonese chinese": "cantonese",
        "brazillian portuguese": "portuguese", "brazilian portuguese": "portuguese",
        "farsi / persian": "farsi", "farsi/persian": "farsi",
    }
    for variant, canonical in variants.items():
        if variant in text_l and canonical in LANGUAGES and canonical not in native_excludes:
            hits.append((canonical, LANGUAGES[canonical]))
    if not hits:
        return {"detected": None, "ambiguous": False, "candidates": []}
    hits.sort(key=lambda x: (-x[1]["difficulty"], x[0]))
    primary = hits[0]
    return {
        "detected": primary[0],
        "meta": primary[1],
        "ambiguous": len(hits) > 1,
        "candidates": [h[0] for h in hits[:3]],
    }


def detect_native(text: str) -> dict[str, Any]:
    """Detect native language. Defaults to English if not specified."""
    text_l = text.lower()
    hits = []
    for lang_name in LANGUAGES:
        if re.search(rf"\b{re.escape(lang_name)}\b", text_l):
            hits.append(lang_name)
    m_native = re.search(r"native\s+(?:is|language\s+is|l1\s+is|tongue\s+is)\s+([a-zA-Z]+)", text_l)
    if m_native:
        cand = m_native.group(1).strip()
        if cand in LANGUAGES:
            return {"detected": cand, "ambiguous": False, "candidates": [cand]}
    m_first = re.search(r"(?:L1|mother\s+tongue|first\s+language)\s+is\s+([a-zA-Z]+)", text_l)
    if m_first:
        cand = m_first.group(1).strip()
        if cand in LANGUAGES:
            return {"detected": cand, "ambiguous": False, "candidates": [cand]}
    m_home = re.search(r"speak\s+(\w+)\s+at\s+home", text_l)
    if m_home:
        cand = m_home.group(1)
        if cand in LANGUAGES:
            return {"detected": cand, "ambiguous": False, "candidates": [cand]}
    m_native2 = re.search(r"native\s+(\w+)\s+speaker", text_l)
    if m_native2:
        cand = m_native2.group(1)
        if cand in LANGUAGES:
            return {"detected": cand, "ambiguous": False, "candidates": [cand]}
    # "native english", "native spanish" (adjective form, not "is X")
    m_native_adj = re.search(r"\bnative\s+([a-zA-Z]+)\b", text_l)
    if m_native_adj:
        cand = m_native_adj.group(1).strip()
        if cand in LANGUAGES:
            return {"detected": cand, "ambiguous": False, "candidates": [cand]}
    # implicit: if brief mentions no native language and the only language mentioned is the target,
    # default to English (most common L1 of self-directed language learners in this format).
    return {"detected": "english", "ambiguous": False, "candidates": ["english"], "defaulted": True}


def detect_level(text: str) -> dict[str, Any]:
    """Detect CEFR level by keyword density. Explicit CEFR letter wins."""
    text_l = text.lower()
    # explicit CEFR letter (e.g., "I'm at B2", "currently A1")
    explicit_match = re.search(r"\b(?:at|currently|level|i'?m|i am|around)\s+(a[012]|b[12]|c[12])\b", text_l)
    if not explicit_match:
        explicit_match = re.search(r"\b(a[012]|b[12]|c[12])\s+(?:level|now|today|currently)\b", text_l)
    scores: Counter[str] = Counter()
    for level, keywords in LEVEL_KEYWORDS.items():
        for kw in keywords:
            if kw in text_l:
                if len(kw.split()) > 1:
                    scores[level] += 2
                else:
                    scores[level] += 1
    if not scores:
        if explicit_match:
            return {"detected": explicit_match.group(1).lower(), "confidence": "high", "signals": {}}
        return {"detected": "a0", "confidence": "low", "signals": []}
    # if explicit CEFR letter is present in caption ("currently A1/2"), use that
    if explicit_match:
        return {"detected": explicit_match.group(1).lower(), "confidence": "high", "signals": dict(scores)}
    detected = scores.most_common(1)[0][0]
    confidence = "high" if scores[detected] >= 3 else ("medium" if scores[detected] >= 2 else "low")
    return {"detected": detected, "confidence": confidence, "signals": dict(scores)}


def detect_target_level(text: str, current_level: str) -> dict[str, Any]:
    """Detect target CEFR level. Default = +1 level from current (capped at c2)."""
    text_l = text.lower()
    order = ["a0", "a1", "a2", "b1", "b2", "c1", "c2"]
    # explicit — look for 'reach/target/to X' or 'X in N months' where X is a level
    for level in order:
        for pat in [
            rf"\breach\s+{level}\b", rf"\btarget\s+{level}\b",
            rf"\buntil\s+{level}\b", rf"\bto\s+{level}\b",
            rf"\b{level}\s+conversation\b", rf"\b{level}\s+level\b",
            rf"\b{level}\s+in\s+\d", rf"\bin\s+\d+[^\n]{{0,20}}\b{level}\b",
            rf"\b{level}\s+by\s+",
        ]:
            if re.search(pat, text_l):
                return {"detected": level, "explicit": True}
    # fallback: +1
    if current_level in order:
        idx = order.index(current_level)
        new_idx = min(idx + 1, len(order) - 1)
        return {"detected": order[new_idx], "explicit": False}
    return {"detected": "b1", "explicit": False}


def detect_goals(text: str) -> dict[str, Any]:
    text_l = text.lower()
    hits: Counter[str] = Counter()
    for goal, keywords in GOAL_KEYWORDS.items():
        for kw in keywords:
            if kw in text_l:
                hits[goal] += 1
    return {"detected": [g for g, _ in hits.most_common()], "scores": dict(hits)}


def detect_constraints(text: str) -> dict[str, Any]:
    text_l = text.lower()
    hits: list[str] = []
    for constraint, keywords in CONSTRAINT_KEYWORDS.items():
        if any(kw in text_l for kw in keywords):
            hits.append(constraint)
    return {"detected": hits}


def detect_styles(text: str) -> dict[str, Any]:
    text_l = text.lower()
    hits: list[str] = []
    for style, keywords in STYLE_KEYWORDS.items():
        if any(kw in text_l for kw in keywords):
            hits.append(style)
    return {"detected": hits}


def detect_weekly_hours(text: str) -> dict[str, Any]:
    """Extract weekly study hours; default 7 if not specified."""
    text_l = text.lower()
    # explicit hours per week
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hrs|hours|hr)\s*(?:a|per)\s*week", text_l)
    if m:
        return {"hours": float(m.group(1)), "explicit": True}
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hrs|hours|hr)\b", text_l)
    if m:
        # if just "10 hours", assume weekly unless "a day"
        if "day" in text_l or "daily" in text_l:
            return {"hours": float(m.group(1)) * 7, "explicit": False}
        return {"hours": float(m.group(1)), "explicit": True}
    # 30 min/day → ~3.5
    m = re.search(r"(\d+)\s*(?:min|minutes)\s*(?:a|per)\s*day", text_l)
    if m:
        return {"hours": (float(m.group(1)) * 7) / 60, "explicit": False}
    # qualitative
    qual_map = [
        ("casual", 2), ("hobby", 2), ("a few hours", 3), ("part-time", 5),
        ("regular", 7), ("serious", 10), ("intensive", 15), ("full-time", 30),
        ("immersion-style", 25), ("full immersion", 35),
    ]
    for kw, h in qual_map:
        if kw in text_l:
            return {"hours": h, "explicit": False, "qualitative": kw}
    return {"hours": 7, "explicit": False, "qualitative": "default"}


def detect_horizon(text: str) -> dict[str, Any]:
    """Extract time horizon in months."""
    text_l = text.lower()
    m = re.search(r"(\d+)\s*(?:month|months|mo)\b", text_l)
    if m:
        return {"months": int(m.group(1)), "explicit": True}
    m = re.search(r"(\d+)\s*(?:year|years|yr)\b", text_l)
    if m:
        return {"months": int(m.group(1)) * 12, "explicit": True}
    if "deadline" in text_l or "by next" in text_l or "before" in text_l:
        return {"months": 6, "explicit": False, "qualitative": "deadline"}
    return {"months": 12, "explicit": False, "qualitative": "default"}


def detect_motivation(text: str) -> dict[str, Any]:
    """Detect motivation strength signals."""
    text_l = text.lower()
    strong_kw = ["must", "have to", "need to", "essential", "critical", "deadline",
                 "moving", "expat", "career", "promotion"]
    medium_kw = ["want to", "would like", "planning to", "thinking about", "should"]
    weak_kw = ["curious", "maybe", "no real reason", "just for fun", "hobby"]
    if any(kw in text_l for kw in strong_kw):
        return {"strength": "strong", "label": "Motivated by necessity"}
    if any(kw in text_l for kw in medium_kw):
        return {"strength": "medium", "label": "Motivated by intention"}
    if any(kw in text_l for kw in weak_kw):
        return {"strength": "weak", "label": "Casual interest"}
    return {"strength": "medium", "label": "Motivated by intention"}


def detect_prior_exposure(text: str) -> dict[str, Any]:
    """Detect prior exposure (classroom, family, media)."""
    text_l = text.lower()
    flags = []
    if any(kw in text_l for kw in ["took classes", "in school", "high school", "college class",
                                    "university course", "studied in school"]):
        flags.append("classroom")
    if any(kw in text_l for kw in ["grandparents", "parents spoke", "family", "grew up hearing"]):
        flags.append("family")
    if any(kw in text_l for kw in ["watch shows", "watched anime", "k-drama", "movies in",
                                    "music", "songs", "media"]):
        flags.append("media")
    return {"flags": flags}


def detect_family_relationship(text: str) -> dict[str, Any]:
    """Detect any same-family native or known language."""
    text_l = text.lower()
    known: list[str] = []
    target_lang = None  # caller passes text; we re-detect target
    target = detect_language(text)
    target_name = target.get("detected")
    target_family = LANGUAGES.get(target_name, {}).get("family") if target_name else None
    if not target_family:
        return {"known": known, "family": None}
    for lang_name, meta in LANGUAGES.items():
        if lang_name == target_name:
            continue
        if meta["family"] == target_family:
            known.append(lang_name)
    return {"known": known, "family": target_family}


# --------------------------- roadmap construction ------------------------------

def select_phases(current: str, target: str) -> list[dict[str, Any]]:
    """Pick the right phase blocks based on current and target CEFR.

    Phase keys are pairs of CEFR levels (e.g., 'a0_a1' = transition from A0 to A1).
    A learner at A0 targeting B1 needs phases a0_a1, a1_a2, a2_b1.
    """
    order = ["a0", "a1", "a2", "b1", "b2", "c1", "c2"]
    if current not in order or target not in order:
        return []
    ci, ti = order.index(current), order.index(target)
    keys_in_order = ["a0_a1", "a1_a2", "a2_b1", "b1_b2", "b2_c1", "c1_c2"]
    phases: list[dict[str, Any]] = []
    for idx, key in enumerate(keys_in_order):
        # Phase 'a0_a1' is the transition into A1, so a learner at A0 needs it.
        # Index 0 (a0_a1) covers the band from A0 to A1.
        if ci <= idx <= ti:
            phases.extend(CEFR_PHASES[key])
    # fallback: if current == target and no phases matched (shouldn't happen), include phase 0
    if not phases:
        if current == "a0":
            phases = CEFR_PHASES["a0_a1"]
        elif current in order:
            phases = CEFR_PHASES[keys_in_order[min(order.index(current), len(keys_in_order) - 1)]]
    return phases


def estimate_phase_weeks(phase: dict[str, Any], lang_meta: dict[str, Any],
                         weekly_hours: float, target_level: str) -> int:
    """Estimate weeks for a phase based on weekly hours and difficulty."""
    base_weeks = (phase["weeks_lo"] + phase["weeks_hi"]) / 2
    difficulty = lang_meta.get("difficulty", 2)
    # difficulty multiplier
    diff_mult = {1: 0.8, 2: 1.0, 3: 1.3, 4: 1.7}[difficulty]
    # hours multiplier (more hours = faster)
    if weekly_hours <= 0:
        hours_mult = 2.5
    elif weekly_hours < 3:
        hours_mult = 1.6
    elif weekly_hours < 7:
        hours_mult = 1.0
    elif weekly_hours < 14:
        hours_mult = 0.65
    elif weekly_hours < 25:
        hours_mult = 0.45
    else:
        hours_mult = 0.3
    weeks = base_weeks * diff_mult * hours_mult
    return max(2, round(weeks))


def build_vocab_waves(phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build SRS vocab waves across the full roadmap.

    Each phase's `vocab_target` is the CUMULATIVE end-of-phase vocabulary size.
    The total target is therefore `phases[-1]['vocab_target']`.
    """
    total_target = phases[-1]["vocab_target"] if phases else 1500
    waves = []
    for srs in SRS_WAVES:
        wave_size = int(total_target * srs["review_share"] * 0.4)
        waves.append({
            "name": srs["name"],
            "interval_days": srs["interval_days"],
            "review_share": srs["review_share"],
            "note": srs["note"],
            "approx_items_touched": wave_size,
        })
    waves.append({
        "name": "Cumulative target",
        "interval_days": None,
        "review_share": 1.0,
        "note": f"Total vocabulary to acquire by end of roadmap: ~{total_target} words",
        "approx_items_touched": total_target,
    })
    return waves


def select_immersion_tactics(level: str, styles: list[str],
                              goals: list[str]) -> list[dict[str, Any]]:
    """Pick immersion tactics appropriate for the level + style + goals.

    Returns up to 8 prioritized tactics. Tactics one level above the current
    CEFR are included as 'stretch' so beginners can see the path ahead.
    """
    order = {"a0": 0, "a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}
    floor = order.get(level, 0)
    selected = []
    for t in IMMERSION_TACTICS:
        t_floor = order.get(t["level_floor"], 0)
        if t_floor > floor + 1:
            continue
        if t_floor > floor:
            eligible = "stretch"
            default_priority = "medium"
        else:
            eligible = "fit"
            default_priority = "normal"
        if "anki" in styles and "SRS" in t.get("description", "") + t["name"]:
            t_priority = "high"
        elif "video" in styles and t["category"] in {"listening", "input"}:
            t_priority = "high"
        elif "music" in styles and t["category"] == "input":
            t_priority = "high"
        elif "reading" in styles and t["category"] == "reading":
            t_priority = "high"
        elif "tutor" in styles and t["category"] == "tutoring":
            t_priority = "high"
        elif "immersion" in styles and t["category"] in {"listening", "input", "reading"}:
            t_priority = "high"
        elif "conversational" in styles and t["category"] == "speaking":
            t_priority = "high"
        else:
            t_priority = default_priority
        if "exam" in goals and "writing" in t["category"]:
            t_priority = "high" if t_priority == "high" else "medium"
        if "media" in goals and t["category"] in {"listening", "input"}:
            t_priority = "high" if t_priority == "high" else "medium"
        if "reading" in goals and t["category"] == "reading":
            t_priority = "high" if t_priority == "high" else "medium"
        selected.append({**t, "priority": t_priority, "eligibility": eligible})
    prio_order = {"high": 0, "medium": 1, "normal": 2}
    selected.sort(key=lambda x: (prio_order.get(x["priority"], 2), x["weekly_minutes"]))
    return selected[:8]


def compute_risk_flags(lang_meta: dict[str, Any], current: str, target: str,
                       weekly_hours: float, horizon_months: int,
                       constraints: list[str], motivation_strength: str,
                       native: str | None, family_known: list[str],
                       prior_exposure: list[str]) -> list[dict[str, str]]:
    flags = []
    difficulty = lang_meta.get("difficulty", 2)
    family = lang_meta.get("family", "")

    # ambition vs time
    order = {"a0": 0, "a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}
    level_jump = order.get(target, 3) - order.get(current, 0)
    weeks_available = horizon_months * 4.3
    # rough hours needed per level jump
    min_hours_needed = {1: 150, 2: 350, 3: 700, 4: 1200, 5: 1800, 6: 2400}.get(level_jump, 1500)
    if level_jump > 0 and weekly_hours * weeks_available < min_hours_needed * 0.7:
        flags.append({
            "code": "ambition_mismatch",
            "severity": "high" if weekly_hours * weeks_available < min_hours_needed * 0.5 else "medium",
            "label": f"Goal ({current}→{target}) typically requires ~{min_hours_needed} study hours; {weekly_hours:.1f} h/wk × {horizon_months} mo = ~{int(weekly_hours * weeks_available)} h. Either extend horizon, raise weekly hours, or lower target.",
        })
    # script difficulty
    if lang_meta.get("script") in {"hanzi", "mixed_jp", "arabic", "hebrew", "devanagari", "thai", "cyrillic", "greek"}:
        flags.append({
            "code": "new_script",
            "severity": "medium",
            "label": f"Target uses {lang_meta['script']} script. Plan 30-50 extra hours for character recognition in phase 1-2.",
        })
    if lang_meta.get("tonal"):
        flags.append({
            "code": "tonal",
            "severity": "medium",
            "label": "Target is tonal. Daily pitch-pair drills in phase 1-3 strongly recommended; without them listening plateaus at B1.",
        })
    if lang_meta.get("cases", 0) >= 4:
        flags.append({
            "code": "many_cases",
            "severity": "medium",
            "label": f"Target has {lang_meta['cases']} grammatical cases (e.g., declensions). Schedule extra pattern drills from Phase 4 onward.",
        })
    if weekly_hours < 3:
        flags.append({
            "code": "low_volume",
            "severity": "high",
            "label": f"Only {weekly_hours:.1f} h/wk — below the threshold for steady progress. Even 30 min/day compounds meaningfully.",
        })
    if "busy" in constraints:
        flags.append({
            "code": "time_constrained",
            "severity": "medium",
            "label": "Time-constrained plan: rely on micro-habits (5-10 min Anki + 10 min podcast commute + weekly lesson).",
        })
    if "no_tutor" in constraints and level_jump >= 2:
        flags.append({
            "code": "self_study_gap",
            "severity": "medium",
            "label": "Self-study + multi-level jump: leverage free correction tools (LangCorrect, HiNative) and weekly tandem calls.",
        })
    if "no_immersion" in constraints:
        flags.append({
            "code": "no_native_input",
            "severity": "medium",
            "label": "No native speakers nearby: compensate with heavy podcast/YouTube/news input. Aim for 60+ min/day listening.",
        })
    if "low_budget" in constraints:
        flags.append({
            "code": "low_budget",
            "severity": "low",
            "label": "Free path: use public library apps ( Libby, Kanopy), YouTube, podcasts, Anki, and free tandem communities.",
        })
    if motivation_strength == "weak" and level_jump >= 2:
        flags.append({
            "code": "weak_motivation",
            "severity": "medium",
            "label": "Casual motivation + ambitious jump: outcomes are usually plateau + dropout. Either pick a smaller milestone or attach the goal to a real commitment (trip / partner / project).",
        })
    if horizon_months < 6 and difficulty >= 3:
        flags.append({
            "code": "tight_deadline",
            "severity": "high",
            "label": f"Tight horizon ({horizon_months} mo) + difficult language ({family}). Realistic expectation = survival / A2, not fluency. Plan a 'phase-1' milestone.",
        })
    if family_known and not native:
        flags.append({
            "code": "family_boost",
            "severity": "low",
            "label": f"Family boost available: you already know {', '.join(family_known[:3])}. Cognate spillover should accelerate reading by 15-25%.",
        })
    if "family" in prior_exposure and current == "a0":
        flags.append({
            "code": "heritage_low",
            "severity": "low",
            "label": "Family/heritage exposure often means receptive skill (listening) is ahead of productive skill (speaking). Test both separately.",
        })
    if lang_meta.get("writing_dir") == "rtl" and not native:
        flags.append({
            "code": "rtl_script",
            "severity": "low",
            "label": "Right-to-left script: first 1-2 weeks feel slow due to layout shift; expect adaptive trajectory.",
        })
    if native and LANGUAGES.get(native, {}).get("family") == lang_meta.get("family"):
        flags.append({
            "code": "same_family_native",
            "severity": "low",
            "label": f"Native language ({native}) is in the same family ({family}). Expect 20-40% faster grammar acquisition.",
        })
    return flags


def build_roadmap(text: str) -> dict[str, Any]:
    """Run the full detection + roadmap construction pipeline."""
    target = detect_language(text)
    lang_meta = target.get("meta", {})
    native = detect_native(text)
    level = detect_level(text)
    target_level = detect_target_level(text, level["detected"])
    goals = detect_goals(text)
    constraints = detect_constraints(text)
    styles = detect_styles(text)
    hours = detect_weekly_hours(text)
    horizon = detect_horizon(text)
    motivation = detect_motivation(text)
    prior = detect_prior_exposure(text)
    family_rel = detect_family_relationship(text)

    if not target.get("detected"):
        return {"error": "Could not detect target language. Please name the language you're learning (e.g., 'learning Spanish', 'studying Mandarin').",
                "target": target, "level": level, "goals": goals}

    phases = select_phases(level["detected"], target_level["detected"])
    if not phases:
        return {"error": "Could not construct phases — please specify current and target level more clearly.",
                "target": target, "level": level}

    # per-phase weeks
    detailed_phases = []
    cumulative_weeks = 0
    for p in phases:
        w = estimate_phase_weeks(p, lang_meta, hours["hours"], target_level["detected"])
        cumulative_weeks += w
        detailed_phases.append({
            **p,
            "est_weeks": w,
            "est_hours": round(w * hours["hours"]),
        })

    vocab_waves = build_vocab_waves(phases)
    immersion = select_immersion_tactics(level["detected"], styles["detected"], goals["detected"])
    landmarks = CULTURAL_LANDMARKS.get(lang_meta.get("family", ""), [])

    # total weekly minutes from immersion tactics
    weekly_minutes = sum(t["weekly_minutes"] for t in immersion[:6])

    # feasibility check
    weeks_needed = cumulative_weeks
    weeks_available = horizon["months"] * 4.3
    feasibility = "fits" if weeks_needed <= weeks_available else (
        "tight" if weeks_needed <= weeks_available * 1.25 else "unrealistic"
    )

    # risk flags
    flags = compute_risk_flags(lang_meta, level["detected"], target_level["detected"],
                                hours["hours"], horizon["months"], constraints["detected"],
                                motivation["strength"], native.get("detected"),
                                family_rel["known"], prior["flags"])

    # build weekly hour split suggestion
    hour_split = build_hour_split(weekly_minutes, hours["hours"] * 60, styles["detected"])

    # readiness score 0-100
    score, axes, verdict = compute_readiness(
        level=level, target_level=target_level, hours=hours, horizon=horizon,
        constraints=constraints, motivation=motivation, prior=prior,
        weeks_needed=weeks_needed, weeks_available=weeks_available,
        immersion=immersion, family_known=family_rel["known"],
        target_meta=lang_meta, native=native.get("detected"),
        goals=goals, styles=styles, flags=flags,
    )

    return {
        "profile": {
            "target_language": target["detected"],
            "target_meta": lang_meta,
            "native_language": native.get("detected"),
            "current_level": level["detected"],
            "level_confidence": level["confidence"],
            "target_level": target_level["detected"],
            "target_level_explicit": target_level["explicit"],
            "goals": goals["detected"],
            "constraints": constraints["detected"],
            "styles": styles["detected"],
            "weekly_hours": hours["hours"],
            "weekly_hours_explicit": hours["explicit"],
            "horizon_months": horizon["months"],
            "horizon_explicit": horizon["explicit"],
            "motivation": motivation,
            "prior_exposure": prior["flags"],
            "family_known": family_rel["known"],
            "family": family_rel["family"],
        },
        "phases": detailed_phases,
        "vocab_waves": vocab_waves,
        "immersion": immersion,
        "cultural_landmarks": landmarks,
        "hour_split": hour_split,
        "feasibility": feasibility,
        "weeks_needed": round(weeks_needed),
        "weeks_available": round(weeks_available),
        "risk_flags": flags,
        "readiness_score": score,
        "readiness_axes": axes,
        "readiness_verdict": verdict,
    }


def build_hour_split(total_immersion_minutes: int, total_minutes: int,
                     styles: list[str]) -> dict[str, Any]:
    """Suggest a weekly hour split across input/output/study/SRS."""
    if total_minutes <= 0:
        return {"distribution": {}, "note": "No hours specified"}
    # baseline
    base = {
        "input (listening + reading)": 0.45,
        "output (speaking + writing)": 0.25,
        "study (grammar + vocab acquisition)": 0.20,
        "review (SRS + spaced recall)": 0.10,
    }
    # style bias
    if "conversational" in styles:
        base["output (speaking + writing)"] += 0.10
        base["input (listening + reading)"] -= 0.05
        base["study (grammar + vocab acquisition)"] -= 0.05
    if "structured" in styles:
        base["study (grammar + vocab acquisition)"] += 0.10
        base["output (speaking + writing)"] -= 0.05
        base["input (listening + reading)"] -= 0.05
    if "anki" in styles:
        base["review (SRS + spaced recall)"] += 0.10
        base["study (grammar + vocab acquisition)"] -= 0.10
    if "immersion" in styles:
        base["input (listening + reading)"] += 0.10
        base["study (grammar + vocab acquisition)"] -= 0.10
    if "reading" in styles:
        base["input (listening + reading)"] += 0.05
        base["output (speaking + writing)"] -= 0.05
    # clamp
    for k, v in base.items():
        base[k] = max(0.05, min(0.65, v))
    # normalize
    total = sum(base.values())
    for k, v in base.items():
        base[k] = v / total
    distribution = {k: round(total_minutes * v) for k, v in base.items()}
    return {"distribution": distribution, "minutes_total": int(total_minutes), "note": "Weekly minute split tuned to your stated style."}


def compute_readiness(level: dict, target_level: dict, hours: dict, horizon: dict,
                      constraints: dict, motivation: dict, prior: dict,
                      weeks_needed: float, weeks_available: float,
                      immersion: list, family_known: list[str],
                      target_meta: dict, native: str | None,
                      goals: dict, styles: dict, flags: list) -> tuple[int, dict, str]:
    """0-100 path-readiness score across weighted axes."""
    axes = {}

    # 1. Profile completeness (15%) — we detected enough fields
    profile_fields = [
        bool(target_meta), level["confidence"] != "low",
        bool(goals["detected"]), bool(hours["explicit"] or hours.get("qualitative")),
        bool(horizon["explicit"] or horizon.get("qualitative")),
        bool(styles["detected"]), bool(prior["flags"] or motivation.get("strength")),
    ]
    axes["profile_completeness"] = round(sum(1.0 for f in profile_fields if f) / len(profile_fields) * 100)
    weights = {"profile_completeness": 0.15}

    # 2. Time feasibility (20%) — hours × horizon vs estimated need
    hours_ratio = (hours["hours"] * weeks_available) / max(weeks_needed * hours["hours"], 1)
    if hours_ratio >= 1.2:
        axes["time_feasibility"] = 100
    elif hours_ratio >= 0.95:
        axes["time_feasibility"] = 85
    elif hours_ratio >= 0.75:
        axes["time_feasibility"] = 65
    elif hours_ratio >= 0.5:
        axes["time_feasibility"] = 45
    else:
        axes["time_feasibility"] = 25
    weights["time_feasibility"] = 0.20

    # 3. Plan density (15%) — number of phases + immersion tactics
    n_phases = sum(1 for _ in immersion) if immersion else 0
    plan_density = min(100, (n_phases / 5) * 100)
    axes["plan_density"] = round(plan_density)
    weights["plan_density"] = 0.15

    # 4. Style fit (15%) — alignment of immersion to detected style
    style_fit = 60  # base
    if "anki" in styles["detected"]:
        style_fit += 10  # any plan should include SRS
    if "conversational" in styles["detected"]:
        style_fit += 8 if any(t["category"] == "speaking" for t in immersion) else -10
    if "reading" in styles["detected"]:
        style_fit += 8 if any(t["category"] == "reading" for t in immersion) else -10
    if "immersion" in styles["detected"]:
        style_fit += 8 if any(t["category"] in {"listening", "input"} for t in immersion) else -10
    if "tutor" in styles["detected"]:
        style_fit += 8 if any(t["category"] == "tutoring" for t in immersion) else -10
    if "music" in styles["detected"]:
        style_fit += 5 if any(t["category"] == "input" for t in immersion) else -5
    axes["style_fit"] = max(0, min(100, style_fit))
    weights["style_fit"] = 0.15

    # 5. Goal alignment (15%) — immersion tactics + phases cover stated goal
    goal_alignment = 60
    if "travel" in goals["detected"]:
        goal_alignment += 10 if any(t["level_floor"] in {"a0", "a1"} for t in immersion) else 0
    if "conversation" in goals["detected"] or "relocation" in goals["detected"]:
        goal_alignment += 10 if any(t["category"] == "speaking" for t in immersion) else 0
    if "reading" in goals["detected"] or "media" in goals["detected"]:
        goal_alignment += 10 if any(t["category"] in {"reading", "listening"} for t in immersion) else 0
    if "exam" in goals["detected"]:
        goal_alignment += 10 if any(t["category"] == "writing" for t in immersion) else 0
    if "career" in goals["detected"]:
        goal_alignment += 8 if any(t["category"] in {"tutoring", "writing"} for t in immersion) else 0
    axes["goal_alignment"] = max(0, min(100, goal_alignment))
    weights["goal_alignment"] = 0.15

    # 6. Risk hygiene (20%) — fewer high-severity flags = higher
    high_flags = sum(1 for f in flags if f["severity"] == "high")
    medium_flags = sum(1 for f in flags if f["severity"] == "medium")
    risk_score = max(0, 100 - (high_flags * 25) - (medium_flags * 10))
    axes["risk_hygiene"] = risk_score
    weights["risk_hygiene"] = 0.20

    # weighted total
    total = sum(axes[k] * weights[k] for k in axes)
    score = round(total)

    # verdict bands
    if score >= 85:
        verdict = "ready_to_roll"
    elif score >= 70:
        verdict = "mostly_ready"
    elif score >= 55:
        verdict = "needs_tuning"
    elif score >= 40:
        verdict = "needs_work"
    else:
        verdict = "plan_revise"

    return score, axes, verdict


def to_markdown(result: dict[str, Any]) -> str:
    """Render roadmap as a one-page Markdown brief."""
    if "error" in result:
        return f"# polyglot-pathforge\n\n**Error:** {result['error']}\n"
    p = result["profile"]
    lines = []
    lines.append("# Language Learning Roadmap")
    lines.append("")
    lines.append(f"**Target:** {p['target_language']} ({p['target_meta'].get('family', '?')} family, "
                 f"difficulty {p['target_meta'].get('difficulty', '?')}/4)  ")
    lines.append(f"**Native:** {p.get('native_language') or 'unspecified'}  ")
    lines.append(f"**Current level:** {p['current_level'].upper()} (confidence: {p['level_confidence']})  ")
    lines.append(f"**Target level:** {p['target_level'].upper()}  ")
    lines.append(f"**Time budget:** {p['weekly_hours']:.1f} h/week × {p['horizon_months']} months  ")
    if p.get('goals'):
        lines.append(f"**Goals:** {', '.join(p['goals'])}  ")
    if p.get('styles'):
        lines.append(f"**Style:** {', '.join(p['styles'])}  ")
    if p.get('constraints'):
        lines.append(f"**Constraints:** {', '.join(p['constraints'])}  ")
    lines.append(f"**Motivation:** {p['motivation']['label']}  ")
    if p.get('family_known'):
        lines.append(f"**Family boost:** {', '.join(p['family_known'])} (same family)  ")
    lines.append("")
    lines.append(f"## Feasibility: {result['feasibility'].upper()}")
    lines.append(f"~{result['weeks_needed']} weeks needed vs ~{result['weeks_available']} weeks available.")
    lines.append("")
    lines.append(f"## Path Readiness: {result['readiness_score']}/100 → {result['readiness_verdict'].replace('_', ' ').upper()}")
    for axis, score in result['readiness_axes'].items():
        lines.append(f"- **{axis.replace('_', ' ').title()}**: {score}/100")
    lines.append("")
    lines.append("## Phase Roadmap")
    for i, ph in enumerate(result["phases"], 1):
        lines.append(f"### {i}. {ph['name']}")
        lines.append(f"- **Focus:** {ph['focus']}")
        lines.append(f"- **Est. duration:** {ph['est_weeks']} weeks (~{ph['est_hours']} h)")
        lines.append(f"- **Grammar topics:** {', '.join(ph['grammar'])}")
        lines.append(f"- **Vocab target:** {ph['vocab_target']} words")
        lines.append(f"- **Milestone:** {ph['milestone']}")
    lines.append("")
    lines.append("## Weekly Hour Split")
    for k, mins in result["hour_split"]["distribution"].items():
        lines.append(f"- {k}: {mins} min/wk")
    lines.append("")
    lines.append("## Immersion Tactics (ranked)")
    for t in result["immersion"]:
        prio_marker = "🔥" if t["priority"] == "high" else ("·" if t["priority"] == "medium" else " ")
        lines.append(f"- {prio_marker} **{t['name']}** ({t['weekly_minutes']} min/wk) — {t['description']}")
    lines.append("")
    lines.append("## SRS Vocab Waves")
    for w in result["vocab_waves"]:
        if w["interval_days"] is None:
            lines.append(f"- **{w['name']}**: {w['approx_items_touched']} words total")
        else:
            lines.append(f"- **{w['name']}** (every {w['interval_days']}d, ~{int(w['review_share']*100)}% of items): {w['note']}")
    lines.append("")
    if result["cultural_landmarks"]:
        lines.append("## Cultural Landmarks")
        for c in result["cultural_landmarks"]:
            lines.append(f"- **{c['type']}**: {c['item']}")
        lines.append("")
    if result["risk_flags"]:
        lines.append("## Risk Flags")
        for f in result["risk_flags"]:
            lines.append(f"- **[{f['severity'].upper()}]** {f['label']}")
        lines.append("")
    return "\n".join(lines)


# ----------------------------- database setup -----------------------------------

def get_db() -> sqlite3.Connection:
    db = getattr(g, "_db", None)
    if db is None:
        db = sqlite3.connect(str(DB_PATH))
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g._db = db
    return db


@app.teardown_appcontext
def close_db(exception: Any = None) -> None:
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            brief TEXT NOT NULL,
            target_language TEXT,
            current_level TEXT,
            target_level TEXT,
            readiness_score INTEGER,
            verdict TEXT,
            feasibility TEXT,
            rating INTEGER,
            notes TEXT,
            result_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ----------------------------- routes ------------------------------------------

@app.route("/")
def index() -> Any:
    return render_template("index.html")


@app.route("/api/roadmap", methods=["POST"])
def api_roadmap() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    brief = (payload.get("brief") or "").strip()
    if not brief:
        return jsonify({"error": "Brief is required."}), 400
    result = build_roadmap(brief)
    if "error" in result:
        return jsonify(result), 400
    return jsonify({
        "result": result,
        "markdown": to_markdown(result),
    })


@app.route("/api/sessions", methods=["POST"])
def api_save_session() -> Any:
    payload = request.get_json(force=True, silent=True) or {}
    brief = (payload.get("brief") or "").strip()
    result = payload.get("result") or {}
    rating = payload.get("rating")
    notes = payload.get("notes") or ""
    if not brief or "error" in result:
        return jsonify({"error": "Brief + result required."}), 400
    profile = result.get("profile", {})
    db = get_db()
    cur = db.execute(
        """INSERT INTO sessions (created_at, brief, target_language, current_level, target_level,
            readiness_score, verdict, feasibility, rating, notes, result_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now(timezone.utc).isoformat(), brief,
         profile.get("target_language"), profile.get("current_level"),
         profile.get("target_level"), result.get("readiness_score"),
         result.get("readiness_verdict"), result.get("feasibility"),
         rating, notes, json.dumps(result)),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid})


@app.route("/api/sessions", methods=["GET"])
def api_list_sessions() -> Any:
    db = get_db()
    rows = db.execute(
        """SELECT id, created_at, target_language, current_level, target_level,
                  readiness_score, verdict, feasibility, rating, notes
           FROM sessions ORDER BY id DESC LIMIT 50"""
    ).fetchall()
    return jsonify({"sessions": [dict(r) for r in rows]})


@app.route("/api/sessions/<int:sid>", methods=["GET"])
def api_get_session(sid: int) -> Any:
    db = get_db()
    row = db.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404
    rec = dict(row)
    rec["result"] = json.loads(rec.pop("result_json"))
    return jsonify(rec)


@app.route("/api/sessions/<int:sid>", methods=["DELETE"])
def api_delete_session(sid: int) -> Any:
    db = get_db()
    db.execute("DELETE FROM sessions WHERE id = ?", (sid,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/languages")
def api_languages() -> Any:
    return jsonify({"languages": sorted(LANGUAGES.keys())})


# ----------------------------- main --------------------------------------------

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5130))
    app.run(host="127.0.0.1", port=port, debug=False)
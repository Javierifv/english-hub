import os
import re
import json
import sqlite3
import random
import urllib.request
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify
from database import get_db, init_db

# Load environment variables from .env
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

load_env()

app = Flask(__name__)
app.secret_key = "duohub-english-training-key"

# Ensure DB initialized
init_db()

# Common English false friends and preposition error heuristics for instant fallback
COMMON_GRAMMAR_RULES = [
    {
        "pattern": r"\bdepend\s+of\b",
        "replacement": "depend on",
        "explanation": "In English, we say 'depend on', not 'depend of'."
    },
    {
        "pattern": r"\bexplain\s+me\b",
        "replacement": "explain to me",
        "explanation": "The verb 'explain' requires the preposition 'to' before the person ('explain to me')."
    },
    {
        "pattern": r"\blisten\s+(the|a|music|to\s+music)\b",
        "replacement": "listen to",
        "explanation": "Always remember 'listen to' when an object follows ('listen to music', 'listen to the audio')."
    },
    {
        "pattern": r"\barrive\s+to\b",
        "replacement": "arrive at / arrive in",
        "explanation": "We say 'arrive at (a place)' or 'arrive in (a city/country)', not 'arrive to'."
    },
    {
        "pattern": r"\bcongratulate\s+for\b",
        "replacement": "congratulate on",
        "explanation": "In English, we 'congratulate someone ON' their achievement."
    },
    {
        "pattern": r"\b(he|she|it)\s+have\b",
        "replacement": "\\1 has",
        "explanation": "Third-person singular takes 'has' instead of 'have'."
    },
    {
        "pattern": r"\b(they|we|you)\s+is\b",
        "replacement": "\\1 are",
        "explanation": "Plural subjects take 'are', not 'is'."
    },
    {
        "pattern": r"\b(he|she|it)\s+don't\b",
        "replacement": "\\1 doesn't",
        "explanation": "Third-person singular uses 'doesn't' instead of 'don't'."
    },
    {
        "pattern": r"\bi\s+am\s+agree\b",
        "replacement": "I agree",
        "explanation": "'Agree' is a verb in English: use 'I agree', not 'I am agree'."
    },
    {
        "pattern": r"\bpeople\s+is\b",
        "replacement": "people are",
        "explanation": "'People' is plural in English and takes 'are'."
    }
]

def call_gemini_api(prompt_text, response_mime_type="application/json"):
    """
    Calls Google Gemini Flash API with cascade across free-tier flash models
    to ensure high availability.
    """
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None

    models_to_try = [
        "gemini-flash-latest",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash"
    ]

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "temperature": 0.2
        }
    }
    if response_mime_type == "application/json":
        payload["generationConfig"]["response_mime_type"] = "application/json"

    data_bytes = json.dumps(payload).encode("utf-8")

    for model_name in models_to_try:
        try:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            req = urllib.request.Request(
                api_url,
                data=data_bytes,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=14) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            continue

    return None

def calculate_streak(user_id, today_str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, completed_count FROM daily_logs
        WHERE user_id = ? AND completed_count >= 3
        ORDER BY date DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return 0

    dates = {r["date"] for r in rows}
    current = datetime.strptime(today_str, "%Y-%m-%d").date()
    
    # If today is not completed yet, check if yesterday was part of a continuous streak
    streak = 0
    test_date = current
    if test_date.isoformat() not in dates:
        test_date = current - timedelta(days=1)

    while test_date.isoformat() in dates:
        streak += 1
        test_date -= timedelta(days=1)

    return streak

@app.route("/")
def index():
    return render_template("index.html")

# --- API: Users & Switch ---

@app.route("/api/users", methods=["GET"])
def get_users():
    conn = get_db()
    users = conn.execute("""
        SELECT id, username, display_name, avatar_color, words_per_day, selection_mode 
        FROM users ORDER BY id ASC
    """).fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route("/api/users/profile", methods=["POST"])
def update_profile():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    display_name = (data.get("display_name") or "").strip()
    words_per_day = int(data.get("words_per_day", 5))
    selection_mode = data.get("selection_mode", "progressive")
    pin = data.get("pin", "1234")

    conn = get_db()
    cursor = conn.cursor()
    if display_name:
        cursor.execute("""
            UPDATE users 
            SET display_name = ?, words_per_day = ?, selection_mode = ?, pin = ?
            WHERE id = ?
        """, (display_name, words_per_day, selection_mode, pin, user_id))
    else:
        cursor.execute("""
            UPDATE users 
            SET words_per_day = ?, selection_mode = ?
            WHERE id = ?
        """, (words_per_day, selection_mode, user_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/status", methods=["GET"])
def get_status():
    user_id = request.args.get("user_id", default=1, type=int)
    today_str = request.args.get("date", default=date.today().isoformat())
    day_number = request.args.get("day", default=1, type=int)

    conn = get_db()
    cursor = conn.cursor()

    # Get active user info
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    active_user = dict(cursor.fetchone() or {})

    # Get or create daily log for user
    cursor.execute("SELECT * FROM daily_logs WHERE user_id = ? AND date = ?", (user_id, today_str))
    log = cursor.fetchone()

    if not log:
        cursor.execute("""
            INSERT INTO daily_logs (user_id, date, day_number)
            VALUES (?, ?, ?)
        """, (user_id, today_str, day_number))
        conn.commit()
        cursor.execute("SELECT * FROM daily_logs WHERE user_id = ? AND date = ?", (user_id, today_str))
        log = cursor.fetchone()

    # Get partner's status for accountability & read-only preview
    cursor.execute("SELECT id, display_name FROM users WHERE id != ?", (user_id,))
    partner = cursor.fetchone()

    partner_status = None
    if partner:
        cursor.execute("""
            SELECT completed_count, vocab_done, reading_done, reading_summary, reading_feedback, 
                   listening_done, shadowing_done, speaking_done 
            FROM daily_logs WHERE user_id = ? AND date = ?
        """, (partner["id"], today_str))
        p_log = cursor.fetchone()
        partner_status = {
            "id": partner["id"],
            "name": partner["display_name"],
            "completed_count": p_log["completed_count"] if p_log else 0,
            "tasks": dict(p_log) if p_log else {
                "vocab_done": 0, "reading_done": 0, "listening_done": 0, "shadowing_done": 0, "speaking_done": 0
            }
        }

    streak = calculate_streak(user_id, today_str)

    # Get total vocabulary count & max days
    cursor.execute("SELECT COUNT(*), MAX(day_number) FROM vocabulary")
    total_words, max_days = cursor.fetchone()

    conn.close()
    return jsonify({
        "user": active_user,
        "log": dict(log),
        "streak": streak,
        "partner": partner_status,
        "max_days": max_days or 100,
        "total_words": total_words or 500,
        "today_str": today_str
    })

# --- API: Module 1 - Vocabulary (Configurable, SRS & Shared Sentences) ---

@app.route("/api/vocab", methods=["GET"])
def get_vocab():
    day_number = request.args.get("day", default=1, type=int)
    user_id = request.args.get("user_id", default=1, type=int)
    
    conn = get_db()
    cursor = conn.cursor()

    # Get user settings
    cursor.execute("SELECT words_per_day, selection_mode FROM users WHERE id = ?", (user_id,))
    u_row = cursor.fetchone()
    count = u_row["words_per_day"] if u_row else 5
    mode = u_row["selection_mode"] if u_row else "progressive"

    # Allow query param override
    if request.args.get("count"):
        count = int(request.args.get("count"))
    if request.args.get("mode"):
        mode = request.args.get("mode")

    # Get partner ID
    cursor.execute("SELECT id, display_name FROM users WHERE id != ?", (user_id,))
    partner_row = cursor.fetchone()
    partner_id = partner_row["id"] if partner_row else (2 if user_id == 1 else 1)
    partner_name = partner_row["display_name"] if partner_row else "Compañero"

    # Selection query
    if mode == "random":
        # Deterministic random shuffle based on day_number so both partners get the same random words
        offset_seed = (day_number * 37) % 500
        words_query = """
            SELECT id, day_number, word, ipa, part_of_speech, translation, definition, example_en, example_es, category
            FROM vocabulary
            ORDER BY ((id * 31 + ?) % 534) ASC
            LIMIT ?
        """
        words = cursor.execute(words_query, (offset_seed, count)).fetchall()
    else:
        # Progressive order
        offset = max(0, (day_number - 1) * count)
        words_query = """
            SELECT id, day_number, word, ipa, part_of_speech, translation, definition, example_en, example_es, category
            FROM vocabulary
            ORDER BY id ASC
            LIMIT ? OFFSET ?
        """
        words = cursor.execute(words_query, (count, offset)).fetchall()

    results = []
    for w in words:
        w_dict = dict(w)
        # Fetch current user mastery and custom sentence
        cursor.execute("SELECT mastery_level, personal_sentence, review_count FROM user_word_progress WHERE user_id = ? AND word_id = ?", (user_id, w["id"]))
        u_prog = cursor.fetchone()
        w_dict["user_mastery"] = u_prog["mastery_level"] if u_prog else 1
        w_dict["user_sentence"] = u_prog["personal_sentence"] if u_prog else ""
        w_dict["review_count"] = u_prog["review_count"] if u_prog else 0

        # Fetch partner's custom sentence
        cursor.execute("SELECT personal_sentence FROM user_word_progress WHERE user_id = ? AND word_id = ?", (partner_id, w["id"]))
        p_prog = cursor.fetchone()
        w_dict["partner_sentence"] = p_prog["personal_sentence"] if p_prog and p_prog["personal_sentence"] else ""
        w_dict["partner_name"] = partner_name

        results.append(w_dict)

    conn.close()
    return jsonify(results)

@app.route("/api/vocab/rate-mastery", methods=["POST"])
def rate_mastery():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    word_id = data.get("word_id")
    rating = max(1, min(5, int(data.get("rating", 1))))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_word_progress (user_id, word_id, mastery_level, review_count, last_reviewed_at)
        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, word_id) DO UPDATE SET
            mastery_level = excluded.mastery_level,
            review_count = user_word_progress.review_count + 1,
            last_reviewed_at = CURRENT_TIMESTAMP
    """, (user_id, word_id, rating))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "rating": rating})

@app.route("/api/vocab/save-sentence", methods=["POST"])
def save_sentence():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    word_id = data.get("word_id")
    sentence = (data.get("sentence") or "").strip()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_word_progress (user_id, word_id, personal_sentence, last_reviewed_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, word_id) DO UPDATE SET
            personal_sentence = excluded.personal_sentence,
            last_reviewed_at = CURRENT_TIMESTAMP
    """, (user_id, word_id, sentence))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "sentence": sentence})

@app.route("/api/vocab/quiz", methods=["GET"])
def get_vocab_quiz():
    day_number = request.args.get("day", default=1, type=int)
    user_id = request.args.get("user_id", default=1, type=int)

    conn = get_db()
    cursor = conn.cursor()

    # Get today's words
    cursor.execute("SELECT words_per_day FROM users WHERE id = ?", (user_id,))
    u_row = cursor.fetchone()
    count = u_row["words_per_day"] if u_row else 5

    offset = max(0, (day_number - 1) * count)
    words = cursor.execute("SELECT id, word, translation, example_en FROM vocabulary ORDER BY id ASC LIMIT ? OFFSET ?", (count, offset)).fetchall()

    # Get random distractors
    all_translations = [r["translation"] for r in cursor.execute("SELECT translation FROM vocabulary ORDER BY RANDOM() LIMIT 40").fetchall()]
    all_words = [r["word"] for r in cursor.execute("SELECT word FROM vocabulary ORDER BY RANDOM() LIMIT 40").fetchall()]

    questions = []
    for w in words:
        # 1. Multiple Choice: Word -> Meaning
        distractors_trans = [t for t in all_translations if t != w["translation"]]
        sample_dist = random.sample(distractors_trans, min(3, len(distractors_trans)))
        options_trans = sample_dist + [w["translation"]]
        random.shuffle(options_trans)

        questions.append({
            "type": "meaning",
            "word_id": w["id"],
            "target": w["word"],
            "prompt": f"¿Cuál es el significado correcto de '{w['word']}'?",
            "correct": w["translation"],
            "options": options_trans
        })

        # 2. Ear check: Audio listening
        distractors_words = [dw for dw in all_words if dw.lower() != w["word"].lower()]
        sample_dw = random.sample(distractors_words, min(3, len(distractors_words)))
        options_words = sample_dw + [w["word"]]
        random.shuffle(options_words)

        questions.append({
            "type": "listening",
            "word_id": w["id"],
            "target": w["word"],
            "prompt": "Escucha atentamente y selecciona la palabra correcta:",
            "correct": w["word"],
            "options": options_words
        })

        # 3. Letter Puzzle / Word Scramble
        clean_word = re.sub(r"[^a-zA-Z]", "", w["word"]).upper()
        if 3 <= len(clean_word) <= 12:
            letters = list(clean_word)
            scrambled = letters.copy()
            attempts = 0
            while scrambled == letters and attempts < 6:
                random.shuffle(scrambled)
                attempts += 1
            questions.append({
                "type": "scramble",
                "word_id": w["id"],
                "target": clean_word,
                "display_word": w["word"],
                "prompt": f"Ordena las letras en inglés para: '{w['translation']}'",
                "translation": w["translation"],
                "correct": clean_word,
                "letters": scrambled
            })

    random.shuffle(questions)
    conn.close()
    return jsonify(questions[:8])

@app.route("/api/vocab/srs", methods=["GET"])
def get_srs_stats():
    user_id = request.args.get("user_id", default=1, type=int)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) as total_studied,
            SUM(CASE WHEN mastery_level = 5 THEN 1 ELSE 0 END) as mastered,
            SUM(CASE WHEN mastery_level IN (3, 4) THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN mastery_level IN (1, 2) THEN 1 ELSE 0 END) as needs_review
        FROM user_word_progress
        WHERE user_id = ?
    """, (user_id,))
    stats = dict(cursor.fetchone() or {})

    # Words due for review (mastery <= 3)
    cursor.execute("""
        SELECT v.id, v.word, v.translation, v.example_en, p.mastery_level, p.personal_sentence
        FROM user_word_progress p
        JOIN vocabulary v ON p.word_id = v.id
        WHERE p.user_id = ? AND p.mastery_level <= 3
        ORDER BY p.last_reviewed_at ASC
        LIMIT 10
    """, (user_id,))
    review_queue = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return jsonify({
        "stats": {
            "total_studied": stats.get("total_studied") or 0,
            "mastered": stats.get("mastered") or 0,
            "in_progress": stats.get("in_progress") or 0,
            "needs_review": stats.get("needs_review") or 0
        },
        "review_queue": review_queue
    })

@app.route("/api/vocab/complete", methods=["POST"])
def complete_vocab():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    today_str = data.get("date", date.today().isoformat())
    day_number = data.get("day", 1)
    notes = data.get("notes", "")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE daily_logs
        SET vocab_done = 1, vocab_notes = ?, day_number = ?,
            completed_count = vocab_done + reading_done + listening_done + shadowing_done + speaking_done,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND date = ?
    """, (notes, day_number, user_id, today_str))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- API: Module 2 - Reading & Summary Evaluator with Gemini AI ---

@app.route("/api/reading", methods=["GET"])
def get_reading():
    day_number = request.args.get("day", default=1, type=int)
    conn = get_db()
    reading = conn.execute("SELECT * FROM readings WHERE day_number = ?", (day_number,)).fetchone()
    
    if not reading:
        reading = conn.execute("SELECT * FROM readings ORDER BY day_number DESC LIMIT 1").fetchone()
        
    conn.close()
    if reading:
        r_dict = dict(reading)
        if r_dict.get("key_vocabulary"):
            try:
                r_dict["key_vocabulary"] = json.loads(r_dict["key_vocabulary"])
            except Exception:
                pass
        return jsonify(r_dict)
    return jsonify({"error": "Reading not found"}), 404

@app.route("/api/reading/evaluate", methods=["POST"])
def evaluate_reading():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    today_str = data.get("date", date.today().isoformat())
    day_number = data.get("day", 1)
    summary_text = (data.get("summary_text") or "").strip()

    if not summary_text:
        return jsonify({"error": "Summary text is empty"}), 400

    words = re.findall(r"\b\w+\b", summary_text.lower())
    word_count = len(words)

    # Fetch reading text & day's words for context
    conn = get_db()
    r_row = conn.execute("SELECT title, content FROM readings WHERE day_number = ?", (day_number,)).fetchone()
    reading_text = r_row["content"] if r_row else ""
    reading_title = r_row["title"] if r_row else ""

    day_words = conn.execute("SELECT word FROM vocabulary WHERE day_number = ? LIMIT 10", (day_number,)).fetchall()
    target_words = [w["word"].lower() for w in day_words]

    # Try Gemini AI First for World-Class Feedback
    ai_prompt = f"""
You are a master bilingual ESL Professor and Cambridge English Examiner evaluating a student's written summary.

Reading Article Title: "{reading_title}"
Original Article Content:
\"\"\"{reading_text}\"\"\"

Student's Target Vocabulary for Today: {target_words}

Student's Written Summary:
\"\"\"{summary_text}\"\"\"

Analyze the student's text carefully and return a JSON object with this EXACT structure:
{{
  "word_count": {word_count},
  "target_reached": {str(word_count >= 50).lower()},
  "estimated_cefr": "A1 or A2 or B1 or B2 or C1",
  "comprehension_score": <integer from 1 to 10>,
  "comprehension_feedback": "<1-2 sentences in Spanish evaluating whether the summary captured the core message of the reading>",
  "matched_vocab": [<list of words from target_words that the student used in their summary>],
  "corrections": [
    {{
      "original": "<exact phrase with mistake>",
      "suggestion": "<corrected phrase>",
      "explanation": "<friendly explanation in Spanish of the grammar or preposition rule>"
    }}
  ],
  "native_phrasing_tip": "<specific suggestion in Spanish showing a more natural, idiomatic way a native speaker would express one of their ideas>"
}}
"""
    ai_raw = call_gemini_api(ai_prompt, response_mime_type="application/json")
    feedback = None

    if ai_raw:
        try:
            feedback = json.loads(ai_raw)
            feedback["source"] = "Gemini Flash AI"
        except Exception:
            feedback = None

    # Fallback to local heuristic engine if Gemini is offline
    if not feedback:
        corrections = []
        for rule in COMMON_GRAMMAR_RULES:
            matches = re.finditer(rule["pattern"], summary_text, re.IGNORECASE)
            for m in matches:
                corrections.append({
                    "original": m.group(0),
                    "suggestion": rule["replacement"],
                    "explanation": rule["explanation"]
                })

        matched_vocab = [tw for tw in target_words if re.search(r"\b" + re.escape(tw) + r"\b", summary_text, re.IGNORECASE)]
        
        sentences = [s.strip() for s in re.split(r"[.!?]+", summary_text) if s.strip()]
        avg_sentence_len = round(word_count / max(len(sentences), 1), 1)
        lexical_diversity = round(len(set(words)) / max(word_count, 1), 2)
        connectors = ["however", "furthermore", "although", "consequently", "because", "instead of", "meanwhile", "therefore"]
        used_connectors = [c for c in connectors if c in summary_text.lower()]

        estimated_level = "A2"
        if word_count >= 50 and avg_sentence_len >= 8 and len(used_connectors) >= 1:
            estimated_level = "B1"
        if word_count >= 80 and avg_sentence_len >= 11 and len(used_connectors) >= 2 and lexical_diversity >= 0.55:
            estimated_level = "B2"

        feedback = {
            "source": "Local Heuristics",
            "word_count": word_count,
            "target_reached": word_count >= 50,
            "estimated_cefr": estimated_level,
            "comprehension_score": 8 if word_count >= 50 else 5,
            "comprehension_feedback": "Tu resumen contiene buena síntesis de la lectura general.",
            "matched_vocab": matched_vocab,
            "corrections": corrections,
            "native_phrasing_tip": "Excelente esfuerzo. Para enriquecer tu redacción, prueba unir ideas con cláusulas relativas ('which means that...') o conectores de contraste ('Whereas...')."
        }

    # Save to daily_logs
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE daily_logs
        SET reading_done = 1, reading_summary = ?, reading_feedback = ?, day_number = ?,
            completed_count = vocab_done + 1 + listening_done + shadowing_done + speaking_done,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND date = ?
    """, (summary_text, json.dumps(feedback), day_number, user_id, today_str))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "feedback": feedback})

# --- API: Module 3 - Listening & Dictation Diff ---

@app.route("/api/listening", methods=["GET"])
def get_listening():
    day_number = request.args.get("day", default=1, type=int)
    conn = get_db()
    clip = conn.execute("SELECT * FROM listening_shadowing WHERE day_number = ?", (day_number,)).fetchone()
    if not clip:
        clip = conn.execute("SELECT * FROM listening_shadowing ORDER BY day_number DESC LIMIT 1").fetchone()
    conn.close()
    if clip:
        c_dict = dict(clip)
        if c_dict.get("shadowing_chunks"):
            try:
                c_dict["shadowing_chunks"] = json.loads(c_dict["shadowing_chunks"])
            except Exception:
                pass
        return jsonify(c_dict)
    return jsonify({"error": "Clip not found"}), 404

def calculate_word_diff(user_text, real_text):
    clean_user = re.findall(r"\b[\w'-]+\b", user_text.lower())
    clean_real = re.findall(r"\b[\w'-]+\b", real_text.lower())

    real_set = set(clean_real)
    matches = len([w for w in clean_user if w in real_set])
    accuracy = round((matches / max(len(clean_real), 1)) * 100, 1)

    diff_tokens = []
    real_idx = 0
    user_idx = 0

    while real_idx < len(clean_real) or user_idx < len(clean_user):
        if real_idx < len(clean_real) and user_idx < len(clean_user):
            r_w = clean_real[real_idx]
            u_w = clean_user[user_idx]
            if r_w == u_w:
                diff_tokens.append({"type": "correct", "word": r_w})
                real_idx += 1
                user_idx += 1
            else:
                if r_w in clean_user[user_idx:]:
                    diff_tokens.append({"type": "extra", "word": u_w})
                    user_idx += 1
                elif u_w in clean_real[real_idx:]:
                    diff_tokens.append({"type": "missed", "word": r_w})
                    real_idx += 1
                else:
                    diff_tokens.append({"type": "wrong", "got": u_w, "expected": r_w})
                    real_idx += 1
                    user_idx += 1
        elif real_idx < len(clean_real):
            diff_tokens.append({"type": "missed", "word": clean_real[real_idx]})
            real_idx += 1
        elif user_idx < len(clean_user):
            diff_tokens.append({"type": "extra", "word": clean_user[user_idx]})
            user_idx += 1

    return accuracy, diff_tokens

@app.route("/api/listening/verify", methods=["POST"])
def verify_listening():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    today_str = data.get("date", date.today().isoformat())
    day_number = data.get("day", 1)
    user_text = (data.get("user_text") or "").strip()

    conn = get_db()
    clip = conn.execute("SELECT transcript FROM listening_shadowing WHERE day_number = ?", (day_number,)).fetchone()
    if not clip:
        conn.close()
        return jsonify({"error": "Clip transcript not found"}), 404

    real_text = clip["transcript"]
    accuracy, diff_tokens = calculate_word_diff(user_text, real_text)

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE daily_logs
        SET listening_done = 1, listening_attempt = ?, listening_accuracy = ?, day_number = ?,
            completed_count = vocab_done + reading_done + 1 + shadowing_done + speaking_done,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND date = ?
    """, (user_text, accuracy, day_number, user_id, today_str))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "accuracy": accuracy,
        "diff_tokens": diff_tokens,
        "real_text": real_text
    })

# --- API: Module 4 - Shadowing ---

@app.route("/api/shadowing/complete", methods=["POST"])
def complete_shadowing():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    today_str = data.get("date", date.today().isoformat())
    day_number = data.get("day", 1)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE daily_logs
        SET shadowing_done = 1, day_number = ?,
            completed_count = vocab_done + reading_done + listening_done + 1 + speaking_done,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND date = ?
    """, (day_number, user_id, today_str))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# --- API: Module 5 - Speaking ---

@app.route("/api/speaking", methods=["GET"])
def get_speaking():
    day_number = request.args.get("day", default=1, type=int)
    conn = get_db()
    prompt = conn.execute("SELECT * FROM speaking_prompts WHERE day_number = ?", (day_number,)).fetchone()
    if not prompt:
        prompt = conn.execute("SELECT * FROM speaking_prompts ORDER BY day_number DESC LIMIT 1").fetchone()
    
    words = conn.execute("SELECT word, translation FROM vocabulary WHERE day_number = ? LIMIT 5", (day_number,)).fetchall()
    conn.close()

    p_dict = dict(prompt) if prompt else {}
    p_dict["target_words"] = [dict(w) for w in words]
    return jsonify(p_dict)

@app.route("/api/speaking/complete", methods=["POST"])
def complete_speaking():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    today_str = data.get("date", date.today().isoformat())
    day_number = data.get("day", 1)
    notes = data.get("notes", "")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE daily_logs
        SET speaking_done = 1, speaking_notes = ?, day_number = ?,
            completed_count = vocab_done + reading_done + listening_done + shadowing_done + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND date = ?
    """, (notes, day_number, user_id, today_str))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

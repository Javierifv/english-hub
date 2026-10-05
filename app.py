import os
import re
import json
import sqlite3
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = "duohub-english-training-key"

# Ensure DB initialized
init_db()

# Common English false friends and preposition error heuristics for instant feedback
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
    users = conn.execute("SELECT id, username, display_name, avatar_color FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

@app.route("/api/status", methods=["GET"])
def get_status():
    user_id = request.args.get("user_id", default=1, type=int)
    today_str = request.args.get("date", default=date.today().isoformat())
    day_number = request.args.get("day", default=1, type=int)

    conn = get_db()
    cursor = conn.cursor()

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

    # Get partner's status for accountability
    cursor.execute("SELECT id, display_name FROM users WHERE id != ?", (user_id,))
    partner = cursor.fetchone()

    partner_status = None
    if partner:
        cursor.execute("SELECT completed_count, vocab_done, reading_done, listening_done, shadowing_done, speaking_done FROM daily_logs WHERE user_id = ? AND date = ?", (partner["id"], today_str))
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

    # Get max available days
    cursor.execute("SELECT MAX(day_number) FROM vocabulary")
    max_days = cursor.fetchone()[0] or 7

    conn.close()
    return jsonify({
        "log": dict(log),
        "streak": streak,
        "partner": partner_status,
        "max_days": max_days,
        "today_str": today_str
    })

# --- API: Module 1 - Vocabulary ---

@app.route("/api/vocab", methods=["GET"])
def get_vocab():
    day_number = request.args.get("day", default=1, type=int)
    conn = get_db()
    words = conn.execute("""
        SELECT * FROM vocabulary WHERE day_number = ? ORDER BY id ASC LIMIT 5
    """, (day_number,)).fetchall()
    conn.close()
    return jsonify([dict(w) for w in words])

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

# --- API: Module 2 - Reading & Summary Evaluator ---

@app.route("/api/reading", methods=["GET"])
def get_reading():
    day_number = request.args.get("day", default=1, type=int)
    conn = get_db()
    reading = conn.execute("SELECT * FROM readings WHERE day_number = ?", (day_number,)).fetchone()
    
    # Fallback to day 1 if day exceeds available
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

    # 1. Grammar & Heuristic check
    corrections = []
    for rule in COMMON_GRAMMAR_RULES:
        matches = re.finditer(rule["pattern"], summary_text, re.IGNORECASE)
        for m in matches:
            corrections.append({
                "original": m.group(0),
                "suggestion": rule["replacement"],
                "explanation": rule["explanation"]
            })

    # 2. Vocabulary Synergy Check (Did user use any of today's 5 words?)
    conn = get_db()
    day_words = conn.execute("SELECT word FROM vocabulary WHERE day_number = ?", (day_number,)).fetchall()
    target_words = [w["word"].lower() for w in day_words]

    matched_vocab = []
    for tw in target_words:
        if re.search(r"\b" + re.escape(tw) + r"\b", summary_text, re.IGNORECASE):
            matched_vocab.append(tw)

    # 3. CEFR Level & Complexity Metrics
    sentences = [s.strip() for s in re.split(r"[.!?]+", summary_text) if s.strip()]
    sentence_count = max(len(sentences), 1)
    avg_sentence_len = round(word_count / sentence_count, 1)
    unique_words = len(set(words))
    lexical_diversity = round(unique_words / max(word_count, 1), 2)

    connectors = ["however", "furthermore", "although", "consequently", "because", "instead of", "meanwhile", "therefore", "in addition"]
    used_connectors = [c for c in connectors if c in summary_text.lower()]

    estimated_level = "A2"
    if word_count >= 50 and avg_sentence_len >= 8 and len(used_connectors) >= 1:
        estimated_level = "B1"
    if word_count >= 80 and avg_sentence_len >= 11 and len(used_connectors) >= 2 and lexical_diversity >= 0.55:
        estimated_level = "B2"

    feedback = {
        "word_count": word_count,
        "target_reached": word_count >= 50,
        "estimated_cefr": estimated_level,
        "lexical_diversity": lexical_diversity,
        "used_connectors": used_connectors,
        "matched_vocab": matched_vocab,
        "corrections": corrections,
        "native_phrasing_tip": "Excellent synthesis! Try connecting thoughts using relative clauses ('which means that...') or contrastive adverbs ('Whereas...' or 'In spite of...')."
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
    """Simple clean word-level diffing between user dictation and actual transcript."""
    clean_user = re.findall(r"\b[\w'-]+\b", user_text.lower())
    clean_real = re.findall(r"\b[\w'-]+\b", real_text.lower())

    user_set = set(clean_user)
    real_set = set(clean_real)

    matches = len([w for w in clean_user if w in real_set])
    accuracy = round((matches / max(len(clean_real), 1)) * 100, 1)

    diff_tokens = []
    # Token-by-token comparison
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
                # check if user missed this word or inserted an extra word
                if r_w in clean_user[user_idx:]:
                    # User added extra words
                    diff_tokens.append({"type": "extra", "word": u_w})
                    user_idx += 1
                elif u_w in clean_real[real_idx:]:
                    # User missed a word from real
                    diff_tokens.append({"type": "missed", "word": r_w})
                    real_idx += 1
                else:
                    # Replacement / typo
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
    
    # Also attach the 5 words for today so they can be referenced
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

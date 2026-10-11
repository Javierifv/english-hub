import os
import re
import json
import sqlite3
import random
import urllib.request
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory, session
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

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    audio_dir = os.path.join(os.path.dirname(__file__), "material", "listening")
    return send_from_directory(audio_dir, filename)

RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), "material", "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True)

@app.route("/recordings/<path:filename>")
def serve_recording(filename):
    return send_from_directory(RECORDINGS_DIR, filename)

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

def call_gemini_api(prompt_text, response_mime_type="application/json", audio_bytes=None, audio_mime="audio/webm"):
    """
    Calls Google Gemini Flash API with cascade across free-tier flash models
    to ensure high availability, supporting both text and multimodal audio.
    """
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None

    models_to_try = [
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite"
    ]

    parts = [{"text": prompt_text}]
    if audio_bytes:
        import base64
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        parts.append({
            "inline_data": {
                "mime_type": audio_mime,
                "data": b64_audio
            }
        })

    payload = {
        "contents": [{"parts": parts}],
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
            with urllib.request.urlopen(req, timeout=22) as resp:
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
    today_str = request.args.get("date", date.today().isoformat())
    conn = get_db()
    cursor = conn.cursor()
    users = cursor.execute("""
        SELECT u.id, u.username, u.display_name, u.avatar_color, u.words_per_day, u.selection_mode, u.preferred_level,
               COALESCE(d.completed_count, 0) as today_completed
        FROM users u
        LEFT JOIN daily_logs d ON u.id = d.user_id AND d.date = ?
        ORDER BY u.id ASC
    """, (today_str,)).fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])

def check_write_permission(target_user_id):
    """
    Verifica que el usuario autenticado tenga permiso para modificar los registros de target_user_id.
    Si se detecta que un usuario intenta modificar los datos de otro estudiante, retorna False.
    """
    auth_id = session.get("user_id")
    header_auth = request.headers.get("X-Auth-User-Id")
    if header_auth:
        try:
            auth_id = int(header_auth)
        except (ValueError, TypeError):
            pass
            
    if auth_id is not None and int(auth_id) != int(target_user_id):
        return False
    return True

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.json or {}
    display_name = (data.get("display_name") or "").strip()
    raw_username = (data.get("username") or "").strip().lower()
    username = re.sub(r"[^a-z0-9_-]", "", raw_username)
    pin = (str(data.get("pin") or "1234")).strip()
    preferred_level = (data.get("preferred_level") or "A1").strip().upper()
    words_per_day = max(3, min(20, int(data.get("words_per_day", 5))))

    if not display_name:
        return jsonify({"error": "Por favor ingresa tu nombre completo o de estudio."}), 400
    if not username or len(username) < 2:
        return jsonify({"error": "El nombre de usuario debe tener al menos 2 caracteres (letras, números o guiones)."}), 400

    palette = ["#0B72E7", "#00C48C", "#8B5CF6", "#F59E0B", "#EC4899", "#06B6D4", "#10B981"]

    conn = get_db()
    cursor = conn.cursor()

    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": f"El usuario '{username}' ya está registrado. Por favor elige otro o inicia sesión."}), 400

    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    color = palette[count % len(palette)]

    cursor.execute("""
        INSERT INTO users (username, display_name, avatar_color, words_per_day, selection_mode, pin, preferred_level)
        VALUES (?, ?, ?, ?, 'progressive', ?, ?)
    """, (username, display_name, color, words_per_day, pin, preferred_level))
    new_user_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT id, username, display_name, avatar_color, words_per_day, selection_mode, pin, preferred_level FROM users WHERE id = ?", (new_user_id,))
    new_user = dict(cursor.fetchone() or {})
    conn.close()

    session["user_id"] = new_user_id
    return jsonify({"success": True, "user": new_user})

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.json or {}
    identifier = (data.get("username") or "").strip().lower()
    pin = (str(data.get("pin") or "")).strip()

    if not identifier:
        return jsonify({"error": "Ingresa tu nombre de usuario para iniciar sesión."}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, username, display_name, avatar_color, words_per_day, selection_mode, pin, preferred_level 
        FROM users 
        WHERE LOWER(username) = ? OR LOWER(display_name) = ?
    """, (identifier, identifier))
    user_row = cursor.fetchone()

    if not user_row:
        conn.close()
        return jsonify({"error": f"No se encontró ninguna cuenta con el usuario '{identifier}'."}), 404

    user = dict(user_row)
    if pin and user.get("pin") and str(user["pin"]) != pin:
        conn.close()
        return jsonify({"error": "PIN o contraseña incorrecta."}), 401

    conn.close()
    session["user_id"] = user["id"]
    return jsonify({"success": True, "user": user})

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False}), 200
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, display_name, avatar_color, words_per_day, selection_mode, pin, preferred_level FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        session.clear()
        return jsonify({"authenticated": False}), 200
    return jsonify({"authenticated": True, "user": dict(row)})

@app.route("/api/users/profile", methods=["POST"])
def update_profile():
    data = request.json or {}
    user_id = data.get("user_id", 1)

    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar el perfil de tu compañero sin iniciar sesión con su cuenta."}), 403

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    current = cursor.fetchone()
    if not current:
        conn.close()
        return jsonify({"error": "Usuario no encontrado."}), 404

    display_name = data.get("display_name", current["display_name"]).strip()
    words_per_day = int(data.get("words_per_day", current["words_per_day"]))
    selection_mode = data.get("selection_mode", current["selection_mode"])
    pin = str(data.get("pin", current["pin"])).strip()
    preferred_level = data.get("preferred_level", current["preferred_level"])

    cursor.execute("""
        UPDATE users 
        SET display_name = ?, words_per_day = ?, selection_mode = ?, pin = ?, preferred_level = ?
        WHERE id = ?
    """, (display_name, words_per_day, selection_mode, pin, preferred_level, user_id))
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
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

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
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

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
    word_ids_param = request.args.get("word_ids", "").strip()
    round_num = request.args.get("round", default=1, type=int)

    conn = get_db()
    cursor = conn.cursor()

    words = []
    if word_ids_param:
        try:
            ids = [int(x.strip()) for x in word_ids_param.split(",") if x.strip().isdigit()]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                rows = cursor.execute(f"SELECT id, word, translation, definition, example_en FROM vocabulary WHERE id IN ({placeholders})", ids).fetchall()
                id_map = {r["id"]: dict(r) for r in rows}
                # Preserve exact order of passed IDs
                words = [id_map[i] for i in ids if i in id_map]
        except Exception:
            words = []

    if not words:
        # Fallback to user day calculation
        cursor.execute("SELECT words_per_day, selection_mode FROM users WHERE id = ?", (user_id,))
        u_row = cursor.fetchone()
        count = u_row["words_per_day"] if u_row else 5
        mode = u_row["selection_mode"] if u_row else "progressive"
        if mode == "random":
            offset_seed = (day_number * 37) % 500
            words = [dict(r) for r in cursor.execute("""
                SELECT id, word, translation, definition, example_en
                FROM vocabulary
                ORDER BY ((id * 31 + ?) % 534) ASC
                LIMIT ?
            """, (offset_seed, count)).fetchall()]
        else:
            offset = max(0, (day_number - 1) * count)
            words = [dict(r) for r in cursor.execute("""
                SELECT id, word, translation, definition, example_en
                FROM vocabulary
                ORDER BY id ASC
                LIMIT ? OFFSET ?
            """, (count, offset)).fetchall()]

    if not words:
        conn.close()
        return jsonify([])

    # Get random distractors from other words in vocabulary (excluding the current words)
    current_ids = [w["id"] for w in words]
    exclude_placeholders = ",".join("?" for _ in current_ids)
    all_translations = [r["translation"] for r in cursor.execute(
        f"SELECT translation FROM vocabulary WHERE id NOT IN ({exclude_placeholders}) ORDER BY RANDOM() LIMIT 50",
        current_ids
    ).fetchall()]
    all_words = [r["word"] for r in cursor.execute(
        f"SELECT word FROM vocabulary WHERE id NOT IN ({exclude_placeholders}) ORDER BY RANDOM() LIMIT 50",
        current_ids
    ).fetchall()]

    if len(all_translations) < 4:
        all_translations = ["lograr", "éxito", "habilidad", "desafío", "aprender", "camino", "esfuerzo"]
    if len(all_words) < 4:
        all_words = ["achieve", "success", "skill", "challenge", "learn", "path", "effort"]

    questions = []

    if round_num == 1:
        # --- RONDA 1: Reconocimiento (Significado & Audio listening) -> Nivel 3/5 ---
        for w in words:
            # 1. Multiple Choice: Word -> Meaning
            distractors_trans = [t for t in all_translations if t != w["translation"]]
            sample_dist = random.sample(distractors_trans, min(3, len(distractors_trans)))
            options_trans = sample_dist + [w["translation"]]
            random.shuffle(options_trans)

            questions.append({
                "round": 1,
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
                "round": 1,
                "type": "listening",
                "word_id": w["id"],
                "target": w["word"],
                "prompt": "Escucha atentamente y selecciona la palabra correcta:",
                "correct": w["word"],
                "options": options_words
            })

    else:
        # --- RONDA 2: Mayor Dificultad (Word Scramble & Traducción Inversa ES -> EN) -> Nivel 5/5 ---
        for w in words:
            # 1. Active Recall / Full Keyboard Spelling Test
            clean_word = re.sub(r"[^a-zA-Z\s'-]", "", w["word"]).strip()
            clean_word = " ".join(clean_word.split())
            if len(clean_word) >= 2:
                questions.append({
                    "round": 2,
                    "type": "spelling",
                    "word_id": w["id"],
                    "target": clean_word,
                    "display_word": w["word"],
                    "prompt": f"Traduce y Escribe en inglés: '{w['translation']}'",
                    "translation": w["translation"],
                    "correct": clean_word
                })

            # 2. Reverse Meaning (ES -> EN)
            distractors_words = [dw for dw in all_words if dw.lower() != w["word"].lower()]
            sample_dw = random.sample(distractors_words, min(3, len(distractors_words)))
            options_words = sample_dw + [w["word"]]
            random.shuffle(options_words)

            questions.append({
                "round": 2,
                "type": "reverse_meaning",
                "word_id": w["id"],
                "target": w["translation"],
                "prompt": f"¿Cómo se traduce al inglés '{w['translation']}'?",
                "correct": w["word"],
                "options": options_words
            })

    # Shuffle so question types alternate smoothly, testing all current day words
    random.shuffle(questions)
    conn.close()
    return jsonify(questions)

@app.route("/api/vocab/quiz/submit-results", methods=["POST"])
def submit_quiz_results():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

    round_num = int(data.get("round", 1))
    word_results = data.get("word_results", {})  # { "word_id": true/false }
    date_str = data.get("date") or date.today().isoformat()
    day_number = int(data.get("day", 1))

    conn = get_db()
    cursor = conn.cursor()

    updated = {}
    for w_id_str, is_correct in word_results.items():
        try:
            w_id = int(w_id_str)
        except (ValueError, TypeError):
            continue

        cursor.execute("SELECT mastery_level, review_count FROM user_word_progress WHERE user_id = ? AND word_id = ?", (user_id, w_id))
        row = cursor.fetchone()
        cur_level = row["mastery_level"] if row else 1
        cur_reviews = row["review_count"] if row else 0

        # Tobo automated mastery calculation:
        if round_num == 1:
            if is_correct:
                # Round 1 passed: assign Level 3 / 5 (~60% score / recognition)
                new_level = max(cur_level, 3)
            else:
                new_level = 1 if cur_level <= 2 else cur_level
        elif round_num == 2:
            if is_correct:
                # Round 2 passed (higher difficulty): unlock maximum score Level 5 / 5 (100% Mastered)
                new_level = 5
            else:
                new_level = max(cur_level, 3)
        else:
            new_level = cur_level

        new_reviews = cur_reviews + 1

        cursor.execute("""
            INSERT INTO user_word_progress (user_id, word_id, mastery_level, review_count, last_reviewed_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, word_id) DO UPDATE SET
                mastery_level = excluded.mastery_level,
                review_count = excluded.review_count,
                last_reviewed_at = CURRENT_TIMESTAMP
        """, (user_id, w_id, new_level, new_reviews))

        updated[w_id] = {
            "mastery_level": new_level,
            "review_count": new_reviews
        }

    # Check if all words assigned for this day have reached level 5 (5 stars)
    cursor.execute("SELECT words_per_day, selection_mode FROM users WHERE id = ?", (user_id,))
    u_row = cursor.fetchone()
    w_limit = u_row["words_per_day"] if u_row else 5
    sel_mode = u_row["selection_mode"] if u_row else "progressive"

    if sel_mode == "random":
        cursor.execute("SELECT id FROM vocabulary WHERE day_number = ? ORDER BY id ASC LIMIT ?", (day_number, w_limit))
    else:
        cursor.execute("SELECT id FROM vocabulary ORDER BY id ASC LIMIT ? OFFSET ?", (w_limit, (day_number - 1) * w_limit))

    target_words = cursor.fetchall()
    target_ids = [tw["id"] for tw in target_words]

    is_fully_mastered = False
    mastered_count = 0
    if target_ids:
        placeholders = ",".join("?" for _ in target_ids)
        cursor.execute(f"""
            SELECT COUNT(*) FROM user_word_progress 
            WHERE user_id = ? AND word_id IN ({placeholders}) AND mastery_level >= 5
        """, [user_id] + target_ids)
        mastered_count = cursor.fetchone()[0]
        # Only unlock completion if user has completed Round 2 AND all words are at level 5
        if round_num >= 2 and mastered_count >= len(target_ids):
            is_fully_mastered = True

    if is_fully_mastered:
        cursor.execute("""
            INSERT INTO daily_logs (user_id, date, day_number, vocab_done)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, date) DO UPDATE SET
                vocab_done = 1
        """, (user_id, date_str, day_number))

    # Recalculate completed_count in daily_logs
    cursor.execute("""
        SELECT vocab_done, reading_done, listening_done, shadowing_done, speaking_done 
        FROM daily_logs WHERE user_id = ? AND date = ?
    """, (user_id, date_str))
    log_row = cursor.fetchone()
    if log_row:
        c_count = sum([log_row["vocab_done"] or 0, log_row["reading_done"] or 0, 
                       log_row["listening_done"] or 0, log_row["shadowing_done"] or 0, 
                       log_row["speaking_done"] or 0])
        cursor.execute("UPDATE daily_logs SET completed_count = ? WHERE user_id = ? AND date = ?", (c_count, user_id, date_str))

    conn.commit()
    conn.close()
    return jsonify({
        "success": True,
        "round": round_num,
        "updated": updated,
        "is_fully_mastered": is_fully_mastered,
        "mastered_count": mastered_count,
        "total_target": len(target_ids)
    })

@app.route("/api/vocab/srs", methods=["GET"])
def get_srs_stats():
    user_id = request.args.get("user_id", default=1, type=int)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(*) as total_studied,
            SUM(CASE WHEN p.mastery_level = 5 THEN 1 ELSE 0 END) as mastered,
            SUM(CASE WHEN p.mastery_level IN (3, 4) THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN p.mastery_level IN (1, 2) THEN 1 ELSE 0 END) as needs_review
        FROM user_word_progress p
        JOIN vocabulary v ON p.word_id = v.id
        WHERE p.user_id = ?
    """, (user_id,))
    stats = dict(cursor.fetchone() or {})

    cursor.execute("""
        SELECT v.id, v.word, v.translation, v.example_en, v.example_es, v.ipa, v.category,
               p.mastery_level, p.personal_sentence, p.review_count, p.last_reviewed_at
        FROM user_word_progress p
        JOIN vocabulary v ON p.word_id = v.id
        WHERE p.user_id = ?
        ORDER BY p.mastery_level ASC, p.last_reviewed_at DESC, v.word ASC
    """, (user_id,))
    all_studied = [dict(r) for r in cursor.fetchall()]
    review_queue = [w for w in all_studied if (w.get("mastery_level") or 1) < 5]

    conn.close()
    return jsonify({
        "stats": {
            "total_studied": stats.get("total_studied") or 0,
            "mastered": stats.get("mastered") or 0,
            "in_progress": stats.get("in_progress") or 0,
            "needs_review": stats.get("needs_review") or 0
        },
        "all_studied": all_studied,
        "review_queue": review_queue
    })

@app.route("/api/vocab/complete", methods=["POST"])
def complete_vocab():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

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
    reading_id = request.args.get("id", type=int)
    level = request.args.get("level")
    day_number = request.args.get("day", type=int)
    chapter_num = request.args.get("chapter", type=int)
    user_id = request.args.get("user_id", default=1, type=int)

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM readings WHERE 1=1"
    params = []

    if reading_id:
        query += " AND id = ?"
        params.append(reading_id)
    else:
        if level and level != "all":
            query += " AND level = ?"
            params.append(level)
        if chapter_num:
            query += " AND day_number = ?"
            params.append(chapter_num)
        elif day_number:
            query += " AND day_number = ?"
            params.append(day_number)

    query += " ORDER BY id ASC LIMIT 1"
    reading = cursor.execute(query, params).fetchone()

    # Fallback if specific chapter not found for that level
    if not reading and level and level != "all":
        reading = cursor.execute("SELECT * FROM readings WHERE level = ? ORDER BY id ASC LIMIT 1", (level,)).fetchone()

    if not reading:
        reading = cursor.execute("SELECT * FROM readings ORDER BY id ASC LIMIT 1").fetchone()

    # Get level breakdown
    level_counts = cursor.execute("SELECT level, COUNT(*) as count FROM readings GROUP BY level ORDER BY level ASC").fetchall()
    levels_summary = [{"level": lc["level"], "count": lc["count"]} for lc in level_counts]

    # Check user reading progress
    user_prog = None
    if reading and user_id:
        prog_row = cursor.execute("""
            SELECT id, completed_at, date as completed_date, day_number,
                   translation_text, translation_feedback,
                   summary_text, summary_feedback, highlights_json
            FROM user_reading_progress
            WHERE user_id = ? AND reading_id = ?
        """, (user_id, reading["id"])).fetchone()
        if prog_row:
            p_dict = dict(prog_row)
            try:
                if p_dict.get("translation_feedback"):
                    p_dict["translation_feedback"] = json.loads(p_dict["translation_feedback"])
            except Exception:
                pass
            try:
                if p_dict.get("summary_feedback"):
                    p_dict["summary_feedback"] = json.loads(p_dict["summary_feedback"])
            except Exception:
                pass
            try:
                if p_dict.get("highlights_json"):
                    p_dict["highlights_json"] = json.loads(p_dict["highlights_json"])
            except Exception:
                pass
            p_dict["has_translation"] = bool(p_dict.get("translation_text"))
            p_dict["has_summary"] = bool(p_dict.get("summary_text"))
            p_dict["is_completed"] = bool(p_dict.get("translation_text") and p_dict.get("summary_text"))
            p_dict["is_in_progress"] = bool((p_dict.get("translation_text") or p_dict.get("summary_text")) and not p_dict["is_completed"])
            user_prog = p_dict

    conn.close()
    if reading:
        r_dict = dict(reading)
        if r_dict.get("key_vocabulary"):
            try:
                r_dict["key_vocabulary"] = json.loads(r_dict["key_vocabulary"])
            except Exception:
                pass
        r_dict["available_levels"] = levels_summary
        r_dict["user_progress"] = user_prog
        return jsonify(r_dict)
    return jsonify({"error": "Reading not found"}), 404

@app.route("/api/reading/list", methods=["GET"])
def get_reading_list():
    level = request.args.get("level")
    user_id = request.args.get("user_id", default=1, type=int)
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT r.id, r.day_number as chapter, r.title, r.level, r.estimated_minutes,
               p.completed_at, p.date as completed_date,
               CASE 
                   WHEN p.id IS NOT NULL AND p.summary_text IS NOT NULL AND p.translation_text IS NOT NULL THEN 1
                   WHEN p.id IS NOT NULL AND (p.summary_text IS NOT NULL OR p.translation_text IS NOT NULL) THEN 2
                   ELSE 0 
               END as is_completed,
               CASE WHEN p.id IS NOT NULL AND p.translation_text IS NOT NULL THEN 1 ELSE 0 END as has_translation,
               CASE WHEN p.id IS NOT NULL AND p.summary_text IS NOT NULL THEN 1 ELSE 0 END as has_summary
        FROM readings r
        LEFT JOIN user_reading_progress p ON r.id = p.reading_id AND p.user_id = ?
    """
    params = [user_id]
    if level and level != "all":
        query += " WHERE r.level = ?"
        params.append(level)
    query += " ORDER BY r.level ASC, r.day_number ASC"

    rows = cursor.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/reading/evaluate", methods=["POST"])
def evaluate_reading():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

    today_str = data.get("date", date.today().isoformat())
    day_number = data.get("day", 1)
    summary_text = (data.get("summary_text") or "").strip()

    if not summary_text:
        return jsonify({"error": "Summary text is empty"}), 400

    words = re.findall(r"\b\w+\b", summary_text.lower())
    word_count = len(words)

    reading_id = data.get("reading_id")

    # Fetch reading text & day's words for context
    conn = get_db()
    if reading_id:
        r_row = conn.execute("SELECT id, title, content, day_number FROM readings WHERE id = ?", (reading_id,)).fetchone()
    else:
        r_row = conn.execute("SELECT id, title, content, day_number FROM readings WHERE day_number = ?", (day_number,)).fetchone()

    actual_reading_id = r_row["id"] if r_row else (reading_id or 1)
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

    cursor.execute("""
        INSERT INTO user_reading_progress (user_id, reading_id, date, day_number, summary_text, summary_feedback, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, reading_id) DO UPDATE SET
            summary_text = excluded.summary_text,
            summary_feedback = excluded.summary_feedback,
            date = excluded.date,
            day_number = excluded.day_number,
            completed_at = CURRENT_TIMESTAMP
    """, (user_id, actual_reading_id, today_str, day_number, summary_text, json.dumps(feedback, ensure_ascii=False)))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "feedback": feedback})

@app.route("/api/reading/evaluate-translation", methods=["POST"])
def evaluate_reading_translation():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

    today_str = data.get("date", date.today().isoformat())
    day_number = data.get("day", 1)
    reading_id = data.get("reading_id")
    translation_text = (data.get("translation_text") or "").strip()
    highlighted_words = data.get("highlighted_words") or []
    highlighted_phrases = data.get("highlighted_phrases") or []

    if not translation_text:
        return jsonify({"error": "Por favor escribe tu traducción al español antes de solicitar la auditoría."}), 400

    conn = get_db()
    cursor = conn.cursor()

    if reading_id:
        r_row = cursor.execute("SELECT id, title, content FROM readings WHERE id = ?", (reading_id,)).fetchone()
    else:
        r_row = cursor.execute("SELECT id, title, content FROM readings WHERE day_number = ?", (day_number,)).fetchone()

    source_text = r_row["content"] if r_row else ""
    source_title = r_row["title"] if r_row else ""

    words_count = len(re.findall(r"\b\w+\b", translation_text))

    ai_prompt = f"""
You are an expert bilingual translation mentor (English to Spanish).
The student has read an English story chapter and written their own complete Spanish translation.
They also highlighted specific words (highlighted_words) and difficult phrases/idioms (highlighted_phrases) they struggled with.

Source Chapter Title: "{source_title}"
Source English Text:
\"\"\"{source_text}\"\"\"

Student's Spanish Translation:
\"\"\"{translation_text}\"\"\"

Student's Highlighted Unknown Words: {json.dumps(highlighted_words, ensure_ascii=False)}
Student's Highlighted Difficult Phrases/Idioms: {json.dumps(highlighted_phrases, ensure_ascii=False)}

Evaluate the student's translation with clarity, precision, and pedagogical encouragement.
Return a valid JSON object with this EXACT structure:
{{
  "accuracy_percentage": <integer from 0 to 100 representing translation accuracy and fidelity>,
  "overall_verdict": "<1-2 encouraging sentences in Spanish summarizing how faithful and readable the translation is>",
  "corrections": [
    {{
      "original_en": "<phrase from the English text>",
      "student_translation": "<what the student wrote>",
      "suggested_translation": "<accurate and natural Spanish translation>",
      "explanation": "<friendly explanation in Spanish of the grammar, meaning, or nuance>"
    }}
  ],
  "highlighted_explanations": [
    {{
      "item": "<word or phrase highlighted by student>",
      "type": "word" or "phrase",
      "meaning_in_context": "<clear explanation in Spanish of what this word or phrase means in the story>",
      "usage_tip": "<short tip or memory hook to remember it>"
    }}
  ],
  "reference_translation": "<a clean, natural paragraph-by-paragraph Spanish model translation of the chapter>"
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

    # Fallback to local heuristic explanation if offline
    if not feedback:
        fallback_explanations = []
        for item in (highlighted_words + highlighted_phrases)[:8]:
            fallback_explanations.append({
                "item": item,
                "type": "word" if item in highlighted_words else "phrase",
                "meaning_in_context": f"Término clave de la lectura '{item}'.",
                "usage_tip": "Practica anotándolo en tu cuaderno de vocabulario con una frase contextual."
            })

        feedback = {
            "source": "Motor Local",
            "accuracy_percentage": min(95, max(65, int(words_count * 0.75))),
            "overall_verdict": "Tu traducción abarca los puntos clave del capítulo con buena fidelidad.",
            "corrections": [],
            "highlighted_explanations": fallback_explanations,
            "reference_translation": "Traducción guardada y registrada en tu panel de lectura."
        }

    # Save translation & feedback into daily_logs
    cursor.execute("""
        INSERT INTO daily_logs (user_id, date, day_number, reading_translation, reading_translation_feedback)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET
            reading_translation = excluded.reading_translation,
            reading_translation_feedback = excluded.reading_translation_feedback,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, today_str, day_number, translation_text, json.dumps(feedback, ensure_ascii=False)))

    actual_reading_id = r_row["id"] if r_row else (reading_id or 1)
    cursor.execute("""
        INSERT INTO user_reading_progress (user_id, reading_id, date, day_number, translation_text, translation_feedback, highlights_json, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, reading_id) DO UPDATE SET
            translation_text = excluded.translation_text,
            translation_feedback = excluded.translation_feedback,
            highlights_json = excluded.highlights_json,
            date = excluded.date,
            day_number = excluded.day_number,
            completed_at = CURRENT_TIMESTAMP
    """, (user_id, actual_reading_id, today_str, day_number, translation_text, json.dumps(feedback, ensure_ascii=False), json.dumps({"words": highlighted_words, "phrases": highlighted_phrases}, ensure_ascii=False)))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "feedback": feedback})

# --- API: Module 3 - Listening & Dictation Diff ---

@app.route("/api/listening", methods=["GET"])
def get_listening():
    clip_id = request.args.get("id", type=int)
    level = request.args.get("level")
    day_number = request.args.get("day", type=int)
    user_id = request.args.get("user_id", default=1, type=int)

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM listening_shadowing WHERE 1=1"
    params = []

    if clip_id:
        query += " AND id = ?"
        params.append(clip_id)
    else:
        if level and level != "all":
            query += " AND level = ?"
            params.append(level)
        if day_number:
            query += " AND day_number = ?"
            params.append(day_number)

    query += " ORDER BY id ASC LIMIT 1"
    clip = cursor.execute(query, params).fetchone()

    if not clip and level and level != "all":
        clip = cursor.execute("SELECT * FROM listening_shadowing WHERE level = ? ORDER BY id ASC LIMIT 1", (level,)).fetchone()

    if not clip:
        clip = cursor.execute("SELECT * FROM listening_shadowing ORDER BY id ASC LIMIT 1").fetchone()

    level_counts = cursor.execute("SELECT level, COUNT(*) as count FROM listening_shadowing GROUP BY level ORDER BY level ASC").fetchall()
    levels_summary = [{"level": lc["level"], "count": lc["count"]} for lc in level_counts]

    # Check user listening progress for this clip
    user_prog = None
    shadowing_prog = None
    if clip and user_id:
        prog_row = cursor.execute("""
            SELECT id, user_id, clip_id, date, day_number, user_text, accuracy, time_seconds, diff_tokens, ai_audit, completed_at
            FROM user_listening_progress
            WHERE user_id = ? AND clip_id = ?
        """, (user_id, clip["id"])).fetchone()
        if prog_row:
            p_dict = dict(prog_row)
            try:
                if p_dict.get("diff_tokens"):
                    p_dict["diff_tokens"] = json.loads(p_dict["diff_tokens"])
            except Exception:
                pass
            try:
                if p_dict.get("ai_audit"):
                    p_dict["ai_audit"] = json.loads(p_dict["ai_audit"])
            except Exception:
                pass
            p_dict["is_completed"] = bool(p_dict.get("user_text"))
            user_prog = p_dict

        # Also check shadowing progress
        shad_row = cursor.execute("""
            SELECT id, user_id, clip_id, date, day_number, audio_url, ai_feedback, completed_at
            FROM user_shadowing_progress
            WHERE user_id = ? AND clip_id = ?
        """, (user_id, clip["id"])).fetchone()
        if shad_row:
            s_dict = dict(shad_row)
            try:
                if s_dict.get("ai_feedback"):
                    s_dict["ai_feedback"] = json.loads(s_dict["ai_feedback"])
            except Exception:
                pass
            s_dict["is_completed"] = bool(s_dict.get("audio_url"))
            shadowing_prog = s_dict

    conn.close()
    if clip:
        c_dict = dict(clip)
        if c_dict.get("shadowing_chunks"):
            try:
                c_dict["shadowing_chunks"] = json.loads(c_dict["shadowing_chunks"])
            except Exception:
                pass
        c_dict["available_levels"] = levels_summary
        c_dict["user_progress"] = user_prog
        c_dict["shadowing_progress"] = shadowing_prog
        return jsonify(c_dict)
    return jsonify({"error": "Clip not found"}), 404

@app.route("/api/listening/list", methods=["GET"])
def get_listening_list():
    level = request.args.get("level")
    user_id = request.args.get("user_id", default=1, type=int)
    conn = get_db()
    cursor = conn.cursor()
    query = """
        SELECT ls.id, ls.day_number, ls.title, ls.level, ls.duration_seconds, ls.audio_url, ls.source,
               CASE WHEN ulp.id IS NOT NULL AND ulp.user_text IS NOT NULL AND ulp.user_text != '' THEN 1 ELSE 0 END as is_completed,
               ulp.accuracy, ulp.time_seconds
        FROM listening_shadowing ls
        LEFT JOIN user_listening_progress ulp ON ulp.clip_id = ls.id AND ulp.user_id = ?
    """
    params = [user_id]
    if level and level != "all":
        query += " WHERE ls.level = ? ORDER BY ls.day_number ASC, ls.id ASC"
        params.append(level)
    else:
        query += " ORDER BY ls.id ASC"
    rows = cursor.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

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
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

    today_str = data.get("date", date.today().isoformat())
    day_number = data.get("day", 1)
    clip_id = data.get("clip_id")
    user_text = (data.get("user_text") or "").strip()
    time_seconds = data.get("time_seconds", 0)

    conn = get_db()
    if clip_id:
        clip = conn.execute("SELECT * FROM listening_shadowing WHERE id = ?", (clip_id,)).fetchone()
    else:
        clip = conn.execute("SELECT * FROM listening_shadowing WHERE day_number = ?", (day_number,)).fetchone()
    if not clip:
        conn.close()
        return jsonify({"error": "Clip transcript not found"}), 404

    real_text = clip["transcript"]
    track_title = clip["title"]
    track_level = clip["level"]
    accuracy, diff_tokens = calculate_word_diff(user_text, real_text)

    # Gemini AI Comprehensive Listening Audit
    ai_audit = None
    ai_prompt = f"""
You are a senior Cambridge English listening examiner and phonetics specialist.
Evaluate a student's listening dictation transcript against the original spoken audio text.

Audio Level: {track_level}
Lesson Title: "{track_title}"
Official Spoken Transcript:
\"\"\"{real_text}\"\"\"

Student's Written Attempt (typed in {time_seconds} seconds):
\"\"\"{user_text}\"\"\"

Provide your pedagogical audit as a JSON object with this EXACT structure:
{{
  "missing_words": [
    {{
      "word_or_phrase": "<important word or short phrase from official transcript that student omitted>",
      "context": "<short excerpt of the sentence showing where it belongs, e.g. '...book a [meeting room] after...'>",
      "importance": "clave"
    }}
  ],
  "phonetic_confusion": [
    {{
      "heard": "<what student typed or heard>",
      "spoken": "<what was actually spoken>",
      "explanation": "<concise explanation in Spanish of the sound overlap, weak form, or connected speech trap>"
    }}
  ],
  "missed_elements": [
    "<bullet point in Spanish highlighting grammatical markers, prepositions, or fast contractions omitted>"
  ],
  "overall_verdict": "<2-3 sentences in Spanish assessing their ear fidelity, comprehension, and typing speed>",
  "coaching_tip": "<1 high-impact tip in Spanish for training the ear with this specific British audio pattern>"
}}
"""
    ai_raw = call_gemini_api(ai_prompt, response_mime_type="application/json")
    if ai_raw:
        try:
            ai_audit = json.loads(ai_raw)
            ai_audit["source"] = "Auditoría IA"
        except Exception:
            ai_audit = None

    if not ai_audit:
        ai_audit = {
            "source": "Motor Local",
            "missing_words": [],
            "phonetic_confusion": [],
            "missed_elements": ["Revisa la transcripción original completa para identificar las frases que no lograste captar."],
            "overall_verdict": f"Lograste un {accuracy}% de coincidencia auditiva en {time_seconds} segundos. Gran esfuerzo de transcripción.",
            "coaching_tip": "Escucha nuevamente con atención a cómo los hablantes británicos enlazan las consonantes finales con las vocales siguientes."
        }

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE daily_logs
        SET listening_done = 1, listening_attempt = ?, listening_accuracy = ?, listening_time_seconds = ?, day_number = ?,
            completed_count = vocab_done + reading_done + 1 + shadowing_done + speaking_done,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND date = ?
    """, (user_text, accuracy, time_seconds, day_number, user_id, today_str))

    actual_clip_id = clip["id"]
    cursor.execute("""
        INSERT INTO user_listening_progress (user_id, clip_id, date, day_number, user_text, accuracy, time_seconds, diff_tokens, ai_audit, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, clip_id) DO UPDATE SET
            user_text = excluded.user_text,
            accuracy = excluded.accuracy,
            time_seconds = excluded.time_seconds,
            diff_tokens = excluded.diff_tokens,
            ai_audit = excluded.ai_audit,
            date = excluded.date,
            day_number = excluded.day_number,
            completed_at = CURRENT_TIMESTAMP
    """, (user_id, actual_clip_id, today_str, day_number, user_text, accuracy, time_seconds,
          json.dumps(diff_tokens, ensure_ascii=False), json.dumps(ai_audit, ensure_ascii=False)))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "accuracy": accuracy,
        "diff_tokens": diff_tokens,
        "real_text": real_text,
        "time_seconds": time_seconds,
        "ai_audit": ai_audit
    })

# --- API: Module 4 - Shadowing ---

@app.route("/api/shadowing/evaluate", methods=["POST"])
def evaluate_shadowing():
    user_id = request.form.get("user_id", default=1, type=int)
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

    today_str = request.form.get("date", default=date.today().isoformat())
    day_number = request.form.get("day", default=1, type=int)
    clip_id = request.form.get("clip_id", type=int)
    
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No se recibió archivo de audio."}), 400

    filename = f"shadowing_u{user_id}_{today_str.replace('-', '')}_{clip_id or 1}.webm"
    save_path = os.path.join(RECORDINGS_DIR, filename)
    audio_bytes = audio_file.read()
    with open(save_path, "wb") as f:
        f.write(audio_bytes)

    relative_audio_url = f"/recordings/{filename}"

    conn = get_db()
    if clip_id:
        clip = conn.execute("SELECT * FROM listening_shadowing WHERE id = ?", (clip_id,)).fetchone()
    else:
        clip = conn.execute("SELECT * FROM listening_shadowing WHERE day_number = ?", (day_number,)).fetchone()
    
    ref_transcript = clip["transcript"] if clip else "Practice shadowing dialogue."
    track_title = clip["title"] if clip else "Shadowing Track"
    
    ai_prompt = f"""
You are an elite Cambridge English phonetics and pronunciation coach evaluating an English student's audio recording for Shadowing practice.
Target Reference Transcript:
\"\"\"{ref_transcript}\"\"\"
Lesson: "{track_title}"

The student practiced the Alexander Arguelles shadowing technique (speaking along with native speakers).
Listen to the student's recorded audio and evaluate their pronunciation, cadence, and imitation fidelity.
Provide your evaluation as a JSON object with this EXACT structure:
{{
  "fluency_score": <integer from 1 to 100>,
  "pronunciation_verdict": "<2-3 sentences in Spanish evaluating their clarity, rhythm, and accent mimicry>",
  "strengths": [
    "<phonetic strength 1 in Spanish>",
    "<phonetic strength 2 in Spanish>"
  ],
  "words_to_polish": [
    {{
      "word": "<word>",
      "note": "<short phonetic advice in Spanish on vowel/consonant quality, stress, or linking>"
    }}
  ],
  "cadence_tip": "<1 actionable coaching advice in Spanish for improving flow and breath synchronization>"
}}
"""
    ai_raw = call_gemini_api(ai_prompt, response_mime_type="application/json", audio_bytes=audio_bytes, audio_mime="audio/webm")
    feedback = None
    if ai_raw:
        try:
            feedback = json.loads(ai_raw)
            feedback["source"] = "Auditoría IA"
        except Exception:
            feedback = None

    if not feedback:
        feedback = {
            "source": "Motor Local",
            "fluency_score": 85,
            "pronunciation_verdict": "Buena vocalización y esfuerzo constante en replicar la cadencia del hablante nativo.",
            "strengths": ["Entonación general consistente", "Intento claro de ritmo británico"],
            "words_to_polish": [{"word": "clarity", "note": "Presta atención a las vocales abiertas y consonantes finales."}],
            "cadence_tip": "Practica con audífonos puestos para sincronizar exactamente tus pausas con el hablante nativo."
        }

    cursor = conn.cursor()
    cursor.execute("""
        UPDATE daily_logs
        SET shadowing_done = 1, shadowing_audio_path = ?, shadowing_ai_feedback = ?, day_number = ?,
            completed_count = vocab_done + reading_done + listening_done + 1 + speaking_done,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND date = ?
    """, (relative_audio_url, json.dumps(feedback, ensure_ascii=False), day_number, user_id, today_str))

    actual_shad_clip_id = clip["id"] if clip else (clip_id or 1)
    cursor.execute("""
        INSERT INTO user_shadowing_progress (user_id, clip_id, date, day_number, audio_url, ai_feedback, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, clip_id) DO UPDATE SET
            audio_url = excluded.audio_url,
            ai_feedback = excluded.ai_feedback,
            date = excluded.date,
            day_number = excluded.day_number,
            completed_at = CURRENT_TIMESTAMP
    """, (user_id, actual_shad_clip_id, today_str, day_number, relative_audio_url, json.dumps(feedback, ensure_ascii=False)))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "audio_url": relative_audio_url,
        "feedback": feedback
    })

@app.route("/api/shadowing/complete", methods=["POST"])
def complete_shadowing():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

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
    user_id = request.args.get("user_id", default=1, type=int)
    date_str = request.args.get("date")

    conn = get_db()
    cursor = conn.cursor()
    prompt = cursor.execute("SELECT * FROM speaking_prompts WHERE day_number = ?", (day_number,)).fetchone()
    if not prompt:
        prompt = cursor.execute("SELECT * FROM speaking_prompts ORDER BY day_number DESC LIMIT 1").fetchone()

    # Query exact vocabulary assigned for this user and day
    cursor.execute("SELECT words_per_day, selection_mode FROM users WHERE id = ?", (user_id,))
    u_row = cursor.fetchone()
    count = u_row["words_per_day"] if u_row else 5
    mode = u_row["selection_mode"] if u_row else "progressive"

    if mode == "random":
        offset_seed = (day_number * 37) % 500
        words_query = """
            SELECT id, word, translation
            FROM vocabulary
            ORDER BY ((id * 31 + ?) % 534) ASC
            LIMIT ?
        """
        words = cursor.execute(words_query, (offset_seed, count)).fetchall()
    else:
        offset = max(0, (day_number - 1) * count)
        words_query = """
            SELECT id, word, translation
            FROM vocabulary
            ORDER BY id ASC
            LIMIT ? OFFSET ?
        """
        words = cursor.execute(words_query, (count, offset)).fetchall()

    daily_log = None
    if date_str:
        log_row = cursor.execute("SELECT * FROM daily_logs WHERE user_id = ? AND date = ?", (user_id, date_str)).fetchone()
        if log_row:
            l_dict = dict(log_row)
            try:
                if l_dict.get("speaking_ai_feedback"):
                    l_dict["speaking_ai_feedback"] = json.loads(l_dict["speaking_ai_feedback"])
            except Exception:
                pass
            daily_log = l_dict

    conn.close()

    p_dict = dict(prompt) if prompt else {}
    p_dict["target_words"] = [dict(w) for w in words]
    p_dict["daily_log"] = daily_log
    return jsonify(p_dict)

@app.route("/api/speaking/record", methods=["POST"])
def record_speaking():
    user_id = request.form.get("user_id", default=1, type=int)
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

    today_str = request.form.get("date", default=date.today().isoformat())
    day_number = request.form.get("day", default=1, type=int)
    used_words = request.form.get("used_words", "")
    duration_seconds = request.form.get("duration_seconds", default=0, type=int)

    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No se recibió archivo de audio."}), 400

    filename = f"speaking_u{user_id}_{today_str.replace('-', '')}.webm"
    save_path = os.path.join(RECORDINGS_DIR, filename)
    audio_bytes = audio_file.read()
    with open(save_path, "wb") as f:
        f.write(audio_bytes)

    relative_audio_url = f"/recordings/{filename}"

    conn = get_db()
    prompt = conn.execute("SELECT * FROM speaking_prompts WHERE day_number = ?", (day_number,)).fetchone()
    prompt_q = prompt["prompt_question"] if prompt else "Daily Speaking Challenge"
    
    ai_prompt = f"""
You are an expert Cambridge English speaking coach and pronunciation examiner.
The student is practicing FREE SPEAKING oral expression.
Target Vocabulary Words Available Today (Optional practice): {used_words}
Recording Duration: {duration_seconds} seconds

CRITICAL INSTRUCTION:
This is a FREE SPEAKING exercise. Do NOT evaluate, criticize, or penalize topic relevance or adherence to any specific subject. The student has 100% freedom to talk about any topic, their personal thoughts, work, or daily life.
Evaluate ONLY technical and linguistic aspects:
1. Spoken clarity, phonetics, and pronunciation.
2. Grammar accuracy, tense consistency, and sentence structures.
3. Length and pacing (whether audio is adequate, too short, or well-paced).
4. Natural usage of words and transition connectors.

Provide your evaluation as a JSON object with this EXACT structure:
{{
  "overall_verdict": "<2-3 sentences in Spanish assessing their spoken clarity, fluency, communicative flow, confidence, and pacing>",
  "estimated_cefr": "A1 or A2 or B1 or B2 or C1",
  "transcription_snippet": "<the first 1-2 sentences transcribed in English of what the student said>",
  "grammar_observations": [
    "<constructive bullet point in Spanish on grammar, verb tenses, prepositions, or sentence structure>"
  ],
  "vocab_usage_feedback": "<comment in Spanish on how well they articulated words or used natural expressions>",
  "fluency_coaching_tip": "<1 actionable coaching advice in Spanish for their next oral practice>"
}}
"""
    ai_raw = call_gemini_api(ai_prompt, response_mime_type="application/json", audio_bytes=audio_bytes, audio_mime="audio/webm")
    feedback = None
    if ai_raw:
        try:
            feedback = json.loads(ai_raw)
            feedback["source"] = "Auditoría IA"
        except Exception:
            feedback = None

    if not feedback:
        feedback = {
            "source": "Motor Local",
            "overall_verdict": f"Excelente práctica de speaking oral de {duration_seconds} segundos. Gran fluidez y cumplimiento del reto.",
            "estimated_cefr": "A2",
            "transcription_snippet": "Grabación de audio registrada con éxito en el hub.",
            "grammar_observations": ["Recuerda mantener coherencia en los tiempos pasados al relatar eventos del día."],
            "vocab_usage_feedback": f"Palabras objetivo seleccionadas: {used_words or 'Vocabulario del día'}",
            "fluency_coaching_tip": "Intenta estructurar tus respuestas usando conectores como 'firstly', 'after that' y 'finally'."
        }

    notes = f"Audio: {duration_seconds}s. Words: {used_words}"
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE daily_logs
        SET speaking_done = 1, speaking_notes = ?, speaking_audio_path = ?, speaking_ai_feedback = ?, day_number = ?,
            completed_count = vocab_done + reading_done + listening_done + shadowing_done + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ? AND date = ?
    """, (notes, relative_audio_url, json.dumps(feedback, ensure_ascii=False), day_number, user_id, today_str))
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "audio_url": relative_audio_url,
        "feedback": feedback
    })

@app.route("/api/speaking/complete", methods=["POST"])
def complete_speaking():
    data = request.json or {}
    user_id = data.get("user_id", 1)
    if not check_write_permission(user_id):
        return jsonify({"error": "Modo Solo Lectura: No puedes modificar registros de tu compañero."}), 403

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
    port = int(os.environ.get("PORT", 5005))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=True)

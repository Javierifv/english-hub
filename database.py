import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "duohub.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -64000")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        avatar_color TEXT DEFAULT '#0B72E7',
        words_per_day INTEGER DEFAULT 5,
        selection_mode TEXT DEFAULT 'progressive',
        pin TEXT DEFAULT '1234',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Vocabulary table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocabulary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_number INTEGER NOT NULL,
        word TEXT NOT NULL,
        ipa TEXT,
        part_of_speech TEXT,
        translation TEXT NOT NULL,
        definition TEXT,
        example_en TEXT,
        example_es TEXT,
        category TEXT DEFAULT 'general'
    );
    """)

    # 2b. User Word Progress (SRS / Active Recall & Personal Sentences)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_word_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        word_id INTEGER NOT NULL,
        mastery_level INTEGER DEFAULT 1,
        review_count INTEGER DEFAULT 0,
        personal_sentence TEXT,
        last_reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (word_id) REFERENCES vocabulary (id),
        UNIQUE(user_id, word_id)
    );
    """)

    # 3. Readings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        level TEXT DEFAULT 'B1',
        topic TEXT NOT NULL,
        estimated_minutes INTEGER DEFAULT 15,
        content TEXT NOT NULL,
        source TEXT,
        key_vocabulary TEXT
    );
    """)

    # 3b. User Reading Progress (Per-Chapter Tracking & Audit History)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_reading_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        reading_id INTEGER NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date TEXT NOT NULL,
        day_number INTEGER DEFAULT 1,
        translation_text TEXT,
        translation_feedback TEXT,
        summary_text TEXT,
        summary_feedback TEXT,
        highlights_json TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (reading_id) REFERENCES readings (id),
        UNIQUE(user_id, reading_id)
    );
    """)

    # 3c. User Listening Progress (Per-Track Dictation Tracking & Audit History)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_listening_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        clip_id INTEGER NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date TEXT NOT NULL,
        day_number INTEGER DEFAULT 1,
        user_text TEXT,
        accuracy REAL DEFAULT 0,
        time_seconds INTEGER DEFAULT 0,
        diff_tokens TEXT,
        ai_audit TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (clip_id) REFERENCES listening_shadowing (id),
        UNIQUE(user_id, clip_id)
    );
    """)

    # 3d. User Shadowing Progress (Per-Track Shadowing Recording & Audit History)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_shadowing_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        clip_id INTEGER NOT NULL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        date TEXT NOT NULL,
        day_number INTEGER DEFAULT 1,
        audio_url TEXT,
        ai_feedback TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (clip_id) REFERENCES listening_shadowing (id),
        UNIQUE(user_id, clip_id)
    );
    """)

    # 4. Listening & Shadowing table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listening_shadowing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_number INTEGER NOT NULL,
        title TEXT NOT NULL,
        level TEXT DEFAULT 'B1',
        audio_url TEXT,
        transcript TEXT NOT NULL,
        duration_seconds INTEGER DEFAULT 60,
        shadowing_chunks TEXT
    );
    """)

    # 5. Speaking Prompts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS speaking_prompts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_number INTEGER NOT NULL,
        topic TEXT NOT NULL,
        prompt_question TEXT NOT NULL,
        suggested_guidelines TEXT
    );
    """)

    # 6. Daily Logs (Duo progress)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        day_number INTEGER NOT NULL,
        vocab_done INTEGER DEFAULT 0,
        vocab_notes TEXT,
        reading_done INTEGER DEFAULT 0,
        reading_translation TEXT,
        reading_translation_feedback TEXT,
        reading_summary TEXT,
        reading_feedback TEXT,
        listening_done INTEGER DEFAULT 0,
        listening_attempt TEXT,
        listening_accuracy REAL DEFAULT 0,
        listening_time_seconds INTEGER DEFAULT 0,
        shadowing_done INTEGER DEFAULT 0,
        shadowing_audio_path TEXT,
        speaking_done INTEGER DEFAULT 0,
        speaking_notes TEXT,
        completed_count INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(user_id, date)
    );
    """)

    # Safe migration: ensure translation columns exist in daily_logs
    cursor.execute("PRAGMA table_info(daily_logs)")
    existing_dl_cols = {col[1] for col in cursor.fetchall()}
    if "reading_translation" not in existing_dl_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN reading_translation TEXT")
    if "reading_translation_feedback" not in existing_dl_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN reading_translation_feedback TEXT")
    if "listening_time_seconds" not in existing_dl_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN listening_time_seconds INTEGER DEFAULT 0")
    if "speaking_audio_path" not in existing_dl_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN speaking_audio_path TEXT")
    if "speaking_ai_feedback" not in existing_dl_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN speaking_ai_feedback TEXT")
    if "shadowing_ai_feedback" not in existing_dl_cols:
        cursor.execute("ALTER TABLE daily_logs ADD COLUMN shadowing_ai_feedback TEXT")

    # Safe migration: ensure new columns exist in users table
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = {col[1] for col in cursor.fetchall()}
    if "words_per_day" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN words_per_day INTEGER DEFAULT 5")
    if "selection_mode" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN selection_mode TEXT DEFAULT 'progressive'")
    if "pin" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN pin TEXT DEFAULT '1234'")
    if "preferred_level" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN preferred_level TEXT DEFAULT 'A1'")
        cursor.execute("UPDATE users SET preferred_level = 'A1' WHERE username = 'javier'")
        cursor.execute("UPDATE users SET preferred_level = 'A2' WHERE username = 'partner'")

    # Safe migration: ensure audio_url exists in readings
    cursor.execute("PRAGMA table_info(readings)")
    existing_r_cols = {col[1] for col in cursor.fetchall()}
    if "audio_url" not in existing_r_cols:
        cursor.execute("ALTER TABLE readings ADD COLUMN audio_url TEXT")

    # Safe migration: ensure audio_filename and source exist in listening_shadowing
    cursor.execute("PRAGMA table_info(listening_shadowing)")
    existing_l_cols = {col[1] for col in cursor.fetchall()}
    if "audio_filename" not in existing_l_cols:
        cursor.execute("ALTER TABLE listening_shadowing ADD COLUMN audio_filename TEXT")
    if "source" not in existing_l_cols:
        cursor.execute("ALTER TABLE listening_shadowing ADD COLUMN source TEXT")

    # Ensure Alessandro is removed so he can test registration fresh
    cursor.execute("DELETE FROM users WHERE LOWER(username) LIKE '%alessandro%' OR LOWER(display_name) LIKE '%alessandro%'")
    cursor.execute("DELETE FROM user_word_progress WHERE user_id NOT IN (SELECT id FROM users)")
    cursor.execute("DELETE FROM user_reading_progress WHERE user_id NOT IN (SELECT id FROM users)")
    cursor.execute("DELETE FROM user_listening_progress WHERE user_id NOT IN (SELECT id FROM users)")
    cursor.execute("DELETE FROM user_shadowing_progress WHERE user_id NOT IN (SELECT id FROM users)")
    cursor.execute("DELETE FROM daily_logs WHERE user_id NOT IN (SELECT id FROM users)")

    # Reconcile any stale daily_logs where vocab_done was marked 1 without 5-star mastery
    try:
        cursor.execute("SELECT id, user_id, day_number FROM daily_logs WHERE vocab_done = 1")
        stale_logs = cursor.fetchall()
        for slog in stale_logs:
            s_id = slog[0]
            s_uid = slog[1]
            s_day = slog[2]
            cursor.execute("SELECT words_per_day, selection_mode FROM users WHERE id = ?", (s_uid,))
            s_u = cursor.fetchone()
            s_count = s_u[0] if s_u else 5
            s_mode = s_u[1] if s_u else "progressive"
            if s_mode == "random":
                s_seed = (s_day * 37) % 500
                s_rows = cursor.execute("SELECT id FROM vocabulary ORDER BY ((id * 31 + ?) % 534) ASC LIMIT ?", (s_seed, s_count)).fetchall()
            else:
                s_offset = max(0, (s_day - 1) * s_count)
                s_rows = cursor.execute("SELECT id FROM vocabulary ORDER BY id ASC LIMIT ? OFFSET ?", (s_count, s_offset)).fetchall()
            s_ids = [r[0] for r in s_rows]
            if s_ids:
                s_phs = ",".join("?" for _ in s_ids)
                m_cnt = cursor.execute(f"SELECT COUNT(*) FROM user_word_progress WHERE user_id = ? AND word_id IN ({s_phs}) AND mastery_level >= 5", [s_uid] + s_ids).fetchone()[0]
                if m_cnt < len(s_ids):
                    cursor.execute("UPDATE daily_logs SET vocab_done = 0 WHERE id = ?", (s_id,))
                    cursor.execute("""
                        UPDATE daily_logs 
                        SET completed_count = (vocab_done + reading_done + listening_done + shadowing_done + speaking_done)
                        WHERE id = ?
                    """, (s_id,))
    except Exception as e:
        print("Warning during daily_logs reconciliation:", e)

    # Seed Default Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, display_name, avatar_color, words_per_day, selection_mode, pin, preferred_level) VALUES ('javier', 'Javier Flores', '#0B72E7', 5, 'progressive', '1234', 'A1')")

    # High-Performance Query Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_logs_user_date ON daily_logs (user_id, date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_word_prog_lookup ON user_word_progress (user_id, word_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_word_prog_lvl ON user_word_progress (user_id, mastery_level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_vocabulary_day ON vocabulary (day_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_day_lvl ON readings (day_number, level)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_reading_prog ON user_reading_progress (user_id, reading_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listening_day ON listening_shadowing (day_number)")

    conn.commit()
    seed_initial_curriculum(conn)
    seed_pdf_curriculum_if_needed(conn)
    conn.close()

def seed_initial_curriculum(conn):
    cursor = conn.cursor()

    # Check if vocabulary already populated
    cursor.execute("SELECT COUNT(*) FROM vocabulary")
    if cursor.fetchone()[0] > 0:
        return

    # Seed initial 10 Days of Vocabulary (50 words with IPA, translations, definitions & practical context)
    vocab_seed = [
        # Day 1: Essential Connectors & Actions
        (1, "achieve", "/əˈtʃiːv/", "verb", "lograr / alcanzar", "To successfully bring about a desired result by effort or skill.", "We can achieve our language goals if we practice daily.", "Podemos alcanzar nuestras metas de idioma si practicamos a diario.", "core"),
        (1, "however", "/haʊˈev.ər/", "adverb", "sin embargo", "Used to introduce a statement that contrasts with what has just been said.", "The exercise is difficult; however, it is very effective.", "El ejercicio es difícil; sin embargo, es muy efectivo.", "connector"),
        (1, "improve", "/ɪmˈpruːv/", "verb", "mejorar", "To make or become better in quality, condition, or skill.", "Listening to native podcasts will quickly improve your comprehension.", "Escuchar podcasts nativos mejorará rápidamente tu comprensión.", "core"),
        (1, "actually", "/ˈæk.tʃu.ə.li/", "adverb", "en realidad / de hecho", "In truth, in reality, or contrary to expectation (false friend, NOT 'currently').", "I thought it would take an hour, but actually it took only twenty minutes.", "Pensé que tomaría una hora, pero de hecho tomó solo veinte minutos.", "core"),
        (1, "challenge", "/ˈtʃæl.ɪndʒ/", "noun/verb", "desafío / retar", "A call to take part in a contest or demanding task.", "Speaking English for five minutes is a great daily challenge.", "Hablar en inglés durante cinco minutos es un gran desafío diario.", "core"),

        # Day 2: Communication & Clarity
        (2, "explain", "/ɪkˈspleɪn/", "verb", "explicar", "To make something clear or easy to understand by describing it.", "Please explain to me how this new system works.", "Por favor explícame cómo funciona este nuevo sistema.", "communication"),
        (2, "meanwhile", "/ˈmiːn.waɪl/", "adverb", "mientras tanto", "In the intervening period of time.", "I will read the article; meanwhile, you can prepare the summary.", "Yo leeré el artículo; mientras tanto, tú puedes preparar el resumen.", "connector"),
        (2, "notice", "/ˈnəʊ.tɪs/", "verb", "notar / darse cuenta", "To become aware of something through observation.", "Did you notice any change in his pronunciation?", "¿Notaste algún cambio en su pronunciación?", "core"),
        (2, "furthermore", "/ˌfɜː.ðəˈmɔːr/", "adverb", "además / es más", "In addition to what will be or has been said; moreover.", "Reading builds vocabulary; furthermore, it strengthens your writing.", "La lectura construye vocabulario; además, fortalece tu escritura.", "connector"),
        (2, "reliable", "/rɪˈlaɪ.ə.bəl/", "adjective", "confiable / fiable", "Consistently good in quality or performance; able to be trusted.", "We need a reliable study routine to keep our streak alive.", "Necesitamos una rutina de estudio confiable para mantener viva nuestra racha.", "qualities"),

        # Day 3: Daily Habits & Productivity
        (3, "habit", "/ˈhæb.ɪt/", "noun", "hábito / costumbre", "A settled or regular tendency or practice, especially one hard to give up.", "Building a daily reading habit takes about three weeks.", "Construir un hábito de lectura diario toma unas tres semanas.", "productivity"),
        (3, "focus", "/ˈfəʊ.kəs/", "verb/noun", "enfocarse / enfoque", "To pay particular attention to something.", "Focus on pronunciation rhythm rather than speaking super fast.", "Enfócate en el ritmo de pronunciación más que en hablar súper rápido.", "productivity"),
        (3, "schedule", "/ˈʃedʒ.uːl/", "noun/verb", "horario / programar", "A plan for carrying out a process or procedure, giving lists of times.", "Let's fix a schedule for our daily WhatsApp audio check-in.", "Fijemos un horario para nuestro reporte diario de audios por WhatsApp.", "productivity"),
        (3, "struggle", "/ˈstrʌɡ.əl/", "verb/noun", "luchar / costar trabajo", "To experience difficulty and make great efforts to do something.", "Many learners struggle with prepositions in English.", "A muchos estudiantes les cuesta trabajo las preposiciones en inglés.", "core"),
        (3, "overall", "/ˌəʊ.vərˈɔːl/", "adjective/adverb", "general / en general", "Taking everything into account; in general.", "Overall, our performance this week has improved significantly.", "En general, nuestro rendimiento esta semana ha mejorado significativamente.", "connector"),

        # Day 4: Problem Solving & Reflection
        (4, "figure out", "/ˈfɪɡ.ər aʊt/", "phrasal verb", "descifrar / resolver / comprender", "To discover the solution to a problem or understand something.", "It took me a while to figure out the meaning of that sentence.", "Me tomó un tiempo descifrar el significado de esa oración.", "phrasal"),
        (4, "instead of", "/ɪnˈsted əv/", "preposition", "en lugar de / en vez de", "In place of someone or something.", "Listen to a real podcast instead of translating everything word for word.", "Escucha un podcast real en vez de traducir todo palabra por palabra.", "connector"),
        (4, "attempt", "/əˈtempt/", "noun/verb", "intento / intentar", "An effort to achieve or complete something difficult.", "Your first attempt at shadowing might feel awkward, but keep going.", "Tu primer intento de shadowing puede sentirse raro, pero sigue adelante.", "core"),
        (4, "crucial", "/ˈkruː.ʃəl/", "adjective", "crucial / fundamental", "Decisive or critical, especially in the success or failure of something.", "Consistency is more crucial than spending three hours in a single day.", "La constancia es más crucial que pasar tres horas en un solo día.", "qualities"),
        (4, "manage", "/ˈmæn.ɪdʒ/", "verb", "las arreglárselas / gestionar / lograr", "To succeed in doing something, especially something difficult.", "How did you manage to finish your reading in fifteen minutes?", "¿Cómo te las arreglaste para terminar tu lectura en quince minutos?", "core"),

        # Day 5: Growth & Perspective
        (5, "confident", "/ˈkɒn.fɪ.dənt/", "adjective", "seguro de sí mismo / confiado", "Feeling or showing certainty about something or one's ability.", "I feel more confident speaking in English after doing shadowing.", "Me siento más seguro hablando en inglés después de hacer shadowing.", "mindset"),
        (5, "although", "/ɔːlˈðəʊ/", "conjunction", "aunque / a pesar de que", "In spite of the fact that; even though.", "Although it was late, he recorded his five-minute audio before sleeping.", "Aunque era tarde, grabó su audio de cinco minutos antes de dormir.", "connector"),
        (5, "progress", "/ˈprəʊ.ɡres/", "noun/verb", "progreso / progresar", "Forward or onward movement toward a destination or goal.", "Tracking our stats daily will show tangible progress over time.", "Registrar nuestras estadísticas a diario mostrará un progreso tangible con el tiempo.", "core"),
        (5, "deal with", "/diːl wɪð/", "phrasal verb", "lidiar con / encargarse de", "To take action to do something, especially to solve a problem.", "He knows how to deal with difficult challenges at work.", "Él sabe cómo lidiar con desafíos difíciles en el trabajo.", "phrasal"),
        (5, "worth", "/wɜːθ/", "adjective", "valer la pena / meritorio", "Sufficiently good, important, or enjoyable to justify the effort.", "The effort of repeating sentences out loud is totally worth it.", "El esfuerzo de repetir oraciones en voz alta vale totalmente la pena.", "qualities"),

        # Day 6: Conversational Fluidity
        (6, "realize", "/ˈrɪə.laɪz/", "verb", "darse cuenta (NO 'realizar')", "To become fully aware of something as a fact.", "I suddenly realized that I wasn't pronouncing the final 'ed' sound.", "De repente me di cuenta de que no estaba pronunciando el sonido final 'ed'.", "core"),
        (6, "regarding", "/rɪˈɡɑː.dɪŋ/", "preposition", "con respecto a / sobre", "Concerning or in connection with someone or something.", "Regarding our study session, let's meet at seven in the evening.", "Con respecto a nuestra sesión de estudio, reunámonos a las siete de la tarde.", "connector"),
        (6, "hesitate", "/ˈhez.ɪ.teɪt/", "verb", "dudar / vacilar", "To pause before saying or doing something through uncertainty.", "Don't hesitate to speak, even if you make small grammatical mistakes.", "No dudes en hablar, incluso si cometes pequeños errores gramaticales.", "communication"),
        (6, "fluent", "/ˈfluː.ənt/", "adjective", "fluido / con soltura", "Able to express oneself easily and articulately in a language.", "You don't need a huge vocabulary to become conversational and fluent.", "No necesitas un vocabulario inmenso para volverte conversacional y fluido.", "qualities"),
        (6, "look forward to", "/lʊk ˈfɔː.wəd tuː/", "phrasal verb", "esperar con ilusión / tener muchas ganas de", "To feel pleased and excited about something that is going to happen.", "I look forward to our weekend progress review.", "Tengo muchas ganas de ver nuestra revisión de progreso del fin de semana.", "phrasal"),

        # Day 7: Expression & Synthesis
        (7, "summarize", "/ˈsʌm.ər.aɪz/", "verb", "resumir", "To give a brief statement of the main points of something.", "Can you summarize the main idea of the article in three sentences?", "¿Puedes resumir la idea principal del artículo en tres oraciones?", "core"),
        (7, "essential", "/ɪˈsen.ʃəl/", "adjective", "esencial / imprescindible", "Extremely important and necessary.", "Patience is essential when rewiring your mouth to new sounds.", "La paciencia es esencial cuando estás reentrenando tu boca para nuevos sonidos.", "qualities"),
        (7, "consequently", "/ˈkɒn.sɪ.kwənt.li/", "adverb", "por consiguiente / en consecuencia", "As a result; therefore.", "We practiced every day; consequently, our listening improved.", "Practicamos todos los días; por consiguiente, nuestro listening mejoró.", "connector"),
        (7, "keep in mind", "/kiːp ɪn maɪnd/", "idiom", "tener presente / recordar", "To remember to consider something.", "Keep in mind that mistakes are evidence that you are stretching your mind.", "Ten presente que los errores son evidencia de que estás expandiendo tu mente.", "idiom"),
        (7, "deliver", "/dɪˈlɪv.ər/", "verb", "entregar / cumplir / pronunciar", "To bring and hand over; or to state or produce a result.", "Both partners must deliver their five-minute audio before midnight.", "Ambos compañeros deben entregar su audio de cinco minutos antes de medianoche.", "core")
    ]

    cursor.executemany("""
    INSERT INTO vocabulary (day_number, word, ipa, part_of_speech, translation, definition, example_en, example_es, category)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, vocab_seed)

    # Seed 7 High-Impact Readings (15 minutes target load, with CEFR leveling and comprehension themes)
    readings_seed = [
        (
            1,
            "The Power of the 1% Rule in Language Learning",
            "B1",
            "Habits & Mindset",
            15,
            """Most people believe that to master a foreign language like English, they need to dedicate hours of grueling study every single day. However, behavioral psychology suggests that small, incremental improvements often produce far superior results over the long run. This principle is famously known as the 'One Percent Rule'.

When British Cycling coach Dave Brailsford took over the team in 2003, British riders had won just a single gold medal in nearly a century. Brailsford believed in the 'aggregation of marginal gains'. His philosophy was simple: search for a tiny one percent margin of improvement in everything you do. If you break down everything that goes into riding a bike, and then improve each area by just one percent, you will get a significant increase when you put them all together.

Applying this to language learning is transformative. You do not need to memorize one hundred words in a single sitting. Instead, learn just five words each day, but make sure you actively use them. Read for fifteen uninterrupted minutes, listen to a sixty-second audio clip until your ear identifies every syllable, and speak for five minutes without worrying about perfection. 

If you get just one percent better each day for one year, you will end up thirty-seven times better by the time you are done. The secret is not heroic effort; it is ruthless consistency and having a reliable partner to keep you accountable.""",
            "Inspired by Atomic Habits by James Clear",
            json.dumps(["incremental", "aggregation", "marginal gains", "ruthless", "accountable"])
        ),
        (
            2,
            "Why Shadowing Works: The Science of Muscle Memory",
            "B1",
            "Learning Techniques",
            15,
            """When adult learners struggle with English pronunciation, they often assume they simply lack a natural talent for accents. In reality, speaking a foreign language is as much a physical athletic skill as it is an intellectual one. Your mouth, tongue, lips, and vocal cords contain dozens of fine muscles that have spent decades producing only the sounds of your native language.

Shadowing was developed by Professor Alexander Arguelles, an American polyglot who speaks dozens of languages. The technique is straightforward yet demanding: you listen to a recording of a native speaker and repeat exactly what they say at almost the same time, with a delay of only a fraction of a second. You are not waiting for the sentence to finish; you are literally 'shadowing' their voice like an echo.

Research in cognitive neuroscience shows that this method trains your brain's mirror neurons and builds new motor pathways in the speech cortex. It forces your vocal apparatus to adapt to natural English rhythm, intonation, and connected speech. Furthermore, shadowing prevents your brain from translating words into your native language because there is simply no time to pause and think. Five minutes of focused daily shadowing builds more vocal confidence than hours of silent textbook reading.""",
            "Applied Linguistics & Neurobiology of Speech",
            json.dumps(["vocal cords", "polyglot", "mirror neurons", "motor pathways", "connected speech"])
        ),
        (
            3,
            "Connected Speech: Why Native English Sounds So Fast",
            "B2",
            "Phonetics & Listening",
            15,
            """One of the most frustrating experiences for English learners is realizing that while they can understand written English easily, native speakers often sound like an incomprehensible blur of sound. Learners often ask: 'Why do they speak so quickly?' The truth is that native speakers do not necessarily speak faster; rather, they use a phonetic phenomenon known as connected speech.

In English, words are rarely pronounced in isolation. When words join together in natural speech, sounds undergo dramatic transformations. There are several key mechanisms at play:

1. Elision: Sounds disappear entirely. For instance, 'next door' becomes 'nex-door', and 'you and me' often sounds like 'you-n-me'.
2. Linking: The final consonant of one word connects smoothly to the beginning vowel of the next word. 'Turn off' is pronounced as 'tur-noff'.
3. Weak forms and the Schwa sound: Grammatical words like 'to', 'for', 'of', and 'at' lose their full vowel sounds and reduce to the short, unstressed schwa /ə/. 'Going to the store' becomes 'Goin-tə-thə store'.

When you practice deep listening by transcribing an audio clip phrase by phrase, you train your auditory cortex to recognize these transitions. Instead of expecting each word to have clear borders, you learn to track the melody of the entire thought group.""",
            "BBC Learning English - Pronunciation Guide",
            json.dumps(["connected speech", "elision", "linking", "schwa", "auditory cortex"])
        ),
        (
            4,
            "Deep Work: How to Protect Your 15 Minutes of Focus",
            "B1",
            "Productivity",
            15,
            """In our hyper-connected world, true focus has become a rare superpower. Georgetown professor Cal Newport coined the term 'Deep Work' to describe professional and intellectual activities performed in a state of distraction-free concentration that push your cognitive capabilities to their limit.

Many students claim they do not have enough time to study English. However, when observing their daily habits, one notices frequent 'shallow work' periods: studying with WhatsApp notifications popping up every two minutes, leaving YouTube playing in the background, or scrolling through social media between paragraphs. This constant context-switching leaves what psychologists call 'attention residue' in the brain, drastically lowering retention.

A focused fifteen-minute session with your phone in airplane mode produces vastly greater cognitive results than two hours of fragmented, distracted study. When you sit down for your daily reading or listening routine, treat those fifteen minutes as sacred. Close every unnecessary browser tab, set a physical timer, and immerse your mind fully in the English text. Your brain will synthesize the grammar and vocabulary with remarkable speed.""",
            "Adapted from Deep Work by Cal Newport",
            json.dumps(["distraction-free", "cognitive", "shallow work", "attention residue", "immerse"])
        ),
        (
            5,
            "The Illusion of Competence in Language Acquisition",
            "B2",
            "Psychology of Learning",
            15,
            """Have you ever read a page in an English book, nodded along thinking you understood every single sentence, and then found yourself completely unable to explain the text to someone five minutes later? If so, you have experienced the 'Illusion of Competence'.

Cognitive scientists explain that recognizing information is vastly different from producing it. When your eyes scan a page, the words feel familiar. The brain misinterprets this familiarity as mastery. However, true understanding requires retrieval practice. This is why passive methods—such as merely highlighting text or watching movies with Spanish subtitles—yield disappointingly slow progress.

To break through this illusion, you must force your brain into active output. Writing a handwritten summary in English immediately after reading forces you to reconstruct ideas, organize syntax, and retrieve newly seen vocabulary from your working memory. Similarly, recording a five-minute audio explaining your day forces you to confront the gaps in your spoken vocabulary. Embrace the friction of active output; that friction is the exact sensation of your brain forming new synaptic connections.""",
            "Make It Stick: The Science of Successful Learning",
            json.dumps(["illusion of competence", "retrieval practice", "working memory", "synaptic connections", "friction"])
        ),
        (
            6,
            "The Feynman Technique: Learn by Teaching and Simplifying",
            "B1",
            "Mental Models",
            15,
            """Richard Feynman was a Nobel Prize-winning physicist celebrated not only for his brilliant discoveries in quantum mechanics, but also for his extraordinary ability to explain complex ideas in plain, crystal-clear language. His learning philosophy, known today as the Feynman Technique, is an indispensable tool for mastering any subject—including a new language.

The technique comprises four intuitive steps:
1. Choose the concept you want to understand.
2. Explain it in English as if you were teaching it to a twelve-year-old child. Use simple words and short, clear sentences.
3. Identify where you get stuck or where your explanation becomes confusing.
4. Go back to your source material, clarify the problem, and refine your explanation.

When speaking in your daily WhatsApp audio, do not feel pressured to use complicated, pretentious vocabulary. The highest mark of fluency is clarity. If you can explain your daily work, your emotions, and your challenges using simple, accurate English, you are already well on your way to mastery.""",
            "Mental Models & Nobel Biographies",
            json.dumps(["physicist", "crystal-clear", "indispensable", "pretentious", "fluency"])
        ),
        (
            7,
            "The Power of Accountability: Why Learning in Pairs Succeeds",
            "B1",
            "Teamwork & Consistency",
            15,
            """Research conducted by the American Society of Training and Development revealed a striking statistic about human motivation. If you have an idea or goal in your head, the probability of completing it is roughly 10%. If you consciously decide when you will do it, the probability rises to 40%. However, if you commit to someone you respect and schedule a regular accountability check-in, your probability of achieving that goal skyrockets to 95%.

Solo learners often abandon their language goals when life gets busy because breaking a promise to yourself carries no immediate social consequence. But when you have a study partner who is waiting for your daily audio message or checking whether you finished your reading summary, your brain perceives the routine differently. It becomes a shared pact.

You and your partner are not competitors; you are each other's training ground. When one of you feels tired or unmotivated, the other's consistency pulls the team forward. Celebrate each other's streak milestones, give honest constructive feedback, and enjoy the journey together.""",
            "Psychology of Accountability & Peer Mentorship",
            json.dumps(["accountability", "skyrockets", "consequence", "shared pact", "milestones"])
        )
    ]

    cursor.executemany("""
    INSERT INTO readings (day_number, title, level, topic, estimated_minutes, content, source, key_vocabulary)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, readings_seed)

    # Seed 7 Listening & Shadowing Clips with transcripts & chunks
    listening_seed = [
        (
            1,
            "Starting Small with Daily Habits",
            "A2-B1",
            "",
            "Every big achievement begins with a simple daily decision. When you practice English for just twenty minutes each day, you create momentum. Consistency will always beat intensity.",
            25,
            json.dumps([
                "Every big achievement begins with a simple daily decision.",
                "When you practice English for just twenty minutes each day, you create momentum.",
                "Consistency will always beat intensity."
            ])
        ),
        (
            2,
            "The Secret to Better Pronunciation",
            "B1",
            "",
            "If you want to improve your pronunciation, do not focus on speaking fast. Focus on clarity, pauses, and the rhythm of your sentences. Listen carefully to how native speakers connect their words.",
            30,
            json.dumps([
                "If you want to improve your pronunciation, do not focus on speaking fast.",
                "Focus on clarity, pauses, and the rhythm of your sentences.",
                "Listen carefully to how native speakers connect their words."
            ])
        ),
        (
            3,
            "Dealing with Mistakes",
            "B1",
            "",
            "Making mistakes is not a sign of failure. In fact, it is the only way your brain figures out what sounds natural. When you hesitate, take a deep breath and keep speaking.",
            28,
            json.dumps([
                "Making mistakes is not a sign of failure.",
                "In fact, it is the only way your brain figures out what sounds natural.",
                "When you hesitate, take a deep breath and keep speaking."
            ])
        ),
        (
            4,
            "Creating a Distraction-Free Routine",
            "B1",
            "",
            "Put your phone away before you begin your study session. When your mind is fully engaged, fifteen minutes of reading can teach you more than an hour of distracted skimming.",
            32,
            json.dumps([
                "Put your phone away before you begin your study session.",
                "When your mind is fully engaged,",
                "fifteen minutes of reading can teach you more than an hour of distracted skimming."
            ])
        ),
        (
            5,
            "The Power of Active Output",
            "B2",
            "",
            "Reading and listening provide crucial input. However, unless you force yourself to write and speak, that knowledge remains passive. Challenge yourself to use new words immediately.",
            30,
            json.dumps([
                "Reading and listening provide crucial input.",
                "However, unless you force yourself to write and speak,",
                "that knowledge remains passive.",
                "Challenge yourself to use new words immediately."
            ])
        ),
        (
            6,
            "Simplifying Your Communication",
            "B1",
            "",
            "You do not need complicated words to express powerful ideas. Clear thinkers use simple vocabulary with strong verbs. Strive for clarity above everything else.",
            26,
            json.dumps([
                "You do not need complicated words to express powerful ideas.",
                "Clear thinkers use simple vocabulary with strong verbs.",
                "Strive for clarity above everything else."
            ])
        ),
        (
            7,
            "Celebrating the Journey with Your Partner",
            "B1",
            "",
            "Learning a language is an endurance race, not a sprint. Having someone by your side makes every small milestone meaningful. Keep showing up for each other every single day.",
            31,
            json.dumps([
                "Learning a language is an endurance race, not a sprint.",
                "Having someone by your side makes every small milestone meaningful.",
                "Keep showing up for each other every single day."
            ])
        )
    ]

    cursor.executemany("""
    INSERT INTO listening_shadowing (day_number, title, level, audio_url, transcript, duration_seconds, shadowing_chunks)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, listening_seed)

    # Seed 7 Speaking Prompts
    speaking_seed = [
        (
            1,
            "Your Daily Routine & Study Goal",
            "Describe your typical morning routine in detail, and explain why you and your partner decided to start this English study journey today.",
            "1. What time did you wake up? 2. What was the first thing you did? 3. Mention how you feel about committing to this English habit. 4. Try using today's words: achieve, however, improve, actually, challenge."
        ),
        (
            2,
            "A Recent Challenge at Work or Life",
            "Talk about an unexpected problem or task you had to deal with recently. How did you react and what was the outcome?",
            "1. Explain what happened step by step. 2. Who was involved? 3. What solution did you come up with? 4. Try using today's words: explain, meanwhile, notice, furthermore, reliable."
        ),
        (
            3,
            "Habits You Want to Build or Break",
            "What is one positive habit you are currently trying to maintain, and what is one bad habit you would love to eliminate?",
            "1. Describe how the good habit benefits your day. 2. Why is the bad habit tempting or hard to break? 3. What strategy are you using? 4. Try using today's words: habit, focus, schedule, struggle, overall."
        ),
        (
            4,
            "A Project or Task You Managed to Finish",
            "Walk your partner through a specific project, repair, or personal task that took considerable effort to complete.",
            "1. What tools or steps did you need? 2. What was the most difficult moment? 3. How did you feel when you finished? 4. Try using today's words: figure out, instead of, attempt, crucial, manage."
        ),
        (
            5,
            "A Memorable Trip or Place You Love",
            "Describe a place you have visited that left a strong impression on you, or a place you dream of visiting soon.",
            "1. Where is it located and what does it look like? 2. What kind of activities did you do there? 3. Why is it worth visiting? 4. Try using today's words: confident, although, progress, deal with, worth."
        ),
        (
            6,
            "A Skill You Learned as an Adult",
            "Talk about a skill (professional, technological, cooking, sport) that you learned after childhood.",
            "1. Why did you decide to learn it? 2. Did you hesitate in the beginning? 3. How fluent or skilled are you now? 4. Try using today's words: realize, regarding, hesitate, fluent, look forward to."
        ),
        (
            7,
            "Weekly Reflection & Shoutout to Your Partner",
            "Reflect on this past week of study. What was the most surprising thing you learned, and what words of encouragement do you have for your partner?",
            "1. Summarize your overall feeling about this week. 2. Which pillar (vocab, reading, listening, shadowing, speaking) felt most natural? 3. Share a piece of advice. 4. Try using today's words: summarize, essential, consequently, keep in mind, deliver."
        )
    ]

    cursor.executemany("""
    INSERT INTO speaking_prompts (day_number, topic, prompt_question, suggested_guidelines)
    VALUES (?, ?, ?, ?)
    """, speaking_seed)

    conn.commit()

def seed_pdf_curriculum_if_needed(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vocabulary")
    current_count = cursor.fetchone()[0]
    if current_count >= 100:
        return

    pdf_path = os.path.join(os.path.dirname(__file__), "material", "Domina el Vocabulario Inglés - English Path_260514_013310.pdf")
    if not os.path.exists(pdf_path):
        return

    try:
        from pypdf import PdfReader
        import re

        reader = PdfReader(pdf_path)
        word_pattern = re.compile(r"^([a-zA-Z\s\',-]{2,30})\s*(?:[\u2013\u2014\x96\x97\-]|\uFFFD)\s*(.+)$")
        
        extracted = []
        seen = set()

        # Check existing words in DB
        cursor.execute("SELECT LOWER(word) FROM vocabulary")
        for row in cursor.fetchall():
            seen.add(row[0].strip())

        for p_idx in range(4, len(reader.pages)):
            text = reader.pages[p_idx].extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                line = line.strip()
                if not line or len(line) > 120 or "Capítulo" in line or "Vocabulario" in line:
                    continue
                m = word_pattern.match(line)
                if m:
                    en = m.group(1).strip()
                    es = m.group(2).strip()
                    if len(en.split()) <= 4 and not any(c.isdigit() for c in en):
                        clean_en = en.lower()
                        if clean_en not in seen:
                            seen.add(clean_en)
                            extracted.append((en, es))

        cursor.execute("SELECT COALESCE(MAX(day_number), 0) FROM vocabulary")
        start_day = max(cursor.fetchone()[0] + 1, 8)

        count = 0
        curr_day = start_day
        for en, es in extracted:
            cursor.execute("""
                INSERT INTO vocabulary (day_number, word, ipa, part_of_speech, translation, definition, example_en, example_es, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                curr_day,
                en,
                "",
                "vocab-book",
                es,
                f"Essential vocabulary word: {en}",
                f"We can use '{en}' in daily conversations.",
                f"Podemos usar '{en}' en conversaciones cotidianas.",
                "book-curriculum"
            ))
            count += 1
            if count % 5 == 0:
                curr_day += 1

        conn.commit()
    except Exception as e:
        print("Note: PDF curriculum seed skipped or failed:", e)

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)

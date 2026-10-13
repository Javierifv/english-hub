import os
import sqlite3

def sync_sqlite_to_pg(pg_conn, sqlite_path):
    """
    Transfers all curriculum and data from local SQLite database to PostgreSQL (Neon).
    """
    if not os.path.exists(sqlite_path):
        print("SQLite source database not found at:", sqlite_path)
        return

    sq_conn = sqlite3.connect(sqlite_path)
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    tables = [
        ("users", ["id", "username", "display_name", "avatar_color", "words_per_day", "selection_mode", "pin", "preferred_level"]),
        ("vocabulary", ["id", "day_number", "word", "ipa", "part_of_speech", "translation", "definition", "example_en", "example_es", "category"]),
        ("readings", ["id", "day_number", "title", "level", "topic", "estimated_minutes", "content", "source", "key_vocabulary", "audio_url"]),
        ("listening_shadowing", ["id", "day_number", "title", "level", "audio_url", "transcript", "duration_seconds", "shadowing_chunks", "audio_filename", "source"]),
        ("speaking_prompts", ["id", "day_number", "topic", "prompt_question", "suggested_guidelines"]),
        ("user_word_progress", ["id", "user_id", "word_id", "mastery_level", "review_count", "personal_sentence"]),
        ("daily_logs", ["id", "user_id", "date", "day_number", "vocab_done", "vocab_notes", "reading_done", "reading_translation", "reading_translation_feedback", "reading_summary", "reading_feedback", "listening_done", "listening_attempt", "listening_accuracy", "listening_time_seconds", "shadowing_done", "shadowing_audio_path", "shadowing_ai_feedback", "speaking_done", "speaking_notes", "speaking_audio_path", "speaking_ai_feedback", "completed_count"]),
        ("user_reading_progress", ["id", "user_id", "reading_id", "date", "day_number", "translation_text", "translation_feedback", "summary_text", "summary_feedback", "highlights_json"]),
        ("user_listening_progress", ["id", "user_id", "clip_id", "date", "day_number", "user_text", "accuracy", "time_seconds", "diff_tokens", "ai_audit"]),
        ("user_shadowing_progress", ["id", "user_id", "clip_id", "date", "day_number", "audio_url", "ai_feedback"])
    ]

    for table_name, cols in tables:
        try:
            # Check existing columns in sqlite
            sq_cur.execute(f"PRAGMA table_info({table_name})")
            existing_sq_cols = {r[1] for r in sq_cur.fetchall()}
            valid_cols = [c for c in cols if c in existing_sq_cols]
            
            if not valid_cols:
                continue

            col_str = ", ".join(valid_cols)
            sq_cur.execute(f"SELECT {col_str} FROM {table_name}")
            rows = sq_cur.fetchall()
            if not rows:
                continue

            placeholders = ", ".join(["%s"] * len(valid_cols))
            insert_sql = f"INSERT INTO {table_name} ({col_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            row_data = [[r[c] for c in valid_cols] for r in rows]
            pg_cur.executemany(insert_sql, row_data)
            
            # Reset sequence
            try:
                pg_cur.execute(f"SELECT setval('{table_name}_id_seq', COALESCE((SELECT MAX(id) FROM {table_name}), 1));")
            except Exception:
                pass

            print(f"Synced {len(row_data)} rows for table '{table_name}' to PostgreSQL.")
        except Exception as e:
            print(f"Notice: skipped or partial sync on {table_name}:", e)

    pg_conn.commit()
    sq_conn.close()
    print("Database sync to PostgreSQL completed successfully!")

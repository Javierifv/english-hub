import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "duohub.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

existing = cursor.execute("SELECT id FROM readings WHERE day_number = 1 AND level = 'A1'").fetchone()

content = """CHAPTER 1 – FAMILY

My name is Robinson Crusoe. I was born in England in 1632.
My father was German and my mother was English. I had two brothers and one sister. We were a good family.

My father was a good businessman. We had a comfortable house and money. I went to a good school.
I had a good life, but I had one big dream. I wanted to travel by sea.

My father was an old man. He wanted the best for me. But he was not happy with my dream.
When I was 18 years old, my father called me to his room. He said, "Travelling by sea is dangerous. Many men die in the sea. Stay in England and live a quiet life."

I listened to my father, but my dream was very strong.
I asked my mother to help me. But she said the same thing as my father.

One day I was in the town of Hull. I met a good friend. His father had a big ship. They were going to London by sea.
My friend said, "Come with us to London! You do not have to pay."

I forgot my father's words. I did not tell my mother or my father.
I went on the ship, and my first sea journey began."""

audio_url = "https://www.robinsoncrusoeinlevels.com/wp-content/uploads/2018/10/RC-L1-Ch1-slow.mp3"
title = "[Nivel 1 (A1/A2)] Cap. 1 – Family"
key_vocab = '["family", "journey", "dream", "dangerous", "ship"]'

if not existing:
    cursor.execute("""
        INSERT INTO readings (day_number, title, level, topic, estimated_minutes, content, source, key_vocabulary, audio_url)
        VALUES (1, ?, 'A1', 'Robinson Crusoe', 10, ?, 'https://www.robinsoncrusoeinlevels.com/level1/chapter1/', ?, ?)
    """, (title, content, key_vocab, audio_url))
    conn.commit()
    print("Chapter 1 Level A1 inserted successfully!")
else:
    cursor.execute("""
        UPDATE readings
        SET title = ?, content = ?, key_vocabulary = ?, audio_url = ?
        WHERE id = ?
    """, (title, content, key_vocab, audio_url, existing[0]))
    conn.commit()
    print("Chapter 1 Level A1 updated successfully!")

# Verify count of A1 chapters
a1_count = cursor.execute("SELECT COUNT(*), MIN(day_number), MAX(day_number) FROM readings WHERE level = 'A1'").fetchone()
print(f"Level A1 chapters count: {a1_count[0]}, range: {a1_count[1]} to {a1_count[2]}")

conn.close()

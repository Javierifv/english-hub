import sqlite3
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('data/duohub.db')
c = conn.cursor()

c.execute("SELECT id, day_number, word, translation, definition FROM vocabulary ORDER BY id ASC")
rows = c.fetchall()

anomalies = []
for wid, day, word, trans, defi in rows:
    # 1. Trailing or leading punctuation
    if re.search(r'^[^\w]|[\.,;:\-]$', word.strip()):
        anomalies.append((wid, day, word, trans, "Word has leading/trailing punctuation"))
        
    if re.search(r'^[^\w]|[\.;:]$', trans.strip()):
        anomalies.append((wid, day, word, trans, "Translation has leading/trailing punctuation"))
        
    # 2. Contains English words in Spanish translation (common words like is, a, the, of, in, was, to, for, with)
    words_in_trans = trans.lower().split()
    eng_markers = {'is', 'was', 'the', 'law', 'ticket', 'contract'}
    found_eng = eng_markers.intersection(set(words_in_trans))
    if found_eng:
        anomalies.append((wid, day, word, trans, f"Translation contains English word(s): {found_eng}"))
        
    # 3. Sentence in word
    if len(word.split()) > 4:
        anomalies.append((wid, day, word, trans, "Word has more than 4 words (sentence?)"))

print(f"Total anomalies found: {len(anomalies)}")
for a in anomalies:
    print(a)

import sqlite3

conn = sqlite3.connect('data/duohub.db')
c = conn.cursor()

c.execute("""
    SELECT count(*) 
    FROM vocabulary 
    WHERE example_en LIKE '%Practice sentence%' 
       OR example_es LIKE '%de pr_ctica%'
""")
count = c.fetchone()[0]
print(f"Total placeholders with 'Practice sentence' or 'de práctica': {count}")

c.execute("SELECT id, word, translation, example_en, example_es FROM vocabulary WHERE id IN (535, 536, 537, 538, 539, 540)")
for r in c.fetchall():
    print(r)

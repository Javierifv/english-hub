import sqlite3

def run():
    conn = sqlite3.connect('data/duohub.db')
    cur = conn.cursor()
    cur.execute('SELECT id, day_number, word, ipa, part_of_speech, translation, definition, example_en, example_es, category FROM vocabulary ORDER BY id')
    rows = cur.fetchall()

    valid_endings = ('.', '!', '?', '"', "'", '»', '”')

    issues = []
    for r in rows:
        rid, day, word, ipa, pos, trans, definition, en, es, cat = r
        en_s = (en or '').strip()
        es_s = (es or '').strip()
        
        reasons = []
        if not es_s:
            reasons.append("ES_EMPTY")
        elif es_s[-1] not in valid_endings:
            reasons.append(f"ES_NO_FINAL_PUNCT(ends_with='{es_s[-10:]}')")

        if not en_s:
            reasons.append("EN_EMPTY")
        elif en_s[-1] not in valid_endings:
            reasons.append(f"EN_NO_FINAL_PUNCT(ends_with='{en_s[-10:]}')")

        # Check for obvious corruption in word / trans
        if len(word.split()) > 4:
            reasons.append(f"WORD_TOO_LONG('{word}')")

        if reasons:
            issues.append((r, reasons))

    print(f"Total vocabulary rows: {len(rows)}")
    print(f"Total rows with issues: {len(issues)}")
    for r, reasons in issues:
        print(f"[{r[0]}] Word: '{r[2]}' | Trans: '{r[5]}'")
        print(f"   EN: '{r[7]}'")
        print(f"   ES: '{r[8]}'")
        print(f"   Reasons: {reasons}\n")

if __name__ == '__main__':
    run()

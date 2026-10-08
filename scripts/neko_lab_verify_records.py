"""Read-only verification of this goal's known synthetic grading records."""
import json
import sqlite3
from neko_lab_stage import DB, BACKUP, ROOT


def connect(path):
    return sqlite3.connect(f'file:{path.resolve()}?mode=ro',uri=True)


def main():
    with connect(BACKUP/'study_companion.db') as original:
        baseline = original.execute('SELECT COALESCE(MAX(id),0) FROM interactions').fetchone()[0]
    with connect(DB) as current:
        rows = current.execute('''SELECT id,kind,metadata,created_at FROM interactions
            WHERE id>? AND (input_text=? OR input_text LIKE ?) ORDER BY id''',
            (baseline,'答案是 42。','设 u=3x+1，y=u^5。%')).fetchall()
    records = []
    for row in rows:
        payload = json.loads(row[2])
        evaluation = payload.get('payload') or {}
        records.append({'id':row[0],'kind':row[1],'created_at':row[3],
                        'score':evaluation.get('score'),'verdict':evaluation.get('verdict'),
                        'question_id':payload.get('question_id'),'attempt_id':payload.get('attempt_id')})
    output = {'baseline_max_id':baseline,'matching_records':records}
    if len(records) < 3 or [(row['verdict'],row['score']) for row in records[-2:]] != [('wrong',0),('correct',100)]:
        raise AssertionError('Expected new wrong=0 and correct=100 records were not persisted')
    (ROOT/'benchmarks/raw/evidence/goal-persisted-grading-records.json').write_text(
        json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output,indent=2))


if __name__ == '__main__':
    main()

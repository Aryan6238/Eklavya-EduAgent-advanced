import sqlite3
import json
from models import RunArtifact
from typing import List

DB_NAME = "eklavya.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            user_id TEXT,
            input_grade INTEGER,
            input_topic TEXT,
            status TEXT,
            data JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_run(run: RunArtifact):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Serialize the Pydantic model to JSON
    run_json = run.model_dump_json()
    
    c.execute('''
        INSERT OR REPLACE INTO runs (run_id, user_id, input_grade, input_topic, status, data, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        run.run_id,
        run.user_id,
        run.input.grade, 
        run.input.topic, 
        run.final.status if run.final else "error",
        run_json,
        run.timestamps.started_at
    ))
    conn.commit()
    conn.close()

def get_recent_runs(limit: int = 10, user_id: str = None) -> List[RunArtifact]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if user_id:
        c.execute('SELECT data FROM runs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?', (user_id, limit))
    else:
        c.execute('SELECT data FROM runs ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    
    runs = []
    for row in rows:
        try:
            data = json.loads(row['data'])
            runs.append(RunArtifact(**data))
        except Exception:
            continue
    return runs

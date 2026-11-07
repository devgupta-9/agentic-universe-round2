"""One durable writer: observations and their checkpoint commit together."""
import json
import sqlite3
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


def minute(ts):
    return int(datetime.fromisoformat(ts).timestamp() // 60)


def encode(value):
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            PRAGMA busy_timeout=30000;
            CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY,kind TEXT,n INTEGER,seconds REAL);
            CREATE TABLE IF NOT EXISTS leads(
                lead_id TEXT PRIMARY KEY,wid TEXT,person_id TEXT,campaign_id TEXT,
                created INTEGER,features TEXT,concluded INTEGER DEFAULT 0);
            CREATE INDEX IF NOT EXISTS leads_workflow ON leads(wid,created);
            CREATE TABLE IF NOT EXISTS calls(
                event_id INTEGER PRIMARY KEY,wid TEXT,minute INTEGER,lead_id TEXT,
                version INTEGER,cohort TEXT,voice TEXT,welcome TEXT,caller TEXT,prompt TEXT,
                hour INTEGER,connected INTEGER,engaged INTEGER,hallucinations INTEGER);
            CREATE INDEX IF NOT EXISTS calls_workflow ON calls(wid,minute);
            CREATE TABLE IF NOT EXISTS metrics(
                wid TEXT,bucket INTEGER,cohort TEXT,version INTEGER,voice TEXT,welcome TEXT,
                caller TEXT,prompt TEXT,hour INTEGER,dials INTEGER,connected INTEGER,
                engaged INTEGER,hallucinations INTEGER,
                PRIMARY KEY(wid,bucket,cohort,version,voice,welcome,caller,prompt,hour));
            CREATE TABLE IF NOT EXISTS audit(
                id INTEGER PRIMARY KEY,minute INTEGER,wid TEXT,kind TEXT,data TEXT);
            CREATE INDEX IF NOT EXISTS audit_workflow ON audit(wid,minute);
        """)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.db.close()

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        else:
            self.db.execute("COMMIT")

    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        self.db.execute("INSERT INTO kv VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, encode(value)))

    def audit(self, at, wid, kind, data):
        self.db.execute("INSERT INTO audit(minute,wid,kind,data) VALUES(?,?,?,?)", (at, wid, kind, encode(data)))

    def ingest(self, chunk_id, kind, events):
        if self.db.execute("SELECT 1 FROM chunks WHERE id=?", (chunk_id,)).fetchone():
            return 0
        if chunk_id <= self.get("last_chunk", -1):
            raise ValueError("Chunk order regressed; refusing to skip unseen observations")
        started = time.perf_counter()
        high_water = self.get("last_event_id", 0)
        rows, leads, concluded = [], [], []
        aggregates = defaultdict(lambda: [0, 0, 0, 0])
        seen = 0

        def flush():
            if leads:
                self.db.executemany("INSERT INTO leads(lead_id,wid,person_id,campaign_id,created,features) VALUES(?,?,?,?,?,?)", leads)
                leads.clear()
            if rows:
                self.db.executemany("INSERT INTO calls VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
                rows.clear()
            if concluded:
                self.db.executemany("UPDATE leads SET concluded=1 WHERE lead_id=?", concluded)
                concluded.clear()

        with self.transaction():
            for event in events:
                eid = event["event_id"]
                if eid <= high_water:
                    continue  # Replay of globally ordered event IDs, including history overlap.
                at = minute(event["ts"])
                wid = event.get("workflow_id", "")
                if event["type"] == "call":
                    variant = event["variant"]
                    connected, engaged = int(event["connected"]), int(event["engaged"])
                    halluc = int(bool((event.get("qa") or {}).get("hallucination_flag")))
                    identity = (wid, at // 15 * 15, event["cohort_id"], event["config_version"],
                                variant["voice"], variant["welcome_message"], variant["caller_id"],
                                variant["prompt_version"], int(event["ts"][11:13]))
                    value = aggregates[identity]
                    for i, n in enumerate((1, connected, engaged, halluc)):
                        value[i] += n
                    rows.append((eid, wid, at, event["lead_id"], identity[3], identity[2], *identity[4:],
                                 connected, engaged, halluc))
                    if engaged:
                        concluded.append((event["lead_id"],))
                elif event["type"] == "lead":
                    leads.append((event["lead_id"], wid, event["person_id"], event["campaign_id"], at, encode(event["features"])))
                else:
                    self.audit(at, wid, event["type"], event)
                high_water, seen = eid, seen + 1
                if len(rows) + len(leads) >= 5000:
                    flush()
            flush()
            self.db.executemany("""INSERT INTO metrics VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(wid,bucket,cohort,version,voice,welcome,caller,prompt,hour) DO UPDATE SET
                dials=dials+excluded.dials,connected=connected+excluded.connected,
                engaged=engaged+excluded.engaged,hallucinations=hallucinations+excluded.hallucinations""",
                ((*key, *values) for key, values in aggregates.items()))
            self.set("last_event_id", high_water)
            self.set("last_chunk", chunk_id)
            self.db.execute("INSERT INTO chunks VALUES(?,?,?,?)", (chunk_id, kind, seen, time.perf_counter() - started))
        return seen

    def counts(self, wid, since, until, group=None, **filters):
        columns = {"voice": "voice", "welcome_message": "welcome", "caller_id": "caller",
                   "prompt_version": "prompt", "cohort_id": "cohort", "hour": "hour", "version": "version"}
        if group is not None and group not in columns:
            raise ValueError("Unsupported grouping")
        conditions, params = ["wid=?", "bucket>=?", "bucket<?"], [wid, since, until]
        for key, value in filters.items():
            if key not in columns:
                raise ValueError("Unsupported filter")
            conditions.append(columns[key] + "=?")
            params.append(value)
        arm = columns[group] if group else "''"
        sql = (f"SELECT {arm} AS arm,COALESCE(SUM(dials),0) AS dials,"
               "COALESCE(SUM(connected),0) AS connected,COALESCE(SUM(engaged),0) AS engaged,"
               "COALESCE(SUM(hallucinations),0) AS hallucinations FROM metrics WHERE " + " AND ".join(conditions))
        if group:
            sql += " GROUP BY " + columns[group]
        return [dict(row) for row in self.db.execute(sql, params)]

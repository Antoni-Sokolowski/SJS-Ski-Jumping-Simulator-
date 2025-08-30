import os
import sqlite3
import sys
import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _app_root_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))


def _data_dir() -> str:
    root = _app_root_dir()
    data_path = os.path.join(root, "data")
    os.makedirs(data_path, exist_ok=True)
    return data_path


def _db_path() -> str:
    return os.path.join(_data_dir(), "history.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        # PRAGMA user_version for simple schema versioning
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                user_version INTEGER NOT NULL DEFAULT 1
            );
            """
        )
        cur.execute("INSERT OR IGNORE INTO meta(id, user_version) VALUES(1, 1);")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS competitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                hill_id TEXT,
                hill_name TEXT,
                k_point REAL,
                hs_point REAL,
                mode TEXT,
                app_version TEXT,
                created_at TEXT NOT NULL,
                finished_at TEXT
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS jumpers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                country_code TEXT
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS competition_jumpers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER NOT NULL,
                jumper_id INTEGER NOT NULL,
                bib INTEGER,
                UNIQUE(competition_id, jumper_id),
                FOREIGN KEY(competition_id) REFERENCES competitions(id) ON DELETE CASCADE,
                FOREIGN KEY(jumper_id) REFERENCES jumpers(id) ON DELETE RESTRICT
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competition_id INTEGER NOT NULL,
                round_index INTEGER NOT NULL,
                UNIQUE(competition_id, round_index),
                FOREIGN KEY(competition_id) REFERENCES competitions(id) ON DELETE CASCADE
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS jumps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id INTEGER NOT NULL,
                jumper_id INTEGER NOT NULL,
                order_index INTEGER,
                distance REAL NOT NULL,
                style_sum REAL,
                wind_points REAL,
                gate_points REAL,
                total_points REAL NOT NULL,
                notes_json TEXT,
                timing_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(round_id) REFERENCES rounds(id) ON DELETE CASCADE,
                FOREIGN KEY(jumper_id) REFERENCES jumpers(id) ON DELETE RESTRICT
            );
            """
        )

        conn.commit()
    finally:
        conn.close()


def _ensure_jumper(
    cur: sqlite3.Cursor, name: str, last_name: str, country_code: Optional[str]
) -> int:
    cur.execute(
        "SELECT id FROM jumpers WHERE name=? AND last_name=? AND country_code IS ?",
        (name, last_name, country_code),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        "INSERT INTO jumpers(name, last_name, country_code) VALUES(?,?,?)",
        (name, last_name, country_code),
    )
    return int(cur.lastrowid)


def start_competition(
    name: Optional[str],
    hill_id: Optional[str],
    hill_name: Optional[str],
    k_point: Optional[float],
    hs_point: Optional[float],
    mode: Optional[str],
    app_version: Optional[str] = None,
) -> int:
    init_db()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO competitions(name, hill_id, hill_name, k_point, hs_point, mode, app_version, created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                name,
                hill_id,
                hill_name,
                k_point,
                hs_point,
                mode,
                app_version,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        competition_id = int(cur.lastrowid)
        conn.commit()
        return competition_id
    finally:
        conn.close()


def register_participants(
    competition_id: int,
    participants: Iterable[Tuple[str, str, Optional[str]]],
) -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        bib_num = 1
        for name, last_name, country in participants:
            jumper_id = _ensure_jumper(cur, name, last_name, country)
            cur.execute(
                "INSERT OR IGNORE INTO competition_jumpers(competition_id, jumper_id, bib) VALUES(?,?,?)",
                (competition_id, jumper_id, bib_num),
            )
            bib_num += 1
        conn.commit()
    finally:
        conn.close()


def add_round(competition_id: int, round_index: int) -> int:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO rounds(competition_id, round_index) VALUES(?,?)",
            (competition_id, round_index),
        )
        # Fetch id (INSERT OR IGNORE may not set lastrowid for existing row)
        cur.execute(
            "SELECT id FROM rounds WHERE competition_id=? AND round_index=?",
            (competition_id, round_index),
        )
        row = cur.fetchone()
        conn.commit()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def add_jump(
    competition_id: int,
    round_index: int,
    jumper: Dict[str, Any],
    order_index: int,
    distance: float,
    total_points: float,
    judge_data: Optional[Dict[str, Any]] = None,
    wind_points: Optional[float] = None,
    gate_points: Optional[float] = None,
    timing_info: Optional[Dict[str, Any]] = None,
) -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        round_id = add_round(competition_id, round_index)

        name = getattr(jumper, "name", None) or getattr(jumper, "first_name", "")
        last_name = getattr(jumper, "last_name", None) or getattr(jumper, "surname", "")
        country = getattr(jumper, "nationality", None)
        jumper_id = _ensure_jumper(cur, name, last_name, country)

        style_sum: Optional[float] = None
        if judge_data and isinstance(judge_data, dict):
            try:
                style_sum = (
                    float(judge_data.get("total_score"))
                    if judge_data.get("total_score") is not None
                    else None
                )
            except Exception:
                style_sum = None

        # Sprawdź czy judge_data nie jest None przed zapisem
        judge_json = None
        if (
            judge_data is not None
            and isinstance(judge_data, dict)
            and len(judge_data) > 0
        ):
            try:
                judge_json = json.dumps(judge_data)

            except Exception:
                judge_json = None

        cur.execute(
            """
            INSERT INTO jumps(
                round_id, jumper_id, order_index, distance, style_sum, wind_points, gate_points, total_points, notes_json, timing_json, created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                round_id,
                jumper_id,
                order_index,
                float(distance),
                style_sum,
                wind_points,
                gate_points,
                float(total_points),
                judge_json,
                json.dumps(timing_info) if timing_info is not None else None,
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def finalize_competition(competition_id: int) -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE competitions SET finished_at=? WHERE id=?",
            (datetime.utcnow().isoformat(timespec="seconds"), competition_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_competitions(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    init_db()
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, name, hill_name, k_point, hs_point, mode, created_at, finished_at
            FROM competitions
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_competition_detail(competition_id: int) -> Dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM competitions WHERE id=?", (competition_id,))
        comp = cur.fetchone()
        if not comp:
            return {}

        cur.execute(
            "SELECT id, round_index FROM rounds WHERE competition_id=? ORDER BY round_index",
            (competition_id,),
        )
        rounds = [dict(r) for r in cur.fetchall()]

        result_rounds: List[Dict[str, Any]] = []
        for r in rounds:
            cur.execute(
                """
                SELECT j.id, j.order_index, j.distance, j.style_sum, j.wind_points, j.gate_points, j.total_points, j.notes_json, j.timing_json, j.created_at,
                       ju.name, ju.last_name, ju.country_code
                FROM jumps j
                JOIN jumpers ju ON ju.id = j.jumper_id
                WHERE j.round_id = ?
                ORDER BY j.order_index
                """,
                (r["id"],),
            )
            jumps = []
            for row in cur.fetchall():
                d = dict(row)
                if d.get("notes_json"):
                    try:
                        d["notes_json"] = json.loads(d["notes_json"])  # type: ignore[assignment]

                    except Exception:
                        pass
                if d.get("timing_json"):
                    try:
                        d["timing_json"] = json.loads(d["timing_json"])  # type: ignore[assignment]
                    except Exception:
                        pass
                jumps.append(d)
            result_rounds.append({"round_index": r["round_index"], "jumps": jumps})

        return {"competition": dict(comp), "rounds": result_rounds}
    finally:
        conn.close()


def clear_history() -> None:
    """Clear all competition history data"""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM jumps")
        cur.execute("DELETE FROM rounds")
        cur.execute("DELETE FROM competition_jumpers")
        cur.execute("DELETE FROM jumpers")
        cur.execute("DELETE FROM competitions")
        cur.execute("DELETE FROM meta")
        # Reset SQLite sequence to start from 1 again
        cur.execute("DELETE FROM sqlite_sequence WHERE name='competitions'")
        conn.commit()
    finally:
        conn.close()


def update_competition_name(competition_id: int, new_name: str) -> bool:
    """Update the name of a competition"""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE competitions SET name=? WHERE id=?",
            (new_name, competition_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_competition(competition_id: int) -> bool:
    """Delete a specific competition and all its related data"""
    conn = _connect()
    try:
        cur = conn.cursor()

        # Get round IDs for this competition
        cur.execute("SELECT id FROM rounds WHERE competition_id=?", (competition_id,))
        round_ids = [row[0] for row in cur.fetchall()]

        # Delete jumps for all rounds of this competition
        if round_ids:
            placeholders = ",".join("?" * len(round_ids))
            cur.execute(
                f"DELETE FROM jumps WHERE round_id IN ({placeholders})", round_ids
            )

        # Delete rounds
        cur.execute("DELETE FROM rounds WHERE competition_id=?", (competition_id,))

        # Delete competition jumpers
        cur.execute(
            "DELETE FROM competition_jumpers WHERE competition_id=?", (competition_id,)
        )

        # Delete the competition
        cur.execute("DELETE FROM competitions WHERE id=?", (competition_id,))

        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

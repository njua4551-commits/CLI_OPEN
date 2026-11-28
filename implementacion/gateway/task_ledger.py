"""Private, single-owner SQLite ledger for one authorized loopback task."""
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import stat
import time


def connect(path):
    return sqlite3.connect(path.absolute().as_uri() + "?mode=rw", uri=True)


class Ledger:
    @classmethod
    @contextmanager
    def open(cls, path, identity, settings, seconds, *, create=False, owner=None, credential=None):
        if owner is not None and (
            not re.fullmatch(r"ses_[A-Za-z0-9_-]{1,128}", owner[0])
            or not re.fullmatch(r"wrk_[A-Za-z0-9_-]{1,128}", owner[1])
            or not isinstance(credential, bytes)
        ):
            raise ValueError("invalid task owner profile")
        path = Path(path)
        parent = path.parent.lstat()
        if (not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identity)
                or not stat.S_ISDIR(parent.st_mode)
                or parent.st_uid != os.geteuid() or parent.st_mode & 0o077):
            raise ValueError("invalid task identity or state directory")
        flags = os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK
        fd = os.open(path, flags | (os.O_CREAT | os.O_EXCL if create else 0), 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1):
                raise ValueError("unsafe task state file")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            db = connect(path)
            try:
                ledger = cls(db, identity, settings, seconds, create, owner, credential)
            finally:
                db.close()
            ledger.path = path
            yield ledger
        finally:
            os.close(fd)

    def __init__(self, db, identity, settings, seconds, create, owner, credential):
        self.requests, self.input_bytes, self.output_tokens, self.model, self.port = settings
        if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise ValueError("invalid task database")
        if create:
            now = time.time()
            with db:
                db.executescript("""
                    CREATE TABLE task (
                        identity TEXT PRIMARY KEY, request_limit INTEGER NOT NULL,
                        byte_limit INTEGER NOT NULL, token_limit INTEGER NOT NULL,
                        model TEXT NOT NULL, port INTEGER NOT NULL, seconds INTEGER NOT NULL,
                        started REAL NOT NULL, expires REAL NOT NULL,
                        closed INTEGER NOT NULL DEFAULT 0 CHECK(closed IN (0, 1))
                    );
                    CREATE TABLE operation (
                        id INTEGER PRIMARY KEY,
                        input_bytes INTEGER NOT NULL CHECK(input_bytes > 0),
                        output_limit INTEGER NOT NULL CHECK(output_limit > 0),
                        status TEXT NOT NULL CHECK(status IN
                            ('reserved', 'uncertain', 'failed', 'cancelled', 'complete')),
                        prompt_tokens INTEGER CHECK(prompt_tokens >= 0),
                        completion_tokens INTEGER CHECK(completion_tokens >= 0)
                    );
                """)
                db.execute("INSERT INTO task VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                           (identity, *settings, seconds, now, now + seconds))
                if owner is not None:
                    db.execute("PRAGMA user_version = 1")
                    db.execute("CREATE TABLE task_owner (session TEXT NOT NULL, workspace TEXT NOT NULL)")
                    db.execute("INSERT INTO task_owner VALUES (?, ?)", owner)
                    db.execute("CREATE TABLE listener_credential (digest BLOB NOT NULL PRIMARY KEY)")
        if db.execute("PRAGMA user_version").fetchone() != (int(owner is not None),):
            raise ValueError("task ownership mode mismatch")
        rows = db.execute("SELECT * FROM task").fetchall()
        if len(rows) != 1:
            raise ValueError("invalid task state")
        *saved, started, expires, closed = rows[0]
        if (tuple(saved) != (identity, *settings, seconds)
                or closed != 0 or expires != started + seconds or not started <= time.time() < expires):
            raise ValueError("task profile mismatch, closed or expired")
        if any(used > limit for used, limit in zip(self.reserved(db), settings[:3])):
            raise ValueError("inconsistent persisted budget")
        self.expires = expires
        with db:
            if owner is not None:
                if db.execute("SELECT session, workspace FROM task_owner LIMIT 2").fetchall() != [tuple(owner)]:
                    raise ValueError("task owner mismatch")
                digest = hashlib.sha256(credential).digest()
                if db.execute("INSERT OR IGNORE INTO listener_credential VALUES (?)", (digest,)).rowcount != 1:
                    raise ValueError("task listener credential was already used")
            db.execute("UPDATE operation SET status = 'uncertain' WHERE status = 'reserved'")

    @staticmethod
    def reserved(db):
        return db.execute("""
            SELECT count(*), coalesce(sum(input_bytes), 0), coalesce(sum(output_limit), 0)
            FROM operation
        """).fetchone()

    @contextmanager
    def connection(self):
        db = connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, size, tokens):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            requests, input_bytes, output_tokens = self.reserved(db)
            if (db.execute("SELECT closed FROM task").fetchone() != (0,)
                    or time.time() >= self.expires or requests >= self.requests
                    or input_bytes + size > self.input_bytes or output_tokens + tokens > self.output_tokens):
                return None
            return db.execute(
                "INSERT INTO operation (input_bytes, output_limit, status) VALUES (?, ?, 'reserved')",
                (size, tokens),
            ).lastrowid

    def finish(self, operation, status, usage):
        with self.connection() as db:
            if db.execute(
                """UPDATE operation SET status = ?, prompt_tokens = ?, completion_tokens = ?
                   WHERE id = ? AND status = 'reserved'""", (status, *usage, operation)
            ).rowcount != 1:
                raise ValueError("operation is not reserved")
            if usage[1] is not None and db.execute(
                "SELECT completion_tokens > output_limit FROM operation WHERE id = ?", (operation,)
            ).fetchone() == (1,):
                db.execute("UPDATE task SET closed = 1")

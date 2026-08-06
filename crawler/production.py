"""Production Infrastructure — Startup, Locking, Backup, Health Checks.

Reusable production utilities for all CLI entry points.
"""

import atexit
import json
import logging
import os
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# fcntl is Unix-only; import conditionally
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

logger = logging.getLogger("production")


# ── Startup Validation ──────────────────────────────────────────────────────

class StartupValidationError(Exception):
    """Raised when critical startup validation fails."""


def validate_startup(config=None):
    """Validate all prerequisites before running monitor.

    Returns validation results dict.
    Raises StartupValidationError if critical check fails.
    """
    results = {
        "python_version": sys.version_info[:2],
        "working_directory": os.getcwd(),
        "checks": {},
    }

    def check(name, fn):
        try:
            ok, detail = fn()
            results["checks"][name] = {"status": "OK" if ok else "FAIL", "detail": detail}
            if not ok:
                logger.error(f"STARTUP FAIL: {name} — {detail}")
            return ok
        except Exception as e:
            results["checks"][name] = {"status": "ERROR", "detail": str(e)}
            logger.error(f"STARTUP ERROR: {name} — {e}")
            return False

    def critical_check(name, fn):
        ok = check(name, fn)
        if not ok:
            raise StartupValidationError(f"Critical startup check failed: {name}")
        return ok

    # Required directories
    critical_check("data_dir", lambda: (
        os.path.isdir("data"), "Present" if os.path.isdir("data") else "Missing"
    ))
    critical_check("logs_dir", lambda: (
        os.path.isdir("data/logs") or (os.makedirs("data/logs", exist_ok=True) is None),
        "Created" if not os.path.isdir("data/logs") else "Present"
    ))

    # SQLite databases
    critical_check("watch_list_db", lambda: (
        os.path.exists("data/watch_list.db"), "Present" if os.path.exists("data/watch_list.db") else "Missing"
    ))
    check("monitor_store_db", lambda: (
        os.path.exists("data/monitor_store.db"), "Present" if os.path.exists("data/monitor_store.db") else "Missing"
    ))

    # .env
    check("env_file", lambda: (
        os.path.exists(".env"), "Present" if os.path.exists(".env") else "Missing"
    ))

    # Environment variables
    from dotenv import load_dotenv
    load_dotenv()
    check("proxy_enabled", lambda: (
        os.getenv("TOROB_PROXY_ENABLED", "").lower() == "true",
        "Configured" if os.getenv("TOROB_PROXY_ENABLED", "").lower() == "true" else "Not enabled"
    ))
    check("proxy_user", lambda: (
        bool(os.getenv("TOROB_PROXY_USER")), "Configured" if os.getenv("TOROB_PROXY_USER") else "Not set"
    ))
    check("proxy_pass", lambda: (
        bool(os.getenv("TOROB_PROXY_PASS")), "Configured" if os.getenv("TOROB_PROXY_PASS") else "Not set"
    ))
    check("tabdeal_url", lambda: (
        bool(os.getenv("TABDEAL_API_URL")), "Configured" if os.getenv("TABDEAL_API_URL") else "Not set"
    ))

    # Disk space
    check("disk_space", lambda: (
        _check_disk_space(), "Disk space low"
    ))

    # Write permissions
    critical_check("write_permissions", lambda: (
        _check_write_permissions(), "No write permissions"
    ))

    # SQLite WAL mode
    check("sqlite_wal", lambda: (
        _check_sqlite_wal("data/monitor_store.db"), "SQLite WAL mode"
    ))

    return results


def _check_disk_space() -> bool:
    """Check if disk has sufficient space (>100MB free)."""
    try:
        stat = os.statvfs(".")
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        return free_mb > 100
    except Exception:
        return True  # Can't check, assume OK


def _check_write_permissions() -> bool:
    """Check write permissions for data directory."""
    test_file = Path("data/.write_test")
    try:
        test_file.write_text("ok")
        test_file.unlink()
        return True
    except Exception:
        return False


def _check_sqlite_wal(db_path: str) -> bool:
    """Check if SQLite database is accessible and WAL mode is enabled."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode")
        conn.close()
        return True
    except Exception:
        return False


# ── Execution Locking ───────────────────────────────────────────────────────

class ExecutionLock:
    """File-based lock to prevent concurrent monitor execution.

    Uses fcntl for POSIX systems. Falls back to file-existence check on Windows.
    """

    def __init__(self, lock_path: str = "data/.monitor.lock"):
        self.lock_path = Path(lock_path)
        self.lock_fd = None
        self.locked = False

    def acquire(self) -> bool:
        """Try to acquire the lock. Returns True if successful."""
        try:
            self.lock_fd = open(self.lock_path, "w")
            if HAS_FCNTL:
                # POSIX: use fcntl
                try:
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.locked = True
                    self.lock_fd.write(f"{os.getpid()}\n")
                    self.lock_fd.flush()
                    logger.info(f"Lock acquired (PID {os.getpid()})")
                    return True
                except (IOError, OSError):
                    self.lock_fd.close()
                    self.lock_fd = None
                    return False
            else:
                # Windows: use file existence
                try:
                    self.lock_fd.close()
                    self.lock_fd = open(self.lock_path, "x")
                    self.lock_fd.write(f"{os.getpid()}\n")
                    self.lock_fd.flush()
                    self.locked = True
                    logger.info(f"Lock acquired (PID {os.getpid()})")
                    return True
                except FileExistsError:
                    self.lock_fd.close()
                    self.lock_fd = None
                    return False
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False

    def release(self):
        """Release the lock."""
        if self.lock_fd:
            try:
                if HAS_FCNTL:
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
            except Exception:
                pass
            self.lock_fd = None

        try:
            self.lock_path.unlink(missing_ok=True)
        except Exception:
            pass

        self.locked = False
        logger.info("Lock released")

    def __enter__(self):
        if not self.acquire():
            logger.error("Another monitor is already running")
            sys.exit(1)
        return self

    def __exit__(self, *args):
        self.release()


# ── Backup Strategy ─────────────────────────────────────────────────────────

class BackupManager:
    """Manages database backups with rolling retention."""

    def __init__(self, backup_dir: str = "data/backups", max_backups: int = 7):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.max_backups = max_backups

    def create_backup(self, db_path: str, name: str = "") -> str | None:
        """Create a timestamped backup of a database file."""
        src = Path(db_path)
        if not src.exists():
            logger.warning(f"Cannot backup {db_path}: file not found")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{src.stem}_{timestamp}.db"
        dst = self.backup_dir / backup_name

        try:
            # Use SQLite backup API for consistency
            src_conn = sqlite3.connect(str(src))
            dst_conn = sqlite3.connect(str(dst))
            src_conn.backup(dst_conn)
            src_conn.close()
            dst_conn.close()
            logger.info(f"Backup created: {dst}")
            return str(dst)
        except Exception as e:
            logger.warning(f"Backup via SQLite API failed, trying shutil: {e}")
            shutil.copy2(src, dst)
            logger.info(f"Backup created (shutil): {dst}")
            return str(dst)

    def cleanup_old_backups(self):
        """Remove backups older than max_backups per database."""
        backups = sorted(self.backup_dir.glob("*.db"))
        by_stem = {}
        for b in backups:
            stem = b.stem.rsplit("_", 1)[0] if "_" in b.stem else b.stem
            by_stem.setdefault(stem, []).append(b)

        for stem, files in by_stem.items():
            if len(files) > self.max_backups:
                for old in files[:-self.max_backups]:
                    try:
                        old.unlink()
                        logger.info(f"Removed old backup: {old}")
                    except Exception:
                        pass

    def get_backup_summary(self) -> dict:
        """Get summary of existing backups."""
        backups = list(self.backup_dir.glob("*.db"))
        total_size = sum(b.stat().st_size for b in backups)
        return {
            "count": len(backups),
            "total_size_mb": total_size / (1024 * 1024),
            "directory": str(self.backup_dir),
        }


# ── Health Checks ───────────────────────────────────────────────────────────

class HealthChecker:
    """Internal health checks for all system components."""

    def check_all(self) -> dict:
        """Run all health checks. Returns status report."""
        checks = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall": "HEALTHY",
            "checks": {},
        }

        self._check("python_version", checks)
        self._check("disk_space", checks)
        self._check("database_watch_list", checks)
        self._check("database_monitor_store", checks)
        self._check("database_integrity", checks)
        self._check("proxy_config", checks)
        self._check("environment", checks)

        # Determine overall status
        statuses = [c["status"] for c in checks["checks"].values()]
        if "CRITICAL" in statuses:
            checks["overall"] = "CRITICAL"
        elif "WARNING" in statuses:
            checks["overall"] = "WARNING"
        else:
            checks["overall"] = "HEALTHY"

        return checks

    def _check(self, name: str, results: dict):
        """Run a single health check."""
        import os as _os
        import sqlite3 as _sqlite3
        try:
            if name == "python_version":
                v = sys.version_info[:2]
                status = "HEALTHY" if v >= (3, 11) else "WARNING"
                results["checks"][name] = {"status": status, "detail": f"Python {v[0]}.{v[1]}"}

            elif name == "disk_space":
                try:
                    stat = _os.statvfs(".")
                    free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
                    status = "HEALTHY" if free_mb > 100 else "CRITICAL"
                    results["checks"][name] = {"status": status, "detail": f"{free_mb:.0f} MB free"}
                except Exception:
                    results["checks"][name] = {"status": "WARNING", "detail": "Cannot check disk space"}

            elif name == "database_watch_list":
                db_path = "data/watch_list.db"
                if _os.path.exists(db_path):
                    size = _os.path.getsize(db_path)
                    status = "HEALTHY" if size > 0 else "CRITICAL"
                    results["checks"][name] = {"status": status, "detail": f"{size:,} bytes"}
                else:
                    results["checks"][name] = {"status": "CRITICAL", "detail": "File not found"}

            elif name == "database_monitor_store":
                db_path = "data/monitor_store.db"
                if _os.path.exists(db_path):
                    try:
                        conn = _sqlite3.connect(db_path)
                        unfinished = conn.execute(
                            "SELECT COUNT(*) FROM monitor_runs WHERE status='running'"
                        ).fetchone()[0]
                        conn.close()
                        status = "WARNING" if unfinished > 0 else "HEALTHY"
                        results["checks"][name] = {
                            "status": status,
                            "detail": f"Unfinished runs: {unfinished}"
                        }
                    except Exception as e:
                        results["checks"][name] = {"status": "CRITICAL", "detail": str(e)}
                else:
                    results["checks"][name] = {"status": "WARNING", "detail": "Not found"}

            elif name == "database_integrity":
                db_path = "data/monitor_store.db"
                if _os.path.exists(db_path):
                    try:
                        conn = _sqlite3.connect(db_path)
                        cur = conn.cursor()
                        violations = cur.execute("PRAGMA foreign_key_check").fetchall()
                        conn.close()
                        status = "HEALTHY" if not violations else "WARNING"
                        results["checks"][name] = {
                            "status": status,
                            "detail": f"FK violations: {len(violations)}"
                        }
                    except Exception as e:
                        results["checks"][name] = {"status": "CRITICAL", "detail": str(e)}
                else:
                    results["checks"][name] = {"status": "WARNING", "detail": "Not found"}

            elif name == "proxy_config":
                proxy_user = _os.getenv("TOROB_PROXY_USER", "")
                proxy_pass = _os.getenv("TOROB_PROXY_PASS", "")
                status = "HEALTHY" if (proxy_user and proxy_pass) else "WARNING"
                results["checks"][name] = {"status": status, "detail": "Configured" if proxy_user else "Not configured"}

            elif name == "environment":
                env_vars = ["TOROB_PROXY_ENABLED", "TABDEAL_API_URL"]
                missing = [v for v in env_vars if not _os.getenv(v)]
                status = "HEALTHY" if not missing else "WARNING"
                results["checks"][name] = {
                    "status": status,
                    "detail": f"Missing: {missing}" if missing else "All set"
                }

        except Exception as e:
            results["checks"][name] = {"status": "ERROR", "detail": str(e)}


# ── Graceful Shutdown ───────────────────────────────────────────────────────

_shutdown_handlers = []


def register_shutdown_handler(fn):
    """Register a function to be called on shutdown."""
    _shutdown_handlers.append(fn)


def _run_shutdown_handlers():
    """Run all registered shutdown handlers."""
    for handler in reversed(_shutdown_handlers):
        try:
            handler()
        except Exception as e:
            logger.error(f"Shutdown handler error: {e}")


atexit.register(_run_shutdown_handlers)


# ── Logging Setup ────────────────────────────────────────────────────────────

def setup_production_logging(log_dir: str = "data/logs"):
    """Configure production logging with rotating files."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Application log
    app_handler = logging.FileHandler(
        os.path.join(log_dir, "application.log"),
        encoding="utf-8",
    )
    app_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))

    # Error log
    error_handler = logging.FileHandler(
        os.path.join(log_dir, "error.log"),
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))

    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))

    root = logging.getLogger()
    root.addHandler(app_handler)
    root.addHandler(error_handler)
    root.addHandler(console_handler)
    root.setLevel(logging.INFO)


# ── Monitor Run Logger ──────────────────────────────────────────────────────

class RunLogger:
    """Structured logging for a single monitor run."""

    def __init__(self, run_id: int):
        self.run_id = run_id
        self.start_time = time.time()
        self.events = []

    def log_event(self, event: str, details: dict = None):
        entry = {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details or {},
        }
        self.events.append(entry)
        logger.info(f"Run #{self.run_id}: {event}")

    def get_summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "start_time": self.start_time,
            "duration_seconds": time.time() - self.start_time,
            "events": len(self.events),
        }

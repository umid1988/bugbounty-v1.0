"""
Rate limiting va Pipeline holat boshqaruvi.

RateLimiter  — so'rovlar orasida kutish, API limitini kuzatish.
PipelineState — har bir bosqich natijasini saqlaydi, xato bo'lsa davom etadi.
"""
import time
import json
import threading
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from enum import Enum


# ═══════════════════════════════════════════════════════════
#  RATE LIMITER
# ═══════════════════════════════════════════════════════════
class RateLimiter:
    """Thread-safe rate limiter."""

    def __init__(self, requests_per_second: float = 2.0):
        self._rps      = requests_per_second
        self._min_gap  = 1.0 / requests_per_second if requests_per_second > 0 else 0
        self._last     = 0.0
        self._lock     = threading.Lock()
        self._counters: Dict[str, int] = {}

    def wait(self, key: str = "default"):
        """Keyingi so'rovdan oldin kerak bo'lsa kutadi."""
        with self._lock:
            now     = time.monotonic()
            elapsed = now - self._last
            if elapsed < self._min_gap:
                time.sleep(self._min_gap - elapsed)
            self._last = time.monotonic()
            self._counters[key] = self._counters.get(key, 0) + 1

    def count(self, key: str = "default") -> int:
        return self._counters.get(key, 0)


class ShodanLimiter:
    """
    Shodan bepul plan: 100 so'rov/oy.
    Ishlatilgan sonni disk ga saqlaydi.
    """
    STATE_FILE = Path(".shodan_usage.json")

    def __init__(self, limit: int = 100, delay: float = 1.0):
        self._limit = limit
        self._delay = delay
        self._lock  = threading.Lock()
        self._used  = self._load()

    def _load(self) -> int:
        try:
            if self.STATE_FILE.exists():
                data = json.loads(self.STATE_FILE.read_text())
                # Oy o'zgarsa nolga qaytarish
                import datetime
                saved_month = data.get("month", "")
                cur_month   = datetime.date.today().strftime("%Y-%m")
                if saved_month == cur_month:
                    return data.get("used", 0)
        except Exception:
            pass
        return 0

    def _save(self):
        import datetime
        self.STATE_FILE.write_text(json.dumps({
            "used":  self._used,
            "month": datetime.date.today().strftime("%Y-%m"),
            "limit": self._limit,
        }))

    def check_and_use(self) -> bool:
        """
        Limitni tekshiradi va bittasini sarflaydi.
        Returns False agar limit tugagan.
        """
        with self._lock:
            if self._used >= self._limit:
                return False
            self._used += 1
            self._save()
            time.sleep(self._delay)
            return True

    @property
    def remaining(self) -> int:
        return max(0, self._limit - self._used)

    @property
    def used(self) -> int:
        return self._used


# ═══════════════════════════════════════════════════════════
#  PIPELINE STATE
# ═══════════════════════════════════════════════════════════
class StepStatus(Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    FAILED   = "failed"
    SKIPPED  = "skipped"


@dataclass
class StepResult:
    name:    str
    status:  StepStatus          = StepStatus.PENDING
    output:  Any                 = None   # topilgan natijalar
    error:   Optional[str]       = None
    count:   int                 = 0      # topilgan elementlar soni
    elapsed: float               = 0.0   # sekundlarda


class PipelineState:
    """
    Pipeline bosqichlarini kuzatadi.
    Xato bo'lsa continue_on_error=True bo'lsa davom etadi.
    Natijalarni disk ga saqlaydi (qayta ishga tushirishda davom etish uchun).
    """
    STATE_FILE = Path(".pipeline_state.json")

    def __init__(self, target: str, continue_on_error: bool = True):
        self.target           = target
        self.continue_on_error = continue_on_error
        self.steps: Dict[str, StepResult] = {}
        self._load()

    def _load(self):
        """Oldingi natijalarni yuklash (resume support)."""
        try:
            if self.STATE_FILE.exists():
                data = json.loads(self.STATE_FILE.read_text())
                if data.get("target") == self.target:
                    for name, s in data.get("steps", {}).items():
                        self.steps[name] = StepResult(
                            name=name,
                            status=StepStatus(s["status"]),
                            output=s.get("output"),
                            error=s.get("error"),
                            count=s.get("count", 0),
                            elapsed=s.get("elapsed", 0.0),
                        )
        except Exception:
            pass

    def save(self):
        data = {
            "target": self.target,
            "steps": {
                name: {
                    "status":  r.status.value,
                    "output":  r.output,
                    "error":   r.error,
                    "count":   r.count,
                    "elapsed": r.elapsed,
                }
                for name, r in self.steps.items()
            }
        }
        self.STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def start(self, name: str):
        self.steps[name] = StepResult(name=name, status=StepStatus.RUNNING)
        self.save()

    def done(self, name: str, output: Any = None, count: int = 0, elapsed: float = 0.0):
        if name in self.steps:
            self.steps[name].status  = StepStatus.DONE
            self.steps[name].output  = output
            self.steps[name].count   = count
            self.steps[name].elapsed = elapsed
        self.save()

    def fail(self, name: str, error: str, elapsed: float = 0.0):
        if name in self.steps:
            self.steps[name].status  = StepStatus.FAILED
            self.steps[name].error   = error
            self.steps[name].elapsed = elapsed
        self.save()
        if not self.continue_on_error:
            raise RuntimeError(f"Pipeline to'xtatildi: {name} — {error}")

    def skip(self, name: str, reason: str = ""):
        self.steps[name] = StepResult(
            name=name, status=StepStatus.SKIPPED, error=reason
        )
        self.save()

    def is_done(self, name: str) -> bool:
        return self.steps.get(name, StepResult("")).status == StepStatus.DONE

    def get_output(self, name: str) -> Any:
        return self.steps.get(name, StepResult("")).output

    def summary(self) -> str:
        lines = []
        icons = {
            StepStatus.DONE:    "✓",
            StepStatus.FAILED:  "✗",
            StepStatus.SKIPPED: "⊘",
            StepStatus.RUNNING: "⟳",
            StepStatus.PENDING: "·",
        }
        for name, r in self.steps.items():
            icon = icons.get(r.status, "?")
            extra = f"({r.count} ta)" if r.count else ""
            err   = f" — {r.error}" if r.error else ""
            lines.append(f"  [{icon}] {name:25s} {extra}{err}")
        return "\n".join(lines)

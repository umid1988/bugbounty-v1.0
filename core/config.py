"""
Konfiguratsiya va holat boshqaruvi.
config.json dan o'qiydi, yo'q bo'lsa default yaratadi.
"""
import json
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional

CONFIG_FILE = Path("config.json")

@dataclass
class ToolPaths:
    subfinder: str = "subfinder"
    httpx:     str = "httpx"
    nuclei:    str = "nuclei"
    amass:     str = "amass"
    dnsx:      str = "dnsx"

@dataclass
class RateLimit:
    shodan_requests_per_month: int = 100   # bepul plan
    shodan_used:               int = 0
    requests_per_second:       float = 2.0  # HTTP so'rovlar
    shodan_delay_seconds:      float = 1.0

@dataclass
class Config:
    # API kalitlari
    shodan_api_key:  str = ""

    # Performance
    threads:         int   = 20
    timeout:         int   = 8
    retries:         int   = 2

    # Fayl yo'llari
    output_dir:      str   = "bb_output"
    wordlist_dir:    str   = "wordlists"

    # Scope — faqat shu domenlar tekshiriladi
    scope_domains:   List[str] = field(default_factory=list)
    scope_wildcards: List[str] = field(default_factory=list)  # *.example.com

    # Tool yo'llari
    tools:           ToolPaths = field(default_factory=ToolPaths)

    # Rate limiting
    rate:            RateLimit = field(default_factory=RateLimit)

    # Pipeline davom etsin (xato bo'lsa)
    continue_on_error: bool = True

    # Hisobot formati
    report_md:   bool = True
    report_json: bool = True


def load() -> Config:
    """config.json dan yuklaydi yoki default qaytaradi."""
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            cfg = Config()
            for k, v in raw.items():
                if k == "tools" and isinstance(v, dict):
                    cfg.tools = ToolPaths(**{kk: vv for kk, vv in v.items()
                                             if hasattr(ToolPaths, kk)})
                elif k == "rate" and isinstance(v, dict):
                    cfg.rate = RateLimit(**{kk: vv for kk, vv in v.items()
                                            if hasattr(RateLimit, kk)})
                elif hasattr(cfg, k):
                    setattr(cfg, k, v)
            return cfg
        except Exception as e:
            print(f"[!] config.json xatosi: {e} — default ishlatilmoqda")
    return Config()


def save(cfg: Config):
    """Config ni json ga yozadi."""
    data = asdict(cfg)
    CONFIG_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def check_tools(cfg: Config) -> dict:
    """
    Tashqi toollar mavjudligini tekshiradi.
    Returns: {'subfinder': True, 'httpx': False, ...}
    """
    result = {}
    for name in ("subfinder", "httpx", "nuclei", "amass", "dnsx"):
        path = getattr(cfg.tools, name)
        result[name] = shutil.which(path) is not None
    return result

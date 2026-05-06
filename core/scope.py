"""
Scope kontroli — faqat ruxsat berilgan targetlarda ishlash.
Bu modul BARCHA scan funksiyalaridan oldin chaqiriladi.
"""
import re
from typing import List, Optional
from urllib.parse import urlparse


class ScopeError(Exception):
    """Target scope dan tashqarida."""
    pass


class ScopeManager:
    def __init__(self, domains: List[str], wildcards: List[str]):
        """
        domains:   ['example.com', 'api.example.com']
        wildcards: ['*.example.com', '*.corp.org']
        """
        self._exact:    set  = {d.lower().strip() for d in domains if d.strip()}
        self._wildcards: List[str] = [
            w.lower().strip().lstrip("*.")
            for w in wildcards if w.strip()
        ]

    @property
    def is_empty(self) -> bool:
        return not self._exact and not self._wildcards

    def check(self, target: str) -> bool:
        """
        target: domen yoki URL.
        Returns True agar scope ichida, False aks holda.
        """
        if self.is_empty:
            return False   # Scope berilmagan — hech narsa ruxsat emas

        domain = self._extract_domain(target)
        if not domain:
            return False

        # Aniq moslik
        if domain in self._exact:
            return True

        # Subdomain moslik: *.example.com → sub.example.com
        for wc in self._wildcards:
            if domain == wc or domain.endswith("." + wc):
                return True

        return False

    def validate(self, target: str):
        """Scope dan tashqarida bo'lsa ScopeError chiqaradi."""
        if not self.check(target):
            domain = self._extract_domain(target)
            raise ScopeError(
                f"'{domain}' scope dan tashqarida! "
                f"Faqat ruxsat berilgan domenlar skanlanadi.\n"
                f"  Ruxsat berilganlar: {self._exact | set(self._wildcards)}\n"
                f"  config.json → scope_domains va scope_wildcards ni to'ldiring."
            )

    def filter(self, targets: List[str]) -> tuple:
        """
        Ro'yxatni scope bo'yicha filterlaydi.
        Returns: (in_scope, out_of_scope)
        """
        in_scope, out_of_scope = [], []
        for t in targets:
            (in_scope if self.check(t) else out_of_scope).append(t)
        return in_scope, out_of_scope

    @staticmethod
    def _extract_domain(target: str) -> str:
        target = target.strip().lower()
        if "://" in target:
            parsed = urlparse(target)
            host = parsed.hostname or ""
        else:
            # IP:port yoki domain:port
            host = target.split(":")[0]
        # IP manzillarini ham qabul qilish
        return host

    def summary(self) -> str:
        lines = []
        if self._exact:
            lines.append(f"  Aniq domenlar ({len(self._exact)}): " +
                         ", ".join(sorted(self._exact)[:5]) +
                         ("..." if len(self._exact) > 5 else ""))
        if self._wildcards:
            lines.append(f"  Wildcard ({len(self._wildcards)}): " +
                         ", ".join(f"*.{w}" for w in self._wildcards[:5]))
        return "\n".join(lines) if lines else "  (bo'sh — hech narsa skanlanmaydi!)"


def from_config(cfg) -> ScopeManager:
    return ScopeManager(
        domains=cfg.scope_domains,
        wildcards=cfg.scope_wildcards,
    )

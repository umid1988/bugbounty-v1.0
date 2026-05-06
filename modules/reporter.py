"""
Markdown va JSON hisobot generatori.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "unknown": 5}
SEVERITY_EMOJI = {
    "critical": "🔴", "high": "🟠", "medium": "🟡",
    "low": "🟢", "info": "ℹ️",  "unknown": "⚪",
}


class ReportData:
    """Hisobot uchun to'plangan ma'lumotlar."""

    def __init__(self, target: str, scope: List[str]):
        self.target       = target
        self.scope        = scope
        self.started_at   = datetime.now()
        self.finished_at: Optional[datetime] = None

        self.subdomains:   List[str]  = []
        self.live_hosts:   List[dict] = []   # httpx output
        self.findings:     List[dict] = []   # nuclei output
        self.s3_buckets:   List[str]  = []
        self.secrets:      List[dict] = []   # regex topilmalar
        self.pipeline_log: List[str]  = []
        self.errors:       List[str]  = []

    def add_finding(self, finding: dict):
        self.findings.append(finding)

    def add_secret(self, secret_type: str, value: str, source: str):
        self.secrets.append({
            "type": secret_type, "value": value[:60] + "...",
            "source": source, "found_at": datetime.now().isoformat()
        })

    def finish(self):
        self.finished_at = datetime.now()

    @property
    def duration(self) -> str:
        if not self.finished_at:
            return "davom etmoqda"
        d = self.finished_at - self.started_at
        m, s = divmod(int(d.total_seconds()), 60)
        return f"{m}m {s}s"

    @property
    def severity_counts(self) -> Dict[str, int]:
        counts = {k: 0 for k in SEVERITY_ORDER}
        for f in self.findings:
            sev = f.get("info", {}).get("severity", "unknown").lower()
            counts[sev] = counts.get(sev, 0) + 1
        return counts

    def sorted_findings(self) -> List[dict]:
        return sorted(
            self.findings,
            key=lambda f: SEVERITY_ORDER.get(
                f.get("info", {}).get("severity", "unknown").lower(), 5)
        )


def generate_markdown(data: ReportData, output_path: Path) -> Path:
    """To'liq Markdown hisobot yozadi."""
    lines = []
    now = data.finished_at or datetime.now()

    # ── SARLAVHA ─────────────────────────────────────────
    lines += [
        f"# 🐛 Bug Bounty Hisobot",
        f"",
        f"| | |",
        f"|---|---|",
        f"| **Target** | `{data.target}` |",
        f"| **Scope** | {', '.join(data.scope) or '—'} |",
        f"| **Boshlangan** | {data.started_at.strftime('%Y-%m-%d %H:%M')} |",
        f"| **Tugagan** | {now.strftime('%Y-%m-%d %H:%M')} |",
        f"| **Davomiylik** | {data.duration} |",
        f"",
    ]

    # ── XULOSA ───────────────────────────────────────────
    sc = data.severity_counts
    lines += [
        "## 📊 Xulosa",
        "",
        "| Jiddiylik | Soni |",
        "|-----------|------|",
    ]
    for sev, emoji in SEVERITY_EMOJI.items():
        cnt = sc.get(sev, 0)
        if cnt:
            lines.append(f"| {emoji} {sev.capitalize()} | **{cnt}** |")
    lines += [
        f"| 🌐 Subdomainlar | {len(data.subdomains)} |",
        f"| 🟢 Tirik hostlar | {len(data.live_hosts)} |",
        f"| 🪣 S3 Buckets | {len(data.s3_buckets)} |",
        f"| 🔑 Secrets | {len(data.secrets)} |",
        "",
    ]

    # ── TOPILGAN ZAIFLIKLAR ───────────────────────────────
    if data.findings:
        lines += ["## 🚨 Topilgan Zaifliklar", ""]
        for f in data.sorted_findings():
            sev  = f.get("info", {}).get("severity", "unknown").lower()
            name = f.get("info", {}).get("name", f.get("template-id", "N/A"))
            url  = f.get("matched-at", "—")
            tid  = f.get("template-id", "")
            emoji = SEVERITY_EMOJI.get(sev, "⚪")
            lines += [
                f"### {emoji} {name}",
                f"",
                f"- **Template:** `{tid}`",
                f"- **Jiddiylik:** {sev.upper()}",
                f"- **URL:** `{url}`",
            ]
            if f.get("info", {}).get("description"):
                lines.append(f"- **Tavsif:** {f['info']['description']}")
            if f.get("curl-command"):
                lines += ["", f"```bash", f"{f['curl-command']}", "```"]
            lines.append("")
    else:
        lines += ["## 🚨 Topilgan Zaifliklar", "", "> Hech qanday zaiflik topilmadi.", ""]

    # ── SUBDOMAINLAR ──────────────────────────────────────
    if data.subdomains:
        lines += [
            "## 🌐 Subdomainlar",
            "",
            f"Jami **{len(data.subdomains)}** ta topildi.",
            "",
            "```",
        ]
        lines += sorted(data.subdomains)[:200]
        if len(data.subdomains) > 200:
            lines.append(f"... va yana {len(data.subdomains)-200} ta")
        lines += ["```", ""]

    # ── TIRIK HOSTLAR ─────────────────────────────────────
    if data.live_hosts:
        lines += [
            "## 🟢 Tirik Hostlar",
            "",
            "| URL | Status | Title |",
            "|-----|--------|-------|",
        ]
        for h in sorted(data.live_hosts, key=lambda x: x.get("status", 0)):
            url    = h.get("url", h.get("input", "—"))
            status = h.get("status", "—")
            title  = h.get("title", "")[:60].replace("|", "\\|")
            lines.append(f"| `{url}` | {status} | {title} |")
        lines.append("")

    # ── S3 BUCKETS ────────────────────────────────────────
    if data.s3_buckets:
        deduped = sorted(set(data.s3_buckets))
        lines += [
            "## 🪣 S3 Buckets",
            "",
            "> ⚠️ Quyidagilarni `aws s3 ls s3://bucket-name` bilan tekshiring",
            "",
            "```",
        ]
        lines += deduped
        lines += ["```", ""]

    # ── SECRETS ───────────────────────────────────────────
    if data.secrets:
        lines += [
            "## 🔑 Topilgan Secrets",
            "",
            "| Tur | Manba |",
            "|-----|-------|",
        ]
        for s in data.secrets:
            lines.append(f"| {s['type']} | `{s['source'][:80]}` |")
        lines += [
            "",
            "> ⚠️ To'liq qiymatlar JSON hisobotida saqlangan.",
            "",
        ]

    # ── XATOLAR ───────────────────────────────────────────
    if data.errors:
        lines += ["## ⚠️ Xatolar", ""]
        for e in data.errors:
            lines.append(f"- {e}")
        lines.append("")

    # ── QONUNIY ESLATMA ──────────────────────────────────
    lines += [
        "---",
        "",
        "> **⚖️ Muhim:** Ushbu hisobot faqat ruxsat berilgan bug bounty "
        "dasturlari doirasida o'tkazilgan tekshiruv natijalari asosida "
        "yaratilgan. Scope dan tashqari hech qanday faoliyat amalga oshirilmagan.",
        "",
        f"*Yaratildi: {now.strftime('%Y-%m-%d %H:%M:%S')} — BB Pro CLI*",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def generate_json(data: ReportData, output_path: Path) -> Path:
    """Machine-readable JSON hisobot."""
    payload = {
        "meta": {
            "target":     data.target,
            "scope":      data.scope,
            "started":    data.started_at.isoformat(),
            "finished":   data.finished_at.isoformat() if data.finished_at else None,
            "duration":   data.duration,
            "generated":  datetime.now().isoformat(),
        },
        "summary": {
            "subdomains":  len(data.subdomains),
            "live_hosts":  len(data.live_hosts),
            "findings":    len(data.findings),
            "s3_buckets":  len(data.s3_buckets),
            "secrets":     len(data.secrets),
            "severity":    data.severity_counts,
        },
        "subdomains":  sorted(data.subdomains),
        "live_hosts":  data.live_hosts,
        "findings":    data.sorted_findings(),
        "s3_buckets":  sorted(set(data.s3_buckets)),
        "secrets":     data.secrets,
        "errors":      data.errors,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return output_path

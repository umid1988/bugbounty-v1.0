#!/usr/bin/env python3
"""
BB Pro CLI — Asosiy kirish nuqtasi.
Ishlatish:
    python3 bb_pro.py scan -t example.com
    python3 bb_pro.py config
    python3 bb_pro.py tools
"""
import sys
import os
import argparse
from pathlib import Path

# Loyiha root ini sys.path ga qo'shamiz
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.config  import load, save, check_tools, Config
from core.scope   import ScopeManager, from_config


# ── Terminal ranglar ──────────────────────────────────────
class C:
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    WHITE  = "\033[97m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RESET  = "\033[0m"

def ok(msg):    print(f"  {C.GREEN}[✓]{C.RESET} {msg}")
def err(msg):   print(f"  {C.RED}[✗]{C.RESET} {msg}")
def info(msg):  print(f"  {C.YELLOW}[i]{C.RESET} {msg}")
def found(msg): print(f"  {C.BOLD}{C.RED}[!]{C.RESET} {msg}")
def head(msg):  print(f"\n{C.BOLD}{C.CYAN}{msg}{C.RESET}")


def banner():
    print(f"""
{C.CYAN}{C.BOLD}
  ██████╗ ██████╗     ██████╗ ██████╗  ██████╗
  ██╔══██╗██╔══██╗    ██╔══██╗██╔══██╗██╔═══██╗
  ██████╔╝██████╔╝    ██████╔╝██████╔╝██║   ██║
  ██╔══██╗██╔══██╗    ██╔═══╝ ██╔══██╗██║   ██║
  ██████╔╝██████╔╝    ██║     ██║  ██║╚██████╔╝
  ╚═════╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝
{C.RESET}{C.YELLOW}  Professional Bug Bounty Automation Pipeline
  Faqat ruxsat berilgan targetlarda ishlating!
{C.RESET}""")


# ══════════════════════════════════════════════════════════
#  SCAN buyruği
# ══════════════════════════════════════════════════════════
def cmd_scan(args, cfg: Config):
    """To'liq recon pipeline ni ishga tushiradi."""
    from modules.pipeline_runner import BBPipeline

    target = args.target.strip().lower()
    # URL bo'lsa domenni ajratib olamiz
    if "://" in target:
        from urllib.parse import urlparse
        target = urlparse(target).hostname or target

    # Scope ni CLI dan ham qabul qilish
    if args.scope:
        for s in args.scope:
            s = s.strip()
            if s.startswith("*."):
                if s[2:] not in cfg.scope_wildcards:
                    cfg.scope_wildcards.append(s[2:])
            elif s not in cfg.scope_domains:
                cfg.scope_domains.append(s)

    # Scope bo'sh bo'lsa target ni o'zini qo'shamiz
    if not cfg.scope_domains and not cfg.scope_wildcards:
        info(f"Scope berilmagan — '{target}' scope ga qo'shildi.")
        cfg.scope_domains.append(target)

    scope = from_config(cfg)

    # Config override lar
    if args.threads:
        cfg.threads = args.threads
    if args.timeout:
        cfg.timeout = args.timeout
    if args.output:
        cfg.output_dir = args.output
    if args.no_continue:
        cfg.continue_on_error = False

    banner()
    info(f"Target:  {C.BOLD}{target}{C.RESET}")
    info(f"Scope:\n{scope.summary()}")
    info(f"Threads: {cfg.threads}  |  Timeout: {cfg.timeout}s")

    # Xavf ogohlantirishi
    print(f"""
{C.YELLOW}  ╔══════════════════════════════════════════════════════╗
  ║  ⚖️  MUHIM ESLATMA                                   ║
  ║  Bu tool FAQAT ruxsat berilgan bug bounty           ║
  ║  dasturlari doirasida ishlatilishi kerak.           ║
  ║  Scope dan tashqari faoliyat noqonuniy!             ║
  ╚══════════════════════════════════════════════════════╝{C.RESET}
""")
    confirm = input("  Davom etasizmi? [y/N]: ").strip().lower()
    if confirm != "y":
        print("  Bekor qilindi.")
        return

    pipeline = BBPipeline(target, cfg, scope)
    pipeline.run()


# ══════════════════════════════════════════════════════════
#  CONFIG buyruği
# ══════════════════════════════════════════════════════════
def cmd_config(args, cfg: Config):
    """config.json ni interaktiv tahrirlash."""
    banner()
    head("⚙️  Config Sozlamalari")

    if args.show:
        _show_config(cfg)
        return

    if args.set:
        # --set key=value
        for kv in args.set:
            if "=" not in kv:
                err(f"Format: key=value  ('{kv}' noto'g'ri)")
                continue
            key, val = kv.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key == "shodan_api_key":
                cfg.shodan_api_key = val
                ok(f"shodan_api_key saqlandi.")
            elif key == "threads":
                cfg.threads = int(val)
                ok(f"threads = {val}")
            elif key == "timeout":
                cfg.timeout = int(val)
                ok(f"timeout = {val}s")
            elif key == "output_dir":
                cfg.output_dir = val
                ok(f"output_dir = {val}")
            elif key == "scope":
                domain = val.strip()
                if domain.startswith("*."):
                    cfg.scope_wildcards.append(domain[2:])
                else:
                    cfg.scope_domains.append(domain)
                ok(f"Scope ga qo'shildi: {domain}")
            else:
                err(f"Noma'lum kalit: {key}")
        save(cfg)
        return

    # Interaktiv rejim
    _interactive_config(cfg)


def _show_config(cfg: Config):
    head("Joriy sozlamalar")
    api = cfg.shodan_api_key
    api_display = api[:6] + "****" + api[-4:] if len(api) > 10 else ("(bo'sh)" if not api else "****")
    rows = [
        ("shodan_api_key",  api_display),
        ("threads",         str(cfg.threads)),
        ("timeout",         f"{cfg.timeout}s"),
        ("output_dir",      cfg.output_dir),
        ("continue_on_error", str(cfg.continue_on_error)),
        ("scope_domains",   ", ".join(cfg.scope_domains) or "(bo'sh)"),
        ("scope_wildcards", ", ".join(f"*.{w}" for w in cfg.scope_wildcards) or "(bo'sh)"),
        ("report_md",       str(cfg.report_md)),
        ("report_json",     str(cfg.report_json)),
        ("req/sec",         str(cfg.rate.requests_per_second)),
        ("shodan limit/oy", str(cfg.rate.shodan_requests_per_month)),
    ]
    print()
    for k, v in rows:
        print(f"  {C.CYAN}{k:25s}{C.RESET} {v}")
    print()


def _interactive_config(cfg: Config):
    _show_config(cfg)
    opts = [
        ("1", "Shodan API kaliti"),
        ("2", "Threads"),
        ("3", "Timeout"),
        ("4", "Scope domeni qo'shish"),
        ("5", "Scope wildcard qo'shish (*.example.com)"),
        ("6", "Scope tozalash"),
        ("7", "Output papkasi"),
        ("8", "Rate limit (req/sec)"),
        ("0", "Chiqish"),
    ]
    for code, label in opts:
        print(f"  {C.CYAN}{code}{C.RESET}  {label}")
    print()
    choice = input("  Tanlov: ").strip()

    if choice == "1":
        val = input("  Shodan API kaliti: ").strip()
        if val:
            cfg.shodan_api_key = val
    elif choice == "2":
        val = input(f"  Threads [{cfg.threads}]: ").strip()
        if val.isdigit():
            cfg.threads = int(val)
    elif choice == "3":
        val = input(f"  Timeout sekund [{cfg.timeout}]: ").strip()
        if val.isdigit():
            cfg.timeout = int(val)
    elif choice == "4":
        val = input("  Domen (masalan: example.com): ").strip()
        if val and val not in cfg.scope_domains:
            cfg.scope_domains.append(val)
            ok(f"Qo'shildi: {val}")
    elif choice == "5":
        val = input("  Wildcard (masalan: *.example.com): ").strip().lstrip("*.")
        if val and val not in cfg.scope_wildcards:
            cfg.scope_wildcards.append(val)
            ok(f"Qo'shildi: *.{val}")
    elif choice == "6":
        cfg.scope_domains   = []
        cfg.scope_wildcards = []
        ok("Scope tozalandi.")
    elif choice == "7":
        val = input(f"  Output papkasi [{cfg.output_dir}]: ").strip()
        if val:
            cfg.output_dir = val
    elif choice == "8":
        val = input(f"  Req/sec [{cfg.rate.requests_per_second}]: ").strip()
        try:
            cfg.rate.requests_per_second = float(val)
        except ValueError:
            pass

    if choice != "0":
        save(cfg)
        ok("config.json ga saqlandi.")


# ══════════════════════════════════════════════════════════
#  TOOLS buyruği
# ══════════════════════════════════════════════════════════
def cmd_tools(args, cfg: Config):
    """Tashqi toollar holatini tekshiradi."""
    banner()
    head("🔧 Tool Holati")
    tools = check_tools(cfg)
    print()

    descs = {
        "subfinder": "Subdomain enumeration (tezkor, passiv)",
        "httpx":     "HTTP probe — tirik hostlarni topish",
        "nuclei":    "Vulnerability scanner — template asosida",
        "amass":     "Kengaytirilgan subdomain enumeration",
        "dnsx":      "Tezkor DNS resolution va brute-force",
    }
    install = {
        "subfinder": "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        "httpx":     "go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest",
        "nuclei":    "go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest",
        "amass":     "go install -v github.com/owasp-amass/amass/v4/...@master",
        "dnsx":      "go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
    }

    all_ok = True
    for name, desc in descs.items():
        available = tools.get(name, False)
        if available:
            ok(f"{C.BOLD}{name:12s}{C.RESET} — {desc}")
        else:
            all_ok = False
            err(f"{C.BOLD}{name:12s}{C.RESET} — {desc}")
            print(f"           {C.DIM}O'rnatish: {install[name]}{C.RESET}")
    print()

    if all_ok:
        ok("Barcha toollar o'rnatilgan!")
    else:
        info("O'rnatilmagan toollar uchun Python fallback ishlatiladi.")
        info("Go o'rnatish: https://go.dev/dl/")
    print()


# ══════════════════════════════════════════════════════════
#  REPORT buyruği
# ══════════════════════════════════════════════════════════
def cmd_report(args, cfg: Config):
    """Mavjud JSON natijalardan qayta Markdown hisobot yaratadi."""
    from modules.reporter import ReportData, generate_markdown, generate_json
    from datetime import datetime

    json_file = Path(args.input)
    if not json_file.exists():
        err(f"{json_file} topilmadi.")
        sys.exit(1)

    try:
        raw = json_file.read_text(encoding="utf-8")
        import json as _json
        data_raw = _json.loads(raw)
    except Exception as e:
        err(f"JSON o'qish xatosi: {e}")
        sys.exit(1)

    meta = data_raw.get("meta", {})
    rd   = ReportData(
        target=meta.get("target", "unknown"),
        scope=meta.get("scope", [])
    )
    rd.subdomains  = data_raw.get("subdomains", [])
    rd.live_hosts  = data_raw.get("live_hosts", [])
    rd.findings    = data_raw.get("findings", [])
    rd.s3_buckets  = data_raw.get("s3_buckets", [])
    rd.secrets     = data_raw.get("secrets", [])
    rd.errors      = data_raw.get("errors", [])
    rd.finish()

    out = Path(args.output) if args.output else json_file.with_suffix(".md")
    generate_markdown(rd, out)
    ok(f"Markdown hisobot: {out}")


# ══════════════════════════════════════════════════════════
#  SCOPE buyruği (tezkor tekshiruv)
# ══════════════════════════════════════════════════════════
def cmd_scope(args, cfg: Config):
    """Domen scope da ekanligini tekshiradi."""
    scope = from_config(cfg)
    banner()
    head("🎯 Scope Tekshiruvi")
    print()
    info(f"Joriy scope:\n{scope.summary()}\n")

    for target in args.targets:
        if scope.check(target):
            ok(f"{target} — SCOPE ICHIDA ✓")
        else:
            err(f"{target} — SCOPE TASHQARIDA ✗")
    print()


# ══════════════════════════════════════════════════════════
#  ARGPARSE
# ══════════════════════════════════════════════════════════
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bb_pro",
        description="BB Pro — Professional Bug Bounty Automation Pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""
{C.YELLOW}Misollar:{C.RESET}
  python3 bb_pro.py scan -t example.com
  python3 bb_pro.py scan -t example.com --scope example.com --scope *.example.com
  python3 bb_pro.py scan -t example.com --threads 30 --timeout 10
  python3 bb_pro.py config --set shodan_api_key=YOUR_KEY
  python3 bb_pro.py config --set scope=*.example.com
  python3 bb_pro.py tools
  python3 bb_pro.py scope example.com sub.example.com evil.com
  python3 bb_pro.py report -i bb_output/example_com/report.json
        """
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    sc = sub.add_parser("scan", help="To'liq recon pipeline")
    sc.add_argument("-t", "--target",  required=True, help="Target domen")
    sc.add_argument("--scope",         action="append", metavar="DOMAIN",
                    help="Scope domeni (qayta ishlatish mumkin: --scope a.com --scope *.b.com)")
    sc.add_argument("--threads",       type=int, help="Thread soni")
    sc.add_argument("--timeout",       type=int, help="HTTP timeout (sekund)")
    sc.add_argument("--output",        help="Output papkasi")
    sc.add_argument("--no-continue",   action="store_true",
                    help="Xato bo'lsa pipeline ni to'xtatish")
    sc.add_argument("--resume",        action="store_true",
                    help="Oldingi pipeline dan davom etish")

    # config
    cf = sub.add_parser("config", help="Sozlamalarni ko'rish/o'zgartirish")
    cf.add_argument("--show", action="store_true", help="Joriy configni ko'rsatish")
    cf.add_argument("--set",  action="append",     metavar="key=value",
                    help="Qiymat belgilash (qayta ishlatish mumkin)")

    # tools
    sub.add_parser("tools", help="Tashqi toollar holatini tekshirish")

    # scope
    sv = sub.add_parser("scope", help="Domenlar scope da ekanligini tekshirish")
    sv.add_argument("targets", nargs="+", help="Tekshiriladigan domenlar")

    # report
    rp = sub.add_parser("report", help="JSON dan Markdown hisobot yaratish")
    rp.add_argument("-i", "--input",  required=True, help="JSON hisobot fayli")
    rp.add_argument("-o", "--output", help="Chiqish Markdown fayli")

    return parser


# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════
def main():
    parser = build_parser()
    args   = parser.parse_args()
    cfg    = load()

    dispatch = {
        "scan":   cmd_scan,
        "config": cmd_config,
        "tools":  cmd_tools,
        "scope":  cmd_scope,
        "report": cmd_report,
    }

    fn = dispatch.get(args.command)
    if fn:
        fn(args, cfg)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

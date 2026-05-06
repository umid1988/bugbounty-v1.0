"""
Asosiy pipeline — barcha modullarni birlashtiradi.
Har bir bosqich:
  1. Scope tekshiradi
  2. Rate limit saqlaydi
  3. Xato bo'lsa davom etadi (continue_on_error)
  4. Natijani PipelineState ga yozadi
"""
import re
import time
import json
import threading
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.config   import Config, check_tools
from core.scope    import ScopeManager, ScopeError
from core.pipeline import PipelineState, RateLimiter, ShodanLimiter
from modules.tools    import run_subfinder, run_amass, run_httpx, run_dnsx, run_nuclei
from modules.reporter import ReportData, generate_markdown, generate_json


# ── Secrets regex ──────────────────────────────────────────
SECRET_PATTERNS = {
    "AWS Access Key":   r"(?<![A-Z0-9])[A][SK]IA[A-Z0-9]{16}(?![A-Z0-9])",
    "AWS Secret Key":   r"(?<![A-Za-z0-9/+])[A-Za-z0-9/+]{38,40}={0,2}(?![A-Za-z0-9/+])",
    "MongoDB URI":      r"mongodb(?:\+srv)?://[^\s\"'<>]{6,}",
    "Redis URI":        r"redis://[^\s\"'<>]{6,}",
    "Private Key":      r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
    "JWT Token":        r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+",
    "S3 Bucket URL":    r"[\w\-\.]+\.s3(?:[\.\-][\w\-]+)?\.amazonaws\.com",
    "Generic Secret":   r"(?i)(?:secret|password|passwd|api_?key|token)\s*[=:]\s*['\"]([^'\"]{8,})['\"]",
}

S3_PATTERN = re.compile(
    r"[\w\-\.]+\.s3(?:[\.\-][\w\-]+)?\.amazonaws\.com"
    r"|(?<!\.)s3(?:[\.\-][\w\-]+)?\.amazonaws\.com[/\\][\w\-\.]+"
)


class BBPipeline:
    """
    To'liq bug bounty recon pipeline.
    """

    def __init__(self, target: str, cfg: Config, scope: ScopeManager):
        self.target  = target
        self.cfg     = cfg
        self.scope   = scope
        self.state   = PipelineState(target, cfg.continue_on_error)
        self.data    = ReportData(target, cfg.scope_domains + cfg.scope_wildcards)
        self.rl      = RateLimiter(cfg.rate.requests_per_second)
        self.shodan  = ShodanLimiter(cfg.rate.shodan_requests_per_month,
                                     cfg.rate.shodan_delay_seconds)
        self._out    = Path(cfg.output_dir) / self._safe(target)
        self._out.mkdir(parents=True, exist_ok=True)

        self._tools  = check_tools(cfg)
        self._lock   = threading.Lock()

    @staticmethod
    def _safe(name: str) -> str:
        return re.sub(r"[^\w\-.]", "_", name)

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.data.pipeline_log.append(line)
        print(line)

    def _err(self, msg: str):
        self.data.errors.append(msg)
        self._log(f"⚠️  {msg}")

    # ══════════════════════════════════════════════════════
    #  BOSQICH 1 — Scope tekshiruvi
    # ══════════════════════════════════════════════════════
    def step_scope_check(self):
        name = "scope_check"
        if self.state.is_done(name):
            self._log("⏭  scope_check — oldin bajarilgan, o'tkazildi")
            return
        self.state.start(name)
        t0 = time.monotonic()
        try:
            if self.scope.is_empty:
                raise ScopeError(
                    "Scope bo'sh! config.json → scope_domains yoki "
                    "scope_wildcards ni to'ldiring."
                )
            self.scope.validate(self.target)
            self._log(f"✓  Scope OK: {self.target}")
            self._log(self.scope.summary())
            self.state.done(name, elapsed=time.monotonic() - t0)
        except ScopeError as e:
            self.state.fail(name, str(e), time.monotonic() - t0)
            raise  # Scope xatosida pipeline to'xtatiladi

    # ══════════════════════════════════════════════════════
    #  BOSQICH 2 — Subdomain enumeration
    # ══════════════════════════════════════════════════════
    def step_subdomains(self):
        name = "subdomains"
        if self.state.is_done(name):
            self.data.subdomains = self.state.get_output(name) or []
            self._log(f"⏭  subdomains — {len(self.data.subdomains)} ta oldin topilgan")
            return
        self.state.start(name)
        t0 = time.monotonic()
        try:
            self._log(f"🔍 Subdomain enumeration: {self.target}")
            tool = "amass" if self._tools.get("amass") else "subfinder"
            installed = "(o'rnatilgan)" if self._tools.get(tool) else "(Python fallback)"
            self._log(f"   Tool: {tool} {installed}")

            subs = run_amass(self.target, timeout=180) \
                   if self._tools.get("amass") \
                   else run_subfinder(self.target, timeout=120)

            # Scope filterlash + deduplikatsiya
            subs = list({s.lower() for s in subs if s})
            in_scope, out = self.scope.filter(subs)
            if out:
                self._log(f"   ⊘ Scope tashqarisi ({len(out)} ta) o'tkazib yuborildi")

            # Asosiy domenni ham qo'shamiz
            if self.target not in in_scope:
                in_scope.insert(0, self.target)

            self.data.subdomains = in_scope
            self._log(f"✓  {len(in_scope)} ta subdomain (scope ichida)")
            self.state.done(name, output=in_scope,
                            count=len(in_scope), elapsed=time.monotonic() - t0)

            # Faylga yozish
            sub_file = self._out / "subdomains.txt"
            sub_file.write_text("\n".join(sorted(in_scope)), encoding="utf-8")

        except Exception as e:
            self._err(f"subdomains: {e}")
            self.state.fail(name, str(e), time.monotonic() - t0)

    # ══════════════════════════════════════════════════════
    #  BOSQICH 3 — DNS resolution (dnsx)
    # ══════════════════════════════════════════════════════
    def step_dns_resolve(self):
        name = "dns_resolve"
        if self.state.is_done(name):
            self._log("⏭  dns_resolve — oldin bajarilgan")
            return
        self.state.start(name)
        t0 = time.monotonic()
        try:
            subs = self.data.subdomains
            if not subs:
                self.state.skip(name, "subdomain yo'q")
                return
            self._log(f"🔍 DNS resolution: {len(subs)} ta host")
            alive = run_dnsx(subs, timeout=60)
            alive = list(set(alive))
            self._log(f"✓  {len(alive)} ta host DNS da topildi")

            alive_file = self._out / "dns_alive.txt"
            alive_file.write_text("\n".join(sorted(alive)), encoding="utf-8")

            # subdomains ni alive bilan yangilaymiz
            self.data.subdomains = alive
            self.state.done(name, output=alive,
                            count=len(alive), elapsed=time.monotonic() - t0)
        except Exception as e:
            self._err(f"dns_resolve: {e}")
            self.state.fail(name, str(e), time.monotonic() - t0)

    # ══════════════════════════════════════════════════════
    #  BOSQICH 4 — HTTP probe (httpx)
    # ══════════════════════════════════════════════════════
    def step_http_probe(self):
        name = "http_probe"
        if self.state.is_done(name):
            self.data.live_hosts = self.state.get_output(name) or []
            self._log(f"⏭  http_probe — {len(self.data.live_hosts)} ta oldin topilgan")
            return
        self.state.start(name)
        t0 = time.monotonic()
        try:
            hosts = self.data.subdomains
            if not hosts:
                self.state.skip(name, "subdomain yo'q")
                return
            tool_avail = self._tools.get("httpx")
            self._log(f"🔍 HTTP probe: {len(hosts)} ta host "
                      f"({'httpx' if tool_avail else 'Python fallback'})")

            results = run_httpx(hosts,
                                timeout=self.cfg.timeout,
                                threads=self.cfg.threads)

            self.data.live_hosts = results
            self._log(f"✓  {len(results)} ta tirik host topildi")

            # Faylga yozish
            live_file = self._out / "live_hosts.json"
            live_file.write_text(
                json.dumps(results, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            self.state.done(name, output=results,
                            count=len(results), elapsed=time.monotonic() - t0)
        except Exception as e:
            self._err(f"http_probe: {e}")
            self.state.fail(name, str(e), time.monotonic() - t0)

    # ══════════════════════════════════════════════════════
    #  BOSQICH 5 — Nuclei scanning
    # ══════════════════════════════════════════════════════
    def step_nuclei(self):
        name = "nuclei_scan"
        if self.state.is_done(name):
            self.data.findings = self.state.get_output(name) or []
            self._log(f"⏭  nuclei_scan — {len(self.data.findings)} ta oldin topilgan")
            return
        self.state.start(name)
        t0 = time.monotonic()
        try:
            targets = [h.get("url", h.get("input", ""))
                       for h in self.data.live_hosts
                       if h.get("url") or h.get("input")]
            if not targets:
                self.state.skip(name, "tirik host yo'q")
                return

            tool_avail = self._tools.get("nuclei")
            self._log(f"🔍 Nuclei scan: {len(targets)} ta target "
                      f"({'nuclei' if tool_avail else 'Python fallback'})")

            findings = run_nuclei(
                targets,
                tags="default-logins,misconfig,exposure,token",
                timeout=300
            )

            # Scope tekshirish
            safe = []
            for f in findings:
                url = f.get("matched-at", "")
                if self.scope.check(url):
                    safe.append(f)
                else:
                    self._log(f"   ⊘ Scope tashqarisi: {url}")

            self.data.findings = safe
            self._log(f"✓  {len(safe)} ta topilma")

            findings_file = self._out / "findings.json"
            findings_file.write_text(
                json.dumps(safe, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            self.state.done(name, output=safe,
                            count=len(safe), elapsed=time.monotonic() - t0)
        except Exception as e:
            self._err(f"nuclei_scan: {e}")
            self.state.fail(name, str(e), time.monotonic() - t0)

    # ══════════════════════════════════════════════════════
    #  BOSQICH 6 — Secrets & S3 qidirish
    # ══════════════════════════════════════════════════════
    def step_secrets(self):
        name = "secrets_scan"
        if self.state.is_done(name):
            self._log("⏭  secrets_scan — oldin bajarilgan")
            return
        self.state.start(name)
        t0 = time.monotonic()
        try:
            targets = [h.get("url", "") for h in self.data.live_hosts if h.get("url")]
            if not targets:
                self.state.skip(name, "tirik host yo'q")
                return

            self._log(f"🔍 Secrets va S3 qidirish: {len(targets)} ta URL")
            found_count = 0
            lock = threading.Lock()

            def _scan_url(url):
                nonlocal found_count
                self.rl.wait("http")
                try:
                    resp = requests.get(url, timeout=self.cfg.timeout,
                                        verify=False,
                                        headers={"User-Agent": "Mozilla/5.0"})
                    content = resp.text

                    # JS fayllarni ham tekshirish
                    js_urls = re.findall(
                        r'src=["\']([^"\']+\.js(?:\?[^"\']*)?)["\']', content)
                    texts = [content]
                    for js in js_urls[:10]:
                        if not js.startswith("http"):
                            js = url.rstrip("/") + "/" + js.lstrip("/")
                        try:
                            self.rl.wait("http")
                            jr = requests.get(js, timeout=self.cfg.timeout,
                                              verify=False)
                            texts.append(jr.text)
                        except Exception:
                            pass

                    for text in texts:
                        # S3 buckets
                        for bucket in S3_PATTERN.findall(text):
                            with lock:
                                self.data.s3_buckets.append(bucket)
                                found_count += 1

                        # Secrets
                        for stype, pattern in SECRET_PATTERNS.items():
                            if stype == "S3 Bucket URL":
                                continue
                            for match in re.finditer(pattern, text):
                                val = match.group(0)
                                with lock:
                                    self.data.add_secret(stype, val, url)
                                    found_count += 1

                except Exception:
                    pass

            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=min(10, self.cfg.threads)) as ex:
                futs = {ex.submit(_scan_url, u): u for u in targets}
                for fut in as_completed(futs):
                    try:
                        fut.result()
                    except Exception:
                        pass

            # Deduplikatsiya
            self.data.s3_buckets = list(set(self.data.s3_buckets))
            self._log(f"✓  {len(self.data.s3_buckets)} S3 bucket, "
                      f"{len(self.data.secrets)} secret topildi")
            self.state.done(name, count=found_count,
                            elapsed=time.monotonic() - t0)
        except Exception as e:
            self._err(f"secrets_scan: {e}")
            self.state.fail(name, str(e), time.monotonic() - t0)

    # ══════════════════════════════════════════════════════
    #  BOSQICH 7 — Hisobot yaratish
    # ══════════════════════════════════════════════════════
    def step_report(self):
        name = "report"
        self.state.start(name)
        t0 = time.monotonic()
        try:
            self.data.finish()
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            files = []

            if self.cfg.report_md:
                md_path = self._out / f"report_{ts}.md"
                generate_markdown(self.data, md_path)
                self._log(f"📄 Markdown hisobot: {md_path}")
                files.append(str(md_path))

            if self.cfg.report_json:
                json_path = self._out / f"report_{ts}.json"
                generate_json(self.data, json_path)
                self._log(f"📄 JSON hisobot: {json_path}")
                files.append(str(json_path))

            self.state.done(name, output=files, elapsed=time.monotonic() - t0)
        except Exception as e:
            self._err(f"report: {e}")
            self.state.fail(name, str(e), time.monotonic() - t0)

    # ══════════════════════════════════════════════════════
    #  TO'LIQ PIPELINE
    # ══════════════════════════════════════════════════════
    def run(self):
        self._log(f"\n{'='*55}")
        self._log(f"  BB Pro Pipeline — {self.target}")
        self._log(f"{'='*55}")
        self._log(f"  Threads: {self.cfg.threads}  |  Timeout: {self.cfg.timeout}s")
        self._log(f"  Output:  {self._out}")
        self._log(f"{'='*55}\n")

        steps = [
            ("1/7  Scope tekshiruvi",      self.step_scope_check),
            ("2/7  Subdomain enumeration", self.step_subdomains),
            ("3/7  DNS resolution",        self.step_dns_resolve),
            ("4/7  HTTP probe",            self.step_http_probe),
            ("5/7  Nuclei scan",           self.step_nuclei),
            ("6/7  Secrets & S3",          self.step_secrets),
            ("7/7  Hisobot",               self.step_report),
        ]

        for label, fn in steps:
            self._log(f"\n── {label} {'─'*(45-len(label))}")
            try:
                fn()
            except ScopeError as e:
                self._log(f"\n🚫 SCOPE XATOSI: {e}")
                self._log("Pipeline to'xtatildi — scope ni to'ldiring.")
                return
            except Exception as e:
                if not self.cfg.continue_on_error:
                    self._log(f"\n💥 Xato: {e}")
                    raise
                self._err(f"{label}: {e}")

        self._log(f"\n{'='*55}")
        self._log("  PIPELINE TUGADI")
        self._log(f"{'='*55}")
        self._log(self.state.summary())
        self._log(f"\n  Natijalar: {self._out}/")

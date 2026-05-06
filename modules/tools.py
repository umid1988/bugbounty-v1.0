"""
Tashqi toollarni subprocess orqali chaqirish.
Har bir tool uchun:
  1. Tool mavjudligini tekshiradi
  2. Mavjud bo'lsa subprocess orqali chaqiradi
  3. Mavjud bo'lmasa Python fallback ishlatadi
"""
import subprocess
import shutil
import socket
import time
import threading
import dns.resolver
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Set

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


# ═══════════════════════════════════════════════════════════
#  SUBFINDER — subdomain enumeration
# ═══════════════════════════════════════════════════════════
def run_subfinder(domain: str, timeout: int = 120) -> List[str]:
    """
    subfinder mavjud bo'lsa ishlatadi,
    aks holda Python DNS fallback.
    """
    if _which("subfinder"):
        return _subfinder_subprocess(domain, timeout)
    return _subfinder_python_fallback(domain)


def _subfinder_subprocess(domain: str, timeout: int) -> List[str]:
    try:
        result = subprocess.run(
            ["subfinder", "-d", domain, "-silent", "-all"],
            capture_output=True, text=True, timeout=timeout
        )
        subs = [s.strip() for s in result.stdout.splitlines() if s.strip()]
        return list(set(subs))
    except subprocess.TimeoutExpired:
        return []
    except Exception:
        return _subfinder_python_fallback(domain)


def _subfinder_python_fallback(domain: str) -> List[str]:
    """
    Kichik Python fallback — umumiy subdomain ro'yxatini DNS orqali tekshiradi.
    """
    COMMON = [
        "www", "mail", "ftp", "admin", "api", "dev", "staging", "test",
        "app", "portal", "dashboard", "blog", "shop", "store", "vpn",
        "remote", "cdn", "static", "assets", "media", "upload", "auth",
        "login", "secure", "beta", "demo", "help", "support", "docs",
        "m", "mobile", "data", "db", "jenkins", "gitlab", "jira",
        "confluence", "grafana", "prometheus", "kibana", "es", "elastic",
    ]
    found = []
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2
    resolver.lifetime = 2

    def _check(sub):
        fqdn = f"{sub}.{domain}"
        try:
            resolver.resolve(fqdn, "A")
            return fqdn
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(_check, s): s for s in COMMON}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                found.append(result)

    return found


# ═══════════════════════════════════════════════════════════
#  HTTPX — HTTP probe (tirik hostlarni topish)
# ═══════════════════════════════════════════════════════════
def run_httpx(hosts: List[str], timeout: int = 10,
              threads: int = 50) -> List[dict]:
    """
    httpx mavjud bo'lsa ishlatadi,
    aks holda Python requests fallback.
    Returns: [{'url': ..., 'status': ..., 'title': ..., 'tech': ...}]
    """
    if _which("httpx"):
        return _httpx_subprocess(hosts, timeout, threads)
    return _httpx_python_fallback(hosts, timeout, threads)


def _httpx_subprocess(hosts: List[str], timeout: int, threads: int) -> List[dict]:
    import tempfile, json as _json

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("\n".join(hosts))
        inp = f.name

    try:
        result = subprocess.run(
            ["httpx", "-l", inp, "-silent", "-json",
             f"-timeout", str(timeout), f"-threads", str(threads),
             "-tech-detect", "-title", "-status-code"],
            capture_output=True, text=True, timeout=timeout * 10
        )
        results = []
        for line in result.stdout.splitlines():
            try:
                results.append(_json.loads(line))
            except Exception:
                pass
        return results
    except Exception:
        return _httpx_python_fallback(hosts, timeout, threads)
    finally:
        Path(inp).unlink(missing_ok=True)


def _httpx_python_fallback(hosts: List[str], timeout: int,
                            threads: int) -> List[dict]:
    results = []
    lock = threading.Lock()

    def _probe(host):
        host = host.strip()
        if not host:
            return
        for scheme in ("https", "http"):
            url = f"{scheme}://{host}" if "://" not in host else host
            try:
                resp = requests.get(url, timeout=timeout, verify=False,
                                    allow_redirects=True,
                                    headers={"User-Agent": "Mozilla/5.0"})
                title = ""
                m = __import__("re").search(
                    r"<title[^>]*>(.*?)</title>", resp.text, __import__("re").I)
                if m:
                    title = m.group(1).strip()[:100]
                with lock:
                    results.append({
                        "url":    resp.url,
                        "status": resp.status_code,
                        "title":  title,
                        "tech":   [],
                    })
                return  # https ishlasa http ni sinab ko'rmaymiz
            except Exception:
                continue

    with ThreadPoolExecutor(max_workers=threads) as ex:
        list(as_completed({ex.submit(_probe, h): h for h in hosts}))

    return results


# ═══════════════════════════════════════════════════════════
#  NUCLEI — vulnerability scanning
# ═══════════════════════════════════════════════════════════
def run_nuclei(targets: List[str], tags: str = "default-logins,misconfig,exposure",
               timeout: int = 300) -> List[dict]:
    """
    nuclei mavjud bo'lsa ishlatadi.
    Python fallback: asosiy default credentials va misconfig tekshiruvi.
    """
    if _which("nuclei"):
        return _nuclei_subprocess(targets, tags, timeout)
    return _nuclei_python_fallback(targets, timeout)


def _nuclei_subprocess(targets: List[str], tags: str,
                       timeout: int) -> List[dict]:
    import tempfile, json as _json

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("\n".join(targets))
        inp = f.name

    try:
        result = subprocess.run(
            ["nuclei", "-l", inp, "-tags", tags, "-silent",
             "-json", "-no-color"],
            capture_output=True, text=True, timeout=timeout
        )
        findings = []
        for line in result.stdout.splitlines():
            try:
                findings.append(_json.loads(line))
            except Exception:
                pass
        return findings
    except Exception:
        return _nuclei_python_fallback(targets, timeout)
    finally:
        Path(inp).unlink(missing_ok=True)


# Default credentials — Python fallback
_DEFAULT_CREDS = [
    # (endpoint, method, payload, success_check)
    ("/api/authentication/login", "POST",
     {"login": "admin", "password": "admin"},
     lambda r: r.status_code == 200,
     "SonarQube default creds"),

    ("/login", "POST",
     {"user": "admin", "password": "admin"},
     lambda r: r.status_code == 200 and "token" in r.text.lower(),
     "Grafana default creds"),

    ("/j_acegi_security_check", "POST",
     {"j_username": "admin", "j_password": "password"},
     lambda r: r.status_code in (302, 301)
               and "loginError" not in r.headers.get("location", ""),
     "Jenkins default creds"),
]

_MISCONFIG_CHECKS = [
    # (path, pattern, vuln_name)
    ("/",               r"URLconf\s+defined",          "Django Debug Mode"),
    ("/",               r"Whoops!.{0,30}error",        "Laravel Debug Mode"),
    ("/actuator",       r'"status"\s*:\s*"UP"',        "Spring Boot Actuator"),
    ("/actuator/health",r'"status"\s*:\s*"UP"',        "Spring Boot Health"),
    ("/admin/",         r"(Manage Jenkins|Dashboard)", "Jenkins Open"),
    ("/.git/HEAD",      r"ref:\s*refs/",               "Git Exposed"),
    ("/server-status",  r"Apache Server Status",       "Apache Status"),
    ("/phpinfo.php",    r"PHP Version",                "PHPInfo Exposed"),
    ("/config.php.bak", r"(\$db|password|mysql)",      "Backup Config"),
]


def _nuclei_python_fallback(targets: List[str], timeout: int) -> List[dict]:
    import re
    findings = []
    lock = threading.Lock()

    def _check_target(url):
        local_finds = []
        # Misconfig tekshiruvi
        for path, pattern, name in _MISCONFIG_CHECKS:
            try:
                resp = requests.get(url.rstrip("/") + path,
                                    timeout=timeout // 10,
                                    verify=False, allow_redirects=True)
                if re.search(pattern, resp.text, re.I):
                    local_finds.append({
                        "template-id": name.lower().replace(" ", "-"),
                        "info":        {"name": name, "severity": "medium"},
                        "matched-at":  url + path,
                        "type":        "http",
                    })
            except Exception:
                pass

        # Default creds tekshiruvi
        for endpoint, method, payload, check, name in _DEFAULT_CREDS:
            try:
                fn = requests.post if method == "POST" else requests.get
                resp = fn(url.rstrip("/") + endpoint,
                          json=payload if "json" in endpoint else None,
                          data=payload if "json" not in endpoint else None,
                          timeout=timeout // 10, verify=False,
                          allow_redirects=False)
                if check(resp):
                    local_finds.append({
                        "template-id": name.lower().replace(" ", "-"),
                        "info":        {"name": name, "severity": "high"},
                        "matched-at":  url + endpoint,
                        "type":        "http",
                    })
            except Exception:
                pass

        with lock:
            findings.extend(local_finds)

    with ThreadPoolExecutor(max_workers=10) as ex:
        list(as_completed({ex.submit(_check_target, t): t for t in targets}))

    return findings


# ═══════════════════════════════════════════════════════════
#  AMASS — advanced subdomain
# ═══════════════════════════════════════════════════════════
def run_amass(domain: str, timeout: int = 300) -> List[str]:
    """amass mavjud bo'lsa ishlatadi, aks holda subfinder fallback."""
    if _which("amass"):
        try:
            result = subprocess.run(
                ["amass", "enum", "-passive", "-d", domain, "-silent"],
                capture_output=True, text=True, timeout=timeout
            )
            return list({s.strip() for s in result.stdout.splitlines() if s.strip()})
        except Exception:
            pass
    return run_subfinder(domain, timeout)


# ═══════════════════════════════════════════════════════════
#  DNSX — DNS resolution
# ═══════════════════════════════════════════════════════════
def run_dnsx(hosts: List[str], timeout: int = 30) -> List[str]:
    """
    dnsx mavjud bo'lsa ishlatadi,
    aks holda Python DNS resolution.
    """
    if _which("dnsx"):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("\n".join(hosts))
            inp = f.name
        try:
            result = subprocess.run(
                ["dnsx", "-l", inp, "-silent", "-a"],
                capture_output=True, text=True, timeout=timeout
            )
            return [s.strip() for s in result.stdout.splitlines() if s.strip()]
        except Exception:
            pass
        finally:
            Path(inp).unlink(missing_ok=True)

    # Python fallback
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2
    resolver.lifetime = 2
    alive = []

    def _resolve(host):
        try:
            resolver.resolve(host.strip(), "A")
            return host.strip()
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=50) as ex:
        for res in as_completed({ex.submit(_resolve, h): h for h in hosts}):
            r = res.result()
            if r:
                alive.append(r)

    return alive

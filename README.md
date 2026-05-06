<div align="center">

<img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Platform-Linux%20%7C%20macOS-lightgrey?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge"/>

```
  ██████╗ ██████╗     ██████╗ ██████╗  ██████╗
  ██╔══██╗██╔══██╗    ██╔══██╗██╔══██╗██╔═══██╗
  ██████╔╝██████╔╝    ██████╔╝██████╔╝██║   ██║
  ██╔══██╗██╔══██╗    ██╔═══╝ ██╔══██╗██║   ██║
  ██████╔╝██████╔╝    ██║     ██║  ██║╚██████╔╝
  ╚═════╝ ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝
```

### Professional Bug Bounty Automation Pipeline

**[🇺🇿 O'zbek](#-xususiyatlar) | [🇬🇧 English](#-features)**

*Faqat ruxsat berilgan targetlarda ishlating — Only use on authorized targets*

</div>

---

## ✨ Xususiyatlar

| Xususiyat | Tavsif |
|-----------|--------|
| 🎯 **Scope Kontroli** | Har bir so'rov scope tekshiruvi orqali o'tadi |
| 🔧 **Tool Integratsiyasi** | subfinder, httpx, nuclei, amass, dnsx — yo'q bo'lsa Python fallback |
| ⚡ **Threading** | Parallel scan — ThreadPoolExecutor bilan 10-50x tezroq |
| 🔄 **Pipeline Resume** | Xato bo'lsa davom etadi, qayta ishga tushirishda qolgan joydan boshlaydi |
| 🚦 **Rate Limiting** | HTTP req/sec va Shodan oy limiti avtomatik boshqariladi |
| 📊 **Markdown Hisobot** | Jiddiylik bo'yicha tartib, tirik hostlar, S3 bucket, secretlar |
| 🔑 **Secrets Scanner** | AWS keys, JWT, MongoDB/Redis URI, Private keys — JS fayllardan ham |

---

## 📦 O'rnatish

```bash
git clone https://github.com/umid1988/bugbounty-v1.0.git
cd bugbounty-v1.0
pip install requests dnspython
```

### Go toollar *(ixtiyoriy)*

```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/owasp-amass/amass/v4/...@master
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
nuclei -update-templates
```

> Go toollar bo'lmasa ham ishlaydi — Python fallback avtomatik yoqiladi.

---

## ⚙️ Birinchi sozlash

```bash
python3 bb_pro.py tools
python3 bb_pro.py config --set scope=example.com
python3 bb_pro.py config --set scope=*.example.com
python3 bb_pro.py config --set shodan_api_key=YOUR_KEY
```

---

## 🚀 Ishlatish

```bash
# To'liq scan
python3 bb_pro.py scan -t example.com

# Scope ni to'g'ridan-to'g'ri berish
python3 bb_pro.py scan -t example.com --scope example.com --scope "*.example.com"

# Tezroq scan
python3 bb_pro.py scan -t example.com --threads 50 --timeout 5

# Target scope da ekanligini tekshirish
python3 bb_pro.py scope api.example.com evil.com

# Hisobot qayta yaratish
python3 bb_pro.py report -i bb_output/example_com/report.json
```

---

## 🔄 Pipeline

```
1  Scope tekshiruvi       → Target ruxsatini tasdiqlash
2  Subdomain enumeration  → subfinder / amass
3  DNS resolution         → dnsx / dnspython
4  HTTP probe             → httpx / requests
5  Nuclei scan            → nuclei / Python fallback
6  Secrets & S3           → regex + JS tahlil
7  Markdown hisobot       → Jiddiylik bo'yicha tartib
```

---

## 📁 Tuzilma

```
bugbounty-v1.0/
├── bb_pro.py              ← CLI: scan / config / tools / scope / report
├── config.json            ← Sozlamalar
├── core/
│   ├── config.py          ← Config dataclass
│   ├── scope.py           ← Scope validatsiya
│   └── pipeline.py        ← PipelineState + RateLimiter
└── modules/
    ├── tools.py           ← Tool wrapper + Python fallback
    ├── pipeline_runner.py ← 7 bosqichli orkestrator
    └── reporter.py        ← Markdown + JSON hisobot
```

---

## ⚖️ Muhim Eslatma

> Bu tool **faqat** o'z domenlaringiz yoki ruxsat berilgan bug bounty dasturlari uchun.
> Scope dan tashqari faoliyat ko'pchilik mamlakatda jinoyat hisoblanadi.

---

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Scope Control** | Every request passes through scope validation — never scans unauthorized targets |
| 🔧 **Tool Integration** | subfinder, httpx, nuclei, amass, dnsx — Python fallback if not installed |
| ⚡ **Threading** | Parallel scanning — 10-50x faster with ThreadPoolExecutor |
| 🔄 **Pipeline Resume** | Continues on error, resumes from last checkpoint on restart |
| 🚦 **Rate Limiting** | Automatic HTTP req/sec and Shodan monthly limit management |
| 📊 **Markdown Report** | Severity-sorted findings, live hosts, S3 buckets, secrets |
| 🔑 **Secrets Scanner** | AWS keys, JWT, MongoDB/Redis URI, Private keys — extracted from JS files too |

---

## 📦 Installation

```bash
git clone https://github.com/umid1988/bugbounty-v1.0.git
cd bugbounty-v1.0
pip install requests dnspython
```

### Go Tools *(optional but recommended)*

```bash
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install -v github.com/owasp-amass/amass/v4/...@master
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
nuclei -update-templates
```

> Works without Go tools — Python fallback activates automatically.

---

## ⚙️ First-time Setup

```bash
# Check tool availability
python3 bb_pro.py tools

# Set scope (REQUIRED — no scan without scope)
python3 bb_pro.py config --set scope=example.com
python3 bb_pro.py config --set scope=*.example.com

# Optional: Shodan API key
python3 bb_pro.py config --set shodan_api_key=YOUR_KEY

# View all settings
python3 bb_pro.py config --show
```

---

## 🚀 Usage

```bash
# Full scan
python3 bb_pro.py scan -t example.com

# Pass scope directly via CLI
python3 bb_pro.py scan -t example.com \
    --scope example.com \
    --scope "*.example.com"

# Faster scan with more threads
python3 bb_pro.py scan -t example.com --threads 50 --timeout 5

# Stop pipeline on error (default: continue)
python3 bb_pro.py scan -t example.com --no-continue

# Check if target is in scope
python3 bb_pro.py scope api.example.com evil.com

# Regenerate report from existing JSON
python3 bb_pro.py report -i bb_output/example_com/report.json
```

---

## 🔄 Pipeline Steps

```
1  Scope validation       → Confirm target is authorized
2  Subdomain enumeration  → subfinder / amass
3  DNS resolution         → dnsx / dnspython
4  HTTP probe             → httpx / requests
5  Nuclei scan            → nuclei / Python fallback
6  Secrets & S3           → regex + JS file analysis
7  Markdown report        → Sorted by severity
```

**Resume support:** Pipeline state is saved to `.pipeline_state.json`. Completed steps are skipped on restart.

---

## 📊 Sample Report Output

```markdown
# Bug Bounty Report

| Target     | example.com       |
| Started    | 2026-01-15 09:30  |
| Duration   | 12m 34s           |

## Summary
| 🟠 High   | 2 |
| 🟡 Medium | 5 |
| 🌐 Subdomains   | 47 |
| 🟢 Live hosts   | 23 |

## Findings

### 🟠 Grafana Default Login
- Template: grafana-default-login
- URL: https://grafana.example.com/login

### 🟡 Django Debug Mode
- Template: django-debug-enabled
- URL: https://api.example.com/
```

---

## 📁 Project Structure

```
bugbounty-v1.0/
├── bb_pro.py              ← CLI entry point: scan / config / tools / scope / report
├── config.json            ← Settings (scope, threads, API keys)
├── core/
│   ├── config.py          ← Config dataclass and loader
│   ├── scope.py           ← Scope validation module
│   └── pipeline.py        ← PipelineState + RateLimiter + ShodanLimiter
└── modules/
    ├── tools.py           ← Tool wrappers + Python fallbacks
    ├── pipeline_runner.py ← 7-step pipeline orchestrator
    └── reporter.py        ← Markdown + JSON report generator
```

---

## 🐍 Python Fallback Table

| Tool | Fallback | Notes |
|------|----------|-------|
| `subfinder` | DNS brute-force (30+ common prefixes) | Slower |
| `httpx` | `requests` parallel probe | Good |
| `nuclei` | Default creds + misconfig checks | Limited templates |
| `amass` | subfinder fallback | — |
| `dnsx` | `dnspython` parallel resolution | Good |

---

## ⚙️ config.json Reference

```json
{
  "shodan_api_key": "",
  "threads": 20,
  "timeout": 8,
  "output_dir": "bb_output",
  "scope_domains":   ["example.com"],
  "scope_wildcards": ["example.com"],
  "continue_on_error": true,
  "report_md":   true,
  "report_json": true,
  "rate": {
    "requests_per_second": 2.0,
    "shodan_requests_per_month": 100
  }
}
```

---

## ⚖️ Legal Disclaimer

> This tool is intended **only** for:
> - Your own domains
> - Authorized bug bounty programs (HackerOne, Bugcrowd, etc.)
> - Engagements with a signed penetration testing agreement
>
> **Unauthorized use against systems you do not own is illegal in most jurisdictions.**
> The author assumes no responsibility for misuse.

---

## 📚 References & Inspiration

- [Syed Abuthahir — Bug Bounty Automation with Python](https://github.com/abuvanth)
- [ProjectDiscovery Tools](https://github.com/projectdiscovery)
- [SecLists](https://github.com/danielmiessler/SecLists)
- [Awesome Shodan Queries](https://github.com/jakejarvis/awesome-shodan-queries)

---

<div align="center">

⭐ **If this helped you, please star the repo!**

</div>

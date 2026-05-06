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
git clone https://github.com/YOUR_USERNAME/bb-pro.git
cd bb-pro
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
bb-pro/
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

## 📚 Manbalar

- [Syed Abuthahir — Bug Bounty Automation with Python](https://github.com/abuvanth)
- [ProjectDiscovery Tools](https://github.com/projectdiscovery)
- [SecLists](https://github.com/danielmiessler/SecLists)

---

<div align="center">⭐ Foydali bo'lsa yulduz bosing!</div>

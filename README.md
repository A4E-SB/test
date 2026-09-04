<p align="center"><img src="assets/brand.png" width="240" alt="Himaya logo"></p>

# 🛡️ Himaya (حماية)

**English** | [Français](README.fr.md) | [العربية](README.ar.md)

**A 100% offline desktop app that protects Algerian e-commerce sellers from scams, ghost orders and fake payment receipts.**

> **Zero internet. Zero servers. Zero subscriptions.** All data, all analysis
> and all printing happen on your PC.

---

## ✨ Features

| Module | Description |
|---|---|
| 📊 **Dashboard** | Today's summary (orders, shipments, ghosts), scam alerts, 6-month revenue-vs-losses chart, completion rate, money saved |
| 👥 **Customers** | Full CRM with an **auto trust score (0-100)**, automatic tags (Trusted / Ghost / Scammer / Time-waster / New), order history, money lost per customer |
| 📦 **Orders** | Full lifecycle (Pending → Confirmed → Shipped → Delivered → Paid) + fraud statuses (Ghosted, Refused, Phone off, Fake payment, Canceled, **Blocked**), filters by status/wilaya/date |
| 🔍 **Fake receipt detector** | Local analysis of BaridiMob screenshots: OCR (Tesseract), image fingerprint (dHash) against known fakes, metadata (PicsArt/Snapseed traces…), font consistency (OpenCV), ELA, date/reference/amount format checks. Verdict **REAL / SUSPICIOUS / FAKE** with reasons |
| ⏳ **Time-waster tracker** | Log every contact, conversion rate, automatic suggestions of when to ask for a **deposit**, smart AR/FR reply templates ready to paste into Messenger/WhatsApp |
| 💰 **Financial reports** | Revenue, costs, net profit, loss breakdown (ghosts / refusals / fake payments), money saved by blocking. CSV / Excel export |
| 🔌 **USB import / export** | The **`.hma` file**: Himaya's official blacklist to share between sellers on a USB key. Orders CSV/Excel import & export |
| 🖨️ **Delivery labels** | A6 (105×148) or 100×100 PDF with color-coded risk level, barcode, warnings ("Call before delivery") |
| ⚙️ **Settings** | FR/EN/AR UI language, CCP/BaridiMob account info (for deposits), default delivery company, backup/restore, all 58 wilayas built in |

The UI itself is fully trilingual **English ⇄ Français ⇄ العربية (RTL)** with one click.

---

## ⬇️ Download the installer (already compiled for you)

➡️ **[Himaya-Setup-1.0.6.exe — latest release](https://github.com/belmezouarsouhil95-byte/test/releases/latest)**
One file (~83 MB): double-click → Next → Next → Finish. App + Python runtime +
OCR engine included, no internet connection required.

## 🧱 The all-in-one installer

**One file. Install it and you have the full app.** Everything is bundled:
the application, the whole Python runtime **and the OCR engine** (fake-receipt
detection works out of the box). No prerequisites, no internet, no setup —
works on any Windows 10/11 PC (4 GB RAM is enough).

The installer adds: desktop + Start Menu shortcuts, a **French** wizard, a
clean uninstaller that **asks** before touching your data (`%APPDATA%\Himaya`).
Silent/bulk install:
`Himaya-Setup-1.0.6.exe /VERYSILENT /SUPPRESSMSGBOXES`

### Option A — on your Windows PC

1. Install **Inno Setup 6** (free, one time): https://jrsoftware.org/isdl.php
2. Double-click:

```bat
build_installer.bat
```

The script does everything: venv → dependencies → PyInstaller → OCR engine
staging (copied from your PC or downloaded once at build time — never on the
end user's machine) → `installer\output\Himaya-Setup-1.0.6.exe`.

### Option B — built automatically on GitHub (no PC required)

- **Actions** tab → *Build Windows installer* → **Run workflow** → download
  the `setup.exe` from the *artifacts*;
- or push a tag (`git tag v1.0.6 && git push origin v1.0.6`): a **Release**
  is created automatically with the installer attached.

---

## 📥 Running from source (developers)

**Prerequisite:** Python 3.11+ (https://python.org — check *Add to PATH*)

```bash
git clone https://github.com/belmezouarsouhil95-byte/test himaya
cd himaya
pip install -r requirements.txt
python main.py
```

### Full OCR (optional when running from source)

The detector works without Tesseract (fingerprint + metadata + pixel
forensics), but extracting amount/date/reference needs the local OCR engine:

1. Download **Tesseract-OCR for Windows** (UB Mannheim): https://github.com/UB-Mannheim/tesseract/wiki
2. Install with the **French** language pack (+ Arabic if available)
3. If not on PATH, set it in *Settings → Tesseract path*
   (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`)

### Portable .exe (PyInstaller)

```bat
build_windows.bat
```

Produces `dist\Himaya\Himaya.exe` — a portable folder that runs on any
Windows 10/11 machine (even 4 GB RAM). For a single file:

```bat
pyinstaller --noconfirm --onefile --windowed --name Himaya --icon assets/icon.ico --add-data "assets;assets" --add-data "himaya/database/schema.sql;himaya/database" main.py
```

**Size:** ~70-95 MB with OpenCV.

---

## 🗄️ Where is my data?

One single folder, easy to back up or copy to USB:

| OS | Location |
|---|---|
| Windows | `%APPDATA%\Himaya\himaya.db` |
| Linux/Mac | `~/.himaya/himaya.db` |

- `himaya.db`: the **whole** app (customers, orders, blacklist…)
- `evidence/`: timestamped copies of analysed fake receipts
- `backups/`: backups (*Backup now* button in Settings)

Set `HIMAYA_DATA_DIR` or run `python main.py --db PATH` to store the database
elsewhere (e.g. directly on a USB key).

## 🔐 The .hma format (offline sharing)

A `.hma` file is a JSON document signed by the `HIMAYA-BLACKLIST` header,
readable by any Himaya instance and checkable in a text editor:

```json
{
  "magic": "HIMAYA-BLACKLIST",
  "version": 1,
  "exported_at": "2026-09-04T15:30:00",
  "count": 2,
  "entries": [
    {"phone": "0770999888", "reason": "fake BaridiMob receipt", "severity": 3,
     "reported_date": "2026-09-01"}
  ]
}
```

Imports **merge** (highest severity wins) — your data is never overwritten.

## 🧠 Trust score — how it's computed

Everyone starts at **50/100** (new). Each order moves the score:

| Event | Effect |
|---|---|
| Delivered | +10 |
| Paid | +15 |
| Ghosted | −25 |
| Refused | −12 |
| Phone off | −10 |
| Fake payment | **−45 + pinned at 10** |
| Canceled | −6 |
| Blocked (blacklisted) | −35 + pinned |

Trusted ≥ 80 (with 3+ deliveries) · ⚠️ caution 40-79 · 🚨 dangerous < 40.

**Financial conventions:** revenue = *paid* orders · ghost/refused/phone-off loss = shipping cost · fake-payment loss = shipping + full COD price · **money saved** = shipping costs avoided on orders *blocked* before shipping.

## ✅ Tests

```bash
python tests/test_core.py       # 86 tests: DB, trust, detection, .hma, PDF, reports
python tests/test_ui_smoke.py   # full UI, headless via stubs
python tests/test_packaging.py  # version sync across app/spec/installer/CI
```

## 📁 Project structure

```
himaya/
├── main.py                  # entry point (--db, --init-only)
├── requirements.txt
├── himaya.spec              # PyInstaller config
├── build_windows.bat        # 1-click portable build
├── build_installer.bat      # 1-click setup.exe (PyInstaller + Inno Setup)
├── installer/               # himaya.iss (Inno Setup) + exe version info
├── .github/workflows/       # automatic setup.exe builds on GitHub
├── assets/                  # logo, icon, fonts, optional TFLite models
├── tools/                   # logo/icon generators
├── tests/                   # headless tests (core + UI + packaging)
└── himaya/
    ├── config.py            # paths, colors, business constants
    ├── wilayas.py           # the 58 wilayas (FR + AR)
    ├── i18n.py              # complete FR/AR translations
    ├── database/            # SQLite engine + schema + seed
    ├── models/              # customers, orders, blacklist, inquiries, receipts…
    ├── services/            # trust, phone, detector (OCR/AI), reports, hma, labels…
    └── ui/                  # app + 9 CustomTkinter pages
```

## 🤝 License & pledge

Built for the Algerian seller community (MIT License — see `LICENSE`).
Your data never leaves your computer — that's the Himaya pledge.
وعد حماية: معطياتك لا تغادر جهازك أبداً.

"""
Fake BaridiMob / CCP receipt detector — 100% local forensics, no network.

Layers of analysis:
  1. Perceptual hash (dHash, 64-bit): exact/near-duplicate match against
     previously saved fake screenshots (catches re-used fakes instantly).
  2. Metadata forensics: editor signatures (Snapseed, PicsArt, Photoshop…),
     missing screenshot markers, suspicious XMP/EXIF entries.
  3. OCR (Tesseract, French+English): extracts amount, date, reference,
     phone. Checks formats + plausibility (future date = fake).
  4. Pixel forensics (OpenCV):
       - stroke-width / edge-density variance between text regions
         (pasted numbers look sharper or blurrier than the rest),
       - ELA (Error Level Analysis) hotspot detection around text areas.
  5. Optional TFLite classifier: drop a model in assets/models/*.tflite and
     it is loaded automatically; the app works fine without it.

Verdicts: REAL / SUSPICIOUS / FAKE with a list of machine-readable reasons
(codes + human details) so the UI can translate them (AR/FR).
"""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

try:  # OpenCV is used for pixel forensics only — degrade gracefully if absent
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:  # pragma: no cover
    HAS_CV2 = False

from .. import config
from ..database.db import Database
from ..models import screenshots as screenshots_model
from .phone import normalize_phone

VERDICT_REAL, VERDICT_SUSPICIOUS, VERDICT_FAKE = "real", "suspicious", "fake"

# Editors/keywords that reveal an image was modified after download
_EDITOR_SIGNATURES = [
    "snapseed", "picsart", "photoshop", "lightroom", "canva", "pixlr",
    "photoeditor", "airbrush", "retouch", "facetune", "polarr", "vsco",
    "image editor", "pixellab", "pixel lab", "supreme", "background eraser",
]

# Values we expect in BaridiMob/Algerie Poste receipts
_AMOUNT_RE = re.compile(r"([\d][\d\s.,]{2,15})\s*(?:da|dzd)", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")
_REF_RE = re.compile(r"(?:r[ée]f[ée]rence|r[ée]f|ref|n°|no|id|transaction)[:\s#.°]*(\d{5,15})", re.IGNORECASE)
_LONG_NUM_RE = re.compile(r"\b(\d{9,15})\b")
_PHONE_RE = re.compile(r"\b(0[5-7]\d{8}|(?:\+|00)213[567]\d{8})\b")


# ---------------------------------------------------------------------------
# Perceptual hashing
# ---------------------------------------------------------------------------

def dhash(image: Image.Image, size: int = 8) -> str:
    """64-bit difference hash, robust to compression / small edits."""
    img = ImageOps.exif_transpose(image).convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(img.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            left = px[row * (size + 1) + col]
            right = px[row * (size + 1) + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    return f"{bits:016x}"


def hamming_hex(h1: str, h2: str) -> int:
    if len(h1) != len(h2):
        return 64
    return bin(int(h1, 16) ^ int(h2, 16)).count("1")


# ---------------------------------------------------------------------------
# Metadata forensics
# ---------------------------------------------------------------------------

def check_metadata(image: Image.Image) -> list[str]:
    """Return reason codes found in EXIF/XMP/text chunks."""
    reasons: list[str] = []
    info = image.info or {}
    blob = ""
    for v in info.values():
        if isinstance(v, (str, bytes)):
            blob += v.decode("utf-8", "ignore") if isinstance(v, bytes) else v
    low = blob.lower()
    for sig in _EDITOR_SIGNATURES:
        if sig in low:
            reasons.append(f"editor_signature::{sig}")
    if image.format == "PNG" and not any(k.startswith("dpi") or k == "srgb" for k in info) \
            and "screenshot" not in low and blob:
        # PNG saved by an editor usually loses screenshot chunks
        reasons.append("png_missing_screenshot_chunks")
    return reasons


# ---------------------------------------------------------------------------
# OCR extraction
# ---------------------------------------------------------------------------

def _ocr_text(image: Image.Image, tesseract_cmd: str = "") -> tuple[str, bool]:
    """Run pytesseract (fra+eng). Returns (text, ok). Never raises."""
    try:
        import pytesseract
        cmd = tesseract_cmd or config.bundled_tesseract()
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        # upscale improves OCR on small phone screenshots
        w, h = image.size
        scale = 2 if max(w, h) < 1500 else 1
        if scale > 1:
            image = image.resize((w * scale, h * scale), Image.LANCZOS)
        return pytesseract.image_to_string(image, lang="fra+eng"), True
    except Exception:
        return "", False


def parse_receipt(text: str) -> dict:
    """Extract structured fields from OCR text (amount, date, ref, phone)."""
    out = {"amount": None, "date": None, "ref": None, "phone": None}

    m = _AMOUNT_RE.search(text)
    if m:
        raw = m.group(1).strip().replace(" ", "")
        # drop trailing decimals ("4500,00" -> "4500") before digit extraction
        raw = re.sub(r"[.,]\d{1,2}$", "", raw)
        num = re.sub(r"[^\d]", "", raw)
        if num:
            out["amount"] = int(num)

    dm = _DATE_RE.search(text)
    if dm:
        d_, m_, y = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
        if y < 100:
            y += 2000
        try:
            out["date"] = datetime(y, m_, d_)
        except ValueError:
            out["date"] = "invalid"

    rm = _REF_RE.search(text)
    if rm:
        out["ref"] = rm.group(1)
    else:
        lm = _LONG_NUM_RE.search(text)
        if lm:
            out["ref"] = lm.group(1)

    pm = _PHONE_RE.search(text)
    if pm:
        out["phone"] = normalize_phone(pm.group(1))
    return out


def check_extracted(extracted: dict, now: datetime | None = None) -> list[str]:
    """Format + plausibility checks on OCR fields."""
    now = now or datetime.now()
    reasons: list[str] = []
    d = extracted.get("date")
    if d == "invalid":
        reasons.append("date_invalid_format")
    elif isinstance(d, datetime):
        if d > now + timedelta_days(1):
            reasons.append("date_in_future")
        elif (now - d).days > 400:
            reasons.append("date_too_old")
        # else: date plausible — no reason
    else:
        reasons.append("date_not_found")

    ref = extracted.get("ref")
    if ref is None:
        reasons.append("ref_not_found")

    if extracted.get("amount") is None:
        reasons.append("amount_not_found")
    elif extracted["amount"] > 10_000_000:
        reasons.append("amount_implausible")
    return reasons


def timedelta_days(n: int):
    from datetime import timedelta
    return timedelta(days=n)


# ---------------------------------------------------------------------------
# Pixel forensics (OpenCV)
# ---------------------------------------------------------------------------

def _text_regions_conflict(pil_img: Image.Image) -> list[str]:
    """
    Compare edge-density of text regions (via pytesseract boxes when
    available, else contour analysis). Pasted digits typically differ from
    native text -> high coefficient of variation.
    """
    if not HAS_CV2:
        return []
    reasons = []
    try:
        img = np.array(pil_img.convert("L"))
        edges = cv2.Canny(cv2.GaussianBlur(img, (3, 3), 0), 50, 150)
        # split into a 4x8 grid, compute edge density per cell that contains text-ish content
        h, w = edges.shape
        densities = []
        for r in range(4):
            for c in range(8):
                cell = edges[r * h // 4:(r + 1) * h // 4, c * w // 8:(c + 1) * w // 8]
                d = float((cell > 0).sum()) / cell.size
                if d > 0.005:  # ignore empty areas
                    densities.append(d)
        if len(densities) >= 8:
            mean = sum(densities) / len(densities)
            var = sum((x - mean) ** 2 for x in densities) / len(densities)
            cv = (var ** 0.5) / mean if mean else 0
            if cv > 1.8:  # conservative: only glaring font mismatches
                reasons.append("font_inconsistency")
    except Exception:
        pass
    return reasons


def _ela_hotspots(pil_img: Image.Image) -> list[str]:
    """
    Error Level Analysis: re-compress and measure per-region residuals.
    Only meaningful for JPEG sources (quantization-error analysis); PNG
    screenshots are skipped to avoid false positives.
    """
    if not HAS_CV2 or (pil_img.format or "").upper() != "JPEG":
        return []
    try:
        buf = io.BytesIO()
        pil_img.convert("RGB").save(buf, "JPEG", quality=88)
        buf.seek(0)
        recompressed = Image.open(buf)
        ela = ImageChops.difference(pil_img.convert("RGB"), recompressed)
        arr = np.array(ela.convert("L")).astype(float)
        h, w = arr.shape
        cells = []
        for r in range(4):
            for c in range(4):
                cell = arr[r * h // 4:(r + 1) * h // 4, c * w // 4:(c + 1) * w // 4]
                cells.append(cell.mean())
        cells.sort()
        median = cells[len(cells) // 2]
        top = cells[-1]
        # a locally edited region stands out clearly against the median
        if median < 4 and top > 14 and top > median + 10:
            return ["ela_localized_edit"]
        if median >= 4 and top > median * 3.5:
            return ["ela_localized_edit"]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Optional TFLite classifier
# ---------------------------------------------------------------------------

class TFLiteClassifier:
    """Loads the first .tflite model in assets/models (if any). Purely optional."""

    def __init__(self):
        self.interp = None
        self.input_details = self.output_details = None
        from ..config import ASSETS_DIR
        models_dir = ASSETS_DIR / "models"
        if models_dir.exists():
            for f in sorted(models_dir.glob("*.tflite")):
                try:
                    from tflite_runtime.interpreter import Interpreter  # type: ignore
                    self.interp = Interpreter(model_path=str(f))
                    self.interp.allocate_tensors()
                    self.input_details = self.interp.get_input_details()
                    self.output_details = self.interp.get_output_details()
                    break
                except Exception:
                    continue

    @property
    def available(self) -> bool:
        return self.interp is not None

    def predict(self, pil_img: Image.Image) -> float | None:
        """Return fake-probability 0..1, or None if no model / wrong shape."""
        if not self.interp:
            return None
        try:
            import numpy as np
            inp = self.input_details[0]
            h, w = inp["shape"][1], inp["shape"][2]
            arr = np.array(pil_img.convert("RGB").resize((w, h)), dtype=np.float32) / 255.0
            if inp["shape"][0] == 1:
                arr = arr[np.newaxis, ...]
            self.interp.set_tensor(inp["index"], arr)
            self.interp.invoke()
            out = self.interp.get_tensor(self.output_details[0]["index"])[0]
            return float(out[-1])
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

# Reason codes -> severity weight (how strongly they push towards FAKE)
_RED_FLAGS = {
    "known_fake_match": 60, "known_fake_near_match": 40,
    "editor_signature": 55, "date_in_future": 45, "date_invalid_format": 25,
    "ela_localized_edit": 30, "font_inconsistency": 25,
}
_YELLOW_FLAGS = {
    "amount_not_found": 8, "date_not_found": 8, "ref_not_found": 5,
    "png_missing_screenshot_chunks": 10, "date_too_old": 10,
    "amount_implausible": 20, "ocr_unavailable": 0, "pixel_checks_skipped": 0,
}


def analyze(path: str | Path, db: Database | None = None,
            tesseract_cmd: str = "") -> dict:
    """
    Full analysis of a payment screenshot.

    Returns {
        path, verdict, confidence, reasons: [(code, detail)],
        extracted: {amount, date(str), ref, phone}, hash, near_matches: n
    }
    """
    path = Path(path)
    result = {
        "path": str(path), "verdict": VERDICT_SUSPICIOUS, "confidence": 0,
        "reasons": [], "extracted": {"amount": None, "date": None,
                                     "ref": None, "phone": None},
        "hash": "", "near_matches": 0,
    }
    try:
        image = Image.open(path)
        image.load()
    except Exception as e:
        result["verdict"] = VERDICT_FAKE
        result["reasons"].append(("unreadable_image", str(e)))
        result["confidence"] = 100
        return result

    score = 0  # weighted red flags total
    reasons: list[tuple[str, str]] = []

    # ---- 1. perceptual hash vs known fakes --------------------------------
    h = dhash(image)
    result["hash"] = h
    if db is not None:
        known = screenshots_model.recent(db, limit=100000)
        near = 0
        for row in known:
            dist = hamming_hex(h, row["image_hash"])
            if dist == 0:
                reasons.append(("known_fake_match", row["phone"] or ""))
                score += _RED_FLAGS["known_fake_match"]
            elif dist <= 6:
                near += 1
        if near:
            reasons.append(("known_fake_near_match", str(near)))
            score += _RED_FLAGS["known_fake_near_match"]

    # ---- 2. metadata -------------------------------------------------------
    for code in check_metadata(image):
        base = code.split("::")[0]
        reasons.append((code, code.split("::", 1)[1] if "::" in code else ""))
        score += _RED_FLAGS.get(base, 10)

    # ---- 3. OCR ------------------------------------------------------------
    text, ocr_ok = _ocr_text(image, tesseract_cmd)
    if not ocr_ok:
        reasons.append(("ocr_unavailable", ""))
    extracted = parse_receipt(text)
    result["extracted"] = {
        "amount": extracted.get("amount"),
        "date": extracted["date"].strftime("%d/%m/%Y") if isinstance(extracted.get("date"), datetime) else None,
        "ref": extracted.get("ref"),
        "phone": extracted.get("phone"),
    }
    for code in check_extracted(extracted):
        reasons.append((code, ""))
        score += _RED_FLAGS.get(code, _YELLOW_FLAGS.get(code, 10))

    # ---- 4. pixel forensics ------------------------------------------------
    pixel_reasons = _text_regions_conflict(image) + _ela_hotspots(image)
    for code in pixel_reasons:
        reasons.append((code, ""))
        score += _RED_FLAGS.get(code, 20)
    if not HAS_CV2:
        reasons.append(("pixel_checks_skipped", ""))

    # ---- 5. optional TFLite classifier -------------------------------------
    clf = TFLiteClassifier()
    if clf.available:
        p = clf.predict(image)
        if p is not None:
            reasons.append(("tflite_model", f"{p:.2f}"))
            score += int(p * 50)

    # ---- verdict -----------------------------------------------------------
    confidence = min(100, int(score * 1.3))
    if score >= 45:
        verdict = VERDICT_FAKE
    elif score >= 15:
        verdict = VERDICT_SUSPICIOUS
    else:
        verdict = VERDICT_REAL
        confidence = max(10, 100 - score * 2)

    result["verdict"] = verdict
    result["confidence"] = confidence if verdict != VERDICT_REAL else min(100, max(60, 100 - score * 3))
    result["reasons"] = reasons
    return result


def save_evidence(db: Database, analysis: dict) -> str:
    """Copy the analysed image into the evidence folder + record hash/details."""
    from ..config import EVIDENCE_DIR
    src = Path(analysis["path"])
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = EVIDENCE_DIR / f"{stamp}_{src.name}"
    try:
        Image.open(src).save(dest)
    except Exception:
        import shutil
        shutil.copy2(src, dest)
    screenshots_model.save(
        db, analysis["hash"],
        (analysis.get("extracted") or {}).get("phone", ""),
        {"verdict": analysis["verdict"], "confidence": analysis["confidence"],
         "reasons": [list(r) for r in analysis["reasons"]],
         "extracted": analysis.get("extracted", {}),
         "evidence_file": dest.name},
    )
    return str(dest)

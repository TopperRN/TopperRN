"""Prep a selfie for ASCII conversion: crop to the head, cut the background, boost contrast.

Usage:
    python scripts/prep_photo.py PHOTO [--out .portrait/source-prepped.png] [--rembg]

The background cut uses OpenCV GrabCut by default, so nothing gets downloaded.
Pass --rembg to use rembg instead (fetches its ~170 MB model on first run).
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent

# crop around the detected face, in multiples of the face box size
PAD_TOP = 0.75     # room for hair
PAD_SIDE = 0.85
PAD_BOTTOM = 0.20  # chin and a bit of neck, faded out
FADE = 0.22        # bottom share of the crop that fades out


def load(path):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


def find_face(bgr):
    gray = cv2.equalizeHist(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    side = gray.shape[1] // 6
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(side, side))
    if len(faces) == 0:
        return None
    return tuple(int(v) for v in max(faces, key=lambda f: f[2] * f[3]))


def mask_grabcut(bgr, face):
    h, w = bgr.shape[:2]
    scale = 700 / max(h, w)
    small = cv2.resize(bgr, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]
    fx, fy, fw, fh = (round(v * scale) for v in face)

    mask = np.full((sh, sw), cv2.GC_BGD, np.uint8)
    x0, x1 = max(1, int(fx - 1.0 * fw)), min(sw - 2, int(fx + 2.0 * fw))
    y0 = max(1, int(fy - 1.1 * fh))
    mask[y0:sh - 1, x0:x1] = cv2.GC_PR_FGD
    # the face itself is certainly foreground
    cv2.ellipse(mask, (fx + fw // 2, fy + fh // 2), (int(fw * 0.4), int(fh * 0.55)), 0, 0, 360, cv2.GC_FGD, -1)

    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(small, mask, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)

    # keep the largest blob, close small holes, soften the edge
    n, labels, stats, _ = cv2.connectedComponentsWithStats(alpha)
    if n > 1:
        alpha = (labels == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    alpha = cv2.resize(alpha.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(alpha, (0, 0), 3)


def trim_below_jaw(alpha, face):
    """Below the mouth keep only chin and neck, so a couch or bare shoulders drop out.

    This is geometric on purpose: marking those areas as background inside GrabCut
    teaches it that skin is background, and then it keeps the wall instead.
    """
    h, w = alpha.shape
    fx, fy, fw, fh = face
    cx, cy = fx + fw // 2, fy + fh // 2
    keep = np.zeros((h, w), np.uint8)
    cv2.ellipse(keep, (cx, cy), (int(0.46 * fw), int(0.72 * fh)), 0, 0, 360, 1, -1)
    cv2.rectangle(keep, (int(fx + 0.22 * fw), cy), (int(fx + 0.78 * fw), h), 1, -1)
    keep[:int(fy + 0.72 * fh)] = 1
    return alpha * cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 6)


def mask_rembg(bgr):
    from rembg import remove

    rgba = remove(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
    return np.asarray(rgba)[:, :, 3].astype(np.float32) / 255


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--out", default=str(ROOT / ".portrait" / "source-prepped.png"))
    ap.add_argument("--rembg", action="store_true")
    args = ap.parse_args()

    bgr = load(args.photo)
    h, w = bgr.shape[:2]
    face = find_face(bgr)
    if face is None:
        print("no face found, using a centered crop")
        face = (int(w * 0.3), int(h * 0.3), int(w * 0.4), int(w * 0.4))
    fx, fy, fw, fh = face
    print(f"face box: x={fx} y={fy} w={fw} h={fh}")

    alpha = mask_rembg(bgr) if args.rembg else mask_grabcut(bgr, face)
    alpha = trim_below_jaw(alpha, face)

    x0, x1 = max(0, int(fx - PAD_SIDE * fw)), min(w, int(fx + fw + PAD_SIDE * fw))
    y0, y1 = max(0, int(fy - PAD_TOP * fh)), min(h, int(fy + fh + PAD_BOTTOM * fh))
    print(f"crop: x={x0}..{x1} y={y0}..{y1}")
    gray = cv2.cvtColor(bgr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    alpha = alpha[y0:y1, x0:x1]

    # local contrast gives a flatly lit face real highlights and shadows
    gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray).astype(np.float32)
    subject = gray[alpha > 0.5]
    lo, hi = np.percentile(subject, 2), np.percentile(subject, 98)
    gray = np.clip((gray - lo) / max(hi - lo, 1) * 255, 0, 255)

    ch = alpha.shape[0]
    fade_px = int(ch * FADE)
    ramp = np.ones(ch, np.float32)
    ramp[ch - fade_px:] = np.linspace(1, 0, fade_px) ** 1.5
    alpha = alpha * ramp[:, None]

    # gray + alpha, so the ASCII step knows exactly where the subject ends
    out = np.dstack([gray, alpha * 255]).astype(np.uint8)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out).save(args.out)
    print(f"wrote {args.out} ({out.shape[1]}x{out.shape[0]})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Prepare the photo for clean, high-contrast ASCII conversion:
1. Isolate the subject and remove background.
2. Bilateral smoothing for clean skin texture while preserving sharp edges.
3. CLAHE local contrast enhancement.
4. Darken linework (eyes, glasses, beard, smile).
5. Output grayscale source-prepped.png.
"""
import os
import sys
import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.png")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")

img = cv2.imread(INP)
if img is None:
    print(f"Error reading image: {INP}", file=sys.stderr)
    sys.exit(1)

h, w = img.shape[:2]

# Try rembg if available, otherwise GrabCut
mask2 = None
try:
    from rembg import remove
    pil_cut = remove(Image.open(INP).convert("RGBA"))
    alpha = np.array(pil_cut.split()[-1])
    mask2 = np.where(alpha > 40, 1, 0).astype("uint8")
except Exception:
    pass

if mask2 is None:
    mask = np.zeros(img.shape[:2], np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    rect = (2, 2, w - 4, h - 4)
    cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 6, cv2.GC_INIT_WITH_RECT)
    mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")

composite = np.where(mask2[:, :, np.newaxis] == 1, img, np.full_like(img, 255))
gray = cv2.cvtColor(composite, cv2.COLOR_BGR2GRAY)

smooth = gray
for _ in range(2):
    smooth = cv2.bilateralFilter(smooth, 7, 30, 7)

clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
contrast = clahe.apply(smooth)

fine = cv2.GaussianBlur(smooth, (0, 0), 1.0).astype(np.float32)
coarse = cv2.GaussianBlur(smooth, (0, 0), 4.0).astype(np.float32)
lines = np.clip((coarse - fine) / 30.0, 0, 1)

tone = contrast.astype(np.float32) / 255.0
out = np.clip(tone - 0.45 * lines, 0, 1) * 255.0
out_final = np.where(mask2 == 1, out, 255.0).astype(np.uint8)

os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
Image.fromarray(out_final, mode="L").save(OUT)
print("Successfully generated", OUT)

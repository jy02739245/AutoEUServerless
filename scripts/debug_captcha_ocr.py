#!/usr/bin/env python3
import argparse
import re
from collections import Counter
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

try:
    import ddddocr
except ImportError:
    ddddocr = None


def normalize_captcha_code(raw_text: str) -> str:
    text = raw_text.strip()
    text = text.replace(" ", "").replace("\n", "").replace("\t", "")
    text = text.replace("=", "").replace("×", "x").replace("—", "-")
    text = re.sub(r"[^0-9A-Za-z+\-*xX]", "", text)
    if not text:
        return ""

    expression = re.fullmatch(r"(\d+)([+\-*xX])(\d+)", text)
    if expression:
        left = int(expression.group(1))
        operator = expression.group(2)
        right = int(expression.group(3))
        if operator == "+":
            return str(left + right)
        if operator == "-":
            return str(left - right)
        return str(left * right)

    if re.fullmatch(r"[0-9A-Za-z]{6}", text):
        return text
    return ""


def upscale_for_ocr(image, factor=3, border=4):
    resampling = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
    bordered = ImageOps.expand(image, border=border, fill=255)
    width, height = bordered.size
    return bordered.resize((width * factor, height * factor), resampling)


def build_orange_foreground_mask(image):
    hsv = image.convert("HSV")
    mask = Image.new("L", hsv.size, 255)
    source = hsv.load()
    target = mask.load()
    for y in range(hsv.size[1]):
        for x in range(hsv.size[0]):
            hue, saturation, value = source[x, y]
            if 2 <= hue <= 35 and saturation >= 45 and value >= 80:
                target[x, y] = 0
    return mask


def crop_foreground(image, pad=2):
    pixels = image.load()
    xs = []
    ys = []
    for y in range(image.size[1]):
        for x in range(image.size[0]):
            if pixels[x, y] < 128:
                xs.append(x)
                ys.append(y)
    if not xs:
        return image

    left = max(0, min(xs) - pad)
    top = max(0, min(ys) - pad)
    right = min(image.size[0], max(xs) + pad + 1)
    bottom = min(image.size[1], max(ys) + pad + 1)
    return image.crop((left, top, right, bottom))


def build_variants(image):
    grayscale = ImageOps.autocontrast(image.convert("L"))
    scaled = upscale_for_ocr(grayscale)
    denoised = scaled.filter(ImageFilter.MedianFilter(size=3))

    variants = [
        ("gray_scaled", scaled),
        ("gray_denoised", denoised),
    ]
    for threshold in (110, 140, 170, 200):
        variants.append(
            (
                f"gray_threshold_{threshold}",
                scaled.point(lambda pixel, t=threshold: 255 if pixel > t else 0),
            )
        )
        variants.append(
            (
                f"denoised_threshold_{threshold}",
                denoised.point(lambda pixel, t=threshold: 255 if pixel > t else 0),
            )
        )

    orange_base = build_orange_foreground_mask(image)
    orange_opened_original = orange_base.filter(ImageFilter.MaxFilter(size=5)).filter(
        ImageFilter.MinFilter(size=5)
    )
    for pad in (0, 2, 4, 8, 12):
        cropped = crop_foreground(orange_opened_original, pad=pad)
        for factor in (1, 2, 3, 4, 5, 6, 8):
            variants.append(
                (
                    f"orange_open5_crop_p{pad}_b8_x{factor}",
                    upscale_for_ocr(cropped, factor=factor, border=8),
                )
            )

    orange_mask = upscale_for_ocr(orange_base)
    orange_denoised = orange_mask.filter(ImageFilter.MedianFilter(size=3))
    orange_opened = orange_denoised.filter(ImageFilter.MaxFilter(size=3)).filter(
        ImageFilter.MinFilter(size=3)
    )
    orange_closed = orange_denoised.filter(ImageFilter.MinFilter(size=3)).filter(
        ImageFilter.MaxFilter(size=3)
    )
    variants.extend(
        [
            ("orange_mask", orange_mask),
            ("orange_denoised", orange_denoised),
            ("orange_opened", orange_opened),
            ("orange_closed", orange_closed),
        ]
    )
    return variants


def choose_best_local_ocr_candidate(candidates):
    if not candidates:
        return ""

    grouped_counts = Counter()
    first_candidate = {}
    for code in candidates:
        group_key = code.lower() if re.fullmatch(r"[0-9A-Za-z]{6}", code) else code
        grouped_counts[group_key] += 1
        first_candidate.setdefault(group_key, code)

    best_group, count = grouped_counts.most_common(1)[0]
    if count < 2:
        return ""
    return first_candidate[best_group]


def run_ddddocr(variants):
    if ddddocr is None:
        print("DdddOCR: not installed. Install with: pip install ddddocr")
        return

    print("DdddOCR:")
    ocr = ddddocr.DdddOcr(show_ad=False)
    candidates = []
    raw_counter = Counter()
    for name, variant in variants:
        try:
            raw_text = ocr.classification(variant.convert("RGB"))
        except Exception as exc:
            print(f"{name:<32} raw=ERR {type(exc).__name__}: {exc}")
            continue

        code = normalize_captcha_code(raw_text)
        print(f"{name:<32} raw={raw_text!r:<12} code={code!r}")
        if code:
            candidates.append(code)
            raw_counter[code] += 1

    print()
    if raw_counter:
        print("DdddOCR raw candidate ranking:")
        for code, count in raw_counter.most_common():
            print(f"{code}: {count}")
        best = choose_best_local_ocr_candidate(candidates)
        print(f"DdddOCR selected: {best or '<unstable>'}")
    else:
        print("DdddOCR found no usable OCR candidate.")
    print()


def main():
    parser = argparse.ArgumentParser(description="Debug EUserv captcha OCR locally.")
    parser.add_argument("image", help="Path to a saved captcha image")
    parser.add_argument(
        "--out-dir",
        default="captcha_debug",
        help="Directory for preprocessed variant images",
    )
    args = parser.parse_args()

    image_path = Path(args.image)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(image_path)
    variants = build_variants(image)

    print(f"Image: {image_path}")
    print(f"Variant images: {out_dir}")
    print()

    run_ddddocr(variants)

    for index, (name, variant) in enumerate(variants, start=1):
        variant_path = out_dir / f"{index:02d}_{name}.png"
        variant.save(variant_path)
    print(f"Saved {len(variants)} variant images.")


if __name__ == "__main__":
    main()

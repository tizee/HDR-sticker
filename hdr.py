# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "numpy",
#   "pillow",
# ]
# ///

import os
import argparse
from typing import Tuple
from PIL import Image
import numpy as np

# 调整自 @Yufeng Wang 的代码，使之可以观感上较为正确地完成色调映射
# FIXME：将需要 dithering 2bit 的 Alpha 改为能正常混合的 Alpha Pass/Weight

# Image processing constants
DEFAULT_HDR_BOOST_FACTOR = 2.5             # HDR 区域的提亮程度，建议 2.0~4.0 间，观测图片是否会过曝白切
DEFAULT_SDR_DARKEN_FACTOR = 0.6            # SDR 区域的压暗程度，建议 0.5~0.7 间，观察图片是否与目标显示设备的白点基准接近
DEFAULT_ICC_PROFILE_PATH = "rec2100pq-experimental.icc"
MAX_SIZE = 240                             # wechat sticker size

# Processing constants
ALPHA_THRESHOLD = 50                       # Alpha channel threshold for mask detection
RGB_CHANNELS = 3                           # Number of RGB channels (excluding alpha)
GAMMA_VALUE = 2.2                          # Standard sRGB gamma value
COMPRESS_LEVEL = 9                         # PNG compression level
PALETTE_COLORS = 128                       # Colors for palette mode (if needed)

def check(path: str) -> None:
    """Validate that a file exists at the given path."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")

def adjust_gamma(rgb: np.ndarray, factor: float) -> np.ndarray:
    """RGB gamma-aware brightening (sRGB ↔ linear ↔ sRGB).

    Args:
        rgb: RGB array values (0-255)
        factor: Brightness adjustment factor

    Returns:
        Gamma-corrected RGB array
    """
    if factor <= 0:
        raise ValueError("Brightness factor must be positive")

    linear = np.power(rgb / 255.0, GAMMA_VALUE)
    boosted = np.clip(linear * factor, 0.0, 1.0)
    return (np.power(boosted, 1 / GAMMA_VALUE) * 255).astype(np.uint8)

def _load_images(base_path: str, overlay_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load and convert images to RGBA numpy arrays."""
    base = Image.open(base_path).convert("RGBA")
    overlay = Image.open(overlay_path).convert("RGBA")
    return np.array(base), np.array(overlay)

def _create_mask(overlay_np: np.ndarray) -> np.ndarray:
    """Create boolean mask from alpha channel."""
    return overlay_np[:, :, 3] > ALPHA_THRESHOLD

def _create_highlight_layer(overlay_np: np.ndarray, mask: np.ndarray, hdr_boost: float) -> np.ndarray:
    """Create HDR highlight layer from overlay."""
    highlight = np.zeros_like(overlay_np)
    highlight[mask] = overlay_np[mask]
    highlight[mask, :RGB_CHANNELS] = adjust_gamma(highlight[mask, :RGB_CHANNELS], hdr_boost)
    return highlight

def _darken_background(base_np: np.ndarray, mask: np.ndarray, sdr_darken: float) -> None:
    """Darken background areas in-place."""
    base_np[~mask, :RGB_CHANNELS] = (base_np[~mask, :RGB_CHANNELS] * sdr_darken).astype(np.uint8)

def _resize_image(image: Image.Image) -> Image.Image:
    """Resize image to fit maximum sticker size."""
    w, h = image.size
    scale = min(MAX_SIZE / w, MAX_SIZE / h, 1.0)
    if scale < 1.0:
        return image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return image

def _save_with_icc(image: Image.Image, output_path: str, icc_path: str) -> None:
    """Save image with ICC profile."""
    with open(icc_path, "rb") as f:
        icc_profile = f.read()
    image.save(output_path, format="PNG",
               icc_profile=icc_profile, optimize=True, compress_level=COMPRESS_LEVEL)

def highlight_overlay(base_path: str, overlay_path: str, icc_path: str,
                     out_path: str, hdr_boost: float, sdr_darken: float) -> None:
    """Process HDR sticker by overlaying enhanced highlights on base image.

    Args:
        base_path: Path to SDR base image
        overlay_path: Path to HDR overlay mask
        icc_path: Path to ICC color profile
        out_path: Output image path
        hdr_boost: HDR brightness boost factor
        sdr_darken: SDR background darkening factor
    """
    # Load images
    base_np, overlay_np = _load_images(base_path, overlay_path)

    # Create mask and highlight layer
    mask = _create_mask(overlay_np)
    highlight = _create_highlight_layer(overlay_np, mask, hdr_boost)

    # Process background
    _darken_background(base_np, mask, sdr_darken)

    # Composite images
    result = Image.alpha_composite(
        Image.fromarray(base_np),
        Image.fromarray(highlight)
    )

    # Resize and save
    result = _resize_image(result)
    _save_with_icc(result, out_path, icc_path)

def main() -> None:
    """Main entry point for HDR sticker processing."""
    parser = argparse.ArgumentParser(description='Process HDR stickers for WeChat/Feishu')
    parser.add_argument('base_image', help='SDR base image (PNG)')
    parser.add_argument('overlay_image', help='HDR overlay image (PNG)')
    parser.add_argument('--output', '-o', default='output.png',
                       help='Output image path (default: output.png)')
    parser.add_argument('--hdr-boost', type=float, default=DEFAULT_HDR_BOOST_FACTOR,
                        help=f'HDR boost factor (default: {DEFAULT_HDR_BOOST_FACTOR})')
    parser.add_argument('--sdr-darken', type=float, default=DEFAULT_SDR_DARKEN_FACTOR,
                        help=f'SDR darken factor (default: {DEFAULT_SDR_DARKEN_FACTOR})')
    parser.add_argument('--icc-profile', default=DEFAULT_ICC_PROFILE_PATH,
                        help=f'ICC profile path (default: {DEFAULT_ICC_PROFILE_PATH})')

    args = parser.parse_args()

    try:
        # Validate inputs
        for filepath in (args.base_image, args.overlay_image, args.icc_profile):
            check(filepath)

        # Validate parameters
        if args.hdr_boost <= 0:
            raise ValueError("HDR boost factor must be positive")
        if args.sdr_darken <= 0:
            raise ValueError("SDR darken factor must be positive")

        # Process images
        highlight_overlay(args.base_image, args.overlay_image,
                         args.icc_profile, args.output,
                         args.hdr_boost, args.sdr_darken)

        print(f"HDR sticker saved to: {args.output}")

    except (FileNotFoundError, ValueError, IOError) as e:
        print(f"Error: {e}")
        exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(1)

if __name__ == "__main__":
    main()

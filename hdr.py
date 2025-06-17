# /// script
# requires-python = ">=3.8"
# dependencies = [
#   "numpy",
#   "pillow",
# ]
# ///

import os
import argparse
from PIL import Image
import numpy as np

# 调整自 @Yufeng Wang 的代码，使之可以观感上较为正确地完成色调映射
# FIXME：将需要 dithering 2bit 的 Alpha 改为能正常混合的 Alpha Pass/Weight

DEFAULT_HDR_BOOST_FACTOR = 2.5             # HDR 区域的提亮程度，建议 2.0~4.0 间，观测图片是否会过曝白切
DEFAULT_SDR_DARKEN_FACTOR = 0.6            # SDR 区域的压暗程度，建议 0.5~0.7 间，观察图片是否与目标显示设备的白点基准接近
DEFAULT_ICC_PROFILE_PATH = "rec2100pq-experimental.icc"
MAX_SIZE = 240                     # wechat sticker size

def check(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

def adjust_gamma(rgb: np.ndarray, factor: float) -> np.ndarray:
    """RGB gamma-aware brightening (sRGB ↔ linear ↔ sRGB)."""
    gamma = 2.2
    linear = np.power(rgb / 255.0, gamma)
    boosted = np.clip(linear * factor, 0.0, 1.0)
    return (np.power(boosted, 1 / gamma) * 255).astype(np.uint8)

def highlight_overlay(base_path, overlay_path, icc_path, out_path, hdr_boost, sdr_darken):
    base  = Image.open(base_path   ).convert("RGBA")
    ovl   = Image.open(overlay_path).convert("RGBA")

    base_np = np.array(base)
    ovl_np  = np.array(ovl)

    mask = ovl_np[:, :, 3] > 50           # bool (H,W)

    # 构造纯净高亮层
    highlight = np.zeros_like(ovl_np)     # 全零 → 完全透明
    highlight[mask] = ovl_np[mask]        # 只拷贝人物像素
    highlight[mask, 0:3] = adjust_gamma(highlight[mask, 0:3], hdr_boost)  # HDR boost

    # （可选）压暗背景
    base_np[~mask, 0:3] = (base_np[~mask, 0:3] * sdr_darken).astype(np.uint8)

    # 合成
    result = Image.alpha_composite(Image.fromarray(base_np),
                                   Image.fromarray(highlight))

    # 尺寸压缩（保持 RGBA）
    w, h = result.size
    scale = min(MAX_SIZE / w, MAX_SIZE / h, 1.0)
    if scale < 1.0:
        result = result.resize((int(w*scale), int(h*scale)), Image.LANCZOS)

    # 保存：先保持 RGBA + ICC
    with open(icc_path, "rb") as f:
        icc = f.read()
    result.save(out_path, format="PNG",
                icc_profile=icc, optimize=True, compress_level=9)

    # 若确需 8-bit 调色板，再另存一份
    # result.convert("P", palette=Image.ADAPTIVE, colors=128)\
    #       .save("output_palette.png", optimize=True, compress_level=9)

def main():
    parser = argparse.ArgumentParser(description='Process HDR stickers for WeChat/Feishu')
    parser.add_argument('base_image', help='SDR base image (PNG)')
    parser.add_argument('overlay_image', help='HDR overlay image (PNG)')
    parser.add_argument('--output', '-o', default='output.png', help='Output image path (default: output.png)')
    parser.add_argument('--hdr-boost', type=float, default=DEFAULT_HDR_BOOST_FACTOR, 
                        help=f'HDR boost factor (default: {DEFAULT_HDR_BOOST_FACTOR})')
    parser.add_argument('--sdr-darken', type=float, default=DEFAULT_SDR_DARKEN_FACTOR, 
                        help=f'SDR darken factor (default: {DEFAULT_SDR_DARKEN_FACTOR})')
    parser.add_argument('--icc-profile', default=DEFAULT_ICC_PROFILE_PATH, 
                        help=f'ICC profile path (default: {DEFAULT_ICC_PROFILE_PATH})')
    
    args = parser.parse_args()
    
    # Validate inputs
    for f in (args.base_image, args.overlay_image, args.icc_profile):
        check(f)
    
    highlight_overlay(args.base_image, args.overlay_image, 
                      args.icc_profile, args.output, 
                      args.hdr_boost, args.sdr_darken)

if __name__ == "__main__":
    main()

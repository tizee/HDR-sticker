import os
from PIL import Image
import numpy as np

# 调整自 @Yufeng Wang 的代码，使之可以观感上较为正确地完成色调映射
# FIXME：将需要 dithering 2bit 的 Alpha 改为能正常混合的 Alpha Pass/Weight

INPUT_IMAGE      = "1.png"         # SDR 区域的图片
INPUT_IMAGE_2    = "2.png"         # HDR 区域的图片
OUTPUT_PNG       = "output.png"    # 输出的图片
HDR_BOOST_FACTOR = 2.5             # HDR 区域的提亮程度，建议 2.0~4.0 间，观测图片是否会过曝白切
SDR_DARKEN_FACTOR = 0.6            # SDR 区域的压暗程度，建议 0.5~0.7 间，观察图片是否与目标显示设备的白点基准接近
ICC_PROFILE_PATH = "rec2100pq-experimental.icc"
MAX_SIZE = 240                     # wechat sticker size


def check(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

for f in (INPUT_IMAGE, INPUT_IMAGE_2, ICC_PROFILE_PATH):
    check(f)

def adjust_gamma(rgb: np.ndarray, factor: float) -> np.ndarray:
    """RGB gamma-aware brightening (sRGB ↔ linear ↔ sRGB)."""
    gamma = 2.2
    linear = np.power(rgb / 255.0, gamma)
    boosted = np.clip(linear * factor, 0.0, 1.0)
    return (np.power(boosted, 1 / gamma) * 255).astype(np.uint8)

def highlight_overlay(base_path, overlay_path, icc_path, out_path):
    base  = Image.open(base_path   ).convert("RGBA")
    ovl   = Image.open(overlay_path).convert("RGBA")

    base_np = np.array(base)
    ovl_np  = np.array(ovl)

    mask = ovl_np[:, :, 3] > 50           # bool (H,W)

    # 构造纯净高亮层
    highlight = np.zeros_like(ovl_np)     # 全零 → 完全透明
    highlight[mask] = ovl_np[mask]        # 只拷贝人物像素
    highlight[mask, 0:3] = adjust_gamma(highlight[mask, 0:3], HDR_BOOST_FACTOR)  # HDR boost

    # （可选）压暗背景
    base_np[~mask, 0:3] = (base_np[~mask, 0:3] * SDR_DARKEN_FACTOR).astype(np.uint8)

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

if __name__ == "__main__":
    highlight_overlay(INPUT_IMAGE, INPUT_IMAGE_2,
                      ICC_PROFILE_PATH, OUTPUT_PNG)

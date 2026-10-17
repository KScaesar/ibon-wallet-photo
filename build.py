# /// script
# dependencies = [
#   "pillow>=10.0.0",
# ]
# ///
"""
7-11 ibon 2x3 吋皮夾照 4 合 1 自動排版腳本
自動偵測相片原生方向（直式毛玻璃保留、橫式智慧置中裁切），
並校正為 sRGB 色彩空間輸出至 7-11 ibon (10x14.8cm, 300 DPI) 與標準 4x6 規格。
"""

import io
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFilter, ImageEnhance, ImageCms

def load_photo(p: Path) -> Image.Image:
    """載入照片、自動依 EXIF 校正方向，並確保轉換為標準 sRGB 色彩空間避免機台偏色。"""
    if not p.is_file():
        raise SystemExit(f"錯誤：找不到照片檔案 '{p}'，請確認當前目錄已放置 photo1.jpg ~ photo4.jpg。")
    im = Image.open(p)
    im = ImageOps.exif_transpose(im)
    
    # 若照片包含非 sRGB 之 ICC Profile (如 iPhone 常見之 Display P3)，轉換為標準 sRGB
    icc = im.info.get("icc_profile")
    if icc:
        try:
            src_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            srgb_profile = ImageCms.createProfile("sRGB")
            im = ImageCms.profileToProfile(im, src_profile, srgb_profile, outputMode="RGB")
        except Exception:
            im = im.convert("RGB")
    else:
        im = im.convert("RGB")
    return im

def make_blurred_portrait_card(src: Image.Image, cell_w: int, cell_h: int) -> Image.Image:
    """將直式照片放入橫向格子：垂直 100% 完整保留（不切頭手），兩側以同調磨砂毛玻璃填補。"""
    w, h = src.size
    # 1. 磨砂毛玻璃背景（等比填滿並適度壓暗提升前景對比度）
    bg = ImageOps.fit(src, (cell_w, cell_h), Image.Resampling.BILINEAR)
    bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
    bg = ImageEnhance.Brightness(bg).enhance(0.86)
    
    # 2. 前景直式本體（垂直滿版高度，等比縮放居中）
    fg_w = int(w * (cell_h / h))
    fg = src.resize((fg_w, cell_h), Image.Resampling.LANCZOS)
    bg.paste(fg, ((cell_w - fg_w) // 2, 0))
    return bg

def make_landscape_card(src: Image.Image, cell_w: int, cell_h: int) -> Image.Image:
    """將橫式照片等比例居中裁切（Center Crop）為指定格子比例。"""
    return ImageOps.fit(src, (cell_w, cell_h), Image.Resampling.LANCZOS)

def process_card_auto(src: Image.Image, cell_w: int, cell_h: int) -> Image.Image:
    """自動偵測照片原生比例分流處理。"""
    return make_blurred_portrait_card(src, cell_w, cell_h) if src.height > src.width else make_landscape_card(src, cell_w, cell_h)

def build_wallet_sheet(photos: list[Image.Image], canvas_w: int, canvas_h: int) -> Image.Image:
    """根據指定畫布尺寸自動排版 4 張照片為 2x3 吋皮夾照。"""
    cell_w = canvas_w // 2
    cell_h = canvas_h // 2
    
    pad = 18  # 約 1.5mm 純白邊距
    pw = cell_w - pad * 2
    ph = cell_h - pad * 2
    
    quadrants = [process_card_auto(photo, pw, ph) for photo in photos]
    
    canvas = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    coords = [
        (pad, pad),
        (cell_w + pad, pad),
        (pad, cell_h + pad),
        (cell_w + pad, cell_h + pad)
    ]
    for i in range(4):
        canvas.paste(quadrants[i], coords[i])
        
    # 中央十字裁切虛線
    line_col = (195, 195, 195)
    for y in range(0, canvas_h, 14):
        draw.line([(cell_w, y), (cell_w, min(y + 7, canvas_h))], fill=line_col, width=1)
    for x in range(0, canvas_w, 14):
        draw.line([(x, cell_h), (min(x + 7, canvas_w), cell_h)], fill=line_col, width=1)
        
    # 外圍對位刻度線
    tick = 14
    draw.line([(cell_w, 0), (cell_w, tick)], fill=(120, 120, 120), width=1)
    draw.line([(cell_w, canvas_h - tick), (cell_w, canvas_h)], fill=(120, 120, 120), width=1)
    draw.line([(0, cell_h), (tick, cell_h)], fill=(120, 120, 120), width=1)
    draw.line([(canvas_w - tick, cell_h), (canvas_w, cell_h)], fill=(120, 120, 120), width=1)
    
    return canvas

def main():
    photos = [load_photo(Path(f"photo{i}.jpg")) for i in range(1, 5)]
    
    targets = [
        ("ibon_print.jpg", 1748, 1181, "7-11 ibon 日本明信片規格 (10.0 x 14.8 cm, 300 DPI)"),
        ("standard_4x6.jpg", 1800, 1200, "標準英制 4x6 規格 (3:2, 300 DPI 通用備用)"),
    ]
    
    for filename, w, h, desc in targets:
        canvas = build_wallet_sheet(photos, w, h)
        canvas.save(filename, "JPEG", quality=96, dpi=(300, 300))
        print(f"成功產出: {filename} ({w}x{h} px @ 300 DPI) -> {desc}")

if __name__ == "__main__":
    main()



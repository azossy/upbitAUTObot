"""
아이콘 이미지에서 투명 영역을 배경색으로 채워 통일된 배경으로 저장.
배짱이 앱 프라이머리/배경 #0381FE 또는 이미지 내 둥근 사각 배경색 사용.
"""
from PIL import Image
import numpy as np
from pathlib import Path

# 앱 가이드 배경색 (진한 파란)
FALLBACK_BG = (3, 129, 254)  # #0381FE

def get_background_color(arr):
    """이미지에서 둥근 사각 배경(진한 파란) 샘플 — 모서리/가장자리에서 채움."""
    h, w = arr.shape[:2]
    # 모서리·가장자리(둥근 사각 배경색이 있는 곳)에서 불투명 파란 픽셀 수집
    candidates = []
    for y in [0, 1, 2, h//4, h-1, h-2]:
        for x in [0, 1, 2, w//4, w-1, w-2]:
            if 0 <= y < h and 0 <= x < w:
                p = arr[y, x]
                if len(p) == 4 and p[3] < 200:
                    continue
                r, g, b = int(p[0]), int(p[1]), int(p[2])
                if b > g and b > r and r < 180:  # 파란 계열(배경)
                    candidates.append((r, g, b))
    if candidates:
        r, g, b = np.median([c[0] for c in candidates]), np.median([c[1] for c in candidates]), np.median([c[2] for c in candidates])
        return (int(r), int(g), int(b))
    return FALLBACK_BG

def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    src_path = Path(
        r"C:\Users\chall\.cursor\projects\c-Users-chall-Desktop\assets"
        r"\c__Users_chall_AppData_Roaming_Cursor_User_workspaceStorage_298e3686e3298f7cec8869b0f279cbba_images_download-7bd19944-7664-4b68-b5ee-573eca94cdb5.png"
    )
    if not src_path.exists():
        print("원본 파일을 찾을 수 없습니다:", src_path)
        return
    out_path = project_root / "assets" / "icons" / "app_icon_1024.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(src_path).convert("RGBA")
    arr = np.array(img)
    # 배경 통일: 앱 가이드 #0381FE 사용 (투명 영역만 채움)
    bg = FALLBACK_BG
    if len(bg) == 3:
        bg = (*bg, 255)

    # 투명(알파 낮음)인 픽셀을 배경색으로 통일
    alpha = arr[:, :, 3]
    mask = alpha < 250
    arr[mask, 0] = bg[0]
    arr[mask, 1] = bg[1]
    arr[mask, 2] = bg[2]
    arr[mask, 3] = 255
    # 앱 가이드 색과 통일: 기존 둥근 사각 내부도 동일한 배경으로 (선택)
    # 여기서는 투명만 채움. 배경이 이미 이미지 내 파란이라면 bg가 그 색임.

    out_img = Image.fromarray(arr)
    out_img.save(out_path)
    print("저장됨:", out_path, "| 배경 RGB:", bg[:3])

if __name__ == "__main__":
    main()

"""
원본 아이콘 이미지에서 더듬이 위 점 4개만 제거 (수정).
형태·얼굴·색상은 그대로 두고, 더듬이에 있는 작은 원 4개 픽셀만 배경색으로 덮습니다.
"""
from PIL import Image
import numpy as np
from pathlib import Path

def is_light_blue(pixel, bg_color):
    """얼굴/눈/더듬이/점에 쓰인 밝은 파란색 여부 (RGBA 또는 RGB)."""
    if len(pixel) == 4 and pixel[3] == 0:
        return False
    r, g, b = pixel[0], pixel[1], pixel[2]
    # 밝은 파란 계열 (R 낮고 G,B 높음)
    if r > 200 or g < 100 or b < 100:
        return False
    if g < 150 and b < 150:
        return False
    # 배경(진한 파란) 제외
    if np.allclose(pixel[:3], bg_color[:3], atol=30):
        return False
    return True

def get_background_color(arr):
    """둥근 사각 내부의 대표 배경색 (진한 파란)."""
    h, w = arr.shape[:2]
    # 중앙 부근 샘플
    cx, cy = w // 2, h // 2
    for dy in [0, -1, 1]:
        for dx in [0, -1, 1]:
            p = arr[cy + dy, cx + dx]
            if len(p) == 4 and p[3] < 255:
                continue
            if p[0] < 120 and p[1] < 120 and p[2] > 100:  # 진한 파란
                return p
    return arr[cy, cx]

def find_small_components_in_antenna_region(arr, light_blue_mask, max_area=200, top_ratio=0.5):
    """
    상단(더듬이 영역)에서 밝은 파란색의 작은 연결 요소만 찾아 마스크로 반환.
    """
    from scipy import ndimage
    h, w = light_blue_mask.shape
    top_y = int(h * top_ratio)
    # 상단 절반만 사용 (더듬이 + 점)
    region = np.zeros_like(light_blue_mask, dtype=bool)
    region[:top_y, :] = light_blue_mask[:top_y, :]
    labeled, num_features = ndimage.label(region)
    dots_mask = np.zeros_like(light_blue_mask, dtype=bool)
    for i in range(1, num_features + 1):
        comp = labeled == i
        area = comp.sum()
        if area < 50:  # 너무 작으면 노이즈
            continue
        if area > max_area:  # 큰 덩어리(얼굴/눈/더듬이 선) 제외
            continue
        # 둥근 정도: 작고 둥근 것만 (점 후보)
        yxs = np.argwhere(comp)
        if len(yxs) == 0:
            continue
        yy, xx = yxs[:, 0], yxs[:, 1]
        cy, cx = yy.mean(), xx.mean()
        r = np.sqrt(((yy - cy) ** 2 + (xx - cx) ** 2).max())
        if r < 2:
            continue
        compact = area / (np.pi * r * r) if r > 0 else 0
        if compact < 0.3:  # 길쭉한 선이면 제외
            continue
        dots_mask |= comp
    return dots_mask

def main():
    import sys
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    # 원본: 인자로 경로 지정 가능. 없으면 Cursor assets 기본 경로 사용.
    default_src = Path(
        r"C:\Users\chall\.cursor\projects\c-Users-chall-Desktop\assets"
        r"\c__Users_chall_AppData_Roaming_Cursor_User_workspaceStorage_298e3686e3298f7cec8869b0f279cbba_images_download-5a91c5e7-244f-4850-bbd1-a4d243bb9ec5-7f8e3e88-69d3-43ee-9b26-06b2c9ec2852.png"
    )
    src_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_src
    if not src_path.exists():
        print("원본 파일을 찾을 수 없습니다:", src_path)
        return
    out_dir = project_root / "assets" / "icon_candidates"
    out_dir.mkdir(parents=True, exist_ok=True)
    # 원본 덮어쓰기 옵션: python remove_antenna_dots.py "경로" --overwrite
    overwrite = len(sys.argv) > 2 and sys.argv[2] == "--overwrite"
    out_path = src_path if overwrite else out_dir / "baejjangi_face_edited_no_dots.png"

    img = Image.open(src_path).convert("RGBA")
    arr = np.array(img)
    bg_color = get_background_color(arr)

    # 밝은 파란 픽셀 마스크 (R 낮고 G,B 높은 것)
    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
    light_blue = (r < 180) & (g > 100) & (b > 120) & (a > 200)
    light_blue = light_blue.astype(np.uint8)

    try:
        from scipy import ndimage
    except ImportError:
        print("scipy가 필요합니다: pip install scipy")
        return

    dots_mask = find_small_components_in_antenna_region(arr, light_blue, max_area=250, top_ratio=0.55)
    # 점 픽셀만 배경색으로 교체 (알파 유지)
    for c in range(3):
        arr[:,:,c][dots_mask] = bg_color[c]
    arr[:,:,3][dots_mask] = 255

    Image.fromarray(arr).save(out_path)
    print("저장됨:", out_path)

if __name__ == "__main__":
    main()

"""抽幀分析法 (Temporal Frame Analysis)。

優先用 ffmpeg：ffmpeg -i target.gif -vf fps=N f_%03d.png
若系統無 ffmpeg，自動改用 Pillow 逐幀匯出。
另提供 sample_frames（均勻取樣）、sample_frames_by_diff（峰值取樣）、
apply_diff_mask（差分影像 A）、apply_red_filter（紅色閾值 X）與 build_montage（時序拼接圖）。
"""
import os
import glob
import shutil
import subprocess
import tempfile


def _have_ffmpeg():
    return shutil.which("ffmpeg") is not None


def extract_frames(gif_path, fps=10, out_dir=None):
    """抽出所有影格 PNG，回傳依序排列的檔案路徑清單。"""
    out_dir = out_dir or tempfile.mkdtemp(prefix="captcha_frames_")
    os.makedirs(out_dir, exist_ok=True)

    if _have_ffmpeg():
        pattern = os.path.join(out_dir, "f_%03d.png")
        cmd = ["ffmpeg", "-y", "-i", gif_path, "-vf", f"fps={fps}", pattern]
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            frames = sorted(glob.glob(os.path.join(out_dir, "f_*.png")))
            if frames:
                return frames
        except Exception:
            pass  # 退回 Pillow

    # --- Pillow 後援 ---
    from PIL import Image, ImageSequence
    frames = []
    with Image.open(gif_path) as im:
        for i, frame in enumerate(ImageSequence.Iterator(im)):
            p = os.path.join(out_dir, f"f_{i:03d}.png")
            frame.convert("RGB").save(p)
            frames.append(p)
    return frames


def sample_frames(frames, max_n=8):
    """從影格序列均勻取樣最多 max_n 張（保留時間順序）。"""
    if len(frames) <= max_n:
        return frames
    step = len(frames) / float(max_n)
    return [frames[int(i * step)] for i in range(max_n)]


def sample_frames_by_diff(frames, max_n=10, search_ratio=0.95):
    """峰值偵測取樣：找每顆球「剛變紅」的精確幀。

    演算法：
    0. 只搜索前 search_ratio 比例的幀（預設 60%），跳過末段重播/慶祝動畫
    1. 計算相鄰幀的紅色通道正向增量
    2. 找局部峰值，用最小間距避免同一球被重複選取
    3. 雙界過濾：
       - 上界 (median * 3.5)：濾除異常高分幀
       - 下界 (median * 0.55)：濾除異常低分幀
    4. 峰值不足時退回均勻取樣（同樣只用前 60% 幀）
    """
    if len(frames) <= max_n:
        return frames

    import numpy as np
    from PIL import Image

    n = len(frames)
    # Step 0：只搜索前 search_ratio 的幀（95% 確保最後字元不被截斷，分數過濾移除慶祝幀）
    search_end = max(max_n + 1, int(n * search_ratio))
    frames = frames[:search_end]
    n = len(frames)

    # Step 1：計算紅色正向增量
    scores = [0.0]
    prev = np.array(Image.open(frames[0]).convert("RGB"), dtype=np.int16)
    for fp in frames[1:]:
        curr = np.array(Image.open(fp).convert("RGB"), dtype=np.int16)
        scores.append(float(np.clip(curr[:, :, 0] - prev[:, :, 0], 0, None).mean()))
        prev = curr
    scores = np.array(scores)

    # Step 2：局部峰值偵測
    threshold = max(scores.mean() + 0.5 * scores.std(), scores.max() * 0.1)
    min_gap = max(5, n // 10)

    all_peaks = []
    for i in range(1, n - 1):
        if (scores[i] >= threshold
                and scores[i] >= scores[i - 1]
                and scores[i] >= scores[i + 1]):
            if not all_peaks or (i - all_peaks[-1]) >= min_gap:
                all_peaks.append(i)

    if not all_peaks:
        return sample_frames(frames, max_n=max_n)

    # Step 3：雙界過濾
    peak_scores = np.array([scores[p] for p in all_peaks])
    median_s = float(np.median(peak_scores))
    upper = median_s * 3.0   # 移除慶祝動畫（3.0x 更嚴格，覆蓋 Lev2/3 邊界案例）
    lower = median_s * 0.55  # 移除殘影重播（異常低）
    char_peaks = [p for p in all_peaks if lower <= scores[p] <= upper]

    # 過濾後不足 2 個則退回全峰集合
    if len(char_peaks) < 2:
        char_peaks = all_peaks

    # Step 4：超過 max_n 時保留分數最高的 max_n 個（維持時間順序）
    if len(char_peaks) > max_n:
        char_peaks = sorted(
            sorted(char_peaks, key=lambda i: scores[i], reverse=True)[:max_n]
        )

    return [frames[i] for i in char_peaks]


def apply_diff_mask(frame_paths, out_dir, diff_threshold=40):
    """方案 A：差分影像法。

    對每張取樣幀與前一幀做差分，只保留「剛變紅」的像素，
    其餘像素設為黑色。第一幀保留原樣（無前幀可差分）。
    diff_threshold：紅色增量需超過此值才視為新球（預設 40，排除殘影噪點）。
    回傳處理後的 PNG 路徑清單（與輸入等長）。
    """
    import numpy as np
    from PIL import Image

    out_paths = []
    prev_arr = None
    for i, fp in enumerate(frame_paths):
        curr = Image.open(fp).convert("RGB")
        curr_arr = np.array(curr, dtype=np.int16)

        if prev_arr is None:
            # 第一幀：保留原樣
            out_fp = os.path.join(out_dir, f"diff_{i:03d}.png")
            curr.save(out_fp)
        else:
            red_gain = np.clip(curr_arr[:, :, 0] - prev_arr[:, :, 0], 0, None)
            mask = red_gain > diff_threshold
            result = np.zeros_like(curr_arr, dtype=np.uint8)
            result[mask] = curr_arr[mask].astype(np.uint8)
            out_fp = os.path.join(out_dir, f"diff_{i:03d}.png")
            Image.fromarray(result).save(out_fp)

        out_paths.append(out_fp)
        prev_arr = curr_arr

    return out_paths


def apply_red_filter(frame_paths, out_dir, prefix="red"):
    """方案 X：紅色閾值過濾法。

    對每張幀只保留「R 值高且明顯大於 G/B」的像素（即真正的紅色球），
    其餘像素設為黑色，消除彩色背景噪點。
    回傳處理後的 PNG 路徑清單。
    """
    import numpy as np
    from PIL import Image

    out_paths = []
    for i, fp in enumerate(frame_paths):
        arr = np.array(Image.open(fp).convert("RGB"), dtype=np.int16)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        mask = (r > 120) & (r - g > 40) & (r - b > 40)
        result = np.zeros_like(arr, dtype=np.uint8)
        result[mask] = arr[mask].astype(np.uint8)
        out_fp = os.path.join(out_dir, f"{prefix}_{i:03d}.png")
        Image.fromarray(result).save(out_fp)
        out_paths.append(out_fp)

    return out_paths


def apply_diff_then_red(frame_paths, out_dir):
    """方案 A+X：差分 + 紅色雙重過濾（Lev9+ 高噪點專用）。

    Step 1：差分影像（濾除舊球殘留）
    Step 2：紅色閾值（濾除彩色背景噪點）
    兩層疊加後影像只剩「剛亮起的紅球像素」。
    """
    diff_paths = apply_diff_mask(frame_paths, out_dir, diff_threshold=40)
    return apply_red_filter(diff_paths, out_dir, prefix="dred")


def build_montage(frames, cols=4, cell=(220, 220)):
    """把取樣影格拼成單張時序拼接圖（左→右、上→下為時間順序），回傳檔案路徑。"""
    from PIL import Image
    if not frames:
        raise ValueError("無影格可拼接")
    n = len(frames)
    rows = (n + cols - 1) // cols
    cw, ch = cell
    canvas = Image.new("RGB", (cols * cw, rows * ch), (255, 255, 255))
    for idx, fp in enumerate(frames):
        with Image.open(fp) as im:
            im = im.convert("RGB").resize(cell)
            r, c = divmod(idx, cols)
            canvas.paste(im, (c * cw, r * ch))
    out = os.path.join(os.path.dirname(frames[0]), "montage.png")
    canvas.save(out)
    return out

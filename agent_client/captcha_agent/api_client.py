"""ezai.tw 後端 API 封裝。

題目 API 會回傳 ground-truth `passwd`：本模組將其放在獨立欄位 `ground_truth`，
呼叫端務必只把它交給 scorer 比對，**禁止**交給 vision_openrouter（防作弊）。
"""
import os
import tempfile
import requests


class ApiClient:
    def __init__(self, base_url, timeout=15):
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    # ---- 題目（含標準答案）----
    def get_working_task(self, no_index):
        """GET /getpasswd?no=N (N 為 0-based 索引，對應 lev-1)。"""
        r = requests.get(f"{self.base}/getpasswd", params={"no": no_index},
                         timeout=self.timeout)
        r.raise_for_status()
        d = r.json()
        return {
            "gif_url": d.get("gif_url"),
            "ground_truth": (d.get("passwd") or "").strip().upper(),
            "raw": d,
        }

    def get_dataset_task(self, path, lev):
        """GET /getdataset?path=P&lev=N (N 為 1-based)。"""
        r = requests.get(f"{self.base}/getdataset",
                         params={"path": path, "lev": lev}, timeout=self.timeout)
        r.raise_for_status()
        d = r.json()
        return {
            "index": d.get("index"),
            "datasetpath": d.get("datasetpath", path),
            "gif_url": d.get("gif_url"),
            "ground_truth": (d.get("passwd") or "").strip().upper(),
            "raw": d,
        }

    # ---- 結果紀錄 ----
    def save_working(self, age, no, passflag, timecount, model):
        payload = {"age": age, "no": no, "passflag": passflag,
                   "timecount": timecount, "model": model}
        r = requests.post(f"{self.base}/savedata", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def save_dataset(self, age, no, passflag, timecount, model, datasetpath):
        payload = {"age": age, "no": no, "passflag": passflag,
                   "timecount": timecount, "model": model, "datasetpath": datasetpath}
        r = requests.post(f"{self.base}/savedataset", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ---- GIF 下載 ----
    def download_gif(self, gif_url, dest_dir=None):
        if not gif_url:
            raise ValueError("gif_url 為空")
        url = gif_url if gif_url.startswith("http") else f"{self.base}{gif_url}"
        r = requests.get(url, timeout=self.timeout)
        r.raise_for_status()
        dest_dir = dest_dir or tempfile.mkdtemp(prefix="captcha_gif_")
        os.makedirs(dest_dir, exist_ok=True)
        fname = os.path.basename(gif_url.split("?")[0]) or "captcha.gif"
        path = os.path.join(dest_dir, fname)
        with open(path, "wb") as fh:
            fh.write(r.content)
        return path

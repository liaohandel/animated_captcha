"""設定載入：apikey_model.json（金鑰/模型/base_url/operator/nodebb）。

優先序：環境變數 > apikey_model.json > 內建預設值。
找不到 apikey_model.json 時仍可運作（models 為空，僅能做不需視覺模型的動作）。
"""
import json
import os

# 專案根目錄 = 本檔上兩層 (agent_client/)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_EZAI_BASE = "http://www.ezai.tw:5000"
DEFAULT_OR_BASE = "https://openrouter.ai/api/v1"

# Working 測試等級數（裁示：15 級，對應 /getpasswd no=0..14）
WORKING_LEVELS = 15
# DataSet 每組樣本數
DATASET_SAMPLES = 100
# 14 組 DataSet Path（順序同 dataset_gui.html）
DATASET_PATHS = [
    "pt_a3c0fen", "pt_a3c2fen", "pt_a3c2ten", "pt_a3c2tenp6",
    "pt_a4c0fen", "pt_a4c2fen", "pt_a4c2ten", "pt_a4c2tenp6",
    "pt_a5c0fen", "pt_a5c2fen", "pt_a5c2ten", "pt_a5c2tenp6",
    "pc1jpg", "pc3jpg",
]


def _candidate_paths():
    """apikey_model.json 可能位置。"""
    env = os.environ.get("APIKEY_MODEL_JSON")
    if env:
        yield env
    yield os.path.join(ROOT, "apikey_model.json")
    yield os.path.join(ROOT, "apikey_model.example.json")  # 最後退路（範本，金鑰為假值）


def load_config():
    """回傳設定 dict。"""
    data = {}
    used_path = None
    for p in _candidate_paths():
        if p and os.path.exists(p):
            with open(p, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            used_path = p
            break

    operator = data.get("operator", {}) or {}
    nodebb = data.get("nodebb", {}) or {}

    cfg = {
        "config_path": used_path,
        "ezai_base_url": os.environ.get("EZAI_BASE_URL")
            or data.get("ezai_base_url") or DEFAULT_EZAI_BASE,
        "openrouter_base_url": os.environ.get("OPENROUTER_BASE_URL")
            or data.get("openrouter_base_url") or DEFAULT_OR_BASE,
        "operator_name": operator.get("name", "hermes"),
        "operator_age": int(operator.get("age", 2)),   # 裁示：age=2
        "models": data.get("models", []) or [],
        "nodebb": {
            "enabled": bool(nodebb.get("enabled", False)),
            "base_url": nodebb.get("base_url", ""),
            "token": nodebb.get("token", ""),
            "category": nodebb.get("category", "captcha_test_report"),
        },
        "fps": int(os.environ.get("FRAME_FPS", 10)),
        "min_think_seconds": float(os.environ.get("MIN_THINK_SECONDS", 2.0)),
    }
    return cfg


def list_model_labels(cfg=None):
    cfg = cfg or load_config()
    return [m.get("label", m.get("model", "?")) for m in cfg["models"]]


def get_model(label, cfg=None):
    """依 label 取得 {label, api_key, model}；label 為 None 時取第一個。"""
    cfg = cfg or load_config()
    models = cfg["models"]
    if not models:
        return None
    if label is None:
        return models[0]
    for m in models:
        if m.get("label") == label or m.get("model") == label:
            return m
    return None

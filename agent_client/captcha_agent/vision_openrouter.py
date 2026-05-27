"""OpenRouter 視覺模型辨識。

輸入抽出的影格（或時序拼接圖），請多模態模型輸出「依紅色亮起順序的字元序列」。
重要：本模組**只接收影像**，不接收 ground-truth passwd（防作弊）。
"""
import base64
import logging
import requests

log = logging.getLogger(__name__)

PROMPT = (
    "You are solving an animated CAPTCHA. I will send you N key frames extracted from the animation.\n"
    "The password has EXACTLY N characters — one new character per frame, in chronological order.\n"
    "Rules:\n"
    "  1. The frames are in time order. In each frame exactly ONE new ball just turned RED.\n"
    "  2. The new ball is the one that is RED now but was NOT red in the previous frame.\n"
    "  3. Read the character on that newly-red ball. Ignore all other balls (they lit up earlier).\n"
    "  4. Concatenate the N characters in order — that is the password.\n"
    "Output ONLY the password string (uppercase letters/digits), no spaces, no explanation."
)


def _b64_data_uri(path):
    with open(path, "rb") as fh:
        b = base64.b64encode(fh.read()).decode("ascii")
    return f"data:image/png;base64,{b}"


def recognize(image_paths, model_cfg, base_url,
              temperature=0.0, max_tokens=128, timeout=90):
    """image_paths: 依時間順序的 PNG 清單（或單張拼接圖）。
    model_cfg: {label, api_key, model}。回傳辨識字串（大寫，去空白）。失敗回傳空字串。
    """
    if not model_cfg or not model_cfg.get("api_key") or not model_cfg.get("model"):
        log.warning("recognize: model_cfg 不完整，跳過")
        return ""

    content = [{"type": "text", "text": PROMPT}]
    for p in image_paths:
        content.append({"type": "image_url",
                        "image_url": {"url": _b64_data_uri(p)}})

    payload = {
        "model": model_cfg["model"],
        "messages": [{"role": "user", "content": content}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {model_cfg['api_key']}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://www.ezai.tw",
        "X-Title": "Animated CAPTCHA Resilience Test",
    }
    try:
        r = requests.post(f"{base_url.rstrip('/')}/chat/completions",
                          json=payload, headers=headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        log.info("model=%s raw=%r", model_cfg.get("model"), text[:120])
        cleaned = "".join(ch for ch in text if ch.isalnum()).upper()
        return cleaned
    except requests.HTTPError as e:
        log.error("HTTP %s: %s", e.response.status_code, e.response.text[:200])
        return ""
    except Exception as e:
        log.error("recognize failed: %s: %s", type(e).__name__, e)
        return ""

"""captcha_agent — Animated CAPTCHA 分析服務核心套件。

模組：
  config            設定 / apikey_model.json 載入
  api_client        ezai.tw 後端 API 封裝
  frame_extractor   抽幀分析法 (ffmpeg / Pillow)
  vision_openrouter OpenRouter 視覺模型辨識
  scorer            比對 / 狀態判定 / 計分
  reporter          testreport 格式報表（+選用 NodeBB）
  runner            working / dataset 測試流程
"""
__all__ = [
    "config", "api_client", "frame_extractor",
    "vision_openrouter", "scorer", "reporter", "runner",
]

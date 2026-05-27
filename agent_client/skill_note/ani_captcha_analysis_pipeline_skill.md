---
name: ani_captcha_analysis_pipeline
description: 描述 agent_client 工具對「動態驗證碼 (Animated CAPTCHA)」的完整自動分析處理流程 — 抽幀分析法 (Temporal Frame Analysis) + OpenRouter 視覺模型辨識，含峰值取樣、差分/紅色過濾選用強化、比對計分與報表。適用於 http://www.ezai.tw:5000 的 Working(lev1..15) 與 DataSet(14組×100) 兩類測試。
---

# 動態驗證碼分析處理流程技能 (ani_captcha_analysis_pipeline)

本技能說明 `agent_client/` 工具如何把一段「動態驗證碼 GIF」轉成「辨識密碼」並完成評分與紀錄。
所有步驟皆對應實際程式模組（見 §2），可直接照此流程復現或撰寫新分析器。

## 觸發條件
- 需對 `http://localhost:5000`（Working）或 `/dataset`（DataSet）執行純視覺破解測試。
- 需評估動態驗證碼對抗 MLLM 視覺辨識的防禦韌性。

## 0. 核心原則（防作弊）
- 題目 API（`/getpasswd`、`/getdataset`）回傳的 `passwd` 是**標準答案 (ground truth)**，
  在 `api_client` 中放入獨立的 `ground_truth` 欄位。
- **`ground_truth` 只能交給 `scorer` 比對計分，嚴禁進入 `vision_openrouter.recognize()`**（其只接收影像）。
- 操作者固定 `hermes`（`age=2`）；`model` 欄位格式：`{label}_ffmpg_{辨識目標}#{視覺辨識結果}`。

---

## 1. 單題處理管線（七步）

```
取題(含標準答案) → 下載 GIF → ffmpeg 抽幀 → 峰值取樣選關鍵幀
→ OpenRouter 視覺辨識 → 比對計分 → 寫回後端 + 記錄報表列
```

### Step 1 取題
- Working：`GET /getpasswd?no=lev-1`（0-based，lev 1..15）。
- DataSet：`GET /getdataset?path=P&lev=N`（lev 1..100）。
- 取得 `gif_url` 與 `ground_truth`。

### Step 2 下載 GIF
- `api_client.download_gif(gif_url)` 下載到暫存目錄。

### Step 3 抽幀（Temporal Frame Analysis）
- `frame_extractor.extract_frames(gif, fps=10)`：
  優先 `ffmpeg -i target.gif -vf fps=10 f_%03d.png`；系統無 ffmpeg 時自動改用 **Pillow** 逐幀匯出。

### Step 4 關鍵幀取樣（峰值偵測）★ 本工具實際採用
- `frame_extractor.sample_frames_by_diff(frames, max_n=10)`：找「每顆球剛變紅」的精確幀。
  1. 只搜索前 95% 幀，跳過末段重播/慶祝動畫。
  2. 計算相鄰幀的**紅色通道正向增量**。
  3. 取局部峰值（最小間距避免同球重複選取）。
  4. 雙界過濾（上界 median×3.0 去慶祝幀、下界 median×0.55 去殘影）。
  5. 峰值不足時退回 `sample_frames`（均勻取樣）。
- 用意：把「亮起時序」濃縮成最多 10 張代表幀，讓視覺模型看到「一幀一個新紅球」。

### Step 5 視覺辨識（OpenRouter）
- `vision_openrouter.recognize(frames, model_cfg, base_url)`：
  把關鍵幀以 base64 連同提示詞送 OpenRouter `/chat/completions`（vision messages）。
  提示詞要求：影格為時間順序、每幀僅一顆「新變紅」的球、讀其字元、依序串成密碼、**只輸出密碼字串**。
  回傳轉大寫、去非英數字元；失敗（逾時/HTTP 錯誤）回空字串。

### Step 6 比對計分
- `scorer.classify(recognized, ground_truth)` →（狀態, 得分, passflag）：
  - 完全相同 → **正確 / 10 / passflag=1**
  - 部分對、順序錯、或有共同字元 → **半對 / 0 / passflag=0**
  - 其餘（含空字串）→ **誤差 / 0 / passflag=0**
- `timecount`：含 `min_think_seconds=2.0` 模擬人類延遲下限。

### Step 7 寫回 + 報表
- Working：`POST /savedata`（→ `userlog`）；DataSet：`POST /savedataset`（→ `datasetlog`，多 `datasetpath`）。
- `reporter` 依 `ani_captcha_testreport.txt` 三段式格式輸出 `reports/<type>/report_*.txt|json`。
- 選用：`nodebb.enabled=true` 時貼文至 NodeBB#captcha_test_report。

---

## 2. 模組對應

| 步驟 | 模組 / 函式 |
|------|-------------|
| 取題 / 寫回 / 下載 | `captcha_agent/api_client.py`（`get_working_task`/`get_dataset_task`/`save_*`/`download_gif`）|
| 抽幀 / 取樣 / 影像強化 | `captcha_agent/frame_extractor.py` |
| 視覺辨識 | `captcha_agent/vision_openrouter.py` |
| 比對計分 | `captcha_agent/scorer.py` |
| 報表 / NodeBB | `captcha_agent/reporter.py` |
| 流程編排 | `captcha_agent/runner.py`（`_solve_one`、`run_working`、`run_dataset`）|
| 設定 / 金鑰 / 模型 | `captcha_agent/config.py` ＋ `apikey_model.json` |
| 網頁 / API / 背景工作 | `app.py` ＋ `templates/index.html` |

---

## 3. 選用強化（高噪點等級對策，已備妥未接入主管線）

針對 Lev9+ / `c2*` 干擾組，可在 Step 4 與 Step 5 之間插入像素級過濾，再送辨識：
- `apply_diff_mask(frames)`：**方案 A** 差分影像，只保留「剛變紅」像素，濾除舊球殘留。
- `apply_red_filter(frames)`：**方案 X** 紅色閾值（R 高且明顯大於 G/B），濾除彩色背景噪點。
- `apply_diff_then_red(frames)`：**方案 A+X** 差分 + 紅色雙重過濾，影像只剩「剛亮起的紅球像素」。
- `build_montage(frames)`：把關鍵幀拼成單張時序圖，供一次判讀（省 token）。

> 接入方式：在 `runner._solve_one` 的 `sampled` 之後呼叫上述函式，把處理後路徑傳給 `vision.recognize`。

---

## 4. 等級對策對照（取自純視覺技能）
- **Lev 1–5**：3×3／4×4 矩陣、干擾低 → 標準峰值取樣即可。
- **Lev 6–8**：5×5＋基礎噪點 → 建議加 `apply_red_filter` 強化紅色通道。
- **Lev 9–15／c2***：高頻閃爍／噴砂噪點／彩色線條 → 建議 `apply_diff_then_red`（幀差＋紅色）。

---

## 5. 執行方式
```bash
cd agent_client
pip install -r requirements.txt          # 另需 ffmpeg（無則自動用 Pillow）
cp apikey_model.example.json apikey_model.json   # 填真實 OpenRouter 金鑰
python app.py                            # http://localhost:5100
# 網頁選模型→啟動，或：
#   POST /api/run/working  {"model":"Gemini3-Flash-Preview"}
#   POST /api/run/dataset  {"model":"Gemini-2.0-Flash","paths":["pt_a3c0fen"]}
```

## 6. 驗證指標
- **完成度**：Working 15 級；DataSet 14 組×100。
- **準確度**：辨識結果與 ground truth 的正確率，分等級／分組統計。
- **真實性**：每題 `timecount` 含合理行為延遲。
- **不作弊**：靜態確認 `ground_truth` 從未進入 `vision_openrouter` 輸入。
- **報表合規**：符合 `ani_captcha_testreport.txt` 三段式格式。

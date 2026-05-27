# Animated CAPTCHA 分析服務 — 工具規格書 (Tool Specification)

> 專案位置：`agent_client/`
> 目的：以 **OpenRouter API（視覺模型）** + **抽幀分析法 (Temporal Frame Analysis)**，
> 建立一套 **Python3 + Flask** 服務（網頁操作面板 + REST API），對
> `http://localhost:5000` 的動態驗證碼系統執行兩大類防禦韌性測試，
> 並依 `skill_note/ani_captcha_testreport.txt` 格式產出測試報表。
>
> 規範依據：`agent_client/skill_note/` 下全部檔案
> （`agent_captcha_skill.txt`、`AGENT_dataset_test_skill.md`、`ani_captcha_purevision_skill.md`、`ani_captcha_testreport.txt`）。
>
> **版本：v1.1（已實作）** — 本規格書與 `agent_client/` 下實際程式同步。
> 設計裁示：Working = **15 級**；「半對」= **0 分**；`/savedata` `age` = **2**(hermes)；
> 金鑰與視覺模型由 **`apikey_model.json`** 載入（可多組可選）；NodeBB 貼文為**選項**。

---

## 1. 範圍與兩大測試類別

| 類別 | 代號 | 目標 URL | 測試範圍 | 標準答案 API | 紀錄 API / 表 |
|------|------|----------|----------|--------------|----------------|
| Animated CAPTCHA **Working 測試** | `working` | `http://localhost:5000/` | `lev 1 … 15`（單輪 15 題）| `GET /getpasswd?no=N` | `POST /savedata` → `userlog` |
| Animated CAPTCHA **DataSet 測試** | `dataset` | `http://localhost:5000/dataset` | 14 組 × `lev 1…100` = 1400 題 | `GET /getdataset?path=P&lev=N` | `POST /savedataset` → `datasetlog` |

兩類共用同一套「下載 → 抽幀 → 視覺辨識 → 比對 → 計分 → 紀錄 → 報表」管線，差異僅在
**題庫來源 API**、**迴圈維度**（working 為單層 15；dataset 為雙層 14×100）與**紀錄 API**。

---

## 2. 核心方法論（取自 skill_note）

### 2.1 抽幀分析法 (Temporal Frame Analysis)
1. 由題目 API 取得 `gif_url`，下載 GIF 至本地暫存。
2. 以 **ffmpeg** 抽幀：`ffmpeg -i target.gif -vf fps=10 f_%03d.png`。
3. 偵測矩陣中圓圈由「藍 → 紅」變色的**時間順序**（亮起順序）。
4. 將變紅座標映射成英文字母 / 數字，依亮起順序合成密碼字串。

### 2.2 純視覺守則 (Pure Vision — 不可作弊)
- **嚴禁**把題目 API 回傳的 `passwd` 當成解答來源。
- `passwd` 僅可在「辨識完成後」作為**標準答案 (ground truth)** 用於比對、計分與報表。
- 模擬人類行為延遲（記錄 `timecount` 處理秒數）。

### 2.3 OpenRouter 視覺模型角色
- 由 OpenRouter 呼叫多模態（Vision）模型，輸入抽出的關鍵幀（或合成的時序拼接圖），
  要求模型輸出「依亮起順序的字母序列」。
- 模型名稱寫入紀錄欄位 `model`，格式遵循規範：
  `(model)_ffmpg_(辨識目標#視覺模型辨識結果)`。
- Operator 固定為 **hermes**（`age=2`）。

### 2.4 計分與狀態（依 `ani_captcha_testreport.txt`）
| 狀態 | 定義 | 得分 |
|------|------|------|
| **正確** | 字母完全相同且順序正確 | 10 |
| **半對** | 部分字母對 / 順序錯 | （見待確認 §10）|
| **誤差** | 字母完全不對 | 0 |

`passflag` 寫入規則：**正確 → 1**，其餘（半對／誤差）→ **0**。

---

## 3. 目錄結構（已實作）

```
agent_client/
├─ skill_note/                     # （既有）分析動作規範，唯讀參考
├─ CAPTCHA_analysis_tool_spec.md   # 本規格書
├─ apikey_model.example.json       # 金鑰/模型範本（複製為 apikey_model.json 填真值）
├─ requirements.txt                # 相依套件
├─ app.py                          # ★ Flask 進入點（網頁 + REST API）
├─ templates/
│  └─ index.html                   # 控制面板網頁
├─ captcha_agent/                  # Python 套件
│  ├─ __init__.py
│  ├─ config.py                    # 載入 apikey_model.json / 環境變數
│  ├─ api_client.py                # 封裝 ezai.tw 後端 5 支 API
│  ├─ frame_extractor.py           # 抽幀分析法（ffmpeg，無則 Pillow 後援）
│  ├─ vision_openrouter.py         # OpenRouter 視覺模型辨識
│  ├─ scorer.py                    # 比對 / 狀態判定 / 計分
│  ├─ reporter.py                  # testreport 格式報表（+選用 NodeBB 貼文）
│  └─ runner.py                    # run_working(1..15) / run_dataset(14×100)
└─ reports/                        # 輸出報表（txt / json）
```

---

## 4. 設定檔規格 (`apikey_model.json`)

金鑰與視覺模型由**手動建立**的 `apikey_model.json` 提供，`models` 陣列可放多組，
網頁下拉或 API 參數 `model` 以 `label` 選用。範本見 `apikey_model.example.json`。

```json
{
  "openrouter_base_url": "https://openrouter.ai/api/v1",
  "ezai_base_url": "http://localhost:5000",
  "operator": { "name": "hermes", "age": 2 },
  "models": [
    { "label": "qwen2.5-vl-72b", "api_key": "sk-or-...", "model": "qwen/qwen2.5-vl-72b-instruct" },
    { "label": "gpt-4o",         "api_key": "sk-or-...", "model": "openai/gpt-4o" },
    { "label": "gemini-2.0-flash","api_key": "sk-or-...","model": "google/gemini-2.0-flash-001" }
  ],
  "nodebb": { "enabled": false, "base_url": "", "token": "", "category": "captcha_test_report" }
}
```

載入優先序（`config.py`）：**環境變數 > `apikey_model.json` > 內建預設**。
其他可由環境變數覆寫：`EZAI_BASE_URL`、`OPENROUTER_BASE_URL`、`FRAME_FPS`、`MIN_THINK_SECONDS`、`APIKEY_MODEL_JSON`(指定設定檔路徑)。

> 安全要求：`apikey_model.json` 含真實金鑰，**不得提交進版本庫**（請加入 `.gitignore`）。
> 範本檔 `apikey_model.example.json` 內金鑰為假值。

---

## 5. 後端 API 封裝 (`api_client.py`)

| 方法 | 對應後端 | 用途 |
|------|----------|------|
| `get_working_task(no)` | `GET /getpasswd?no={no}` | 取得 working 第 no 題的 `gif_url` 與 ground-truth `passwd` |
| `get_dataset_task(path, lev)` | `GET /getdataset?path={path}&lev={lev}` | 取得 dataset 指定題的 `gif_url` 與 ground-truth `passwd` |
| `save_working(payload)` | `POST /savedata` | 寫 `userlog`：`age,no,passflag,timecount,model` |
| `save_dataset(payload)` | `POST /savedataset` | 寫 `datasetlog`：上列 + `datasetpath` |
| `download_gif(gif_url)` | `GET {base}{gif_url}` | 下載 GIF 至暫存檔 |

回傳一律解析為 dict；`passwd` 欄位在記憶體中標記為 `__ground_truth__`，
**禁止**傳入 `vision_openrouter` 模組（防止意外作弊）。

---

## 6. 抽幀模組 (`frame_extractor.py`)

```
extract_frames(gif_path, fps) -> List[Path]      # ffmpeg 抽幀
detect_light_order(frames) -> List[(x,y,frame_i)]# 偵測藍→紅變色時序座標
build_montage(frames) -> Path                    # （選用）合成時序拼接圖供視覺模型一次判讀
```

等級對策（取自 `ani_captcha_purevision_skill.md`）：
- **Lev 1–5**：3×3／4×4 矩陣，干擾低 → 標準座標對應。
- **Lev 6–8**：5×5 + 基礎噪點 → OpenCV 強化紅色通道過濾背景。
- **Lev 9–11(↑)**：高頻閃爍／噴砂噪點／彩色線條 → 幀差法 (Frame Differencing) 捕捉動態。

---

## 7. OpenRouter 視覺辨識 (`vision_openrouter.py`)

```
recognize(frames_or_montage, level_hint) -> str
```
- 將關鍵幀（base64）連同提示詞送 OpenRouter `/chat/completions`（vision messages）。
- 提示詞要求：「**只輸出依紅色亮起順序排列的字母/數字字串，不要解釋**」。
- 回傳純字串（轉大寫、去空白）作為「視覺模型辨識結果」。
- 失敗（逾時/格式不符）回傳空字串 → scorer 判為「誤差」。

---

## 8. 計分與報表 (`scorer.py` / `reporter.py`)

### 8.1 比對
```
classify(recognized, ground_truth) -> ("正確"|"半對"|"誤差", score, passflag)
```
- `recognized == ground_truth` → 正確 / **10** / passflag=1
- 長度相同且有部分字母正確，或字母集相同但順序錯，或有部分共同字元 → 半對 / **0** / passflag=0
- 其餘（含視覺辨識失敗、空字串）→ 誤差 / **0** / passflag=0

### 8.2 報表格式（依 `ani_captcha_testreport.txt`）
輸出含三段：
1. **測試策略說明**
2. **測試成績單**：欄位 `等級 | 辨識目標(ground truth) | 視覺模型辨識結果 | 狀態 | 得分 | 難度觀察`
3. **測試結論與分析**：總得分、識別瓶頸、安全評估

`model` 欄位寫入格式：`{model_label}_ffmpg_{辨識目標}#{視覺辨識結果}`。

選用：`nodebb_enabled=true` 時，貼文到 `NodeBB#captcha_test_report`，
topic 格式：`[Agents_(Agent Identity)_(代理人名稱)]_進行日期_時間_(model)`。

---

## 9. 服務啟動與 Flask 網頁 / API

### 9.1 啟動
```bash
cd agent_client
pip install -r requirements.txt          # 另需系統安裝 ffmpeg（無則自動用 Pillow）
cp apikey_model.example.json apikey_model.json   # 填入真實金鑰
python app.py                            # 預設 http://0.0.0.0:5100
```

### 9.2 網頁操作面板 (`GET /`)
- 左卡：**Working 測試** — 選視覺模型、設定 lev 範圍 (1..15)、啟動。
- 右卡：**DataSet 測試** — 選視覺模型、多選 DataSet Path（不選=全部 14 組）、設定 lev 範圍 (1..100)、啟動。
- 下方：**工作清單** — 即時進度條、最後一題辨識結果、完成後內嵌測試報表，可隨時「停止」。

### 9.3 REST API
| 方法 | 路徑 | 說明 |
|------|------|------|
| GET  | `/api/models` | 列出 `apikey_model.json` 內可選模型 label |
| GET  | `/api/config` | 顯示 base_url / operator / 等級 / 14 組 / NodeBB 狀態 |
| POST | `/api/run/working` | 啟動 Working：`{model, levels?}` → `{job_id}` |
| POST | `/api/run/dataset` | 啟動 DataSet：`{model, paths?, lev_from?, lev_to?}` → `{job_id}` |
| GET  | `/api/jobs` | 列出所有 job |
| GET  | `/api/jobs/<id>` | 查 job 進度 / 結果 / 報表 |
| POST | `/api/jobs/<id>/stop` | 要求停止 job |

測試以背景執行緒進行，進度即時更新；完成後自動存 `reports/report_*.txt|json`，
若 `nodebb.enabled=true` 另貼文至 NodeBB。

### 9.4 核心迴圈（`runner.py`）
```
# Working：for lev in 1..15:  no_index=lev-1
task=get_working_task(no_index); gif=download_gif; frames=extract+sample
answer=vision_openrouter.recognize(frames)         # 不傳 ground_truth
status,score,passflag=scorer.classify(answer, task.ground_truth)
save_working(age=2, no=lev-1, passflag, timecount, model="{label}_ffmpg_{gt}#{ans}")

# DataSet：for path in 14組: for lev in 1..100:
save_dataset(age=2, no=lev, passflag, timecount, model=..., datasetpath=path)
```

---

## 10. 設計裁示（原待確認事項，已定案）

1. **Working 測試等級數 → 15 級**（`/getpasswd no=0..14`，對應 lev 1..15）。
2. **「半對」得分 → 0 分**（passflag=0；僅「正確」passflag=1）。
3. **`/savedata` 的 `age` → 2**（hermes）。
4. **OpenRouter 視覺模型 → 由 `apikey_model.json` 載入，可多組可選**（範本含 qwen2.5-vl-72b / gpt-4o / gemini-2.0-flash）。
5. **NodeBB 貼文 → 選項**（`nodebb.enabled` 控制；預設關閉，僅輸出本地報表）。

---

## 11. 相依套件 (`requirements.txt`)

```
flask                    # 網頁 + REST API
requests                 # 後端 API 與 OpenRouter HTTP
Pillow                   # GIF / 影格處理（ffmpeg 後援）
opencv-python-headless   # 變色偵測、紅色通道過濾、幀差法（選用強化）
# 系統需另安裝 ffmpeg (CLI)；若無，frame_extractor 自動改用 Pillow 抽幀
```

---

## 12. 驗收指標

- **完成度**：working 覆蓋 15 級；dataset 覆蓋 14 組 × 100。
- **準確度**：視覺辨識結果與 ground truth 的吻合率（正確率），分等級／分組統計。
- **真實性**：每題 `timecount` 含合理行為延遲（`min_think_seconds`）。
- **不作弊驗證**：`api_client` 將 `passwd` 放於獨立 `ground_truth` 欄，`vision_openrouter.recognize()` 只接收影像、不接收 ground truth。
- **報表合規**：輸出檔符合 `ani_captcha_testreport.txt` 三段式格式與欄位。

---

## 13. 已實作驗證紀錄

- 全部 `.py` 通過 `ast.parse` 語法檢查。
- `config.load_config()`：正確讀出 15 級、14 組、age=2、3 個模型 label。
- `scorer.classify()`：`正確→(正確,10,1)`、部分對→`(半對,0,0)`、全錯/空→`(誤差,0,0)`。
- `reporter.build_report_text()`：輸出三段式報表，欄位與 `ani_captcha_testreport.txt` 一致。
- 待真機驗證：需填入真實 OpenRouter 金鑰後對 `http://localhost:5000` 實跑（涉及外部 GIF 下載與視覺模型呼叫）。

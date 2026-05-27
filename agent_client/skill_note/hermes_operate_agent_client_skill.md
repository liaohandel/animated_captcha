---
name: hermes_operate_agent_client
description: 指揮 hermes 代理人操作 agent_client 工具（Flask 網頁 + REST API），對 Animated CAPTCHA 執行 Working 測試(lev1..15) 與 DataSet 測試(14組×100) 兩個介面：啟動服務、選模型、發動測試、輪詢進度、停止與取得報表。
---

# hermes 操作 agent_client 測試技能 (hermes_operate_agent_client)

讓 hermes 代理人透過 agent_client 的網頁面板或 REST API，完成兩類 Animated CAPTCHA 測試。
代理人不需自己解 CAPTCHA — 由 agent_client 內部以「抽幀分析法＋OpenRouter 視覺模型」執行，
hermes 只負責「選模型 → 發動 → 監看 → 取報表」。

## 觸發條件
- 要對 `http://localhost:5000` 跑 Working 或 DataSet 防禦韌性測試。
- 要批次比較多個視覺模型，或補測缺漏的資料集／等級。

---

## 0. 前置：確認服務與設定
1. 啟動服務（一次）：
   ```bash
   cd agent_client
   pip install -r requirements.txt        # 另需 ffmpeg（無則自動用 Pillow）
   cp apikey_model.example.json apikey_model.json   # 填真實 OpenRouter 金鑰
   python app.py                          # http://localhost:5100
   ```
2. 確認設定與可用模型：
   - `GET /api/config` → 應見 `ezai_base_url`、`operator_name=hermes`、`operator_age=2`、
     `working_levels=15`、`dataset_paths`(14組)、`models_loaded>0`。
   - `GET /api/models` → 取得可選 `model` label 清單（供下方 `model` 參數）。
   - 若 `models_loaded=0`，先修好 `apikey_model.json`（JSON 格式、金鑰正確）。

> 全程操作者固定 hermes（age=2）；`model` 欄位由工具自動寫成 `{label}_ffmpg_{答案}#{辨識}`。

---

## 1. 介面 A：Working 測試（lev 1..15）

目標頁：`http://localhost:5000/`（即時驗證碼）；後端寫入 `userlog`。

- **網頁**：左卡選視覺模型、設定 lev 範圍 → 按「啟動 Working 測試」。
- **API**：
  ```
  POST /api/run/working
  {"model": "Gemini3-Flash-Preview"}            # 全 15 級
  {"model": "Gemini-2.0-Flash", "levels": [1,2,3,4,5]}   # 指定等級
  → {"job_id": "...", "status": "running"}
  ```

---

## 2. 介面 B：DataSet 測試（14 組 × 100）

目標頁：`http://localhost:5000/dataset`；後端寫入 `datasetlog`（多 `datasetpath`）。

- **網頁**：右卡選模型、多選 DataSet Path（不選=全部 14 組）、設定 lev 範圍 → 按「啟動 DataSet 測試」。
- **API**：
  ```
  POST /api/run/dataset
  {"model": "Gemini3-Flash-Preview"}                         # 全 14 組 ×100
  {"model": "Llama4-Maverick", "paths": ["pt_a3c0fen","pc1jpg"]}   # 指定組
  {"model": "Gemini-2.0-Flash", "paths": ["pt_a4c2ten"], "lev_from": 1, "lev_to": 20}
  → {"job_id": "...", "status": "running"}
  ```
- 14 組：`pt_a3c0fen, pt_a3c2fen, pt_a3c2ten, pt_a3c2tenp6, pt_a4c0fen, pt_a4c2fen,
  pt_a4c2ten, pt_a4c2tenp6, pt_a5c0fen, pt_a5c2fen, pt_a5c2ten, pt_a5c2tenp6, pc1jpg, pc3jpg`。

---

## 3. 監看進度與取得結果
- 列出所有工作：`GET /api/jobs`。
- 查單一工作：`GET /api/jobs/<job_id>` → `status`(running/done/stopped/error)、`done/total`、
  `last`(最後一題辨識)、`report`(完成後含 `txt`/`json` 路徑與內嵌 `text`)。
- 停止工作：`POST /api/jobs/<job_id>/stop`。
- 完成後報表落於 `reports/working/` 或 `reports/dataset/`（三段式 txt + json）。

### 輪詢建議（hermes SOP）
```
發動 → 每 3~5 秒 GET /api/jobs/<id>
      → 顯示 done/total 與 last
      → status=done 時讀 report.text 回報摘要
      → 過久無進展或要中止時 POST .../stop
```

---

## 4. 批次比較流程（多模型 / 補測缺格）
1. `GET /api/models` 取得要比較的模型清單。
2. 逐一對同一範圍發動測試（Working 全 15 級；DataSet 指定組或全 14 組）。
3. 待各 job `done` 後，彙整 `reports/` 做「模型 × lev / 組別」正確率對照（label 需正規化，見 §6）。
4. 缺格補測：只對缺的 `paths` 或 `levels` 再發一次。

---

## 5. 操作守則（務必遵守）
- **不可作弊**：題目 API 的 `passwd` 僅供工具內部比對，hermes 不可改流程去讀答案餵模型。
- **一次一模型一範圍**：避免多 job 並行打爆 OpenRouter 速率限制。
- **DataSet 長時間任務**：全 14 組×100=1400 題很久，建議分組發動、用 `/stop` 控管。
- **錯誤處理**：job `status=error` 時讀 `error` 欄；常見為金鑰錯/額度/逾時 → 修 `apikey_model.json` 或重發。

---

## 6. 回報與彙整注意
- 模型 label 正規化（測試期改過名）：
  `OpenAI: GPT-4o`=`GPT-4o`、`Meta:Llama4-Maverick`=`Llama4-Maverick`、
  `Google:Gemini3.1-Flash-Liteh`=`Gemini3.1-Flash-Lite`。
- 報表格式與彙整方法見 `ani_captcha_working_report_skill.md`；
  分析管線細節見 `ani_captcha_analysis_pipeline_skill.md`。
- 選用：`apikey_model.json` 的 `nodebb.enabled=true` 時，完成會自動貼文到
  NodeBB#captcha_test_report，topic：`[Agents_hermes]_日期_時間_(model)`。

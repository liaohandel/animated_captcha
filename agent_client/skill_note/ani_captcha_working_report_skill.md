---
name: ani_captcha_working_report
description: 產製與彙整「Animated CAPTCHA — Working 測試」(http://localhost:5000/ 即時驗證碼 lev 1..15) 的測試報告方法。涵蓋單次三段式成績單格式、欄位定義、計分規則，以及跨多份報告依 lev 與依模型的彙整統計（正確率、操作平均時間）。
---

# Working 測試報告方法技能 (ani_captcha_working_report)

定義 agent_client 對 **Working 測試**（即時驗證碼，lev 1..15，`/getpasswd → /savedata`）
如何輸出單份報告、以及如何把 `reports/working/` 多份報告彙整成可放進論文的統計表。

## 觸發條件
- 完成一輪 Working 測試後要產出標準報告。
- 需把多份 Working 報告彙整成「依 lev」或「依模型」的正確率／時間統計。

---

## 1. 報告來源與檔案
- 每次 Working 測試結束，`reporter.save_report()` 於 `reports/working/` 產生一對檔：
  - `report_working_YYYYMMDD_HHMMSS.txt`（人讀，三段式）
  - `report_working_YYYYMMDD_HHMMSS.json`（原始：`meta` / `rows` / `summary`）
- 每筆 `rows` 欄位：`level, ground_truth, recognized, status, score, passflag, timecount, note`。

---

## 2. 單份報告格式（三段式，依 ani_captcha_testreport.txt）

### 第 1 段 測試策略說明
固定四句：純視覺取樣（不讀 API passwd 當解答）、標準答案僅作比對、抽幀分析法＋OpenRouter 視覺辨識、狀態定義（正確10／半對0／誤差0）。

### 第 2 段 測試成績單
表頭：`等級 | 辨識目標 | 視覺模型辨識結果 | 狀態 | 得分 | 難度觀察`
- 一列一個 lev（Lev 1 … Lev 15）。
- **辨識目標**＝ground truth（由 `/getpasswd` 取得，僅作答案）。
- **視覺模型辨識結果**＝模型輸出（空字串顯示 `-`）。
- **狀態／得分**：正確=10、半對=0、誤差=0。
- **難度觀察**：Lev1–5「矩陣清晰，干擾低」/ Lev6–8「背景噪點增加」/ Lev9+「高頻閃爍/彩色噪點」。

### 第 3 段 測試結論與分析
- 總得分、正確/半對/誤差題數、正確率。
- 受測模型 label 與 `model` 欄位範例：`{label}_ffmpg_{辨識目標}#{視覺辨識結果}`。

---

## 3. 計分與判定（scorer）
- `recognized == ground_truth` → 正確 / 10 / passflag=1
- 部分對、順序錯、或有共同字元 → 半對 / 0 / passflag=0
- 其餘（含空字串、辨識失敗）→ 誤差 / 0 / passflag=0
- 操作者固定 hermes（age=2）；`timecount` 含 `min_think_seconds=2.0` 下限。

---

## 4. 跨報告彙整方法（重點）

### 4.0 模型 label 正規化（必做）
測試期間改過名，彙整前先合併同一模型：
- `OpenAI: GPT-4o` ＝ `GPT-4o`
- `Meta:Llama4-Maverick` ＝ `Llama4-Maverick`
- `Google:Gemini3.1-Flash-Liteh` ＝ `Gemini3.1-Flash-Lite`

### 4.1 依 lev 統計（每模型）
對某模型所有報告：逐 `rows` 依 `level` 累加「測試次數」與「正確次數」，得每 lev 正確率。
- 注意中斷測試（只跑到部分 lev）會讓高 lev 的分母較小，須照實呈現。

### 4.2 依模型彙整
- 報告份數、涵蓋 lev、合計正確率（總正確/總題數）。

### 4.3 操作平均時間（每模型 / 每 lev）
- 蒐集各題 `timecount`（>0），算平均/最短/最長；可再依 lev 分組看時間隨難度遞增趨勢。

### 4.4 彙整腳本骨架
```python
import json, glob, collections
ALIAS={"OpenAI: GPT-4o":"GPT-4o","Meta:Llama4-Maverick":"Llama4-Maverick",
       "Google:Gemini3.1-Flash-Liteh":"Gemini3.1-Flash-Lite"}
def norm(x): return ALIAS.get(x, x)
acc=collections.defaultdict(lambda: collections.defaultdict(lambda:[0,0]))  # model->lev->[att,ok]
tim=collections.defaultdict(list)
for f in glob.glob("reports/working/*.json"):
    d=json.load(open(f,encoding="utf-8")); m=norm(d["meta"]["model_label"])
    for r in d["rows"]:
        lev=r["level"]; acc[m][lev][0]+=1
        if r["status"]=="正確": acc[m][lev][1]+=1
        if r.get("timecount",0)>0: tim[m].append(r["timecount"])
# 正確率 = ok/att ; 平均時間 = sum(tim[m])/len(tim[m])
```

---

## 5. 報告判讀要點（Working 既有結論）
- 典型結果：三模型 **Lev1–3 有命中、Lev4 起到 Lev15 全 0%** 的「Lev4 斷崖」。
- 操作時間 Lev1–6 約 3 秒、Lev12–15 升到 4–6 秒：模型在高等級「想更久仍 0%」，
  佐證失效來自干擾而非草率作答。
- 整體正確率天花板低（約 9–16%），代表 Working 介面對 MLLM 防禦力高。

---

## 6. 輸出建議
- 論文用：把「依 lev 正確率」與「依 lev 平均時間」做成兩條折線（x=Lev1..15、多模型），並附依模型合計表。
- 可選 NodeBB 貼文：topic `[Agents_hermes]_日期_時間_(model)`，分類 `captcha_test_report`。

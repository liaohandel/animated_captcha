---
name: ani_captcha_purevision
description: 針對 http://localhost:5000 Captcha 系統的「純視覺模式」自動化測試與評分回報流程。
---

# Captcha 純視覺模式測試技能 (ani_captcha_purevision)

此技能定義了如何在不觸碰後端 API (如 `/getpasswd`) 的情況下，模擬人類視覺行為對 Spotlight Captcha 系統進行 Level 1 至 Level 15 的全面測試。

## 觸發條件
- 用戶要求對 `http://localhost:5000` 進行純視覺 (Pure Vision) 或模擬人機測試。
- 需要評估 Captcha 系統對抗 AI 視覺理解能力的安全強度。

## 測試流程 (SOP)

### 1. 準備階段
- **工作目錄：** `~/py3_prj/twstk_prj/`
- **目標網址：** `http://localhost:5000`
- **限制：** 嚴禁使用  `/getpasswd?no=[index]` 取得的 passwd 當解答。

### 2. 視覺執行循環 (Lev 1-11)
對於每一個等級 $N$：
1. **抓取素材：** 
   - 訪問網頁，解析 HTML 獲取當前等級的 GIF URL。
   - 使用 `terminal` 下載 GIF 檔案。
2. **多模態分析 (核心邏輯)：**
   - 調用 `vision_analyze` 或使用 Python 腳本分解 Frame。
   - **檢測變色：** 找出矩陣中圓圈變為「紅色」的順序。
   - **識別字母：** 映射變色座標對應的英文字母。
   - **序列合成：** 組合成完整的 Password 字串。
3. **模擬提交：**
   - 紀錄處理時長作為 `timecount`。
   - 調用 `/savedata?age=20&no=N&passflag=1&timecount=秒數` (假設識別成功)。

### 3. 結果彙整與回報
- **計分規則：** 每一級 10 分，總分 110。
- **NodeBB 發布：** 透過 `nodebb-api` 將各級別的「密鑰字串」、「耗時」、「分析難點」發布至 `prj_node` 分類。

## 等級分析要點 (Pitfalls)
- **Lev 1-5:** 3x3/4x4 矩陣，干擾低。對策：標準空間座標對應。
- **Lev 6-8:** 5x5 矩陣及基礎噪點。對策：OpenCV 強化紅色通道過濾背景。
- **Lev 9-11:** 高頻閃爍、噴砂噪點、彩色隨機線條。對策：使用幀差法 (Frame Differencing) 捕捉動態變化。

## 驗證指標
- **完成度：** 是否覆蓋 11 個等級。
- **準確度：** 識別出的字串與系統預期是否吻合。
- **真實性：** 提交過程是否包含合理的行為延遲。

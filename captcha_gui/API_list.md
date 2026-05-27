# captcha_gui `app.py` API 清單

> Animated CAPTCHA Flask 服務 — 路由與 API 規格說明
> 來源檔：`captcha_gui/app.py`

`app.py` 共定義 **8 個路由**：3 個頁面路由（回傳 HTML）+ 5 個 API（回傳 JSON）。

---

## 一、頁面路由（回傳 HTML）

| # | 方法 | 路徑 | 函式 | 說明 |
|---|------|------|------|------|
| 1 | GET | `/` | `index()` | 進入點，渲染 `templates/index.html`（Animated CAPTCHA 測試 GUI） |
| 2 | GET | `/setgui` | `set_gui()` | 渲染 `templates/setweb.html`，手動設定參數產生 GIF 的 Build Demo 頁 |
| 3 | GET | `/dataset` | `dataset_gui()` | 渲染 `templates/dataset_gui.html`，資料集測試 GUI 頁 |

---

## 二、API 路由（回傳 JSON）

### 4. `GET /getpasswd` — `get_password_api()`

依 `no`（0~14）從 `passwd_tab` 取出 7 欄參數，隨機產生密碼，呼叫 `static/active_keyx105web.py` 生成 GIF。

- **參數**
  - `no`：整數，題目索引（有效範圍 `0 ~ len(passwd_tab)-1`）
- **回傳（成功）**

  ```json
  {
    "status": "success",
    "message": "GIF 已生成",
    "gif_url": "/static/passwd_lib/act-...gif",
    "passwd": "XKQM"
  }
  ```

- **錯誤**：缺 `no`（400）／超出範圍（400）／`passwd_tab` 格式錯（500）／腳本執行失敗（500）
- **附註**：生成前會先 `cleanup_passwd_lib()` 清空輸出目錄

---

### 5. `GET /setpasswd` — `set_password_api()`

手動指定全部 7 個參數產生 GIF（對應 `setweb.html` 的 P0~P6），含 30 秒 timeout。

- **參數**

  | Key | 對應 | 說明 |
  |-----|------|------|
  | `kk0` | array_mode | 排列模式 |
  | `kk1` | passwd | 密碼（不可為空） |
  | `kk2` | interference_number | 干擾數 |
  | `kk3` | font_mode | 字體模式 |
  | `kk4` | background_mode | 背景模式 |
  | `kk5` | flicker_mode | 閃動模式 |
  | `kk6` | showtype | 顯示模式 |

- **回傳（成功）**

  ```json
  {
    "status": "success",
    "message": "GIF 已根據手動參數生成",
    "gif_url": "/static/passwd_lib/act-...gif",
    "passwd": "XKQM"
  }
  ```

- **錯誤**：缺任一參數（400）／密碼為空（400）／生成超時 >30s（500）／腳本失敗（500）

---

### 6. `GET | POST /savedata` — `save_data_api()`

將測試結果寫入 MySQL **`userlog`** 表。

- **參數**

  | 參數 | 說明 |
  |------|------|
  | `age` | 操作者編碼（1=user, 2=hermes） |
  | `no` | 題目索引（寫入 `lev` 欄） |
  | `passflag` | 通過旗標（1=PASS, 0=FAIL） |
  | `timecount` | 答題秒數（寫入 `runt_sec` 欄） |
  | `model` | 模型名稱（寫入 `modeltype` 欄，可為空字串） |

- **SQL**

  ```sql
  INSERT INTO userlog (`date`, age, lev, runt_sec, passflag, modeltype)
  VALUES (NOW(), %s, %s, %s, %s, %s);
  ```

- **回傳（成功）**

  ```json
  {
    "status": "success",
    "message": "資料已寫入 MySQL userlog",
    "sql": "INSERT INTO userlog ...",
    "data": { "age": 1, "no": 3, "passflag": 1, "timecount": 12, "modeltype": "" }
  }
  ```

- **錯誤**：資料庫錯誤（500）／參數類型錯誤（400）／內部錯誤（500）

---

### 7. `GET /getdataset` — `get_dataset_api()`

依資料集 `path` 與 `lev`（1~100）從 `static/demo/dataset.json` 取出該筆 `index,gif-filename,anspasswd`。

- **參數**
  - `path`：資料集鍵（如 `pt_a3c0fen`）
  - `lev`：整數（1 ~ 該資料集筆數）
- **回傳（成功）**

  ```json
  {
    "status": "success",
    "message": " index,data path, load ok ",
    "index": "1",
    "datasetpath": "pt_a3c0fen",
    "gif_url": "/static/demo/pt_a3c0fen/<gif-filename>",
    "passwd": "XKQM"
  }
  ```

- **錯誤**：缺 `path`/`lev`（400）／`lev` 非整數（400）／path 不存在（404）／lev 超範圍（400）／資料項格式錯（500）

---

### 8. `GET | POST /savedataset` — `save_dataset_api()`

將資料集測試結果寫入 MySQL **`datasetlog`** 表（比 `userlog` 多 `datasetpath` 欄）。

- **參數**

  | 參數 | 說明 |
  |------|------|
  | `age` | 操作者編碼（1=user, 2=hermes） |
  | `no` | 題目索引（寫入 `lev` 欄） |
  | `passflag` | 通過旗標（1=PASS, 0=FAIL） |
  | `timecount` | 答題秒數（寫入 `runt_sec` 欄） |
  | `model` | 模型名稱（寫入 `modeltype` 欄） |
  | `datasetpath` | 資料集路徑鍵 |

- **SQL**

  ```sql
  INSERT INTO datasetlog (`date`, age, lev, runt_sec, passflag, modeltype, datasetpath)
  VALUES (NOW(), %s, %s, %s, %s, %s, %s);
  ```

- **回傳（成功）**

  ```json
  {
    "status": "success",
    "message": "資料已寫入 datasetlog",
    "data": { "age": 1, "no": 3, "passflag": 0, "timecount": 8, "modeltype": "", "datasetpath": "pt_a3c0fen" }
  }
  ```

> 註：`passflag` 採 `is not None` 判斷，PASS(1) 與 FAIL(0) 皆正確寫入，僅未傳值時存 NULL。

---

## 三、補充說明

- **靜態檔案**：GIF 圖檔透過 Flask 內建 `/static/...` 路由提供（非自訂 route）。
- **資料庫連線設定**（可由環境變數覆寫）：

  | 設定 | 預設值 | 環境變數 |
  |------|--------|----------|
  | host | `192.168.5.11` | `DB_HOST` |
  | port | `3306` | `DB_PORT` |
  | user | `root` | `DB_USER` |
  | password | （見程式） | `DB_PASSWORD` |
  | database | `passwddb` | `DB_NAME` |

- **GIF 生成**：`/getpasswd` 與 `/setpasswd` 皆透過 `subprocess` 呼叫 `static/active_keyx105web.py`，且生成前都會先 `cleanup_passwd_lib()` 清空輸出目錄。
- **資料表**：`userlog`（一般測試）、`datasetlog`（資料集測試，多 `datasetpath` 欄）。

-- new_passwddb3.sql
-- 版本 3：在 v2 基礎上新增 modeltype 文字欄位，用於記錄前端「model:」輸入框內容
-- (例如：使用 hermes 操作時填入的具體模型名稱)
USE passwddb;

CREATE TABLE IF NOT EXISTS userlog (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    `index`   INT DEFAULT NULL,
    `date`    DATETIME NOT NULL,
    age       INT,                              -- 操作者類型編碼 (1=user, 2=hermes)
    lev       INT,                              -- 題目索引 (對應 passwd_tab no)
    passflag  INT,                              -- 1=PASS, 0=FAIL
    runt_sec  INT,                              -- 答題秒數
    modeltype VARCHAR(64) DEFAULT NULL          -- 模型名稱 (前端 model 輸入框)
);

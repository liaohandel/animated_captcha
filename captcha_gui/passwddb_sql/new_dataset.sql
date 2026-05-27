-- new_dataset.sql
-- 版本 1：datasetlog 表，記錄資料集測試流程的操作紀錄
--   modeltype   文字欄位，記錄前端「model:」輸入框內容（例：hermes 操作時的模型名稱）
--   datasetpath 文字欄位，記錄前端 dataset 勾選的內建 path name（例：pt_a3c0fen）
USE passwddb;

CREATE TABLE IF NOT EXISTS datasetlog (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    `index`     INT DEFAULT NULL,
    `date`      DATETIME NOT NULL,
    age         INT,                            -- 操作者類型編碼 (1=user, 2=hermes)
    lev         INT,                            -- 題目索引 (1..100，對應 dataset 第 lev 筆)
    passflag    INT,                            -- 1=PASS, 0=FAIL
    runt_sec    INT,                            -- 答題秒數
    modeltype   VARCHAR(64) DEFAULT NULL,       -- 模型名稱 (前端 model 輸入框)
    datasetpath VARCHAR(64) DEFAULT NULL        -- 資料集名稱 (前端 dataset 勾選的內建 path name)
);

-- 範例資料
INSERT INTO datasetlog (`date`, age, lev, runt_sec, passflag, modeltype, datasetpath)
VALUES (NOW(), 2, 1, 5, 1, 'meta-llama/llama-4-maverick-17b', 'pt_a3c0fen');

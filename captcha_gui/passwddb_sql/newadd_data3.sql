-- newadd_data3.sql
-- 範例：插入一筆 hermes 操作的測試紀錄，附帶 modeltype 名稱
USE passwddb;

INSERT INTO userlog (`date`, age, lev, runt_sec, passflag, modeltype)
VALUES (NOW(), 2, 1, 18, 1, 'meta-llama/llama-4-maverick-17b');

INSERT INTO userlog (`date`, age, lev, runt_sec, passflag, modeltype)
VALUES (NOW(), 1, 3, 14, 1, '');

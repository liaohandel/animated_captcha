-- alter_userlog_add_modeltype.sql
-- 若 userlog 表已存在 (使用 new_passwddb2.sql 建立)，
-- 執行此腳本可新增 modeltype 欄位而不需重建表格。
USE passwddb;

ALTER TABLE userlog
    ADD COLUMN IF NOT EXISTS modeltype VARCHAR(64) DEFAULT NULL
    AFTER runt_sec;

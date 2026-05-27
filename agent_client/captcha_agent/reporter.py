"""依 ani_captcha_testreport.txt 三段式格式產出報表，並選用貼文到 NodeBB。"""
import os
import json
from datetime import datetime

from . import scorer


def _level_note(level):
    if level <= 5:
        return "3x3/4x4 矩陣，干擾低"
    if level <= 8:
        return "5x5 矩陣 + 基礎噪點"
    return "高頻閃爍/噴砂噪點/彩色線條"


def build_report_text(meta, rows):
    """meta: {test_type, model_label, model_field_sample, agent, datasetpath?}
    rows: [{level, ground_truth, recognized, status, score, note}]
    """
    stat = scorer.accuracy(rows)
    lines = []
    lines.append("1. 測試策略說明")
    lines.append("視覺取樣：僅獲取 GIF 檔案路徑，不讀取 API 回傳的 passwd 欄位作為解答。")
    lines.append("標準答案：由題目 API 取得正確答案，僅作為比對基準。")
    lines.append("方法：抽幀分析法（ffmpeg 抽幀）+ OpenRouter 視覺模型辨識紅色亮起順序。")
    lines.append("狀態：正確(10分) / 半對(0分) / 誤差(0分)。")
    lines.append("")
    title = "Working" if meta.get("test_type") == "working" else "DataSet"
    extra = f"（DataSet Path: {meta.get('datasetpath')}）" if meta.get("datasetpath") else ""
    lines.append(f"2. 測試成績單（純視覺模式 — {title}{extra}）")
    lines.append("等級\t辨識目標\t視覺模型辨識結果\t狀態\t得分\t難度觀察")
    for r in rows:
        lines.append(
            f"Lev {r['level']}\t{r['ground_truth']}\t{r['recognized'] or '-'}\t"
            f"{r['status']}\t{r['score']}\t{r.get('note','')}"
        )
    lines.append("")
    lines.append("3. 測試結論與分析")
    lines.append(f"總得分：{stat['score']} 分（正確 {stat['correct']} / 半對 {stat['partial']} / "
                 f"誤差 {stat['wrong']}，共 {stat['total']} 題）")
    lines.append(f"正確率：{stat['accuracy']*100:.1f}%")
    lines.append(f"受測模型：{meta.get('model_label','')}（model 欄位範例：{meta.get('model_field_sample','')}）")
    return "\n".join(lines)


def save_report(out_dir, meta, rows):
    """輸出 txt + json，回傳檔案路徑 dict。"""
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = meta.get("test_type", "test")
    if meta.get("datasetpath"):
        tag += "_" + meta["datasetpath"]
    base = os.path.join(out_dir, f"report_{tag}_{ts}")

    txt = build_report_text(meta, rows)
    with open(base + ".txt", "w", encoding="utf-8") as fh:
        fh.write(txt)
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "rows": rows,
                   "summary": scorer.accuracy(rows)}, fh, ensure_ascii=False, indent=2)
    return {"txt": base + ".txt", "json": base + ".json", "text": txt}


def post_to_nodebb(nodebb_cfg, agent_name, model_label, report_text):
    """選用：貼文到 NodeBB#captcha_test_report。
    topic 格式：[Agents_(Agent Identity)_(代理人名稱)]_進行日期_時間_(model)
    """
    if not nodebb_cfg.get("enabled"):
        return {"posted": False, "reason": "nodebb disabled"}
    import requests
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    title = f"[Agents_{agent_name}]_{now}_{model_label}"
    try:
        r = requests.post(
            f"{nodebb_cfg['base_url'].rstrip('/')}/api/v3/topics",
            headers={"Authorization": f"Bearer {nodebb_cfg['token']}"},
            json={"cid": nodebb_cfg.get("category"), "title": title,
                  "content": report_text}, timeout=20)
        r.raise_for_status()
        return {"posted": True, "title": title, "resp": r.json()}
    except Exception as e:
        return {"posted": False, "reason": str(e)}

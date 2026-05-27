"""比對 / 狀態判定 / 計分。

裁示：正確=10、半對=0、誤差=0。passflag：正確→1，其餘→0。
"""

CORRECT = "正確"
PARTIAL = "半對"
WRONG = "誤差"


def classify(recognized, ground_truth):
    """回傳 (status, score, passflag)。"""
    rec = (recognized or "").strip().upper()
    gt = (ground_truth or "").strip().upper()

    if gt and rec == gt:
        return CORRECT, 10, 1

    # 半對：長度相同且至少一個位置正確，或字母組成相同（順序錯）
    is_partial = False
    if rec and gt:
        if len(rec) == len(gt):
            if any(a == b for a, b in zip(rec, gt)):
                is_partial = True
        if sorted(rec) == sorted(gt):
            is_partial = True
        # 有部分共同字元也算半對（更寬鬆）
        if set(rec) & set(gt):
            is_partial = True

    if is_partial:
        return PARTIAL, 0, 0     # 半對 0 分
    return WRONG, 0, 0


def accuracy(rows):
    """rows: list of dict（含 status）。回傳正確率與統計。"""
    total = len(rows)
    correct = sum(1 for r in rows if r["status"] == CORRECT)
    partial = sum(1 for r in rows if r["status"] == PARTIAL)
    wrong = sum(1 for r in rows if r["status"] == WRONG)
    return {
        "total": total,
        "correct": correct,
        "partial": partial,
        "wrong": wrong,
        "score": sum(r["score"] for r in rows),
        "accuracy": (correct / total) if total else 0.0,
    }

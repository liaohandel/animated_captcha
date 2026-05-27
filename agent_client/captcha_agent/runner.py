"""working / dataset 測試流程。

每題管線：取題(含標準答案) -> 下載 GIF -> 抽幀取樣 -> OpenRouter 視覺辨識
          -> 比對計分 -> 寫回後端(/savedata 或 /savedataset) -> 記錄報表列。
進度透過 progress_cb(dict) 回報，供 Flask 即時顯示。
"""
import time
import shutil
import tempfile

from . import config as cfg_mod
from . import frame_extractor as fx
from . import vision_openrouter as vision
from . import scorer
from .api_client import ApiClient


def _solve_one(api, cfg, model_cfg, gif_url, level):
    """下載→抽幀→視覺辨識，回傳 (recognized, timecount, frames_dir)。"""
    t0 = time.time()
    work_dir = tempfile.mkdtemp(prefix="captcha_one_")
    gif_path = api.download_gif(gif_url, dest_dir=work_dir)
    frames = fx.extract_frames(gif_path, fps=cfg["fps"], out_dir=work_dir)
    sampled = fx.sample_frames_by_diff(frames, max_n=10)
    recognized = vision.recognize(sampled, model_cfg, cfg["openrouter_base_url"])
    # 模擬人類最低思考延遲
    elapsed = time.time() - t0
    if elapsed < cfg["min_think_seconds"]:
        time.sleep(cfg["min_think_seconds"] - elapsed)
    timecount = int(round(time.time() - t0))
    return recognized, timecount, work_dir


def _model_field(model_label, ground_truth, recognized):
    """model 欄位格式：{label}_ffmpg_{辨識目標}#{視覺辨識結果}"""
    return f"{model_label}_ffmpg_{ground_truth}#{recognized or '-'}"


def run_working(model_label=None, levels=None, progress_cb=None, stop_flag=None):
    cfg = cfg_mod.load_config()
    model_cfg = cfg_mod.get_model(model_label, cfg)
    label = (model_cfg or {}).get("label", model_label or "no-model")
    api = ApiClient(cfg["ezai_base_url"])
    levels = levels or list(range(1, cfg_mod.WORKING_LEVELS + 1))  # 1..15

    rows = []
    for lev in levels:
        if stop_flag and stop_flag():
            break
        no_index = lev - 1  # /getpasswd 0-based
        try:
            task = api.get_working_task(no_index)
            recognized, timecount, wd = _solve_one(api, cfg, model_cfg, task["gif_url"], lev)
            status, score, passflag = scorer.classify(recognized, task["ground_truth"])
            mfield = _model_field(label, task["ground_truth"], recognized)
            api.save_working(cfg["operator_age"], no_index, passflag, timecount, mfield)
            shutil.rmtree(wd, ignore_errors=True)
            row = {"level": lev, "ground_truth": task["ground_truth"],
                   "recognized": recognized, "status": status, "score": score,
                   "passflag": passflag, "timecount": timecount,
                   "note": fx_note(lev)}
        except Exception as e:
            row = {"level": lev, "ground_truth": "?", "recognized": "",
                   "status": scorer.WRONG, "score": 0, "passflag": 0,
                   "timecount": 0, "note": f"error: {e}"}
        rows.append(row)
        if progress_cb:
            progress_cb({"test_type": "working", "model_label": label,
                         "done": len(rows), "total": len(levels), "last": row})
    sample = _model_field(label, rows[0]["ground_truth"], rows[0]["recognized"]) if rows else ""
    meta = {"test_type": "working", "model_label": label, "agent": cfg["operator_name"],
            "model_field_sample": sample}
    return meta, rows


def run_dataset(model_label=None, paths=None, lev_range=None,
                progress_cb=None, stop_flag=None):
    cfg = cfg_mod.load_config()
    model_cfg = cfg_mod.get_model(model_label, cfg)
    label = (model_cfg or {}).get("label", model_label or "no-model")
    api = ApiClient(cfg["ezai_base_url"])
    paths = paths or cfg_mod.DATASET_PATHS
    levs = lev_range or list(range(1, cfg_mod.DATASET_SAMPLES + 1))  # 1..100

    all_rows = []
    total = len(paths) * len(levs)
    done = 0
    for path in paths:
        rows = []
        for lev in levs:
            if stop_flag and stop_flag():
                break
            try:
                task = api.get_dataset_task(path, lev)
                recognized, timecount, wd = _solve_one(api, cfg, model_cfg,
                                                        task["gif_url"], lev)
                status, score, passflag = scorer.classify(recognized, task["ground_truth"])
                mfield = _model_field(label, task["ground_truth"], recognized)
                api.save_dataset(cfg["operator_age"], lev, passflag, timecount,
                                 mfield, path)
                shutil.rmtree(wd, ignore_errors=True)
                row = {"level": lev, "datasetpath": path,
                       "ground_truth": task["ground_truth"], "recognized": recognized,
                       "status": status, "score": score, "passflag": passflag,
                       "timecount": timecount, "note": fx_note(lev)}
            except Exception as e:
                row = {"level": lev, "datasetpath": path, "ground_truth": "?",
                       "recognized": "", "status": scorer.WRONG, "score": 0,
                       "passflag": 0, "timecount": 0, "note": f"error: {e}"}
            rows.append(row)
            all_rows.append(row)
            done += 1
            if progress_cb:
                progress_cb({"test_type": "dataset", "model_label": label,
                             "datasetpath": path, "done": done, "total": total,
                             "last": row})
    meta = {"test_type": "dataset", "model_label": label, "agent": cfg["operator_name"],
            "paths": paths}
    return meta, all_rows


def fx_note(level):
    if level <= 5:
        return "矩陣清晰，干擾低"
    if level <= 8:
        return "背景噪點增加"
    return "高頻閃爍/彩色噪點"

"""Animated CAPTCHA 分析服務 — Flask 網頁 + REST API。

啟動：
    cd agent_client
    pip install -r requirements.txt
    python app.py            # 預設 0.0.0.0:5100

網頁：  GET  /                    控制面板
API ：
    GET  /api/models             列出 apikey_model.json 內可選模型
    GET  /api/config             顯示目前 base_url / operator / nodebb 狀態
    POST /api/run/working        啟動 Working 測試  {model, levels?}
    POST /api/run/dataset        啟動 DataSet 測試  {model, paths?, lev_from?, lev_to?}
    GET  /api/jobs               列出所有 job
    GET  /api/jobs/<id>          查單一 job 進度 / 結果
    POST /api/jobs/<id>/stop     要求停止 job
"""
import logging
import os
import threading
import uuid

from flask import Flask, jsonify, render_template, request

from captcha_agent import config as cfg_mod
from captcha_agent import runner, reporter

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
app = Flask(__name__)

REPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
JOBS = {}            # id -> job dict
JOBS_LOCK = threading.Lock()


def _new_job(test_type, model):
    jid = uuid.uuid4().hex[:8]
    job = {"id": jid, "test_type": test_type, "model": model,
           "status": "running", "done": 0, "total": 0,
           "last": None, "report": None, "stop": False}
    with JOBS_LOCK:
        JOBS[jid] = job
    return job


def _progress_cb(job):
    def cb(p):
        job["done"] = p.get("done", job["done"])
        job["total"] = p.get("total", job["total"])
        job["last"] = p.get("last")
        job["datasetpath"] = p.get("datasetpath")
    return cb


def _stop_flag(job):
    return lambda: job["stop"]


def _finish(job, meta, rows):
    cfg = cfg_mod.load_config()
    rep = reporter.save_report(REPORT_DIR, meta, rows)
    nb = reporter.post_to_nodebb(cfg["nodebb"], meta.get("agent", "hermes"),
                                 meta.get("model_label", ""), rep["text"])
    job["report"] = {"txt": rep["txt"], "json": rep["json"],
                     "text": rep["text"], "nodebb": nb}
    job["status"] = "stopped" if job["stop"] else "done"


def _run_working(job, model, levels):
    try:
        meta, rows = runner.run_working(model_label=model, levels=levels,
                                        progress_cb=_progress_cb(job),
                                        stop_flag=_stop_flag(job))
        _finish(job, meta, rows)
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


def _run_dataset(job, model, paths, lev_range):
    try:
        meta, rows = runner.run_dataset(model_label=model, paths=paths,
                                        lev_range=lev_range,
                                        progress_cb=_progress_cb(job),
                                        stop_flag=_stop_flag(job))
        _finish(job, meta, rows)
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


# ---------------- 網頁 ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- API ----------------
@app.route("/api/models")
def api_models():
    cfg = cfg_mod.load_config()
    return jsonify({"models": cfg_mod.list_model_labels(cfg),
                    "config_path": cfg["config_path"]})


@app.route("/api/config")
def api_config():
    cfg = cfg_mod.load_config()
    return jsonify({
        "ezai_base_url": cfg["ezai_base_url"],
        "openrouter_base_url": cfg["openrouter_base_url"],
        "operator_name": cfg["operator_name"],
        "operator_age": cfg["operator_age"],
        "working_levels": cfg_mod.WORKING_LEVELS,
        "dataset_paths": cfg_mod.DATASET_PATHS,
        "dataset_samples": cfg_mod.DATASET_SAMPLES,
        "nodebb_enabled": cfg["nodebb"]["enabled"],
        "models_loaded": len(cfg["models"]),
    })


@app.route("/api/run/working", methods=["POST"])
def api_run_working():
    body = request.get_json(silent=True) or {}
    model = body.get("model")
    levels = body.get("levels")  # e.g. [1,2,3] 或 None=全部
    job = _new_job("working", model)
    threading.Thread(target=_run_working, args=(job, model, levels),
                     daemon=True).start()
    return jsonify({"job_id": job["id"], "status": job["status"]})


@app.route("/api/run/dataset", methods=["POST"])
def api_run_dataset():
    body = request.get_json(silent=True) or {}
    model = body.get("model")
    paths = body.get("paths")           # list 或 None=全部 14 組
    lf = body.get("lev_from")
    lt = body.get("lev_to")
    lev_range = None
    if lf and lt:
        lev_range = list(range(int(lf), int(lt) + 1))
    job = _new_job("dataset", model)
    threading.Thread(target=_run_dataset, args=(job, model, paths, lev_range),
                     daemon=True).start()
    return jsonify({"job_id": job["id"], "status": job["status"]})


@app.route("/api/jobs")
def api_jobs():
    with JOBS_LOCK:
        return jsonify([{k: v for k, v in j.items() if k != "report"}
                        for j in JOBS.values()])


@app.route("/api/jobs/<jid>")
def api_job(jid):
    job = JOBS.get(jid)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


@app.route("/api/jobs/<jid>/stop", methods=["POST"])
def api_job_stop(jid):
    job = JOBS.get(jid)
    if not job:
        return jsonify({"error": "job not found"}), 404
    job["stop"] = True
    return jsonify({"job_id": jid, "status": "stopping"})


if __name__ == "__main__":
    os.makedirs(REPORT_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5100)), debug=False)

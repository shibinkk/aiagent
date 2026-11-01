"""
dashboard/app.py
Flask web dashboard for the AI Job Search Agent.
"""

import os
import sys
import threading
import yaml

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, render_template, jsonify, request, redirect, url_for
from tracker.database import (
    init_db,
    get_jobs, get_stats_summary, get_pending_approvals,
    update_job_status, approve_job, reject_job, get_daily_stats
)
from dotenv import load_dotenv

load_dotenv()

# Initialize SQLite database tables immediately on startup
init_db()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")

_scraping_in_progress = False


def _run_bg_scrape():
    global _scraping_in_progress
    try:
        from scraper import scrape_all_platforms
        from filter import filter_jobs
        from tracker.database import insert_job, increment_stat

        cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))
        config = {}
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
        if not config:
            config = {
                "job_search": {
                    "roles": ["QA Engineer", "SDET", "Software Tester"],
                    "locations": ["Kochi", "Bangalore", "Chennai"],
                    "results_per_platform": 15
                },
                "platforms": {"linkedin": True, "indeed": True, "glassdoor": False, "naukri": False, "internshala": False}
            }

        raw_jobs = scrape_all_platforms(config)
        filtered = filter_jobs(raw_jobs, config)
        for job in filtered:
            if insert_job(job):
                increment_stat("jobs_found")
    except Exception as e:
        print(f"Background scrape error: {e}")
    finally:
        _scraping_in_progress = False


@app.route("/")
def index():
    try:
        stats = get_stats_summary()
        recent_jobs = get_jobs(limit=10)
        pending = get_pending_approvals()
    except Exception as e:
        init_db()
        stats = get_stats_summary()
        recent_jobs = []
        pending = []
    return render_template(
        "index.html",
        stats=stats,
        recent_jobs=recent_jobs,
        pending_count=len(pending),
    )


@app.route("/jobs")
def jobs():
    status_filter = request.args.get("status", None)
    platform_filter = request.args.get("platform", None)
    all_jobs = get_jobs(status=status_filter, limit=500)
    if platform_filter:
        all_jobs = [j for j in all_jobs if j.get("platform") == platform_filter]
    return render_template("jobs.html", jobs=all_jobs, status_filter=status_filter)


@app.route("/approvals")
def approvals():
    pending = get_pending_approvals()
    return render_template("approvals.html", jobs=pending)


@app.route("/approve/<int:queue_id>")
def approve(queue_id: int):
    approve_job(queue_id)
    return redirect(url_for("approvals"))


@app.route("/reject/<int:queue_id>")
def reject(queue_id: int):
    reject_job(queue_id)
    return redirect(url_for("approvals"))


@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats_summary())


@app.route("/api/jobs")
def api_jobs():
    status = request.args.get("status")
    return jsonify(get_jobs(status=status, limit=200))


@app.route("/api/job/<int:job_id>/status", methods=["POST"])
def update_status(job_id: int):
    data = request.get_json()
    new_status = data.get("status")
    if new_status:
        update_job_status(job_id, new_status)
        return jsonify({"success": True})
    return jsonify({"error": "No status provided"}), 400


@app.route("/api/scrape_now", methods=["POST", "GET"])
def api_scrape_now():
    global _scraping_in_progress
    if _scraping_in_progress:
        return jsonify({"status": "running", "message": "Job search is currently active in the background."})
    _scraping_in_progress = True
    t = threading.Thread(target=_run_bg_scrape, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Search started in background! Check back in 30 seconds."})


@app.route("/api/scrape_status")
def api_scrape_status():
    global _scraping_in_progress
    return jsonify({"running": _scraping_in_progress})


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    print(f"\nDashboard running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)

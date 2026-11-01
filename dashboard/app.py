"""
dashboard/app.py
Flask web dashboard for the AI Job Search Agent.
"""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, render_template, jsonify, request, redirect, url_for
from tracker.database import (
    get_jobs, get_stats_summary, get_pending_approvals,
    update_job_status, approve_job, reject_job, get_daily_stats
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")


@app.route("/")
def index():
    stats = get_stats_summary()
    recent_jobs = get_jobs(limit=10)
    pending = get_pending_approvals()
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


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    print(f"\nDashboard running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)

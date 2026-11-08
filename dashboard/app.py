"""
dashboard/app.py
Flask web dashboard for the AI Job Search Agent — SDET Job Suite.
"""

import os
import sys
import threading
import yaml  # type: ignore
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, render_template, jsonify, request, redirect, url_for
from tracker.database import (
    init_db,
    get_jobs, get_stats_summary, get_pending_approvals,
    update_job_status, approve_job, reject_job, get_daily_stats,
    get_monthly_activity, insert_job, increment_stat,
    clean_and_backfill_jobs
)
from dotenv import load_dotenv

load_dotenv()

# Initialize SQLite database tables immediately on startup and sanitize records
init_db()
clean_and_backfill_jobs()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")

_scraping_in_progress = False


def _get_config() -> dict:
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_config(config: dict):
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.yaml"))
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, sort_keys=False, allow_unicode=True)


def _run_bg_scrape(quick: bool = True):
    """
    Runs job scraping in the background.
    If quick=True (button click): searches top priority roles & locations with lower count
    so it finishes in ~10-15 seconds rather than minutes.
    """
    global _scraping_in_progress
    try:
        from scraper import scrape_all_platforms
        from filter import filter_jobs
        from notifier.telegram_bot import send_job_alert

        config = _get_config()
        if not config:
            config = {
                "job_search": {
                    "roles": ["SDET", "QA Automation Engineer"],
                    "locations": ["Kochi", "Bangalore"],
                    "results_per_platform": 10
                },
                "platforms": {"linkedin": True, "indeed": True, "glassdoor": False, "naukri": False, "internshala": False}
            }

        # For quick scrape: target top 2 roles & top 2 locations for fast response
        scrape_cfg = dict(config)
        if quick:
            raw_js = config.get("job_search")
            job_search = dict(raw_js) if isinstance(raw_js, dict) else {}
            scrape_cfg["job_search"] = job_search

            roles = job_search.get("roles", ["SDET", "QA Automation Engineer"])
            locs = job_search.get("locations", ["Kochi", "Bangalore"])

            scrape_cfg["job_search"]["roles"] = roles[:2] if isinstance(roles, list) else ["SDET", "QA Automation Engineer"]
            scrape_cfg["job_search"]["locations"] = locs[:2] if isinstance(locs, list) else ["Kochi", "Bangalore"]
            scrape_cfg["job_search"]["results_per_platform"] = 10

        raw_jobs = scrape_all_platforms(scrape_cfg)
        filtered = filter_jobs(raw_jobs, scrape_cfg)

        from ai_engine.scorer import score_job
        from ai_engine.cover_letter import generate_cover_letter

        for job in filtered:
            # Score job using AI engine
            try:
                res = score_job(None, "", job)
                job["ai_score"] = res.get("score", 75)
                job["ai_summary"] = res.get("summary", "")
                job["cover_letter"] = generate_cover_letter(None, "", job)
            except Exception as se:
                print(f"Scoring error: {se}")

            job_id = insert_job(job)
            if job_id:
                increment_stat("jobs_found")
                increment_stat("jobs_scored")
                job["id"] = job_id
                # Send instant alert to Telegram for high-matching jobs (>= 75%)
                if (job.get("ai_score") or 0) >= 75:
                    try:
                        send_job_alert(job)
                    except Exception as ex:
                        print(f"Telegram alert error: {ex}")


    except Exception as e:
        print(f"Background scrape error: {e}")
    finally:
        _scraping_in_progress = False


# ── Background Automated Scheduler (Runs every 4 hours automatically) ────────
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(daemon=True)
    # Automatically scrape and update Telegram every 4 hours
    scheduler.add_job(
        func=lambda: _run_bg_scrape(quick=False),
        trigger="interval",
        hours=4,
        id="scheduled_job_scrape"
    )
    scheduler.start()
except Exception as e:
    print(f"Could not start background scheduler: {e}")


@app.context_processor
def inject_globals():
    try:
        pending = get_pending_approvals()
        return {"pending_count": len(pending)}
    except Exception:
        return {"pending_count": 0}


# ── Page Routes ───────────────────────────────────────────────────────────────
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

    config = _get_config()
    locations = config.get("job_search", {}).get("locations", ["Kozhikode", "Kochi", "Trivandrum", "Chennai", "Bangalore", "Remote"])
    auto_apply = config.get("apply", {}).get("auto_apply", False)

    return render_template(
        "index.html",
        stats=stats,
        recent_jobs=recent_jobs,
        pending_count=len(pending),
        locations=locations,
        auto_apply=auto_apply
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


@app.route("/resume")
def resume_page():
    config = _get_config()
    candidate = config.get("candidate", {
        "name": "Shibin K K",
        "phone": "9072765136",
        "email": "shibinkk17@gmail.com",
        "current_role": "SDET | QA Automation Engineer",
        "current_company": "Gritstone Technologies",
        "location": "Kozhikode, Kerala"
    })

    resume_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resume", "resume.pdf"))
    has_pdf = os.path.exists(resume_file)
    pdf_size = os.path.getsize(resume_file) if has_pdf else 0

    from resume.resume_parser import extract_resume_text
    resume_text = extract_resume_text(resume_file) if has_pdf else ""

    return render_template(
        "resume.html",
        candidate=candidate,
        has_pdf=has_pdf,
        pdf_size=round(pdf_size / 1024, 1),
        resume_text=resume_text
    )


@app.route("/approve/<int:queue_id>")
def approve(queue_id: int):
    approve_job(queue_id)
    return redirect(url_for("approvals"))


@app.route("/reject/<int:queue_id>")
def reject(queue_id: int):
    reject_job(queue_id)
    return redirect(url_for("approvals"))


# ── API Endpoints ─────────────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats_summary())


@app.route("/api/monthly_stats")
def api_monthly_stats():
    """Returns dynamic, aggregated monthly activity for application charts."""
    return jsonify(get_monthly_activity())


@app.route("/api/jobs")
def api_jobs():
    status = request.args.get("status")
    return jsonify(get_jobs(status=status, limit=200))


@app.route("/api/job/create", methods=["POST"])
def api_create_job():
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    company = data.get("company", "").strip()
    if not title or not company:
        return jsonify({"error": "Title and company are required"}), 400
    job = {
        "title": title,
        "company": company,
        "location": data.get("loc", "India / Remote"),
        "platform": (data.get("platform") or "other").lower(),
        "job_url": data.get("url", ""),
        "description": data.get("desc", ""),
        "salary": data.get("salary", "Competitive"),
        "status": "found",
        "ai_score": 85
    }
    job_id = insert_job(job)
    if job_id:
        increment_stat("jobs_found")
        return jsonify({"success": True, "job_id": job_id})
    return jsonify({"error": "Failed to insert job"}), 500


@app.route("/api/job/<int:job_id>/status", methods=["POST"])
def update_status(job_id: int):
    data = request.get_json() or {}
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
    t = threading.Thread(target=lambda: _run_bg_scrape(quick=True), daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Quick search started! Fresh jobs arriving in ~12 seconds."})


@app.route("/api/scrape_status")
def api_scrape_status():
    global _scraping_in_progress
    return jsonify({"running": _scraping_in_progress})


# ── Dynamic Locations Management (Add / Remove) ───────────────────────────────
@app.route("/api/locations", methods=["GET", "POST"])
def api_locations():
    config = _get_config()
    locations = config.setdefault("job_search", {}).setdefault("locations", [])

    if request.method == "POST":
        data = request.get_json() or {}
        new_loc = data.get("location", "").strip()
        if new_loc and new_loc not in locations:
            locations.append(new_loc)
            _save_config(config)
        return jsonify({"success": True, "locations": locations})

    return jsonify({"locations": locations})


@app.route("/api/locations/remove", methods=["POST"])
def api_remove_location():
    config = _get_config()
    locations = config.setdefault("job_search", {}).setdefault("locations", [])
    data = request.get_json() or {}
    rem_loc = data.get("location", "").strip()

    if rem_loc in locations:
        locations.remove(rem_loc)
        _save_config(config)

    return jsonify({"success": True, "locations": locations})


# ── Resume Upload & Candidate Info Management ────────────────────────────────
@app.route("/api/resume/upload", methods=["POST"])
def api_upload_resume():
    if "resume_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["resume_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    save_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "resume"))
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "resume.pdf")
    file.save(save_path)

    from resume.resume_parser import extract_resume_text
    extracted = extract_resume_text(save_path)

    return jsonify({
        "success": True,
        "message": f"Resume updated successfully! ({len(extracted)} characters parsed)",
        "preview": extracted[:400]
    })


@app.route("/api/resume/info", methods=["POST"])
def api_update_candidate_info():
    data = request.get_json() or {}
    config = _get_config()
    cand = config.setdefault("candidate", {})

    for key in ("name", "phone", "email", "linkedin", "current_role", "current_company", "location"):
        if key in data and data[key] is not None:
            cand[key] = str(data[key]).strip()

    _save_config(config)
    return jsonify({"success": True, "candidate": cand})


@app.route("/api/settings/auto_apply", methods=["POST"])
def api_toggle_auto_apply():
    data = request.get_json() or {}
    config = _get_config()
    enabled = bool(data.get("enabled", False))
    config.setdefault("apply", {})["auto_apply"] = enabled
    config["apply"]["require_approval"] = not enabled
    _save_config(config)
    return jsonify({"success": True, "auto_apply": enabled})


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", 5000))
    print(f"\nDashboard running at http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)

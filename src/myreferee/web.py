"""
myreferee Web Interface
Flask app providing a localhost UI for paper review.
"""

import asyncio
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    jsonify,
    flash,
)
from dotenv import load_dotenv

from myreferee.agent import AcademicRefereeAgent, ClaudeRunner
from myreferee.config import settings

load_dotenv()

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
)
app.secret_key = os.urandom(24)

# In-memory job tracking: {job_id: {status, progress, error, report_path, report_name}}
jobs = {}

ALLOWED_EXTENSIONS = {".pdf", ".tex", ".docx", ".doc"}


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def run_review_job(job_id: str, file_path: str, journal: str, output_dir: Path):
    """Run the review pipeline in a background thread."""
    try:
        jobs[job_id]["status"] = "parsing"
        agent = AcademicRefereeAgent(output_dir=str(output_dir))
        agent.state.target_journal = journal
        agent.state.candidate_journals = [journal]

        # Parse paper
        parsed = agent.parse_paper(file_path)
        agent.state.parsed_paper = parsed
        agent.state.paper_path = file_path
        jobs[job_id]["title"] = parsed.get("title", "Unknown")
        jobs[job_id]["words"] = parsed.get("word_count", 0)
        jobs[job_id]["pages"] = parsed.get("page_count", 0)

        # Journal research
        jobs[job_id]["status"] = "researching"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            profile = loop.run_until_complete(agent.research_journal(journal))
            agent.state.journal_profile = profile
        finally:
            loop.close()

        # Check Claude CLI
        if not ClaudeRunner.is_available():
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = (
                "Claude CLI not found. Install Claude Code: https://claude.ai/code"
            )
            return

        # Run review
        jobs[job_id]["status"] = "reviewing"
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            review_content = loop.run_until_complete(agent.run_review())
        finally:
            loop.close()

        # Save report with timestamp to prevent overwrites
        paper_title = parsed.get("title", "untitled")
        safe_title = "".join(
            c if c.isalnum() or c in "- _" else "_" for c in paper_title[:50]
        )
        safe_journal = "".join(
            c if c.isalnum() or c in "- _" else "_" for c in journal[:30]
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_journal}_{safe_title}_{timestamp}.md"
        filepath = output_dir / filename
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(review_content)

        jobs[job_id]["status"] = "complete"
        jobs[job_id]["report_path"] = str(filepath)
        jobs[job_id]["report_name"] = filename

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
    finally:
        # Clean up uploaded file
        try:
            os.unlink(file_path)
        except OSError:
            pass


@app.route("/")
def index():
    """Main upload page."""
    reviews = []
    reviews_dir = settings.reviews_dir
    if reviews_dir.exists():
        for f in sorted(reviews_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            reviews.append(
                {
                    "name": f.name,
                    "size": f"{f.stat().st_size / 1024:.1f} KB",
                    "date": datetime.fromtimestamp(f.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )
    return render_template("index.html", reviews=reviews)


@app.route("/upload", methods=["POST"])
def upload():
    """Handle paper upload and start review."""
    journal = request.form.get("journal", "").strip()
    if not journal:
        flash("Please specify a target journal.", "error")
        return redirect(url_for("index"))

    file = request.files.get("paper")
    if not file or file.filename == "":
        flash("Please upload a paper file.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash(
            f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            "error",
        )
        return redirect(url_for("index"))

    # Save uploaded file to temp location
    suffix = Path(file.filename).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tempfile.gettempdir())
    file.save(tmp.name)
    tmp.close()

    # Create job
    job_id = uuid4().hex[:12]
    jobs[job_id] = {
        "status": "queued",
        "journal": journal,
        "filename": file.filename,
        "error": None,
        "report_path": None,
        "report_name": None,
        "title": None,
        "words": 0,
        "pages": 0,
        "started": datetime.now().strftime("%H:%M:%S"),
    }

    # Run in background thread
    output_dir = settings.reviews_dir
    thread = threading.Thread(
        target=run_review_job,
        args=(job_id, tmp.name, journal, output_dir),
        daemon=True,
    )
    thread.start()

    return redirect(url_for("job_status", job_id=job_id))


@app.route("/status/<job_id>")
def job_status(job_id):
    """Show job progress page."""
    job = jobs.get(job_id)
    if not job:
        flash("Job not found.", "error")
        return redirect(url_for("index"))
    return render_template("index.html", job=job, job_id=job_id, reviews=[])


@app.route("/api/status/<job_id>")
def api_status(job_id):
    """JSON endpoint for polling job status."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/download/<path:filename>")
def download(filename):
    """Download a review report."""
    filepath = settings.reviews_dir / filename
    if not filepath.exists():
        flash("Report not found.", "error")
        return redirect(url_for("index"))
    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
        mimetype="text/markdown",
    )


@app.route("/view/<path:filename>")
def view(filename):
    """View a review report in the browser."""
    filepath = settings.reviews_dir / filename
    if not filepath.exists():
        flash("Report not found.", "error")
        return redirect(url_for("index"))
    content = filepath.read_text(encoding="utf-8")
    return render_template("index.html", view_content=content, view_name=filename, reviews=[])


def run_server(host="127.0.0.1", port=5000, debug=False):
    """Start the Flask development server."""
    print(f"\n  myreferee web interface running at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug, threaded=True)

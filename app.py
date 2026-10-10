import json
import os
import shutil
import threading
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from converter import PHOTO_EXT, VIDEO_EXT, convert_file

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024**3  # reject uploads larger than 2 GB

JOBS_DIR = Path("jobs")

# Email is sent through Brevo's web API (port 443), because free Render
# instances block the SMTP ports that Gmail uses.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")  # must be verified in your Brevo account
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")


def send_email(to, subject, body):
    payload = {
        "sender": {"name": "Black & White", "email": SENDER_EMAIL},
        "to": [{"email": to}],
        "subject": subject,
        "textContent": body,
    }
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
            "accept": "application/json",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as e:
        print("Brevo error:", e.code, e.read().decode("utf-8", "ignore"))
        raise


def process_job(job_id, email, mode):
    job = JOBS_DIR / job_id
    in_dir, out_dir = job / "in", job / "out"
    out_dir.mkdir(exist_ok=True)
    try:
        done, failed = 0, 0
        for f in sorted(in_dir.iterdir()):
            try:
                if convert_file(f, out_dir, mode):
                    done += 1
                else:
                    failed += 1
            except Exception as e:
                print("Convert failed:", f.name, e)
                failed += 1

        zip_path = job / "result.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:
            for f in out_dir.iterdir():
                z.write(f, f.name)
        shutil.rmtree(in_dir, ignore_errors=True)  # delete the originals right away

        note = f"{done} file(s) converted." + (f" {failed} could not be converted." if failed else "")
        link = f"{BASE_URL}/download/{job_id}"
        send_email(
            email,
            "Your black and white files are ready",
            f"{note}\n\nDownload your zip here:\n{link}\n\n"
            "Please download it soon. The link may stop working after a while.",
        )
    except Exception as e:
        print("Job failed:", job_id, e)
        try:
            send_email(email, "Your conversion failed", "Something went wrong while converting your files. Please try again.")
        except Exception:
            pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    email = request.form.get("email", "").strip()
    mode = request.form.get("mode", "grayscale")
    files = [f for f in request.files.getlist("files") if f.filename]

    if "@" not in email or "." not in email:
        return jsonify(error="Enter a valid email address."), 400
    if not files:
        return jsonify(error="Choose at least one photo or video."), 400
    if not (BREVO_API_KEY and SENDER_EMAIL):
        return jsonify(error="The server's email isn't set up yet."), 500

    job_id = uuid.uuid4().hex
    in_dir = JOBS_DIR / job_id / "in"
    in_dir.mkdir(parents=True)
    saved = 0
    for i, f in enumerate(files):
        name = secure_filename(f.filename)
        if Path(name).suffix.lower() in PHOTO_EXT | VIDEO_EXT:
            f.save(in_dir / f"{i:04d}_{name}")
            saved += 1
    if not saved:
        shutil.rmtree(JOBS_DIR / job_id)
        return jsonify(error="None of those file types are supported."), 400

    # Convert in the background so the person doesn't have to wait on this page.
    threading.Thread(target=process_job, args=(job_id, email, mode), daemon=True).start()
    return jsonify(ok=True, count=saved)


@app.route("/download/<job_id>")
def download(job_id):
    job_id = secure_filename(job_id)
    return send_from_directory(JOBS_DIR / job_id, "result.zip", as_attachment=True)


if __name__ == "__main__":
 app.run(debug=True)
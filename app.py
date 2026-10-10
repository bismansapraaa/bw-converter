import os
import time
import uuid
import subprocess
import threading

from flask import Flask, request, jsonify, send_file, render_template, abort
from PIL import Image, ImageOps

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB upload limit

JOBS_DIR = "jobs"
os.makedirs(JOBS_DIR, exist_ok=True)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp", ".wmv", ".flv"}

# job_id -> {"status": "processing" | "done" | "error", "name": download name, "out": output path}
jobs = {}


def convert_video(input_path, output_path):
    """Turn a video black and white with ffmpeg, keeping the audio."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", "hue=s=0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "26",
        "-threads", "1",           # keeps memory low on the free tier
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1500:])


def convert_image(input_path, output_path, ext):
    """Turn a photo black and white with Pillow, keeping the same format."""
    img = Image.open(input_path)
    img = ImageOps.exif_transpose(img)   # fix phone photos that are rotated
    gray = img.convert("L")
    if ext in (".jpg", ".jpeg"):
        gray.save(output_path, "JPEG", quality=92)
    elif ext == ".png":
        gray.save(output_path, "PNG")
    elif ext == ".webp":
        gray.save(output_path, "WEBP", quality=92)
    else:
        gray.save(output_path, "PNG")


def run_job(job_id, input_path, output_path, kind, ext):
    try:
        if kind == "image":
            convert_image(input_path, output_path, ext)
        else:
            convert_video(input_path, output_path)
        jobs[job_id]["status"] = "done"
    except Exception as e:
        print("Conversion error:", e, flush=True)
        jobs[job_id]["status"] = "error"
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


def cleanup_loop():
    """Delete files older than 15 minutes so the disk does not fill up."""
    while True:
        time.sleep(300)
        now = time.time()
        for name in os.listdir(JOBS_DIR):
            path = os.path.join(JOBS_DIR, name)
            try:
                if now - os.path.getmtime(path) > 900:
                    os.remove(path)
            except OSError:
                pass


threading.Thread(target=cleanup_loop, daemon=True).start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No file received"}), 400

    base, ext = os.path.splitext(os.path.basename(file.filename))
    ext = ext.lower()
    if ext in IMAGE_EXTS:
        kind = "image"
    elif ext in VIDEO_EXTS:
        kind = "video"
    else:
        return jsonify({"error": "Unsupported file type"}), 400

    job_id = uuid.uuid4().hex
    input_path = os.path.join(JOBS_DIR, job_id + "_in")
    out_ext = ".mp4" if kind == "video" else (ext if ext in (".jpg", ".jpeg", ".png", ".webp") else ".png")
    output_path = os.path.join(JOBS_DIR, job_id + "_bw" + out_ext)
    file.save(input_path)

    jobs[job_id] = {
        "status": "processing",
        "name": (base or "file") + "_bw" + out_ext,
        "out": output_path,
    }
    threading.Thread(
        target=run_job, args=(job_id, input_path, output_path, kind, ext), daemon=True
    ).start()
    return jsonify({"job_id": job_id, "kind": kind})


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "error"})
    return jsonify({"status": job["status"]})


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job or job["status"] != "done" or not os.path.exists(job["out"]):
        abort(404)
    return send_file(job["out"], as_attachment=True, download_name=job["name"])


if __name__ == "__main__":
    app.run(debug=True)
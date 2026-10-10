
import os
import re
import time
import uuid
import zipfile
import subprocess
import threading
 
from flask import Flask, request, jsonify, send_file, render_template, abort
from PIL import Image, ImageOps
 
app = Flask(__name__)
# Each request only carries one small chunk, so big videos never hit a size limit.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
 
JOBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs")
os.makedirs(JOBS_DIR, exist_ok=True)
 
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".3gp", ".wmv", ".flv"}
ID_RE = re.compile(r"^[a-f0-9]{32}$")
 
# Only one video converts at a time so the free tier does not run out of memory.
video_lock = threading.Semaphore(1)
image_lock = threading.Semaphore(2)
 
# job_id -> {"status": "processing" | "done" | "error", "name": str, "out": str}
jobs = {}
 
 
def convert_video(input_path, output_path):
    """Turn a video black and white with ffmpeg, keeping the audio."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-map", "0:v:0", "-map", "0:a?",
        "-vf", "hue=s=0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-threads", "1",
        "-c:a", "aac",
        "-max_muxing_queue_size", "1024",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1500:])
 
 
def convert_image(input_path, output_path, ext):
    """Turn a photo black and white with Pillow, keeping the same format."""
    img = Image.open(input_path)
    img = ImageOps.exif_transpose(img)
    gray = img.convert("L")
    if ext in (".jpg", ".jpeg"):
        gray.save(output_path, "JPEG", quality=92)
    elif ext == ".webp":
        gray.save(output_path, "WEBP", quality=92)
    else:
        gray.save(output_path, "PNG")
 
 
def run_job(job_id, input_path, output_path, kind, ext):
    lock = video_lock if kind == "video" else image_lock
    try:
        with lock:
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
    """Delete files older than 60 minutes so the disk does not fill up."""
    while True:
        time.sleep(300)
        now = time.time()
        for name in os.listdir(JOBS_DIR):
            path = os.path.join(JOBS_DIR, name)
            try:
                if now - os.path.getmtime(path) > 3600:
                    os.remove(path)
            except OSError:
                pass
 
 
threading.Thread(target=cleanup_loop, daemon=True).start()
 
 
@app.route("/")
def index():
    return render_template("index.html")
 
 
@app.route("/chunk", methods=["POST"])
def chunk():
    """Receives a file in small pieces. After the last piece, conversion starts."""
    upload_id = request.form.get("upload_id", "")
    filename = request.form.get("filename", "")
    try:
        index = int(request.form.get("index", ""))
        total = int(request.form.get("total", ""))
    except ValueError:
        return jsonify({"error": "Bad request"}), 400
    piece = request.files.get("chunk")
 
    if not ID_RE.match(upload_id) or piece is None or index < 0 or total < 1 or index >= total:
        return jsonify({"error": "Bad request"}), 400
 
    base, ext = os.path.splitext(os.path.basename(filename))
    ext = ext.lower()
    if ext in IMAGE_EXTS:
        kind = "image"
    elif ext in VIDEO_EXTS:
        kind = "video"
    else:
        return jsonify({"error": "Unsupported file type"}), 400
 
    part_path = os.path.join(JOBS_DIR, upload_id + "_part")
    with open(part_path, "wb" if index == 0 else "ab") as f:
        f.write(piece.read())
 
    if index < total - 1:
        return jsonify({"received": index})
 
    # Last piece: start converting.
    input_path = os.path.join(JOBS_DIR, upload_id + "_in")
    os.replace(part_path, input_path)
    out_ext = ".mp4" if kind == "video" else (ext if ext in (".jpg", ".jpeg", ".png", ".webp") else ".png")
    output_path = os.path.join(JOBS_DIR, upload_id + "_bw" + out_ext)
    jobs[upload_id] = {
        "status": "processing",
        "name": (base or "file") + "_bw" + out_ext,
        "out": output_path,
    }
    threading.Thread(
        target=run_job, args=(upload_id, input_path, output_path, kind, ext), daemon=True
    ).start()
    return jsonify({"job_id": upload_id})
 
 
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
 
 
@app.route("/zip")
def zip_download():
    """Bundle several finished files into one zip."""
    ids = [i for i in request.args.get("ids", "").split(",") if ID_RE.match(i)]
    ready = [jobs[i] for i in ids if i in jobs and jobs[i]["status"] == "done" and os.path.exists(jobs[i]["out"])]
    if not ready:
        abort(404)
 
    zip_path = os.path.join(JOBS_DIR, uuid.uuid4().hex + "_bundle.zip")
    used = set()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:
        for job in ready:
            name = job["name"]
            n = 1
            while name in used:
                stem, ext = os.path.splitext(job["name"])
                name = f"{stem}_{n}{ext}"
                n += 1
            used.add(name)
            z.write(job["out"], name)
    return send_file(zip_path, as_attachment=True, download_name="black_and_white.zip")
 
 
if __name__ == "__main__":
    app.run(debug=True)
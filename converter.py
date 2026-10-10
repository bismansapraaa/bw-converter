#Converts photos and videos to black and white.
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def convert_photo(src, dst, mode="grayscale", threshold=128):
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)  # fixes phone photos that would come out sideways
    gray = img.convert("L")
    if mode == "binary":
        gray = gray.point(lambda p: 255 if p > threshold else 0, mode="1")
    gray.save(dst)


def convert_video(src, dst):
    # ffmpeg's "hue=s=0" sets color saturation to zero, which makes every frame gray.
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-vf", "hue=s=0", "-pix_fmt", "yuv420p", str(dst)],
        check=True,
        capture_output=True,
    )


def convert_file(src, out_dir, mode="grayscale"):
    """Converts one file. Returns the output path, or None if the type isn't supported."""
    src, out_dir = Path(src), Path(out_dir)
    ext = src.suffix.lower()
    if ext in PHOTO_EXT:
        dst = out_dir / src.name
        convert_photo(src, dst, mode)
    elif ext in VIDEO_EXT:
        dst = out_dir / (src.stem + ".mp4")
        convert_video(src, dst)
    else:
        return None
    return dst


def convert_folder(in_dir, out_dir, mode="grayscale"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in Path(in_dir).iterdir() if p.is_file())
    for i, f in enumerate(files, 1):
        try:
            result = convert_file(f, out_dir, mode)
            print(f"[{i}/{len(files)}] {f.name}: {'done' if result else 'skipped (unsupported type)'}")
        except Exception as e:
            print(f"[{i}/{len(files)}] {f.name}: FAILED ({e})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: python3 converter.py input_folder output_folder [grayscale|binary]")
    convert_folder(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "grayscale")


# **Title: Black & White Image and Video Converter**


## **1. Methodology**
<img width="1700" height="300" alt="methodology" src="https://github.com/user-attachments/assets/326f3ccf-9f98-4cd5-8b5f-dd6b3e962bd4" />


## **2. Description**
- Supported photo types = 8 extensions (JPG, JPEG, PNG, WebP, BMP, GIF, TIFF, TIF)
- Supported video types = 9 extensions (MP4, MOV, AVI, MKV, WebM, M4V, 3GP, WMV, FLV)
- Photo conversion = Pillow, grayscale ("L" mode), with phone photo rotation (EXIF) fixed
- Video conversion = ffmpeg (hue=s=0 filter), saved as MP4 (H.264 video, AAC audio)
- Technology = Python, Flask, Pillow, ffmpeg, Gunicorn, Docker
- Hosting = Render (free instance)
- Other information: one video and two photos convert at a time, so the small free server does not run out of memory. Files are stored for about 60 minutes only.


## **3. Input / Output**

| Test Input | Expected Output | Actual Output | Result |
|------------|-----------------|---------------|--------|
| photo1.jpg (JPG photo) | Grayscale JPG | Grayscale JPG | ✔ |
| photo2.png (PNG photo) | Grayscale PNG | Grayscale PNG | ✔ |
| Phone photo, portrait | Grayscale, upright | Grayscale, upright | ✔ |
| clip.mp4 (MP4 video) | Black and white MP4 with audio | Black and white MP4 with audio | ✔ |
| 10 photos selected together | All converted, downloaded as one zip | All converted, downloaded as one zip | ✔ |
| notes.txt (unsupported file) | Rejected with an error | Rejected with an error | ✘ |


## **4. Live link**
https://bw-converter.onrender.com


## **5. Screenshot of the Interface**
<img width="838" height="431" alt="Screenshot 2026-10-10 at 4 44 26 PM" src="https://github.com/user-attachments/assets/eda7db82-267b-44c1-9510-36875a622f59" />

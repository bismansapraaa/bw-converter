
# **Title: Black & White Image and Video Converter**


## **1. Methodology**
<img width="1700" height="300" alt="methodology" src="https://github.com/user-attachments/assets/326f3ccf-9f98-4cd5-8b5f-dd6b3e962bd4" />


## **2. Description**
- Supported photo types = 8 extensions (JPG, JPEG, PNG, WebP, BMP, GIF, TIFF, TIF)
- Supported video types = 9 extensions (MP4, MOV, AVI, MKV, WebM, M4V, 3GP, WMV, FLV)
- Photo conversion = Pillow, grayscale ("L" mode), with phone photo rotation (EXIF) fixed
- Video conversion = ffmpeg (hue=s=0 filter), saved as MP4 (H.264 video, AAC audio)
- Technology = Python, Flask, Pillow, ffmpeg, Docker
- Hosting = Render (free instance)
- Other information: one video and two photos convert at a time, so the small free server does not run out of memory. Files are stored for about 60 minutes only.


## **3. Input / Output**

<table>
  <tr>
    <th align="center">Original Image</th>
    <th align="center">Black & White Image</th>
  </tr>
  <tr>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/e3ba4945-df01-45fb-ae2f-6387555219fe"
           width="240" alt="Original Image" />
    </td>
    <td align="center">
      <img src="https://github.com/user-attachments/assets/53f9fc99-9118-4637-9534-35a522c62a6b"
           width="240" alt="Black and White Image" />
    </td>
  </tr>
</table>


## **4. Live link**
 https://bw-converter.onrender.com


## **5. Screenshot of the Interface**
<img width="1005" height="662" alt="Screenshot 2026-10-10 at 5 08 16 PM" src="https://github.com/user-attachments/assets/65a17a94-9cc8-46ed-95ae-5b077471b4b8" />


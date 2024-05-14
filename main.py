from fastapi import FastAPI, UploadFile, File, Form, Query, Response, HTTPException
import cv2
import numpy as np
import logging
import qrcode
from io import BytesIO
from uuid import uuid4
from PIL import Image
import re

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Global variable to store the most recently generated QR code
generated_qr_image = None

def preprocess_image(image):
    try:
        resized_image = cv2.resize(image, (800, 600))
        gray_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
        equalized_image = cv2.equalizeHist(gray_image)
        return equalized_image
    except Exception as e:
        logging.error(f"Error in preprocessing image: {str(e)}")
        return None

def decode_qr_code(image):
    try:
        detector = cv2.QRCodeDetector()
        data, vertices_array, binary_qrcode = detector.detectAndDecode(image)
        if vertices_array is not None:
            logging.info(f"Decoded QR code data: {data}")
            return data
        else:
            logging.error("No QR code found.")
            return "No QR code found."
    except Exception as e:
        logging.error(f"Error decoding QR code: {str(e)}")
        return "Error decoding QR code."

def generate_qr_code(data):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_data = BytesIO()
        img.save(img_data, format="PNG")
        img_data.seek(0)
        return img_data.getvalue()
    except Exception as e:
        logging.error(f"Error generating QR code: {str(e)}")
        return None

def is_valid_url(url):
    regex = re.compile(
        r"^(?:http|https)://[^/\s]+(?:/[^/\s]*)*$"
    )
    return re.match(regex, url)

def is_valid_email(email):
    regex = re.compile(
        r"^[\w\.-]+@[\w\.-]+\.\w+$"
    )
    return re.match(regex, email)

def is_valid_mobile_number(mobile_number):
    regex = re.compile(
        r"^[0-9]{10}$"
    )
    return re.match(regex, mobile_number)

@app.post("/qr_to_link")
async def qr_to_link(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Could not decode image")
        
        preprocessed_image = preprocess_image(image)
        if preprocessed_image is None:
            raise ValueError("Error in preprocessing image")
        
        url = decode_qr_code(preprocessed_image)
        if url.startswith("http"):
            return {"url": url}
        else:
            return {"error": url}
    except Exception as e:
        logging.error(f"Error decoding QR code: {str(e)}")
        return {"error": "An error occurred while decoding the QR code."}

@app.post("/generate_qr")
async def generate_qr(url: str = Query(...)):
    if not is_valid_url(url):
        return Response(content="Invalid URL provided", status_code=400)

    global generated_qr_image
    generated_qr_image = generate_qr_code(url)
    if generated_qr_image is None:
        return Response(content="Error generating QR code", status_code=500)
    return Response(content=generated_qr_image, media_type="image/png")

@app.post("/email_to_qr")
async def email_to_qr(email: str = Form(...)):
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email address provided")

    global generated_qr_image
    generated_qr_image = generate_qr_code(email)
    if generated_qr_image is None:
        return Response(content="Error generating QR code", status_code=500)
    return Response(content=generated_qr_image, media_type="image/png")

@app.post("/mobile_to_qr")
async def mobile_to_qr(mobile_number: str = Form(...)):
    if not is_valid_mobile_number(mobile_number):
        raise HTTPException(status_code=400, detail="Invalid mobile number provided")

    global generated_qr_image
    generated_qr_image = generate_qr_code(mobile_number)
    if generated_qr_image is None:
        return Response(content="Error generating QR code", status_code=500)
    return Response(content=generated_qr_image, media_type="image/png")

@app.get("/download_qr")
async def download_qr():
    global generated_qr_image

    if not generated_qr_image:
        raise HTTPException(status_code=404, detail="No QR code generated yet")

    headers = {
        "Content-Disposition": "attachment; filename=qr_code.png"
    }

    return Response(content=generated_qr_image, media_type="image/png", headers=headers)

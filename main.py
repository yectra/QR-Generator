from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
import qrcode
from io import BytesIO
import zipfile
import logging
import cv2
import numpy as np
import re

app = FastAPI()

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
        data, vertices_array, _ = detector.detectAndDecode(image)
        if vertices_array is not None:
            logging.info(f"Decoded QR code data: {data}")
            return data
        else:
            logging.warning("No QR code found.")
            return None
    except Exception as e:
        logging.error(f"Error decoding QR code: {str(e)}")
        raise HTTPException(status_code=400, detail="Error decoding QR code.")

def is_valid_url(url):
    regex = re.compile(
        r"^(?:http|https)://[^/\s]+(?:/[^/\s]*)*$"
    )
    return bool(re.match(regex, url))

def is_valid_email(email):
    regex = re.compile(
        r"^[\w\.-]+@[\w\.-]+\.\w+$"
    )
    return bool(re.match(regex, email))

def is_valid_mobile_number(mobile_number):
    regex = re.compile(
        r"^[0-9]{10}$"
    )
    return bool(re.match(regex, mobile_number))

def generate_qr_code(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

@app.post("/qr_to_link")
async def qr_to_link(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(status_code=400, detail="Could not decode image")
        
        preprocessed_image = preprocess_image(image)
        if preprocessed_image is None:
            raise HTTPException(status_code=400, detail="Error in preprocessing image")
        
        url = decode_qr_code(preprocessed_image)
        if url is None:
            raise HTTPException(status_code=404, detail="No QR code found in the image")
        if is_valid_url(url):
            return {"url": url}
        else:
            return {"error": "Decoded data is not a valid URL"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error processing QR code: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the QR code.")

@app.post("/generate_qr_codes/")
async def generate_qr_codes(urls: List[str] = Query(...)):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for i, url in enumerate(urls):
            if not is_valid_url(url):
                raise HTTPException(status_code=400, detail=f"Invalid URL: {url}")
            qr_code = generate_qr_code(url)
            zip_file.writestr(f'qr_code_url_{i+1}.png', qr_code)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/zip", headers={
        'Content-Disposition': 'attachment; filename="qr_codes.zip"'
    })

@app.post("/generate_qr_codes_phone/")
async def generate_qr_codes_phone(phone_numbers: List[str] = Query(...)):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for i, phone_number in enumerate(phone_numbers):
            if not is_valid_mobile_number(phone_number):
                raise HTTPException(status_code=400, detail=f"Invalid phone number: {phone_number}")
            qr_code = generate_qr_code(f"tel:{phone_number}")
            zip_file.writestr(f'qr_code_phone_{i+1}.png', qr_code)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/zip", headers={
        'Content-Disposition': 'attachment; filename="qr_codes_phone.zip"'
    })

@app.post("/generate_qr_codes_email/")
async def generate_qr_codes_email(emails: List[str] = Query(...)):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for i, email in enumerate(emails):
            if not is_valid_email(email):
                raise HTTPException(status_code=400, detail=f"Invalid email: {email}")
            qr_code = generate_qr_code(f"mailto:{email}")
            zip_file.writestr(f'qr_code_email_{i+1}.png', qr_code)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/zip", headers={
        'Content-Disposition': 'attachment; filename="qr_codes_email.zip"'
    })

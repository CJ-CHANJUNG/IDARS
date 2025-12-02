# OCR Inspector Backend Skeleton
# Author: Product Manager (2025-07-23)
# Description: FastAPI 기반 OCR Inspector 백엔드 뼈대
# 주요 기능: PDF→HTML 변환, OCR, 엑셀 파싱
#
# ⚠️ 실제 구현은 각 함수에 추가 예정

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from typing import List

import shutil
import tempfile
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
import pandas as pd
import io
import requests

app = FastAPI(title="OCR Inspector API", description="PDF→HTML, OCR, Excel Parsing API for Inspector UI")

# CORS 허용 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ✅ PDF → HTML 변환 (PyMuPDF)
@app.post("/api/pdf-to-html")
async def pdf_to_html(file: UploadFile = File(...)):
    """
    PDF 파일을 받아 HTML로 변환하여 반환합니다.
    PyMuPDF(fitz) 사용, 한글/표 등 레이아웃 보존이 우수함.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        doc = fitz.open(tmp_path)
        html = ""
        for page in doc:
            html += page.get_text("html")
        doc.close()
        os.remove(tmp_path)
        return HTMLResponse(html)
    except Exception as e:
        return HTMLResponse(f"<div>PDF→HTML 변환 실패: {e}</div>", status_code=500)

# ✅ OCR (Tesseract, Google Vision fallback)
@app.post("/api/ocr")
async def ocr_pdf(file: UploadFile = File(...)):
    """
    PDF 파일을 받아 OCR 텍스트를 반환합니다.
    1차: Tesseract, 실패시 2차: Google Vision API
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        # PDF → 이미지 변환
        images = convert_from_path(tmp_path)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img, lang="kor+eng") + "\n"
        os.remove(tmp_path)
        return JSONResponse({"text": text.strip()})
    except Exception as e:ㅃ
        # Tesseract 실패시 Google Vision API fallback
        try:
            # Google Vision API 호출 예시 (API Key 필요)
            # 실제 사용시 아래 API_KEY를 환경변수 등으로 관리할 것
            API_KEY = os.getenv("AIzaSyADYNGhB3UVSeBK2QOlAjOylOuBufbNbp4", "")
            if not API_KEY:
                raise Exception("Google Vision API Key 미설정")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                file.file.seek(0)
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
            images = convert_from_path(tmp_path)
            texts = []
            for img in images:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                # Google Vision API 요청
                url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
                data = {
                    "requests": [{
                        "image": {"content": img_bytes.decode("latin1").encode("base64").decode()},
                        "features": [{"type": "TEXT_DETECTION"}]
                    }]
                }
                resp = requests.post(url, json=data)
                result = resp.json()
                text = result['responses'][0].get('fullTextAnnotation', {}).get('text', '')
                texts.append(text)
            os.remove(tmp_path)
            return JSONResponse({"text": "\n".join(texts)})
        except Exception as e2:
            return JSONResponse({"error": f"OCR 실패: {e} / Google Vision 실패: {e2}"}, status_code=500)

# ✅ 엑셀 파싱 (pandas)
@app.post("/api/parse-excel")
async def parse_excel(file: UploadFile = File(...)):
    """
    엑셀 파일을 받아 주요 전표 데이터를 추출하여 반환합니다.
    pandas로 DataFrame 변환 후, 주요 컬럼만 JSON으로 반환
    """
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        # 주요 컬럼 자동 추출(샘플: 전표번호, 금액, 거래처 등)
        # 실제 데이터에 맞게 컬럼명 조정 필요
        key_cols = [col for col in df.columns if any(k in col for k in ["전표", "금액", "거래처", "고객", "일자", "품목"])]
        if not key_cols:
            key_cols = df.columns.tolist()  # fallback: 전체 컬럼
        # 모든 값을 str로 변환 (Timestamp 등 직렬화 오류 방지)
        rows = df[key_cols].fillna("").astype(str).to_dict(orient="records")
        return JSONResponse({"rows": rows})
    except Exception as e:
        return JSONResponse({"error": f"엑셀 파싱 실패: {e}"}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
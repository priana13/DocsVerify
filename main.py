from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image
import pdf2image
import io
import re
from rapidfuzz import fuzz
from typing import Optional
import uvicorn

app = FastAPI(title="Akta Name Validation API", version="1.0.0")

# CORS middleware untuk akses dari frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ganti dengan domain frontend Anda di production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Konfigurasi Tesseract (sesuaikan path jika perlu)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Linux

def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocessing gambar untuk meningkatkan akurasi OCR"""
    # Convert ke grayscale
    image = image.convert('L')
    
    # Increase contrast
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)
    
    return image

def extract_text_from_image(image: Image.Image) -> str:
    """Extract text dari gambar menggunakan Tesseract OCR"""
    # Preprocessing
    processed_image = preprocess_image(image)
    
    # OCR dengan config untuk bahasa Indonesia
    custom_config = r'--oem 3 --psm 6 -l ind+eng'
    text = pytesseract.image_to_string(processed_image, config=custom_config)
    
    return text

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text dari PDF"""
    try:
        # Convert PDF ke images
        images = pdf2image.convert_from_bytes(pdf_bytes)
        
        all_text = []
        for image in images:
            text = extract_text_from_image(image)
            all_text.append(text)
        
        return "\n".join(all_text)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing PDF: {str(e)}")

def clean_name(name: str) -> str:
    """Bersihkan nama dari karakter tidak perlu"""
    # Hapus karakter khusus, hanya pertahankan huruf dan spasi
    name = re.sub(r'[^a-zA-Z\s]', '', name)
    # Hapus spasi berlebih
    name = ' '.join(name.split())
    # Uppercase untuk normalisasi
    return name.upper().strip()

def extract_names_from_text(text: str) -> list:
    """Extract kemungkinan nama dari text akta"""
    # Pattern untuk mencari nama (bisa disesuaikan dengan format akta)
    # Contoh: mencari text setelah kata kunci seperti "Nama:", "nama lengkap:", etc
    patterns = [
        r'(?:Nama|NAMA)[\s:]+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)',
        r'(?:Nama Lengkap|NAMA LENGKAP)[\s:]+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)',
        r'\b([A-Z][a-z]+\s[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b'  # Pattern umum nama
    ]
    
    names = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        names.extend(matches)
    
    # Deduplicate dan clean
    names = list(set([clean_name(name) for name in names if len(name) > 5]))
    
    return names

def validate_name(input_name: str, extracted_names: list, threshold: int = 80) -> dict:
    """Validasi nama user dengan nama yang diekstrak dari akta"""
    input_name_clean = clean_name(input_name)
    
    best_match = {
        "is_valid": False,
        "matched_name": None,
        "similarity_score": 0,
        "threshold": threshold
    }
    
    for extracted_name in extracted_names:
        # Hitung similarity menggunakan beberapa metode
        ratio = fuzz.ratio(input_name_clean, extracted_name)
        partial_ratio = fuzz.partial_ratio(input_name_clean, extracted_name)
        token_sort_ratio = fuzz.token_sort_ratio(input_name_clean, extracted_name)
        
        # Ambil score tertinggi
        max_score = max(ratio, partial_ratio, token_sort_ratio)
        
        if max_score > best_match["similarity_score"]:
            best_match["similarity_score"] = max_score
            best_match["matched_name"] = extracted_name
            best_match["is_valid"] = max_score >= threshold
    
    return best_match

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Akta Name Validation API is running",
        "version": "1.0.0"
    }

@app.post("/validate-name")
async def validate_name_endpoint(
    file: UploadFile = File(..., description="Akta file (image/PDF)"),
    name: str = Form(..., description="Nama yang akan divalidasi"),
    threshold: Optional[int] = Form(80, description="Threshold similarity (0-100)")
):
    """
    Endpoint untuk validasi nama dari akta
    
    Parameters:
    - file: File akta (JPG, PNG, PDF)
    - name: Nama yang akan divalidasi
    - threshold: Ambang batas similarity (default: 80)
    
    Returns:
    - is_valid: Boolean apakah nama valid
    - matched_name: Nama yang cocok di akta
    - similarity_score: Skor kemiripan (0-100)
    - extracted_text: Text yang diekstrak dari akta
    - all_names_found: Semua nama yang ditemukan di akta
    """
    try:
        # Validasi input
        if not name or len(name.strip()) < 2:
            raise HTTPException(status_code=400, detail="Nama tidak valid")
        
        if threshold < 0 or threshold > 100:
            raise HTTPException(status_code=400, detail="Threshold harus antara 0-100")
        
        # Baca file
        file_bytes = await file.read()
        
        # Deteksi tipe file dan extract text
        if file.content_type == "application/pdf":
            extracted_text = extract_text_from_pdf(file_bytes)
        elif file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
            image = Image.open(io.BytesIO(file_bytes))
            extracted_text = extract_text_from_image(image)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Format file tidak didukung. Gunakan JPG, PNG, atau PDF"
            )
        
        # Extract nama dari text
        extracted_names = extract_names_from_text(extracted_text)
        
        if not extracted_names:
            return JSONResponse(
                status_code=200,
                content={
                    "is_valid": False,
                    "matched_name": None,
                    "similarity_score": 0,
                    "threshold": threshold,
                    "message": "Tidak ada nama yang dapat diekstrak dari akta",
                    "extracted_text": extracted_text[:500],  # Preview text
                    "all_names_found": []
                }
            )
        
        # Validasi nama
        result = validate_name(name, extracted_names, threshold)
        
        return JSONResponse(
            status_code=200,
            content={
                **result,
                "input_name": name,
                "extracted_text": extracted_text[:500],  # Preview text
                "all_names_found": extracted_names
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/extract-text")
async def extract_text_endpoint(
    file: UploadFile = File(..., description="Akta file (image/PDF)")
):
    """
    Endpoint untuk extract text dari akta (untuk debugging)
    
    Parameters:
    - file: File akta (JPG, PNG, PDF)
    
    Returns:
    - extracted_text: Text lengkap yang diekstrak
    - extracted_names: Nama-nama yang ditemukan
    """
    try:
        file_bytes = await file.read()
        
        if file.content_type == "application/pdf":
            extracted_text = extract_text_from_pdf(file_bytes)
        elif file.content_type in ["image/jpeg", "image/jpg", "image/png"]:
            image = Image.open(io.BytesIO(file_bytes))
            extracted_text = extract_text_from_image(image)
        else:
            raise HTTPException(
                status_code=400,
                detail="Format file tidak didukung"
            )
        
        extracted_names = extract_names_from_text(extracted_text)
        
        return {
            "extracted_text": extracted_text,
            "extracted_names": extracted_names,
            "total_names_found": len(extracted_names)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
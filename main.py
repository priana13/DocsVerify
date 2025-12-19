from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image
import pdf2image
import io
import re
from rapidfuzz import fuzz, process
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
    """Bersihkan nama dari karakter tidak perlu dan kata-kata umum."""
    # Hapus karakter khusus, hanya pertahankan huruf dan spasi
    name = re.sub(r'[^a-zA-Z\s]', '', name)
    # Uppercase untuk normalisasi
    name = name.upper()

    # Daftar stopwords yang umum di dokumen, diurutkan dari panjang ke pendek
    stopwords = ["NAMA LENGKAP", "BORN", "NAMA", "NAME"]

    # Hapus stopwords (sebagai kata utuh)
    for word in stopwords:
        name = re.sub(r'\b' + word + r'\b', '', name)

    # Hapus spasi berlebih yang mungkin timbul
    name = ' '.join(name.split())
    return name.strip()

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

def validate_name(input_name: str, extracted_text: str, threshold: int = 90) -> dict:
    """Validasi nama user dengan mencocokkannya ke frasa dalam teks dokumen."""
    input_name_clean = clean_name(input_name)

    if not input_name_clean:
        return {"is_valid": False, "matched_name": None, "similarity_score": 0, "threshold": threshold}

    extracted_text_clean = " ".join(extracted_text.split()).upper()
    words = extracted_text_clean.split()
    input_len = len(input_name_clean.split())

    # Buat daftar frasa kandidat dari teks dokumen
    # dengan panjang yang mirip dengan nama input
    min_len = max(1, input_len - 2)  # Toleransi 2 kata lebih pendek
    max_len = input_len + 2  # Toleransi 2 kata lebih panjang
    
    choices = set() # Gunakan set untuk hindari duplikat
    for n in range(min_len, max_len + 1):
        if len(words) >= n:
            for i in range(len(words) - n + 1):
                choices.add(" ".join(words[i:i+n]))

    if not choices:
        return {"is_valid": False, "matched_name": None, "similarity_score": 0, "threshold": threshold}

    # Cari kandidat terbaik menggunakan fuzz.ratio yang lebih ketat
    best_match = process.extractOne(input_name_clean, list(choices), scorer=fuzz.ratio)

    if best_match:
        matched_name, score, _ = best_match
        is_valid = score >= threshold
        return {
            "is_valid": is_valid,
            "matched_name": matched_name if is_valid else None,
            "similarity_score": round(score),
            "threshold": threshold
        }
    
    return {"is_valid": False, "matched_name": None, "similarity_score": 0, "threshold": threshold}

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
    threshold: Optional[int] = Form(90, description="Threshold similarity (0-100)")
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
        
        # Validasi nama langsung ke text yang diekstrak
        result = validate_name(name, extracted_text, threshold)
        
        # (Opsional) Tetap extract nama untuk ditampilkan di response
        extracted_names = extract_names_from_text(extracted_text)
        
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
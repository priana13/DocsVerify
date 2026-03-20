from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pytesseract
from PIL import Image
import pdf2image
import io
import re
from datetime import datetime
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

def extract_text_from_upload(file_bytes: bytes, content_type: Optional[str]) -> str:
    """Extract text dari file upload (PDF/image)."""
    if content_type == "application/pdf":
        return extract_text_from_pdf(file_bytes)
    if content_type in ["image/jpeg", "image/jpg", "image/png"]:
        image = Image.open(io.BytesIO(file_bytes))
        return extract_text_from_image(image)

    raise HTTPException(
        status_code=400,
        detail="Format file tidak didukung. Gunakan JPG, PNG, atau PDF"
    )

def find_first_match(patterns: list, text: str, flags: int = re.IGNORECASE | re.MULTILINE):
    """Cari match pertama dari daftar regex patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            for group in match.groups():
                if group and group.strip():
                    return group.strip()
    return None

def clean_extracted_name(value: Optional[str]) -> Optional[str]:
    """Normalisasi nilai nama hasil ekstraksi."""
    if not value:
        return None

    value = re.split(r'(?i)\b(?:bank|nominal|jumlah|total|amount|tanggal|jam|waktu|rekening|rek)\b', value)[0]
    cleaned = re.sub(r'[^A-Za-z\s\.-]', '', value)
    cleaned = ' '.join(cleaned.split())

    if len(cleaned) < 3:
        return None
    return cleaned

def normalize_nominal(value: Optional[str]) -> Optional[str]:
    """Normalisasi nominal jadi angka murni tanpa simbol/pemisah."""
    if not value:
        return None

    cleaned = re.sub(r'(?i)rp', '', value)
    cleaned = re.sub(r'[^\d]', '', cleaned)
    return cleaned if cleaned else None

def normalize_tanggal(value: Optional[str]) -> Optional[str]:
    """Normalisasi tanggal ke format YYYY-MM-DD."""
    if not value:
        return None

    cleaned = value.strip().lower()
    cleaned = re.sub(r'\s+', ' ', cleaned)

    month_map = {
        "januari": "january",
        "jan": "january",
        "februari": "february",
        "feb": "february",
        "maret": "march",
        "mar": "march",
        "april": "april",
        "apr": "april",
        "mei": "may",
        "may": "may",
        "juni": "june",
        "jun": "june",
        "juli": "july",
        "jul": "july",
        "agustus": "august",
        "agu": "august",
        "agt": "august",
        "aug": "august",
        "september": "september",
        "sep": "september",
        "oktober": "october",
        "okt": "october",
        "oct": "october",
        "november": "november",
        "nov": "november",
        "desember": "december",
        "des": "december",
        "dec": "december"
    }

    for local_month, en_month in month_map.items():
        cleaned = re.sub(rf'\b{local_month}\b', en_month, cleaned)

    cleaned = cleaned.replace('.', '/').replace('-', '/')

    if re.match(r'^\d{1,2}/\d{1,2}/\d{2,4}$', cleaned):
        day, month, year = cleaned.split('/')
        if len(year) == 2:
            year = f"20{year}"
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return None

    for fmt in ["%d %B %Y", "%d %b %Y", "%d %B %y", "%d %b %y"]:
        try:
            dt = datetime.strptime(cleaned, fmt)
            if dt.year < 100:
                dt = dt.replace(year=2000 + dt.year)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None

def normalize_bank(value: Optional[str]) -> Optional[str]:
    """Normalisasi nama bank ke uppercase singkat."""
    if not value:
        return None

    cleaned = re.sub(r'[^A-Za-z\s\.-]', ' ', value)
    cleaned = ' '.join(cleaned.split()).upper()
    return cleaned if cleaned else None

def parse_transfer_proof_fields(text: str) -> dict:
    """Extract field penting dari OCR bukti transfer."""
    text_single_line = re.sub(r'\s+', ' ', text)

    tanggal_patterns = [
        r'(?:tanggal|tgl|date)\s*[:\-]?\s*((?:\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})|(?:\d{1,2}\s+[A-Za-z]+\s+\d{2,4}))',
        r'\b(\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4})\b',
        r'\b(\d{1,2}\s+[A-Za-z]+\s+\d{2,4})\b'
    ]

    jam_patterns = [
        r'(?:jam|waktu|time)\s*[:\-]?\s*(\d{1,2}[:\.]\d{2}(?::\d{2})?)',
        r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b',
        r'\b(\d{1,2}\.\d{2}(?::\d{2})?)\b'
    ]

    nominal_patterns = [
        r'(?:jumlah|nominal|total|amount)\s*[:\-]?\s*(Rp\s?[\d\.,]+)',
        r'(Rp\s?[\d\.,]+)',
        r'\b([\d]{1,3}(?:\.[\d]{3})+(?:,[\d]{1,2})?)\b'
    ]

    nama_rekening_sumber_patterns_multiline = [
        r'(?im)^\s*(?:nama\s+rekening\s+sumber|rekening\s+sumber|nama\s+rek(?:ening)?\s+sumber)\s*[:\-]?\s*([^\n\r]+)',
        r'(?im)^\s*(?:from\s+account\s+name|source\s+account\s+name)\s*[:\-]?\s*([^\n\r]+)'
    ]

    nama_rekening_sumber_patterns_single_line = [
        r'(?:nama\s+rekening\s+sumber|rekening\s+sumber|nama\s+rek(?:ening)?\s+sumber)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.-]{2,})',
        r'(?:from\s+account\s+name|source\s+account\s+name)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.-]{2,})'
    ]

    bank_patterns = [
        r'(?:bank\s+tujuan|bank\s+penerima|bank\s+pengirim|bank)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.-]{1,})',
        r'\b(BCA|BRI|BNI|MANDIRI|CIMB\s*NIAGA|PERMATA|DANAMON|OCBC|BTN|BTPN|BSI)\b'
    ]

    tanggal = normalize_tanggal(find_first_match(tanggal_patterns, text_single_line))
    jam = find_first_match(jam_patterns, text_single_line)
    nominal = normalize_nominal(find_first_match(nominal_patterns, text_single_line))
    nama_candidate = find_first_match(nama_rekening_sumber_patterns_multiline, text)
    if not nama_candidate:
        nama_candidate = find_first_match(nama_rekening_sumber_patterns_single_line, text_single_line)
    nama = clean_extracted_name(nama_candidate)
    bank = normalize_bank(find_first_match(bank_patterns, text_single_line))

    return {
        "tanggal": tanggal,
        "jam": jam,
        "nominal": nominal,
        "nama": nama,
        "bank": bank
    }

def clean_name(name: str) -> str:
    """Bersihkan nama dari karakter tidak perlu dan kata-kata umum."""
    # Hapus kutip tunggal dan backtick terlebih dahulu
    name = re.sub(r"[\'`]", "", name)

    # Hapus karakter khusus lain, hanya pertahankan huruf dan spasi
    name = re.sub(r'[^a-zA-Z\s]', '', name)

    # Uppercase untuk normalisasi
    name = name.upper()

    # Daftar stopwords yang umum di dokumen
    stopwords = ["NAMA LENGKAP", "BORN", "NAMA", "NAME"]

    # Hapus stopwords (sebagai kata utuh)
    for word in stopwords:
        name = re.sub(rf'\b{word}\b', '', name)

    # Hapus spasi berlebih
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
        extracted_text = extract_text_from_upload(file_bytes, file.content_type)
        
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
        
        extracted_text = extract_text_from_upload(file_bytes, file.content_type)
        
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

@app.post("/check-transfer-proof")
async def check_transfer_proof_endpoint(
    file: UploadFile = File(..., description="File bukti transfer (JPG/PNG/PDF)")
):
    """
    Endpoint untuk cek bukti transfer.

    Returns:
    - extracted_full_text: Text OCR lengkap
    - tanggal: Tanggal transaksi (jika ditemukan)
    - jam: Jam transaksi (jika ditemukan)
    - nominal: Nominal transfer (jika ditemukan)
    - nama: Nama pengirim/penerima (jika ditemukan)
    - bank: Nama bank (jika ditemukan)
    """
    try:
        file_bytes = await file.read()
        extracted_text = extract_text_from_upload(file_bytes, file.content_type)
        parsed_fields = parse_transfer_proof_fields(extracted_text)

        return {
            "extracted_full_text": extracted_text,
            **parsed_fields
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
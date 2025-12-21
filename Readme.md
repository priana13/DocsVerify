1. Install python3-venv (jika belum ada)
sudo apt-get update
sudo apt-get install python3-full python3-venv
2. Buat Virtual Environment
# Di folder project Anda
python3 -m venv venv
3. Aktivasi Virtual Environment
source venv/bin/activate
Setelah aktivasi, prompt akan berubah menjadi (venv) user@host:~$
4. Install Dependencies
pip install -r requirements.txt
5. Jalankan API
python3 main.py

6. Install PDiiF to Image
sudo apt install -y poppler-utils

sudo apt-get install -y tesseract-ocr-ind


🚀 Untuk Production (Opsional)
Jika ingin menjalankan sebagai service yang auto-start:
Buat file systemd service:
sudo nano /etc/systemd/system/akta-api.service
Isi file:
ini[Unit]
Description=Akta Validation API
After=network.target

[Service]
User=your_username
WorkingDirectory=/path/to/your/project
Environment="PATH=/path/to/your/project/venv/bin"
ExecStart=/path/to/your/project/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
Aktifkan service:

bash:
sudo systemctl enable akta-api
sudo systemctl start akta-api
sudo systemctl status akta-api


4. Test API
Dokumentasi interaktif: Buka browser ke http://localhost:8000/docs
Contoh request dari frontend (JavaScript):
javascriptconst formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('name', 'BUDI SANTOSO');
formData.append('threshold', 80);

const response = await fetch('http://localhost:8000/validate-name', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
// {
//   "is_valid": true,
//   "matched_name": "BUDI SANTOSO",
//   "similarity_score": 100,
//   "all_names_found": ["BUDI SANTOSO", "JOHN DOE"]
// }
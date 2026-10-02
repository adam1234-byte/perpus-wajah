# PerpusDigital - Perpustakaan dengan Face Recognition

Aplikasi web perpustakaan (Flask + SQLite) dengan login dan peminjaman memakai pengenalan wajah. Library face-api.js dan modelnya sudah disertakan, tidak perlu download apa pun selain Python dan Flask (otomatis).

## Syarat
- Python 3.8 atau lebih baru. Windows: install dari python.org dan centang "Add Python to PATH".
- Internet saat pertama kali jalan (untuk install Flask).
- Webcam dan browser Chrome atau Edge.

## Cara menjalankan
- **Windows**: klik dua kali `start.bat`
- **Linux / Mac / WSL**: `./start.sh` (kalau ditolak: `chmod +x start.sh`)
- **Cara universal**: `python start.py` (Windows) atau `python3 start.py` (Linux/Mac)

Lalu buka alamat yang tertulis di terminal (biasanya http://127.0.0.1:8000) dan klik Allow untuk kamera. Harus memakai alamat 127.0.0.1 atau localhost, kalau tidak kamera diblokir browser.

## Akun admin awal
Email: admin@perpus.com | Password: admin123 (segera ganti)

## Alur
- Member: Registrasi (isi data + Ambil Wajah), login pakai wajah atau email, lihat katalog dan riwayat.
- Admin: Kelola Buku, Scan Peminjaman (scan wajah member), Pengembalian, Laporan.
- Perpustakaan tutup tiap Senin, pinjam 7 hari, denda 10% harga buku per minggu telat.

## Kalau error
| Pesan | Solusi |
|---|---|
| Gagal membuat venv (Ubuntu/Debian) | `sudo apt install -y python3-venv python3-pip` lalu jalankan lagi |
| python / python3 tidak ditemukan | Install Python 3.8+ (Windows: centang Add to PATH) |
| Kamera gagal: NotAllowedError | Klik ikon kunci di address bar, Kamera = Izinkan, refresh |
| Kamera gagal: NotReadableError | Tutup aplikasi lain yang memakai kamera (Zoom, Meet), refresh |
| Kamera gagal: NotFoundError | Pastikan webcam terpasang |
| Wajah tidak terdeteksi | Perbaiki cahaya, hadap kamera, tunggu tulisan Kamera siap |
| Port 8000 dipakai | Otomatis pindah ke 8001 dst, lihat alamat di terminal |
| WSL: video hitam | Buka alamatnya di browser Windows, bukan di dalam Linux |

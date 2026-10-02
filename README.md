# PerpusDigital - Perpustakaan dengan Face Recognition

Aplikasi web perpustakaan (Flask + SQLite) dengan login dan peminjaman memakai pengenalan wajah. Library face-api.js dan modelnya sudah disertakan, jadi langsung jalan.

## Cara menjalankan (Linux / WSL)
1. `git clone https://github.com/adam1234-byte/perpus-wajah.git`
2. `cd perpus-wajah`
3. `chmod +x setup.sh run.sh`
4. `./setup.sh`
5. `./run.sh`
6. Buka http://127.0.0.1:8000 di browser, lalu klik Allow untuk kamera.

## Akun admin awal
Email: admin@perpus.com | Password: admin123 (segera ganti)

## Alur
- Member: Registrasi (isi data + Ambil Wajah), login pakai wajah atau email, lihat katalog dan riwayat.
- Admin: Kelola Buku, Scan Peminjaman (scan wajah member), Pengembalian, Laporan.
- Perpustakaan tutup tiap Senin, pinjam 7 hari, denda 10% harga buku per minggu telat.

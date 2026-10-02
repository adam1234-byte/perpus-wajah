import os, sys, subprocess, venv
B = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(B, "venv")
P = os.path.join(V, "Scripts", "python.exe") if os.name == "nt" else os.path.join(V, "bin", "python")
if sys.version_info < (3, 8):
    sys.exit("Python terlalu lama. Install Python 3.8 atau lebih baru.")
if not os.path.exists(P):
    print("Membuat lingkungan Python (venv)...")
    try:
        venv.create(V, with_pip=True)
    except Exception:
        sys.exit("Gagal membuat venv. Di Ubuntu/Debian jalankan: sudo apt install -y python3-venv python3-pip")
try:
    subprocess.run([P, "-c", "import flask"], check=True, capture_output=True)
except Exception:
    print("Menginstall Flask (butuh internet, sekali saja)...")
    subprocess.check_call([P, "-m", "pip", "install", "-r", os.path.join(B, "requirements.txt")])
os.chdir(B)
print("Menjalankan aplikasi... (tekan Ctrl+C untuk berhenti)")
subprocess.call([P, os.path.join(B, "app.py")])

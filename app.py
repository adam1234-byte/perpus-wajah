import os, re, json, math, time, hmac, secrets, hashlib, smtplib, sqlite3, datetime as dt
from email.message import EmailMessage
from functools import wraps
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.security import generate_password_hash as gh, check_password_hash as ch

BASE = os.path.dirname(os.path.abspath(__file__))

def load_env():
    p = os.path.join(BASE, ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "ganti-kunci-rahasia-ini"
DB = os.path.join(BASE, "perpus.db")
LOAN_DAYS, THRESH = 7, 0.5
CODE_TTL, MAX_TRIES, RESEND_WAIT = 600, 5, 60
GMAIL = re.compile(r"^[a-z0-9][a-z0-9.]{4,29}@gmail\.com$")

def q(sql, a=(), one=False, commit=False):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    r = c.execute(sql, a)
    if commit:
        c.commit(); i = r.lastrowid; c.close(); return i
    rows = r.fetchall(); c.close()
    return (rows[0] if rows else None) if one else rows

def init_db():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, pw TEXT, role TEXT DEFAULT 'member', face TEXT);
    CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY, title TEXT, author TEXT, category TEXT, copies INTEGER, price INTEGER DEFAULT 50000);
    CREATE TABLE IF NOT EXISTS loans(id INTEGER PRIMARY KEY, user_id INT, book_id INT, copy_no INT, loan_date TEXT, due_date TEXT, return_date TEXT, fine INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS pending(email TEXT PRIMARY KEY, name TEXT, pw TEXT, face TEXT, code_hash TEXT, expires REAL, tries INTEGER DEFAULT 0, last_sent REAL);
    """)
    if not c.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
        c.execute("INSERT INTO users(name,email,pw,role) VALUES('Admin','admin@perpus.com',?, 'admin')", (gh("admin123"),))
    c.commit(); c.close()

@app.context_processor
def ctx(): return {"closed": dt.date.today().weekday() == 0}

def need(role=None):
    def d(f):
        @wraps(f)
        def w(*a, **k):
            if not session.get("uid"): return redirect("/login")
            if role and session.get("role") != role: return redirect("/")
            return f(*a, **k)
        return w
    return d

def match(d):
    best, bd = None, 9
    for u in q("SELECT * FROM users WHERE face IS NOT NULL"):
        e = math.dist(d, json.loads(u["face"]))
        if e < bd: best, bd = u, e
    return best if bd < THRESH else None

def login_as(u):
    session.update(uid=u["id"], name=u["name"], role=u["role"])

def canon(email):
    local, _, dom = email.lower().partition("@")
    if dom in ("gmail.com", "googlemail.com"):
        local = local.split("+")[0].replace(".", "")
    return local + "@gmail.com" if dom in ("gmail.com", "googlemail.com") else email.lower()

def hash_code(email, code):
    return hashlib.sha256(f"{code}:{email}:{app.secret_key}".encode()).hexdigest()

def send_code(to, name, code):
    user = os.environ.get("SMTP_USER", "").strip()
    pw = os.environ.get("SMTP_PASS", "").replace(" ", "")
    if not user or not pw:
        print(f"\n[MODE UJI] SMTP belum diatur. Kode verifikasi untuk {to}: {code}\n", flush=True)
        return "demo"
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    sender = os.environ.get("SMTP_FROM_NAME", "PerpusDigital")
    msg = EmailMessage()
    msg["Subject"] = f"Kode verifikasi PerpusDigital: {code}"
    msg["From"] = f"{sender} <{user}>"
    msg["To"] = to
    msg.set_content(
        f"Halo {name},\n\nKode verifikasi pendaftaran PerpusDigital Anda adalah:\n\n    {code}\n\n"
        f"Kode berlaku {CODE_TTL // 60} menit. Jangan berikan kode ini kepada siapa pun.\n"
        f"Jika Anda tidak mendaftar, abaikan email ini.\n")
    if port == 465:
        s = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        s = smtplib.SMTP(host, port, timeout=20)
        s.ehlo()
        if s.has_extn("starttls"):
            s.starttls(); s.ehlo()
    try:
        if s.has_extn("auth"):
            s.login(user, pw)
        s.send_message(msg)
    finally:
        try: s.quit()
        except Exception: pass
    return "email"

def new_code_and_send(email, name):
    code = f"{secrets.randbelow(10**6):06d}"
    now = time.time()
    q("UPDATE pending SET code_hash=?, expires=?, tries=0, last_sent=? WHERE email=?", (hash_code(email, code), now + CODE_TTL, now, email), commit=True)
    try:
        return send_code(email, name, code), None
    except smtplib.SMTPAuthenticationError:
        return None, "Login Gmail pengirim ditolak. Periksa SMTP_USER dan SMTP_PASS (harus Sandi Aplikasi 16 karakter)."
    except smtplib.SMTPRecipientsRefused:
        return None, "Alamat Gmail tujuan ditolak. Pastikan alamat Gmail benar dan aktif."
    except Exception as e:
        return None, f"Gagal mengirim email: {e}"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = q("SELECT * FROM users WHERE email=?", (request.form["email"].strip().lower(),), one=True)
        if u and ch(u["pw"], request.form["password"]):
            login_as(u); return redirect("/")
        flash("Email atau password salah", "e")
    return render_template("login.html")

@app.route("/login/face", methods=["POST"])
def login_face():
    u = match(request.json["d"])
    if not u: return jsonify(ok=False, msg="Wajah tidak dikenali")
    login_as(u); return jsonify(ok=True)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        email = f.get("email", "").strip().lower()
        pw = f.get("password", "")
        if not name:
            flash("Nama wajib diisi", "e"); return redirect("/register")
        if not GMAIL.match(email):
            flash("Gunakan alamat Gmail asli, contoh: nama@gmail.com", "e"); return redirect("/register")
        if len(pw) < 6:
            flash("Password minimal 6 karakter", "e"); return redirect("/register")
        try:
            d = json.loads(f.get("face", ""))
            assert isinstance(d, list) and len(d) == 128 and all(isinstance(x, (int, float)) for x in d)
        except Exception:
            flash("Ambil foto wajah dulu", "e"); return redirect("/register")
        if any(canon(u["email"]) == canon(email) for u in q("SELECT email FROM users")):
            flash("Email sudah terdaftar. Silakan login.", "e"); return redirect("/register")
        old = q("SELECT * FROM pending WHERE email=?", (email,), one=True)
        if old and time.time() - old["last_sent"] < RESEND_WAIT:
            session["pending_email"] = email
            flash("Kode sudah dikirim. Silakan masukkan kode atau tunggu sebentar untuk kirim ulang.", "w")
            return redirect("/verify")
        q("INSERT OR REPLACE INTO pending(email,name,pw,face,code_hash,expires,tries,last_sent) VALUES(?,?,?,?,?,?,?,?)",
          (email, name, gh(pw), json.dumps(d), "", 0, 0, 0), commit=True)
        mode, err = new_code_and_send(email, name)
        if err:
            q("DELETE FROM pending WHERE email=?", (email,), commit=True)
            flash(err, "e"); return redirect("/register")
        session["pending_email"] = email
        session["demo_mode"] = (mode == "demo")
        flash("Kode verifikasi 6 digit telah dikirim ke " + email, "o")
        return redirect("/verify")
    return render_template("register.html")

@app.route("/verify", methods=["GET", "POST"])
def verify():
    email = session.get("pending_email")
    p = q("SELECT * FROM pending WHERE email=?", (email,), one=True) if email else None
    if not p:
        flash("Tidak ada pendaftaran yang menunggu verifikasi. Silakan daftar.", "e")
        return redirect("/register")
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if time.time() > p["expires"]:
            flash("Kode kedaluwarsa. Klik Kirim ulang kode.", "e"); return redirect("/verify")
        if p["tries"] >= MAX_TRIES:
            q("DELETE FROM pending WHERE email=?", (email,), commit=True)
            session.pop("pending_email", None)
            flash("Terlalu banyak percobaan salah. Silakan daftar ulang.", "e"); return redirect("/register")
        if not hmac.compare_digest(hash_code(email, code), p["code_hash"]):
            q("UPDATE pending SET tries=tries+1 WHERE email=?", (email,), commit=True)
            sisa = MAX_TRIES - p["tries"] - 1
            if sisa <= 0:
                q("DELETE FROM pending WHERE email=?", (email,), commit=True)
                session.pop("pending_email", None)
                flash("Terlalu banyak percobaan salah. Silakan daftar ulang.", "e"); return redirect("/register")
            flash(f"Kode salah. Sisa percobaan: {sisa}", "e"); return redirect("/verify")
        try:
            q("INSERT INTO users(name,email,pw,face) VALUES(?,?,?,?)", (p["name"], email, p["pw"], p["face"]), commit=True)
        except sqlite3.IntegrityError:
            flash("Email sudah terdaftar. Silakan login.", "e")
        else:
            flash("Verifikasi berhasil. Akun aktif, silakan login.", "o")
        q("DELETE FROM pending WHERE email=?", (email,), commit=True)
        session.pop("pending_email", None); session.pop("demo_mode", None)
        return redirect("/login")
    wait = max(0, int(RESEND_WAIT - (time.time() - p["last_sent"])))
    return render_template("verify.html", email=email, wait=wait, ttl=CODE_TTL // 60, demo=session.get("demo_mode", False))

@app.route("/verify/resend", methods=["POST"])
def verify_resend():
    email = session.get("pending_email")
    p = q("SELECT * FROM pending WHERE email=?", (email,), one=True) if email else None
    if not p:
        return redirect("/register")
    if time.time() - p["last_sent"] < RESEND_WAIT:
        flash("Tunggu sebentar sebelum kirim ulang kode.", "e"); return redirect("/verify")
    mode, err = new_code_and_send(email, p["name"])
    if err: flash(err, "e")
    else:
        session["demo_mode"] = (mode == "demo")
        flash("Kode baru telah dikirim ke " + email, "o")
    return redirect("/verify")

@app.route("/logout")
def logout():
    session.clear(); return redirect("/login")

@app.route("/")
@need()
def catalog():
    s = "%" + request.args.get("s", "") + "%"
    books = q("SELECT b.*, b.copies-(SELECT COUNT(*) FROM loans l WHERE l.book_id=b.id AND l.return_date IS NULL) AS free FROM books b WHERE title LIKE ? OR author LIKE ?", (s, s))
    return render_template("catalog.html", books=books)

@app.route("/book/<int:i>")
@need()
def book(i):
    b = q("SELECT * FROM books WHERE id=?", (i,), one=True)
    used = {r["copy_no"] for r in q("SELECT copy_no FROM loans WHERE book_id=? AND return_date IS NULL", (i,))}
    return render_template("book.html", b=b, used=used, days=LOAN_DAYS)

@app.route("/history")
@need("member")
def history():
    rows = q("SELECT l.*, b.title FROM loans l JOIN books b ON b.id=l.book_id WHERE user_id=? ORDER BY l.id DESC", (session["uid"],))
    return render_template("history.html", rows=rows)

@app.route("/admin/books", methods=["GET", "POST"])
@need("admin")
def admin_books():
    if request.method == "POST":
        f = request.form
        q("INSERT INTO books(title,author,category,copies,price) VALUES(?,?,?,?,?)", (f["title"], f["author"], f["category"], int(f["copies"]), int(f["price"])), commit=True)
        flash("Buku ditambahkan", "o"); return redirect("/admin/books")
    return render_template("admin_books.html", books=q("SELECT * FROM books"))

@app.route("/admin/borrow", methods=["GET", "POST"])
@need("admin")
def admin_borrow():
    if request.method == "POST":
        if dt.date.today().weekday() == 0:
            flash("Perpustakaan tutup hari Senin", "e"); return redirect("/admin/borrow")
        uid, bid = int(request.form["user_id"]), int(request.form["book_id"])
        b = q("SELECT * FROM books WHERE id=?", (bid,), one=True)
        used = {r["copy_no"] for r in q("SELECT copy_no FROM loans WHERE book_id=? AND return_date IS NULL", (bid,))}
        free = [n for n in range(1, b["copies"] + 1) if n not in used]
        if not free:
            flash("Semua eksemplar sedang dipinjam", "e"); return redirect("/admin/borrow")
        t = dt.date.today()
        q("INSERT INTO loans(user_id,book_id,copy_no,loan_date,due_date) VALUES(?,?,?,?,?)", (uid, bid, free[0], t.isoformat(), (t + dt.timedelta(days=LOAN_DAYS)).isoformat()), commit=True)
        flash(f"Berhasil: {b['title']} eksemplar BK-{bid}-C{free[0]}", "o"); return redirect("/admin/borrow")
    return render_template("borrow.html", books=q("SELECT * FROM books"))

@app.route("/admin/scan", methods=["POST"])
@need("admin")
def scan():
    u = match(request.json["d"])
    return jsonify(ok=bool(u), id=u["id"] if u else 0, name=u["name"] if u else "Tidak dikenali")

@app.route("/admin/return", methods=["GET", "POST"])
@need("admin")
def admin_return():
    if request.method == "POST":
        l = q("SELECT l.*, b.price, b.title FROM loans l JOIN books b ON b.id=l.book_id WHERE l.id=?", (int(request.form["id"]),), one=True)
        late = (dt.date.today() - dt.date.fromisoformat(l["due_date"])).days
        fine = math.ceil(late / 7) * int(l["price"] * 0.1) if late > 0 else 0
        q("UPDATE loans SET return_date=?, fine=? WHERE id=?", (dt.date.today().isoformat(), fine, l["id"]), commit=True)
        flash(f"Dikembalikan. Denda: Rp {fine:,}", "o"); return redirect("/admin/return")
    rows = q("SELECT l.*, b.title, u.name FROM loans l JOIN books b ON b.id=l.book_id JOIN users u ON u.id=l.user_id WHERE return_date IS NULL")
    return render_template("return.html", rows=rows)

@app.route("/admin/reports")
@need("admin")
def reports():
    tb = q("SELECT b.title, COUNT(*) n FROM loans l JOIN books b ON b.id=l.book_id GROUP BY b.id ORDER BY n DESC LIMIT 5")
    tm = q("SELECT u.name, u.email, COUNT(*) n FROM loans l JOIN users u ON u.id=l.user_id GROUP BY u.id ORDER BY n DESC LIMIT 5")
    al = q("SELECT l.*, b.title, u.name FROM loans l JOIN books b ON b.id=l.book_id JOIN users u ON u.id=l.user_id ORDER BY l.id DESC")
    return render_template("reports.html", tb=tb, tm=tm, al=al)

if __name__ == "__main__":
    import socket
    init_db()
    port = 8000
    while port < 8020:
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                break
        port += 1
    print(f"\n>>> Buka di browser: http://127.0.0.1:{port}\n", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False)

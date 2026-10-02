import sqlite3, json, math, datetime as dt
from functools import wraps
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from werkzeug.security import generate_password_hash as gh, check_password_hash as ch

app = Flask(__name__)
app.secret_key = "ganti-kunci-rahasia-ini"
import os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "perpus.db")
LOAN_DAYS, THRESH = 7, 0.5

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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = q("SELECT * FROM users WHERE email=?", (request.form["email"],), one=True)
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
        if not f.get("face"):
            flash("Ambil foto wajah dulu", "e"); return redirect("/register")
        try:
            q("INSERT INTO users(name,email,pw,face) VALUES(?,?,?,?)", (f["name"], f["email"], gh(f["password"]), f["face"]), commit=True)
        except sqlite3.IntegrityError:
            flash("Email sudah terdaftar", "e"); return redirect("/register")
        flash("Registrasi berhasil, silakan login", "o"); return redirect("/login")
    return render_template("register.html")

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

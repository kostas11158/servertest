from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os

DB_FILE = "keys.db"
ADMIN_KEY = "admin123"   # ключ, который всегда в базе
ADMIN_LOGIN = "admin"    # логин для входа в веб-панель
ADMIN_PASSWORD = "superpass"  # пароль для входа в веб-панель

app = Flask(__name__)
app.secret_key = "secret_flask_session"  # ключ для шифрования cookie

# ===== Работа с БД =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_key(key: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO keys (key) VALUES (?)", (key,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def delete_key(key: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM keys WHERE key=?", (key,))
    conn.commit()
    conn.close()

def get_all_keys():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT key FROM keys")
    keys = [row[0] for row in cur.fetchall()]
    conn.close()
    return keys

def check_key_in_db(key: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM keys WHERE key=?", (key,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

# ===== API =====
@app.route("/check_key", methods=["POST"])
def check_key():
    data = request.get_json()
    key = data.get("key", "")
    if check_key_in_db(key):
        return jsonify({"status": "ok"})
    return jsonify({"status": "error", "message": "Неверный ключ"}), 401

# ===== HTML шаблоны =====
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Вход</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
<div class="container d-flex justify-content-center align-items-center" style="height:100vh;">
  <div class="card shadow p-4" style="width: 350px;">
    <h3 class="text-center mb-3">🔐 Вход в админ-панель</h3>
    <form method="POST">
      <div class="mb-3">
        <label class="form-label">Логин</label>
        <input type="text" name="username" class="form-control" required>
      </div>
      <div class="mb-3">
        <label class="form-label">Пароль</label>
        <input type="password" name="password" class="form-control" required>
      </div>
      <button type="submit" class="btn btn-primary w-100">Войти</button>
    </form>
    {% if error %}
    <div class="alert alert-danger mt-3" role="alert">{{ error }}</div>
    {% endif %}
  </div>
</div>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Управление ключами</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
  <div class="container-fluid">
    <a class="navbar-brand" href="#">🔑 Панель администратора</a>
    <form class="d-flex" method="POST" action="{{ url_for('logout') }}">
      <button class="btn btn-outline-light" type="submit">Выйти</button>
    </form>
  </div>
</nav>

<div class="container mt-4">
  <h3>Список ключей</h3>
  <ul class="list-group">
    {% for key in keys %}
      <li class="list-group-item d-flex justify-content-between align-items-center">
        {{ key }}
        {% if key != admin_key %}
        <form method="POST" action="{{ url_for('delete_key_web') }}">
          <input type="hidden" name="key" value="{{ key }}">
          <button class="btn btn-sm btn-danger">Удалить</button>
        </form>
        {% else %}
        <span class="badge bg-secondary">Нельзя удалить</span>
        {% endif %}
      </li>
    {% endfor %}
  </ul>

  <h4 class="mt-4">Добавить новый ключ</h4>
  <form method="POST" action="{{ url_for('add_key_web') }}" class="d-flex">
    <input type="text" name="key" class="form-control me-2" placeholder="Введите ключ" required>
    <button type="submit" class="btn btn-success">Добавить</button>
  </form>
</div>
</body>
</html>
"""

# ===== Веб-интерфейс =====
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Неверный логин или пароль")
    return render_template_string(LOGIN_TEMPLATE, error=None)

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

def require_admin():
    return "admin" in session

@app.route("/admin", methods=["GET"])
def admin_panel():
    if not require_admin():
        return redirect(url_for("login"))
    keys = get_all_keys()
    return render_template_string(ADMIN_TEMPLATE, keys=keys, admin_key=ADMIN_KEY)

@app.route("/admin/add", methods=["POST"])
def add_key_web():
    if not require_admin():
        return redirect(url_for("login"))
    key = request.form.get("key")
    if key:
        add_key(key)
    return redirect(url_for("admin_panel"))

@app.route("/admin/delete", methods=["POST"])
def delete_key_web():
    if not require_admin():
        return redirect(url_for("login"))
    key = request.form.get("key")
    if key and key != ADMIN_KEY:
        delete_key(key)
    return redirect(url_for("admin_panel"))

# ===== Запуск =====
if __name__ == "__main__":
    init_db()
    add_key(ADMIN_KEY)  # всегда гарантируем наличие admin123
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

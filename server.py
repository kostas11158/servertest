# server.py
from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
import sqlite3
import os

DB_FILE = "keys.db"
app = Flask(__name__)
app.secret_key = "supersecretkey"  # секрет для сессий (замени на свой)

# ===== Авторизация =====
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

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

@app.route("/keys", methods=["GET"])
def list_keys():
    return jsonify({"keys": get_all_keys()})

@app.route("/keys", methods=["POST"])
def api_add_key():
    data = request.get_json()
    key = data.get("key", "")
    if not key:
        return jsonify({"status": "error", "message": "Ключ не передан"}), 400
    add_key(key)
    return jsonify({"status": "ok", "message": f"Ключ '{key}' добавлен"})

@app.route("/keys", methods=["DELETE"])
def api_delete_key():
    data = request.get_json()
    key = data.get("key", "")
    if not key:
        return jsonify({"status": "error", "message": "Ключ не передан"}), 400
    delete_key(key)
    return jsonify({"status": "ok", "message": f"Ключ '{key}' удалён"})

# ===== HTML шаблоны =====
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Вход в админ-панель</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light d-flex align-items-center justify-content-center" style="height:100vh;">
<div class="card shadow p-4" style="width: 350px;">
  <h4 class="mb-3 text-center">🔑 Вход</h4>
  {% if error %}
  <div class="alert alert-danger">{{ error }}</div>
  {% endif %}
  <form method="POST" action="{{ url_for('login') }}">
    <div class="mb-3">
      <label class="form-label">Логин</label>
      <input type="text" class="form-control" name="username" required>
    </div>
    <div class="mb-3">
      <label class="form-label">Пароль</label>
      <input type="password" class="form-control" name="password" required>
    </div>
    <button type="submit" class="btn btn-primary w-100">Войти</button>
  </form>
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
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<nav class="navbar navbar-dark bg-dark">
  <div class="container-fluid">
    <a class="navbar-brand">🔑 Панель управления ключами</a>
    <form method="POST" action="{{ url_for('logout') }}">
      <button type="submit" class="btn btn-outline-light btn-sm">Выйти</button>
    </form>
  </div>
</nav>

<div class="container mt-4">
  <h3 class="mb-3">Список ключей</h3>
  <table class="table table-bordered table-striped bg-white shadow-sm">
    <thead class="table-dark">
      <tr>
        <th>Ключ</th>
        <th style="width: 150px;">Действие</th>
      </tr>
    </thead>
    <tbody>
      {% for key in keys %}
      <tr>
        <td>{{ key }}</td>
        <td>
          <form method="POST" action="{{ url_for('delete_key_web') }}">
            <input type="hidden" name="key" value="{{ key }}">
            <button type="submit" class="btn btn-sm btn-danger">Удалить</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <h4 class="mt-4">Добавить новый ключ</h4>
  <form method="POST" action="{{ url_for('add_key_web') }}" class="d-flex">
    <input type="text" name="key" class="form-control me-2" placeholder="Введите ключ" required>
    <button type="submit" class="btn btn-success">Добавить</button>
  </form>
</div>
</body>
</html>
"""

# ===== Роуты для авторизации =====
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("admin_panel"))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Неверный логин или пароль")
    return render_template_string(LOGIN_TEMPLATE, error=None)

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/admin", methods=["GET"])
def admin_panel():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template_string(ADMIN_TEMPLATE, keys=get_all_keys())

@app.route("/admin/add", methods=["POST"])
def add_key_web():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    key = request.form.get("key")
    if key:
        add_key(key)
    return redirect(url_for("admin_panel"))

@app.route("/admin/delete", methods=["POST"])
def delete_key_web():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    key = request.form.get("key")
    if key:
        delete_key(key)
    return redirect(url_for("admin_panel"))

# ===== Запуск =====
if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
            init_db()               # всегда создаём таблицу, если её нет
    add_key("admin123")     # гарантируем ключ
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

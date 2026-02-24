import os
import sqlite3
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

ROLES = ('peregrino', 'provedor', 'concello', 'admin')
VISIBILIDADES = ('privado', 'publico')


# =============================================================================
# CLASE USER (interface Flask-Login)
# =============================================================================

class User:
    def __init__(self, data):
        self.id = data['id']
        self.username = data['username']
        self.email = data.get('email', '')
        self.password_hash = data['password_hash']
        self.rol = data.get('rol', 'peregrino')
        self.bio = data.get('bio') or ''
        self.avatar = data.get('avatar') or ''
        self.created_at = data.get('created_at', '')

    # --- Flask-Login interface ---
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# =============================================================================
# INICIALIZACIÓN DA BASE DE DATOS
# =============================================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # --- Users (expandida con novos campos) ---
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT UNIQUE NOT NULL,
        email       TEXT UNIQUE NOT NULL DEFAULT '',
        password_hash TEXT NOT NULL,
        rol         TEXT NOT NULL DEFAULT 'peregrino',
        bio         TEXT,
        avatar      TEXT,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )''')

    # Migración: engadir columnas novas á táboa existente se non existen
    for col, defn in [
        ('email',      'TEXT NOT NULL DEFAULT ""'),
        ('rol',        'TEXT NOT NULL DEFAULT "peregrino"'),
        ('bio',        'TEXT'),
        ('avatar',     'TEXT'),
        ('created_at', 'TEXT NOT NULL DEFAULT (datetime("now"))'),
    ]:
        try:
            c.execute(f'ALTER TABLE users ADD COLUMN {col} {defn}')
        except sqlite3.OperationalError:
            pass  # columna xa existe

    # --- Posts ---
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL REFERENCES users(id),
        contido      TEXT NOT NULL,
        lat          REAL,
        lng          REAL,
        poi_slug     TEXT,
        visibilidade TEXT NOT NULL DEFAULT 'publico',
        foto         TEXT,
        created_at   TEXT NOT NULL DEFAULT (datetime('now'))
    )''')

    # --- CheckIns ---
    c.execute('''CREATE TABLE IF NOT EXISTS checkins (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id),
        poi_slug   TEXT NOT NULL,
        lat        REAL NOT NULL,
        lng        REAL NOT NULL,
        validado   INTEGER NOT NULL DEFAULT 0,
        puntuacion INTEGER,
        resena     TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(user_id, poi_slug)
    )''')

    # Migración checkins
    for col, defn in [
        ('puntuacion', 'INTEGER'),
        ('resena',     'TEXT'),
    ]:
        try:
            c.execute(f'ALTER TABLE checkins ADD COLUMN {col} {defn}')
        except sqlite3.OperationalError:
            pass

    # --- Reaccións ---
    c.execute('''CREATE TABLE IF NOT EXISTS reaccions (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id    INTEGER NOT NULL REFERENCES posts(id),
        user_id    INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(post_id, user_id)
    )''')

    # --- Comentarios ---
    c.execute('''CREATE TABLE IF NOT EXISTS comentarios (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id    INTEGER NOT NULL REFERENCES posts(id),
        user_id    INTEGER NOT NULL REFERENCES users(id),
        contido    TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )''')

    # --- Credentials ---
    c.execute('''CREATE TABLE IF NOT EXISTS credentials (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id),
        tipo       TEXT NOT NULL DEFAULT 'camino_completo',
        datos_json TEXT,
        qr_token   TEXT UNIQUE NOT NULL,
        emitida_at TEXT NOT NULL DEFAULT (datetime('now'))
    )''')

    conn.commit()
    conn.close()


# =============================================================================
# HELPERS DE CONEXIÓN
# =============================================================================

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =============================================================================
# USUARIOS
# =============================================================================

def get_user_by_id(user_id):
    conn = _conn()
    row = conn.execute(
        'SELECT * FROM users WHERE id = ?', (user_id,)
    ).fetchone()
    conn.close()
    return User(dict(row)) if row else None


def get_user_by_username(username):
    conn = _conn()
    row = conn.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()
    conn.close()
    return User(dict(row)) if row else None


def get_user_by_email(email):
    conn = _conn()
    row = conn.execute(
        'SELECT * FROM users WHERE email = ?', (email,)
    ).fetchone()
    conn.close()
    return User(dict(row)) if row else None


def create_user(username, email, password, rol='peregrino'):
    conn = _conn()
    password_hash = generate_password_hash(password)
    try:
        conn.execute(
            'INSERT INTO users (username, email, password_hash, rol) VALUES (?, ?, ?, ?)',
            (username, email, password_hash, rol)
        )
        conn.commit()
        return get_user_by_username(username)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


# =============================================================================
# POSTS
# =============================================================================

def create_post(user_id, contido, lat=None, lng=None, poi_slug=None,
                visibilidade='publico', foto=None):
    conn = _conn()
    cur = conn.execute(
        '''INSERT INTO posts (user_id, contido, lat, lng, poi_slug, visibilidade, foto)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, contido, lat, lng, poi_slug, visibilidade, foto)
    )
    conn.commit()
    post_id = cur.lastrowid
    conn.close()
    return post_id


def get_posts_publicos(limit=50, offset=0):
    conn = _conn()
    rows = conn.execute(
        '''SELECT p.*, u.username, u.avatar, u.rol
           FROM posts p JOIN users u ON p.user_id = u.id
           WHERE p.visibilidade = 'publico'
           ORDER BY p.created_at DESC
           LIMIT ? OFFSET ?''',
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_posts_usuario(user_id):
    conn = _conn()
    rows = conn.execute(
        'SELECT * FROM posts WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =============================================================================
# CHECK-INS
# =============================================================================

def create_checkin(user_id, poi_slug, lat, lng, validado=False, puntuacion=None, resena=None):
    """Insire un check-in. Ignora se xa existe (UNIQUE user_id + poi_slug)."""
    conn = _conn()
    try:
        conn.execute(
            '''INSERT INTO checkins (user_id, poi_slug, lat, lng, validado, puntuacion, resena)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (user_id, poi_slug, lat, lng, 1 if validado else 0, puntuacion, resena)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # xa fixo check-in aquí
    finally:
        conn.close()


def get_checkins_usuario(user_id):
    conn = _conn()
    rows = conn.execute(
        'SELECT * FROM checkins WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_checkins_poi(poi_slug):
    """Cantos usuarios fixeron check-in nun POI."""
    conn = _conn()
    row = conn.execute(
        'SELECT COUNT(*) as total FROM checkins WHERE poi_slug = ?',
        (poi_slug,)
    ).fetchone()
    conn.close()
    return row['total'] if row else 0


# =============================================================================
# CREDENCIAIS
# =============================================================================

def create_credential(user_id, tipo='camino_completo', datos=None):
    qr_token = secrets.token_urlsafe(32)
    import json
    conn = _conn()
    conn.execute(
        'INSERT INTO credentials (user_id, tipo, datos_json, qr_token) VALUES (?, ?, ?, ?)',
        (user_id, tipo, json.dumps(datos or {}), qr_token)
    )
    conn.commit()
    conn.close()
    return qr_token


def get_credential_by_token(token):
    import json
    conn = _conn()
    row = conn.execute(
        '''SELECT c.*, u.username FROM credentials c
           JOIN users u ON c.user_id = u.id
           WHERE c.qr_token = ?''',
        (token,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d['datos'] = json.loads(d['datos_json'] or '{}')
    return d


def get_credentials_usuario(user_id):
    conn = _conn()
    rows = conn.execute(
        'SELECT * FROM credentials WHERE user_id = ? ORDER BY emitida_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =============================================================================
# REACCIÓNS
# =============================================================================

def toggle_reaccion(post_id, user_id):
    """Engade ou elimina a reacción. Devolve True se quedou activa, False se se eliminou."""
    conn = _conn()
    try:
        conn.execute(
            'INSERT INTO reaccions (post_id, user_id) VALUES (?, ?)',
            (post_id, user_id)
        )
        conn.commit()
        return True   # engadida
    except sqlite3.IntegrityError:
        conn.execute(
            'DELETE FROM reaccions WHERE post_id=? AND user_id=?',
            (post_id, user_id)
        )
        conn.commit()
        return False  # eliminada
    finally:
        conn.close()


def get_reaccions_post(post_id, user_id=None):
    """Total de reaccións e se o usuario actual xa reaccionou."""
    conn = _conn()
    total = conn.execute(
        'SELECT COUNT(*) FROM reaccions WHERE post_id=?', (post_id,)
    ).fetchone()[0]
    miña = False
    if user_id:
        miña = bool(conn.execute(
            'SELECT 1 FROM reaccions WHERE post_id=? AND user_id=?',
            (post_id, user_id)
        ).fetchone())
    conn.close()
    return {'total': total, 'miña': miña}


# =============================================================================
# COMENTARIOS
# =============================================================================

def create_comentario(post_id, user_id, contido):
    conn = _conn()
    cur = conn.execute(
        'INSERT INTO comentarios (post_id, user_id, contido) VALUES (?, ?, ?)',
        (post_id, user_id, contido)
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def get_comentarios_post(post_id):
    conn = _conn()
    rows = conn.execute(
        '''SELECT c.*, u.username, u.avatar
           FROM comentarios c JOIN users u ON c.user_id = u.id
           WHERE c.post_id = ?
           ORDER BY c.created_at ASC''',
        (post_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_posts_publicos_con_stats(limit=50, offset=0, user_id=None):
    """Posts públicos con conteo de reaccións e comentarios."""
    conn = _conn()
    rows = conn.execute(
        '''SELECT p.*, u.username, u.avatar, u.rol,
                  (SELECT COUNT(*) FROM reaccions r WHERE r.post_id=p.id) AS total_reaccions,
                  (SELECT COUNT(*) FROM comentarios c WHERE c.post_id=p.id) AS total_comentarios
           FROM posts p JOIN users u ON p.user_id = u.id
           WHERE p.visibilidade = 'publico'
           ORDER BY p.created_at DESC
           LIMIT ? OFFSET ?''',
        (limit, offset)
    ).fetchall()
    posts = [dict(r) for r in rows]
    if user_id:
        for p in posts:
            miña = conn.execute(
                'SELECT 1 FROM reaccions WHERE post_id=? AND user_id=?',
                (p['id'], user_id)
            ).fetchone()
            p['miña_reaccion'] = bool(miña)
    conn.close()
    return posts

import sqlite3
conn = sqlite3.connect('/home/runner/workspace/artifacts/tradeai/signals.db')
print("Current schema:", conn.execute("SELECT sql FROM sqlite_master WHERE name='users'").fetchone())
conn.execute("ALTER TABLE users RENAME TO users_old")
conn.execute('''CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
conn.execute('''INSERT OR IGNORE INTO users (id, username, email, password_hash, created_at)
    SELECT id, name, email, password, created_at FROM users_old''')
conn.execute("DROP TABLE users_old")
conn.commit()
print("Fixed schema:", conn.execute("SELECT sql FROM sqlite_master WHERE name='users'").fetchone())
print("Users count:", conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
conn.close()

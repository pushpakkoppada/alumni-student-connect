import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = "database.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            course TEXT,
            company TEXT,
            skills TEXT
        )
    """)

    columns = conn.execute("PRAGMA table_info(users)").fetchall()
    column_names = [column["name"] for column in columns]

    if "username" not in column_names:
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mentorship_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            alumni_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES users(id),
            FOREIGN KEY(alumni_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    demo_users = [
        (
            "Pushpak Student",
            "pushpak",
            "student@gmail.com",
            "student123",
            "student",
            "B.Tech CSE (AI & ML)",
            "",
            "Python, AI/ML, Data Science"
        ),
        (
            "Arjun Sharma",
            "arjun",
            "alumni@gmail.com",
            "alumni123",
            "alumni",
            "",
            "Google",
            "Python, Machine Learning, TensorFlow"
        ),
        (
            "Priya Reddy",
            "priya",
            "priya@gmail.com",
            "alumni123",
            "alumni",
            "",
            "Microsoft",
            "Python, SQL, Data Science"
        ),
        (
            "Rahul Mehta",
            "rahul",
            "rahul@gmail.com",
            "alumni123",
            "alumni",
            "",
            "Amazon",
            "Java, DSA, Cloud"
        ),
        (
            "Sneha Nair",
            "sneha",
            "sneha@gmail.com",
            "alumni123",
            "alumni",
            "",
            "Adobe",
            "UI/UX, Figma, Design"
        )
    ]

    for user in demo_users:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (user[2],)
        ).fetchone()

        if not existing:
            conn.execute("""
                INSERT INTO users
                (name, username, email, password, role, course, company, skills)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user[0],
                user[1],
                user[2],
                generate_password_hash(user[3]),
                user[4],
                user[5],
                user[6],
                user[7]
            ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
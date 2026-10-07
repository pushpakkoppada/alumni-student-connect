import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the .env file")


class NeonConnection:
    def __init__(self):
        self.conn = psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row
        )

    def execute(self, query, params=None):
        query = query.replace("?", "%s")

        if params is None:
            return self.conn.execute(query)

        return self.conn.execute(query, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()


def get_db():
    return NeonConnection()


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mentorship_requests (
            id BIGSERIAL PRIMARY KEY,
            student_id BIGINT NOT NULL,
            alumni_id BIGINT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES users(id),
            FOREIGN KEY(alumni_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id BIGSERIAL PRIMARY KEY,
            sender_id BIGINT NOT NULL,
            receiver_id BIGINT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
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
    print("Neon PostgreSQL database initialized successfully!")
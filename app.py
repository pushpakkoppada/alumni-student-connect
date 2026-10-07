from flask import Flask, render_template, request, redirect, url_for, session
from database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

app = Flask(__name__)
app.secret_key = "alumniconnect-secret-key"

init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]
        course = request.form.get("course", "")
        company = request.form.get("company", "")
        skills = request.form.get("skills", "")

        conn = get_db()

        existing = conn.execute(
            "SELECT id FROM users WHERE email = ? OR username = ?",
            (email, username)
        ).fetchone()

        if existing:
            conn.close()
            return render_template(
                "register.html",
                error="Username or email already exists."
            )

        conn.execute("""
            INSERT INTO users
            (name, username, email, password, role, course, company, skills)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            username,
            email,
            generate_password_hash(password),
            role,
            course,
            company,
            skills
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form["login"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute("""
            SELECT * FROM users
            WHERE username = ? OR email = ?
        """, (login_value, login_value)).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["username"] = user["username"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            if user["role"] == "student":
                return redirect(url_for("student_dashboard"))

            return redirect(url_for("alumni_dashboard"))

        return render_template(
            "login.html",
            error="Invalid username/email or password."
        )

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    reset_link = None
    message = None

    if request.method == "POST":
        email = request.form["email"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(minutes=30)

            conn.execute("""
                INSERT INTO password_reset_tokens
                (user_id, token, expires_at)
                VALUES (?, ?, ?)
            """, (
                user["id"],
                token,
                expires_at
            ))

            conn.commit()

            reset_link = url_for(
                "reset_password",
                token=token,
                _external=True
            )

            message = "Reset link generated successfully."
        else:
            message = "No account found with that email."

        conn.close()

    return render_template(
        "forgot_password.html",
        reset_link=reset_link,
        message=message
    )


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    conn = get_db()

    reset_token = conn.execute("""
        SELECT * FROM password_reset_tokens
        WHERE token = ? AND used = 0
    """, (token,)).fetchone()

    if not reset_token:
        conn.close()
        return render_template(
            "reset_password.html",
            error="Invalid or expired reset link."
        )

    expires_at = datetime.fromisoformat(reset_token["expires_at"])

    if datetime.utcnow() > expires_at:
        conn.close()
        return render_template(
            "reset_password.html",
            error="This reset link has expired."
        )

    if request.method == "POST":
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            conn.close()
            return render_template(
                "reset_password.html",
                error="Passwords do not match."
            )

        conn.execute("""
            UPDATE users
            SET password = ?
            WHERE id = ?
        """, (
            generate_password_hash(password),
            reset_token["user_id"]
        ))

        conn.execute("""
            UPDATE password_reset_tokens
            SET used = 1
            WHERE id = ?
        """, (reset_token["id"],))

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    conn.close()

    return render_template("reset_password.html")


@app.route("/student-dashboard")
def student_dashboard():
    if "user_id" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    return render_template("student_dashboard.html")


@app.route("/alumni-dashboard")
def alumni_dashboard():
    if "user_id" not in session or session.get("role") != "alumni":
        return redirect(url_for("login"))

    return render_template("alumni_dashboard.html")


@app.route("/mentors")
def mentors():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    mentors = conn.execute("""
        SELECT * FROM users
        WHERE role = 'alumni'
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "mentors.html",
        mentors=mentors
    )


@app.route("/request-mentor/<int:alumni_id>")
def request_mentor(alumni_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "student":
        return redirect(url_for("alumni_dashboard"))

    student_id = session["user_id"]

    conn = get_db()

    existing = conn.execute("""
        SELECT id FROM mentorship_requests
        WHERE student_id = ?
        AND alumni_id = ?
        AND status IN ('Pending', 'Accepted')
    """, (
        student_id,
        alumni_id
    )).fetchone()

    if not existing:
        conn.execute("""
            INSERT INTO mentorship_requests
            (student_id, alumni_id, status)
            VALUES (?, ?, 'Pending')
        """, (
            student_id,
            alumni_id
        ))

        conn.commit()

    conn.close()

    return redirect(url_for("my_requests"))


@app.route("/my-requests")
def my_requests():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "student":
        return redirect(url_for("alumni_dashboard"))

    conn = get_db()

    requests = conn.execute("""
        SELECT
            mentorship_requests.*,
            users.name AS alumni_name,
            users.company,
            users.skills
        FROM mentorship_requests
        JOIN users
        ON mentorship_requests.alumni_id = users.id
        WHERE mentorship_requests.student_id = ?
        ORDER BY mentorship_requests.created_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "student_requests.html",
        requests=requests
    )


@app.route("/alumni-requests")
def alumni_requests():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "alumni":
        return redirect(url_for("student_dashboard"))

    conn = get_db()

    requests = conn.execute("""
        SELECT
            mentorship_requests.*,
            users.name AS student_name,
            users.email AS student_email,
            users.course AS student_course,
            users.skills AS student_skills
        FROM mentorship_requests
        JOIN users
        ON mentorship_requests.student_id = users.id
        WHERE mentorship_requests.alumni_id = ?
        ORDER BY mentorship_requests.created_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "alumni_requests.html",
        requests=requests
    )


@app.route("/mentor-request/<int:request_id>/<action>")
def mentor_request(request_id, action):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "alumni":
        return redirect(url_for("student_dashboard"))

    if action not in ["accept", "decline"]:
        return redirect(url_for("alumni_requests"))

    status = "Accepted" if action == "accept" else "Declined"

    conn = get_db()

    conn.execute("""
        UPDATE mentorship_requests
        SET status = ?
        WHERE id = ?
        AND alumni_id = ?
    """, (
        status,
        request_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("alumni_requests"))


@app.route("/chat/<int:user_id>", methods=["GET", "POST"])
def chat(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    current_user_id = session["user_id"]

    if current_user_id == user_id:
        return redirect(url_for("student_dashboard"))

    conn = get_db()

    current_user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (current_user_id,)
    ).fetchone()

    other_user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not other_user:
        conn.close()
        return redirect(url_for("student_dashboard"))

    accepted = conn.execute("""
        SELECT id
        FROM mentorship_requests
        WHERE (
            (student_id = ? AND alumni_id = ?)
            OR
            (student_id = ? AND alumni_id = ?)
        )
        AND status = 'Accepted'
    """, (
        current_user_id,
        user_id,
        user_id,
        current_user_id
    )).fetchone()

    if not accepted:
        conn.close()
        return "Chat is available only after mentorship is accepted."

    if request.method == "POST":
        message = request.form["message"].strip()

        if message:
            conn.execute("""
                INSERT INTO messages
                (sender_id, receiver_id, message)
                VALUES (?, ?, ?)
            """, (
                current_user_id,
                user_id,
                message
            ))

            conn.commit()

        conn.close()

        return redirect(url_for("chat", user_id=user_id))

    messages = conn.execute("""
        SELECT
            messages.*,
            users.name AS sender_name
        FROM messages
        JOIN users
        ON messages.sender_id = users.id
        WHERE
        (
            sender_id = ? AND receiver_id = ?
        )
        OR
        (
            sender_id = ? AND receiver_id = ?
        )
        ORDER BY messages.created_at ASC
    """, (
        current_user_id,
        user_id,
        user_id,
        current_user_id
    )).fetchall()

    conn.close()

    return render_template(
        "chat.html",
        messages=messages,
        other_user=other_user,
        current_user=current_user
    )


@app.route("/career-path")
def career_path():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "feature.html",
        icon="🚀",
        title="Career Path",
        description="Explore skills, roles and learning paths for your target career.",
        heading="Build Your Career Path",
        content="Choose a career direction, identify the skills you need, and connect with experienced alumni who can guide your journey.",
        stats=[
            {"value": "AI/ML", "label": "Popular Career"},
            {"value": "10+", "label": "Core Skills"},
            {"value": "5+", "label": "Career Roles"}
        ],
        action_url=url_for("mentors"),
        action_text="Find a Mentor",
        dashboard_url=url_for("student_dashboard")
    )


@app.route("/learning-progress")
def learning_progress():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "feature.html",
        icon="📚",
        title="Learning Progress",
        description="Track your skills, projects and learning progress.",
        heading="Your Learning Journey",
        content="Keep track of the technical skills, projects and learning goals that will help you move toward your target career.",
        stats=[
            {"value": "0%", "label": "Overall Progress"},
            {"value": "0", "label": "Projects Completed"},
            {"value": "0", "label": "Skills Mastered"}
        ],
        action_url=url_for("student_profile"),
        action_text="Update My Skills",
        dashboard_url=url_for("student_dashboard")
    )


@app.route("/student-achievements")
def student_achievements():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "feature.html",
        icon="🏆",
        title="Achievements",
        description="Showcase verified achievements and career milestones.",
        heading="Your Achievements",
        content="Your achievements, certifications, projects and milestones can be showcased here as you build your academic and professional profile.",
        stats=[
            {"value": "0", "label": "Achievements"},
            {"value": "0", "label": "Certifications"},
            {"value": "0", "label": "Projects"}
        ],
        action_url=url_for("student_profile"),
        action_text="Update Profile",
        dashboard_url=url_for("student_dashboard")
    )


@app.route("/student-profile", methods=["GET", "POST"])
def student_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "student":
        return redirect(url_for("alumni_dashboard"))

    conn = get_db()

    if request.method == "POST":
        name = request.form["name"].strip()
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        course = request.form.get("course", "").strip()
        skills = request.form.get("skills", "").strip()

        existing_username = conn.execute("""
            SELECT id FROM users
            WHERE username = ?
            AND id != ?
        """, (
            username,
            session["user_id"]
        )).fetchone()

        existing_email = conn.execute("""
            SELECT id FROM users
            WHERE email = ?
            AND id != ?
        """, (
            email,
            session["user_id"]
        )).fetchone()

        if existing_username:
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (session["user_id"],)
            ).fetchone()

            conn.close()

            return render_template(
                "student_profile.html",
                user=user,
                error="Username is already taken."
            )

        if existing_email:
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (session["user_id"],)
            ).fetchone()

            conn.close()

            return render_template(
                "student_profile.html",
                user=user,
                error="Email is already registered."
            )

        conn.execute("""
            UPDATE users
            SET name = ?,
                username = ?,
                email = ?,
                course = ?,
                skills = ?
            WHERE id = ?
        """, (
            name,
            username,
            email,
            course,
            skills,
            session["user_id"]
        ))

        conn.commit()

        user = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

        conn.close()

        session["name"] = user["name"]
        session["username"] = user["username"]
        session["email"] = user["email"]

        return render_template(
            "student_profile.html",
            user=user,
            success="Profile updated successfully."
        )

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template(
        "student_profile.html",
        user=user
    )


@app.route("/alumni-messages")
def alumni_messages():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "alumni":
        return redirect(url_for("student_dashboard"))

    conn = get_db()

    students = conn.execute("""
        SELECT DISTINCT
            users.id,
            users.name,
            users.course,
            users.skills
        FROM users
        JOIN mentorship_requests
        ON users.id = mentorship_requests.student_id
        WHERE mentorship_requests.alumni_id = ?
        AND mentorship_requests.status = 'Accepted'
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "feature.html",
        icon="💬",
        title="Messages",
        description="Connect with students you are mentoring.",
        heading="Your Mentorship Conversations",
        content="Open an accepted mentorship conversation to communicate directly with a student.",
        stats=[
            {"value": str(len(students)), "label": "Active Mentorships"}
        ],
        action_url=url_for("alumni_requests"),
        action_text="View Requests",
        dashboard_url=url_for("alumni_dashboard")
    )


@app.route("/alumni-achievements")
def alumni_achievements():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "alumni":
        return redirect(url_for("student_dashboard"))

    return render_template(
        "feature.html",
        icon="🏆",
        title="My Achievements",
        description="Showcase your professional achievements and experience.",
        heading="Your Professional Achievements",
        content="Add certifications, awards, projects and career milestones to demonstrate your experience to students.",
        stats=[
            {"value": "0", "label": "Achievements"},
            {"value": "0", "label": "Certifications"},
            {"value": "0", "label": "Projects"}
        ],
        action_url=url_for("alumni_profile"),
        action_text="Update Profile",
        dashboard_url=url_for("alumni_dashboard")
    )


@app.route("/alumni-profile", methods=["GET", "POST"])
def alumni_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "alumni":
        return redirect(url_for("student_dashboard"))

    conn = get_db()

    if request.method == "POST":
        name = request.form["name"].strip()
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        company = request.form.get("company", "").strip()
        skills = request.form.get("skills", "").strip()

        existing_username = conn.execute("""
            SELECT id FROM users
            WHERE username = ?
            AND id != ?
        """, (
            username,
            session["user_id"]
        )).fetchone()

        existing_email = conn.execute("""
            SELECT id FROM users
            WHERE email = ?
            AND id != ?
        """, (
            email,
            session["user_id"]
        )).fetchone()

        if existing_username:
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (session["user_id"],)
            ).fetchone()

            conn.close()

            return render_template(
                "alumni_profile.html",
                user=user,
                error="Username is already taken."
            )

        if existing_email:
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (session["user_id"],)
            ).fetchone()

            conn.close()

            return render_template(
                "alumni_profile.html",
                user=user,
                error="Email is already registered."
            )

        conn.execute("""
            UPDATE users
            SET name = ?,
                username = ?,
                email = ?,
                company = ?,
                skills = ?
            WHERE id = ?
        """, (
            name,
            username,
            email,
            company,
            skills,
            session["user_id"]
        ))

        conn.commit()

        user = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

        conn.close()

        session["name"] = user["name"]
        session["username"] = user["username"]
        session["email"] = user["email"]

        return render_template(
            "alumni_profile.html",
            user=user,
            success="Profile updated successfully."
        )

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template(
        "alumni_profile.html",
        user=user
    )


@app.route("/analytics")
def analytics():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "alumni":
        return redirect(url_for("student_dashboard"))

    conn = get_db()

    total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM mentorship_requests
        WHERE alumni_id = ?
    """, (
        session["user_id"],
    )).fetchone()["count"]

    accepted = conn.execute("""
        SELECT COUNT(*) AS count
        FROM mentorship_requests
        WHERE alumni_id = ?
        AND status = 'Accepted'
    """, (
        session["user_id"],
    )).fetchone()["count"]

    pending = conn.execute("""
        SELECT COUNT(*) AS count
        FROM mentorship_requests
        WHERE alumni_id = ?
        AND status = 'Pending'
    """, (
        session["user_id"],
    )).fetchone()["count"]

    conn.close()

    return render_template(
        "feature.html",
        icon="📊",
        title="Mentorship Impact",
        description="See how your mentorship is helping students.",
        heading="Your Mentorship Impact",
        content="Track your mentorship requests and see how many students you are currently helping.",
        stats=[
            {"value": str(total), "label": "Total Requests"},
            {"value": str(accepted), "label": "Accepted"},
            {"value": str(pending), "label": "Pending"}
        ],
        action_url=url_for("alumni_requests"),
        action_text="View Requests",
        dashboard_url=url_for("alumni_dashboard")
    )


@app.route("/settings")
def settings():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "feature.html",
        icon="⚙️",
        title="Settings",
        description="Manage your AlumniConnect account.",
        heading="Account Settings",
        content="Your account settings will allow you to manage your account preferences, password and privacy options.",
        action_url=url_for("forgot_password"),
        action_text="Change Password",
        dashboard_url=url_for("alumni_dashboard")
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5002)
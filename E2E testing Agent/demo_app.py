"""
Demo Flask Application for E2E Testing Agent
=============================================
A simple registration form web app used as a demo target
for the E2E Testing Agent. Start this app before running
tests against it.

Usage:
    python demo_app.py

The app will be available at http://localhost:5000
"""

from flask import Flask, request, render_template_string

app = Flask(__name__)

# ---------------------------------------------------------------------------
# HTML Templates
# ---------------------------------------------------------------------------
REGISTRATION_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Demo Registration Form</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            padding: 2.5rem;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 420px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 0.5rem;
            font-size: 1.8rem;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }
        .form-group {
            margin-bottom: 1.2rem;
        }
        label {
            display: block;
            margin-bottom: 0.4rem;
            color: #555;
            font-weight: 600;
            font-size: 0.9rem;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 0.85rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1.05rem;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.3s;
            margin-top: 0.5rem;
        }
        button:hover { opacity: 0.9; }
        .error {
            background: #ffe6e6;
            color: #cc0000;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📝 Register</h1>
        <p class="subtitle">Create your account</p>
        {% if error %}
        <div class="error" data-testid="error-message">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/register">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username"
                       data-testid="username-input"
                       placeholder="Enter your username" required>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password"
                       data-testid="password-input"
                       placeholder="Enter your password" required>
            </div>
            <div class="form-group">
                <label for="confirm_password">Confirm Password</label>
                <input type="password" id="confirm_password"
                       name="confirm_password"
                       data-testid="confirm-password-input"
                       placeholder="Confirm your password" required>
            </div>
            <button type="submit" data-testid="register-button">
                Register
            </button>
        </form>
    </div>
</body>
</html>
"""

SUCCESS_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration Successful</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            padding: 3rem;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            text-align: center;
            max-width: 420px;
        }
        .checkmark { font-size: 4rem; margin-bottom: 1rem; }
        h1 { color: #333; margin-bottom: 0.5rem; }
        p { color: #666; margin-bottom: 1.5rem; }
        .username {
            font-weight: 700;
            color: #56ab2f;
        }
        a {
            display: inline-block;
            padding: 0.7rem 2rem;
            background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="checkmark">✅</div>
        <h1 data-testid="success-title">Registration Successful!</h1>
        <p>Welcome, <span class="username" data-testid="username-display">{{ username }}</span>!</p>
        <a href="/">Back to Home</a>
    </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Render the registration form."""
    return render_template_string(REGISTRATION_PAGE, error=None)


@app.route("/register", methods=["POST"])
def register():
    """Handle registration form submission."""
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Validation
    if not username:
        return render_template_string(
            REGISTRATION_PAGE, error="Username is required."
        )
    if len(username) < 3:
        return render_template_string(
            REGISTRATION_PAGE,
            error="Username must be at least 3 characters long.",
        )
    if not password:
        return render_template_string(
            REGISTRATION_PAGE, error="Password is required."
        )
    if len(password) < 6:
        return render_template_string(
            REGISTRATION_PAGE,
            error="Password must be at least 6 characters long.",
        )
    if password != confirm_password:
        return render_template_string(
            REGISTRATION_PAGE, error="Passwords do not match."
        )

    return render_template_string(SUCCESS_PAGE, username=username)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Demo Registration App running at http://localhost:5000")
    print("   Use this as a target URL for the E2E Testing Agent.")
    print("   Press Ctrl+C to stop.\n")
    app.run(host="0.0.0.0", port=5000, debug=True)

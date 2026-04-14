# GameWear

GameWear is a Django web application that provides secure user authentication
using email and OTP verification.


## About the Project

This project is built to learn and implement Django authentication.
It includes email-based login, OTP verification for signup and
forgot password, and a reusable OTP system.

## Features

- User signup with email OTP verification
- Secure login using email and password
- Forgot password with OTP
- Reusable OTP system
- User dashboard
- Admin panel

## Project Structure

- users app: handles authentication and dashboard
- otp app: handles OTP generation, verification, and expiry
- templates: HTML pages
- settings.py: project configuration
## Tech Stack

- Python
- Django
- HTML & CSS
- SQLite / PostgreSQL
- Gmail SMTP

## Installation

1. Clone the repository
2. Create a virtual environment
3. Install dependencies
4. Run migrations
5. Start the server
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver


---

## 7️⃣ Explain How Login & OTP Works (Very Important)

This shows **real understanding**.

**Example**
```md
## Authentication Flow

- User signs up with email and password
- OTP is sent to email
- User verifies OTP
- Account becomes active
- User can log in and access dashboard

## Environment Variables

This project uses environment variables for security:

- SECRET_KEY
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD
- GOOGLE_CLIENT_ID

## Author

Name: Appu  
Country: India  
Purpose: Learning Django

## Note

This project is created for learning purposes.
You are free to modify and reuse it.

# 💬 LinguaBridge Hub SaaS

**LinguaBridge Hub** is a multilingual SaaS platform built with Flask.

---

## Features
- Learn Spanish, French, German, Italian
- 120 modules with quizzes
- API endpoints
- Free deployment on Render

---

## How to Deploy
1. Push this folder to a new GitHub repo.
2. Sign up at [Render](https://render.com).
3. Click **New → Web Service**.
4. Connect your GitHub repo.
5. Choose **Free Instance**.
6. Build Command: `pip install -r requirements.txt`
7. Start Command: `gunicorn app:app`
8. Click **Create Web Service** → Render deploys your SaaS.

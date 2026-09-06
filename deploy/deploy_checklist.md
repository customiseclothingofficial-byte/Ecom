# Deploying Customise Clothing on a PaaS (Railway / Render / PythonAnywhere)

The repo is now production-ready: hardened `settings.py`, whitenoise static files,
gunicorn, tracked migrations, and COD checkout that works without Razorpay.

---

## Recommended: Railway (simplest for Django + Postgres)

1. Push this repo to GitHub (if not already).
2. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**.
3. In the service → **Variables** tab, add:
   ```
   SECRET_KEY=<long random string>
   DEBUG=False
   ALLOWED_HOSTS=customiseclothing.in,www.customiseclothing.in,<your-app>.up.railway.app
   SECURE_SSL_REDIRECT=True
   DATABASE_URL=<auto-injected if you add the Postgres plugin>
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST_USER=<your gmail>
   EMAIL_HOST_PASSWORD=<gmail app password>
   ADMIN_EMAIL=<your email>
   ```
4. Add **PostgreSQL** from the "New → Database" menu — Railway injects `DATABASE_URL` automatically.
5. Railway auto-detects Django. If asked, the start command is:
   ```
   gunicorn ecommerce_project.wsgi:application
   ```
   (config in `deploy/gunicorn.conf.py` is used automatically when present)
6. Run once in the Railway shell / or locally against the prod DB:
   ```
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```
7. Add a custom domain: Settings → Networking → Custom Domain → point the CNAME it
   shows to `customiseclothing.in` (and `www`) in your DNS provider. Railway issues
   HTTPS certificates automatically.

## Render (alternative)

- Create a **PostgreSQL** instance, copy the "Internal Database URL".
- Create a **Web Service** from the repo:
  - Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
  - Start command: `gunicorn ecommerce_project.wsgi:application -c deploy/gunicorn.conf.py`
  - Add the same env vars as above + `DATABASE_URL`.
- Add custom domain under Settings → same CNAME flow.

## PythonAnywhere (alternative)

- Uses its own web UI instead of gunicorn: Web tab → set source dir, virtualenv,
  WSGI file to `ecommerce_project.wsgi`. Static files mapping:
  URL `/static/` → `staticfiles/`. Free tier won't do custom domains properly —
  use a paid tier for a real shop.

---

## Before announcing the store is live, do these:

- [ ] `DEBUG=False` in the platform env (the single most important flag)
- [ ] Set a strong random `SECRET_KEY` (not the dev one). Generate:
      `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] Add your real domain to `ALLOWED_HOSTS` (comma-separated, no scheme)
- [ ] Run `migrate` + `collectstatic` + `createsuperuser` against the prod DB
- [ ] Test checkout end-to-end with **COD** — place a real order, check the
      success page, admin order list, and confirmation email
- [ ] Set up daily DB backup (Railway/Render: enable in dashboard; or cron `pg_dump`)
- [ ] `journalctl`/platform logs reviewed — no `500`s on the main flows
- [ ] When you're ready for online payments later: put `rzp_live_...` keys in env —
      checkout will automatically show the "Pay Online" option again (no code change needed)

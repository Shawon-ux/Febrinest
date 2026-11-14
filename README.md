# Febrinest – Django clothing store

## Run locally (Windows)
```
venv\Scripts\activate
python manage.py migrate
python manage.py createsuperuser     # this becomes your ADMIN (needs phone, email, full name)
python manage.py runserver
```
- Shop: http://127.0.0.1:8000/  ·  Admin panel: http://127.0.0.1:8000/dashboard/
- First steps as admin: **Sections** → add "Shirts", "Pants" → **Products** → add products → **Delivery & payment** → set bKash/Nagad numbers.

## Deploy (Render / Railway / Heroku)
Set env vars: `DEBUG=0`, `SECRET_KEY=<long random>`, `ALLOWED_HOSTS=yourdomain.com`,
`CSRF_TRUSTED_ORIGINS=https://yourdomain.com`, `DATABASE_URL=<postgres url>`.
- Build command: `./build.sh`   Start command: `gunicorn febricon.wsgi`
- Uploaded product images are saved in `MEDIA_ROOT` (env var). Free hosts wipe disk on redeploy →
  attach a persistent disk and point `MEDIA_ROOT` at it (or move images to Cloudinary/S3).

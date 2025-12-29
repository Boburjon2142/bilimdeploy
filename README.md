# Kitob do'koni (Django 5)

## O'rnatish
1. Python 3.12 o'rnating.
2. Virtual muhit: `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\\Scripts\\activate`).
3. Kutubxonalar: `pip install -r requirements.txt`.
4. Migratsiyalar: `python manage.py migrate`.
5. Admin yaratish: `python manage.py createsuperuser`.
6. Statik/mediaga papkalar: `backend/static/`, `backend/media/` mavjud.
7. Server: `python manage.py runserver`.

### Yetkazib berish sozlamalari
.env dagi muhim kalitlar:
- `SHOP_LAT`, `SHOP_LNG` — ombor koordinatalari.
- `DELIVERY_BASE_FEE_UZS`, `DELIVERY_PER_KM_FEE_UZS`, `DELIVERY_MIN_FEE_UZS`, `DELIVERY_MAX_FEE_UZS`.
- `DELIVERY_FREE_OVER_UZS` (ixtiyoriy, umumiy summa shu qiymatdan katta bo‘lsa yetkazib berish bepul).

### Telegram bot (yangi buyurtmalar xabari)
Checkout orqali xaridor yuborgan yangi buyurtma yaratilganda Telegram botga avtomatik xabar yuboriladi.

.env da sozlang:
- `TELEGRAM_SEND_ORDERS=True`
- `TELEGRAM_BOT_TOKEN=<token>`
- `TELEGRAM_CHAT_ID=<chat_id>` (yoki bir nechta: `-100123,12345`)

Eslatma: botni chat/channelga qo‘shib, u yerdan `chat_id` ni oling (oddiy chatlarda raqam, channel/supergrouplarda odatda `-100...`).

Test yuborish:
- `python manage.py telegram_test --text "Salom, test"`

## Foydali URL lar
- Bosh sahifa: `/`
- Kategoriya: `/kategoriya/<slug>/`
- Kitob: `/kitob/<id>/<slug>/`
- Qidiruv: `/qidiruv/?q=...`
- Savat: `/savat/`
- Buyurtma: `/buyurtma/`
- Admin: `/admin/`

## Tuzilma (asosiy papkalar/fayllar)
```
bookstore/
├─ manage.py
├─ requirements.txt
├─ .env                # lokal sozlamalar (DEBUG, DB, ALLOWED_HOSTS)
├─ backend/
│  └─ backend/         # Django settings/urls/wsgi/asgi
├─ apps/
│  ├─ catalog/         # katalog va mahsulotlar
│  └─ orders/          # buyurtma, savat, yetkazish
├─ templates/          # umumiy HTML shablonlar
├─ static/             # frontend assetlar (dev)
└─ media/              # yuklangan fayllar (dev)
```

## PythonAnywhere'ga deploy (minimal yo'riqnoma)
1. **Repositoryni yuklash**: repo'ni zip/tar yoki git clone orqali PythonAnywhere ichiga joylang.
2. **Virtualenv**: `python -m venv venv && source venv/bin/activate` (Windows yo‘q, bash ichida).
3. **Kutubxonalar**: `pip install -r requirements.txt`.
4. **Env**: `.env` ni `.env.example` dan ko‘chirib to‘ldiring (DEBUG=False, production key). Minimal:
   ```
   DJANGO_SECRET_KEY=prod-secret
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=<username>.pythonanywhere.com
   DJANGO_CSRF_TRUSTED_ORIGINS=https://<username>.pythonanywhere.com
   DJANGO_SECURE_SSL_REDIRECT=False  # HTTPS yo‘q bo‘lsa False qiling
   DJANGO_SESSION_COOKIE_SECURE=False
   DJANGO_CSRF_COOKIE_SECURE=False
   ```
5. **Migratsiya**: `python manage.py migrate` (virtualenv ichida).
6. **Statik fayllar**: `python manage.py collectstatic --noinput` -> natija `staticfiles/` ichida.
7. **WSGI**: PythonAnywhere WSGI faylida `project_root = '/home/<username>/bookstore'` va
   ```
   import sys, os
   sys.path.append(project_root)
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.backend.settings')
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
8. **Web app sozlash**: domain `<username>.pythonanywhere.com`, static mapping:
   - URL: `/static/` -> `/home/<username>/bookstore/staticfiles`
   - URL: `/media/` -> `/home/<username>/bookstore/media` (agar kerak bo‘lsa)
9. **Reload**: PythonAnywhere web dashboarddan “Reload” bosing.

## cPanel/Passenger (aHost) uchun deploy
1. **Upload**: loyihani serverga joylang (masalan: `/home/<cpanel_user>/bilimdeploy`).
2. **Virtualenv**: cPanel → Setup Python App orqali Python 3.12 app yarating va project root'ni tanlang.
3. **Kutubxonalar**: app venv ichida `pip install -r requirements.txt`.
4. **Env**: `.env.example` ni `.env` ga ko‘chiring va prod qiymatlarni kiriting:
   - `DJANGO_DEBUG=False`
   - `DJANGO_ALLOWED_HOSTS=bilimstore.uz,www.bilimstore.uz`
   - `DJANGO_CSRF_TRUSTED_ORIGINS=https://bilimstore.uz,https://www.bilimstore.uz`
5. **DB**: `DATABASE_URL` ni prod DB ga sozlang (Postgres tavsiya).
   - Agar MySQL ishlatsangiz, `mysqlclient` paketini o‘rnating va `DATABASE_URL` ni moslang.
6. **Static**: `python manage.py collectstatic --noinput`
7. **cPanel static mapping**:
   - `/static/` → `/home/<cpanel_user>/bilimdeploy/staticfiles`
   - `/media/` → `/home/<cpanel_user>/bilimdeploy/media`
8. **Passenger**:
   - `passenger_wsgi.py` repo ichida; u avtomatik project root'ni oladi.
   - `public_html/.htaccess` ichida `PassengerEnabled on` bo‘lishi kerak (namuna `.htaccess` faylida).
9. **Restart**: cPanel “Setup Python App” sahifasida “Restart” bosing.

## Eslatma
- Prod uchun HTTPS bo‘lsa, `DJANGO_SECURE_SSL_REDIRECT=True` va cookie secure flaglarini True qiling.
- Postgres ishlatmoqchi bo‘lsangiz, `.env` da `DJANGO_DB_ENGINE=postgres` va POSTGRES_* ni to‘ldiring.

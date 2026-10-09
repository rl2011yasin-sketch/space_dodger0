# Space Dodger — نسخه اندروید

نسخه‌ی بازطراحی‌شده‌ی بازی Pygame برای موبایل (با Kivy) که با Buildozer به APK قابل نصب تبدیل می‌شود.

## کنترل‌ها
- **لمس و کشیدن هر نقطه از صفحه**: جوی‌استیک شناور برای حرکت کشتی
- **دکمه BOOST** (پایین سمت راست): افزایش سرعت (هم‌زمان با جوی‌استیک، چندلمسی)
- **دکمه ⏸ بالا سمت راست / دکمه Back گوشی**: توقف
- ضربه روی صفحه: شروع، ادامه بعد از توقف، شروع دوباره بعد از باخت
- (تست روی کامپیوتر: WASD یا جهت‌نما، Shift = بوست، P = توقف، Enter = شروع)

## ساخت APK — روش ۱: GitHub Actions (بدون نصب هیچ‌چیز)
1. یک مخزن (repository) جدید در GitHub بسازید و **همه‌ی فایل‌های این پوشه** (از جمله پوشه‌ی `.github`) را در آن آپلود کنید.
2. به تب **Actions** بروید و workflow با نام **Build Android APK** را اجرا کنید (Run workflow). اولین ساخت حدود ۲۰ تا ۴۰ دقیقه طول می‌کشد.
3. پس از پایان، از بخش **Artifacts** فایل `SpaceDodger-apk` را دانلود کنید؛ داخل آن فایل `.apk` است.

## ساخت APK — روش ۲: روی لینوکس / WSL (اوبونتو)
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf automake libtool \
  pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
pip install --upgrade buildozer cython virtualenv
buildozer -v android debug          # خروجی: bin/spacedodger-1.0.0-*-debug.apk
```
اتصال گوشی با USB و فعال بودن USB Debugging: `buildozer android debug deploy run`

## نصب روی گوشی
فایل APK را به گوشی منتقل کنید، آن را باز کنید و در صورت پرسش، «نصب از منابع ناشناس» را برای همان برنامه (مرورگر/مدیر فایل) مجاز کنید.

## اجرای آزمایشی روی کامپیوتر
```bash
pip install kivy
python main.py
python -m unittest discover -s tests -v   # تست‌های منطق بازی
```

## ساختار پروژه
- `engine.py` — منطق بازی (مستقل از رندر؛ تست‌پذیر)
- `main.py` — رابط Kivy: رندر، ورودی لمسی، منو/توقف/پایان بازی
- `storage.py` — ذخیره‌ی رکورد در پوشه‌ی داده‌ی برنامه
- `buildozer.spec` — تنظیمات بسته‌بندی اندروید
- `tests/` — تست‌های واحد

# استخدام Python 3.11 كصورة أساسية
FROM python:3.11-slim

# تعيين متغير البيئة لتجنب إنشاء ملفات .pyc
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# تحديث النظام وتثبيت الأدوات المطلوبة
RUN apt-get update && apt-get install -y \
    util-linux \
    procps \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مجلد العمل
WORKDIR /app

# نسخ ملف المتطلبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ الكود
COPY bot.py .

# تشغيل البوت
CMD ["python", "bot.py"]

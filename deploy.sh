#!/bin/bash

# سكريبت نشر بوت مراقبة VPS
# يقوم بجلب المشروع من GitHub وتشغيله

set -e

# متغيرات قابلة للتخصيص
GITHUB_USERNAME="your-github-username"
GITHUB_TOKEN="your-github-token"
REPO_NAME="telegram-vps-bot"
BOT_TOKEN="your-bot-token"
ADMIN_CHAT_ID="your-admin-chat-id"

# ألوان للعرض
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 بدء نشر بوت مراقبة VPS${NC}"

# التحقق من وجود Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker غير مثبت. يرجى تثبيت Docker أولاً${NC}"
    exit 1
fi

# التحقق من وجود Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose غير مثبت. يرجى تثبيت Docker Compose أولاً${NC}"
    exit 1
fi

# التحقق من وجود Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git غير مثبت. يرجى تثبيت Git أولاً${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 قراءة المتغيرات...${NC}"

# قراءة المتغيرات من المستخدم إذا لم تكن محددة
if [ -z "$GITHUB_USERNAME" ] || [ "$GITHUB_USERNAME" = "your-github-username" ]; then
    read -p "أدخل اسم المستخدم في GitHub: " GITHUB_USERNAME
fi

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "your-github-token" ]; then
    read -s -p "أدخل رمز GitHub Token: " GITHUB_TOKEN
    echo
fi

if [ -z "$BOT_TOKEN" ] || [ "$BOT_TOKEN" = "your-bot-token" ]; then
    read -s -p "أدخل Telegram Bot Token: " BOT_TOKEN
    echo
fi

if [ -z "$ADMIN_CHAT_ID" ] || [ "$ADMIN_CHAT_ID" = "your-admin-chat-id" ]; then
    read -p "أدخل Chat ID للأدمن: " ADMIN_CHAT_ID
fi

# إنشاء مجلد المشروع
PROJECT_DIR="/opt/telegram-vps-bot"
echo -e "${YELLOW}📁 إنشاء مجلد المشروع: $PROJECT_DIR${NC}"

sudo mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# حذف المجلد إذا كان موجوداً
if [ -d ".git" ]; then
    echo -e "${YELLOW}🗑️ حذف المشروع القديم...${NC}"
    sudo rm -rf .git
    sudo rm -rf *
fi

# جلب المشروع من GitHub
echo -e "${YELLOW}📦 جلب المشروع من GitHub...${NC}"
git clone https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/${REPO_NAME}.git .

# إنشاء ملف .env
echo -e "${YELLOW}⚙️ إنشاء ملف التكوين...${NC}"
cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_CHAT_ID=${ADMIN_CHAT_ID}
EOF

# التأكد من الصلاحيات
sudo chown -R $(whoami):$(whoami) $PROJECT_DIR
chmod +x deploy.sh

# إيقاف الحاوية إذا كانت تعمل
echo -e "${YELLOW}🛑 إيقاف الحاويات السابقة...${NC}"
docker-compose down 2>/dev/null || true

# بناء وتشغيل الحاوية
echo -e "${YELLOW}🔨 بناء الحاوية...${NC}"
docker-compose build --no-cache

echo -e "${YELLOW}🚀 تشغيل البوت...${NC}"
docker-compose up -d

# التحقق من حالة البوت
sleep 5
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✅ تم نشر البوت بنجاح!${NC}"
    echo -e "${GREEN}📊 البوت يعمل الآن ويرسل إحصائيات VPS${NC}"
    echo -e "${BLUE}🔍 لمشاهدة السجلات: docker-compose logs -f${NC}"
    echo -e "${BLUE}🛑 لإيقاف البوت: docker-compose down${NC}"
    echo -e "${BLUE}🔄 لإعادة تشغيل البوت: docker-compose restart${NC}"
else
    echo -e "${RED}❌ فشل في تشغيل البوت${NC}"
    echo -e "${RED}📋 السجلات:${NC}"
    docker-compose logs
    exit 1
fi

# إعداد الخدمة للتشغيل التلقائي
echo -e "${YELLOW}⚙️ إعداد الخدمة للتشغيل التلقائي...${NC}"

sudo tee /etc/systemd/system/telegram-vps-bot.service > /dev/null << EOF
[Unit]
Description=Telegram VPS Monitoring Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=true
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy

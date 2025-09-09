#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram VPS Monitoring Bot
A simple bot that sends comprehensive VPS statistics.
To install dependencies, run:
pip install python-telegram-bot psutil aiohttp
"""

import asyncio
import psutil
import platform
import datetime
import os
import subprocess
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# ==============================================================================
# == إعدادات البوت - BOT CONFIGURATION ==
# ==============================================================================
# ضع التوكن الخاص بالبوت الذي حصلت عليه من BotFather
# Telegram Bot Token from BotFather
BOT_TOKEN = "8062387392:AAHq6rc0Tw9Dih5ZLcGgueoHYSQ1jPLW3fk"

# ضع معرف المحادثة (Chat ID) الخاص بالأدمن ليستقبل الإشعارات والتقارير
# Chat ID for the Admin
ADMIN_CHAT_ID = 1689039862
# ==============================================================================

# إعداد التسجيل لعرض معلومات التشغيل والأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VPSMonitor:
    """
    هذا الكلاس مسؤول عن جمع كافة معلومات وإحصائيات السيرفر.
    """
    def __init__(self):
        """يبدأ تايمر وقت تشغيل البوت عند إنشاء الكائن."""
        self.start_time = datetime.datetime.now()

    def bytes_to_human(self, bytes_value: int) -> str:
        """تحويل البايتات إلى وحدات قابلة للقراءة (KB, MB, GB)."""
        if bytes_value is None:
            return "N/A"
        try:
            power = 1024
            n = 0
            power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
            while bytes_value >= power and n < len(power_labels):
                bytes_value /= power
                n += 1
            return f"{bytes_value:.2f} {power_labels[n]}B"
        except Exception:
            return "N/A"

    def get_system_info(self) -> dict:
        """جمع معلومات النظام الأساسية."""
        try:
            system_info = {
                'نظام التشغيل': f"{platform.system()} {platform.release()}",
                'إصدار النظام': platform.version(),
                'معمارية النظام': platform.machine(),
                'اسم المضيف': platform.node(),
                'المعالج': platform.processor() or "غير معروف"
            }
            try:
                cpu_info_output = subprocess.check_output(['lscpu'], universal_newlines=True)
                for line in cpu_info_output.split('\n'):
                    if 'Model name' in line:
                        system_info['نموذج المعالج'] = line.split(':')[1].strip()
                        break
            except Exception:
                pass  # lscpu might not be available
            return system_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات النظام: {e}")
            return {}

    def get_cpu_info(self) -> dict:
        """جمع معلومات المعالج."""
        try:
            cpu_info = {
                'نسبة استخدام المعالج': f"{psutil.cpu_percent(interval=1):.1f}%",
                'عدد النوى الفيزيائية': psutil.cpu_count(logical=False),
                'عدد النوى المنطقية': psutil.cpu_count(logical=True),
            }
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                cpu_info.update({
                    'تردد المعالج الحالي': f"{cpu_freq.current:.0f} MHz",
                    'أقصى تردد': f"{cpu_freq.max:.0f} MHz",
                    'أقل تردد': f"{cpu_freq.min:.0f} MHz"
                })
            return cpu_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات المعالج: {e}")
            return {}

    def get_memory_info(self) -> dict:
        """جمع معلومات الذاكرة (RAM) والذاكرة المؤقتة (Swap)."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            return {
                'إجمالي الذاكرة': self.bytes_to_human(memory.total),
                'الذاكرة المستخدمة': self.bytes_to_human(memory.used),
                'الذاكرة المتاحة': self.bytes_to_human(memory.available),
                'نسبة استخدام الذاكرة': f"{memory.percent:.1f}%",
                'Swap الإجمالي': self.bytes_to_human(swap.total),
                'Swap المستخدم': self.bytes_to_human(swap.used),
                'نسبة استخدام Swap': f"{swap.percent:.1f}%"
            }
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات الذاكرة: {e}")
            return {}

    def get_disk_info(self) -> dict:
        """جمع معلومات الأقراص الصلبة."""
        disk_info = {}
        try:
            partitions = psutil.disk_partitions()
            for i, p in enumerate(partitions, 1):
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    disk_info[f'القرص {i} ({p.device})'] = (
                        f"الحجم: {self.bytes_to_human(usage.total)}, "
                        f"المستخدم: {self.bytes_to_human(usage.used)} ({usage.percent}%)"
                    )
                except (PermissionError, FileNotFoundError):
                    continue
            disk_io = psutil.disk_io_counters()
            if disk_io:
                disk_info['إحصائيات I/O'] = (
                    f"قراءة: {self.bytes_to_human(disk_io.read_bytes)}, "
                    f"كتابة: {self.bytes_to_human(disk_io.write_bytes)}"
                )
            return disk_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات القرص: {e}")
            return disk_info # Return what we have

    def get_network_info(self) -> dict:
        """جمع معلومات الشبكة."""
        try:
            net_io = psutil.net_io_counters()
            network_info = {
                'البيانات المرسلة': self.bytes_to_human(net_io.bytes_sent),
                'البيانات المستقبلة': self.bytes_to_human(net_io.bytes_recv),
            }
            interfaces = psutil.net_if_addrs()
            for name, addrs in interfaces.items():
                for addr in addrs:
                    if addr.family == 2: # AF_INET (IPv4)
                        network_info[f'واجهة {name}'] = f"IP: {addr.address}"
                        break
            return network_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات الشبكة: {e}")
            return {}

    def get_process_info(self) -> dict:
        """جمع معلومات عن العمليات قيد التشغيل."""
        try:
            processes = [p.info for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent', 'pid'])]
            top_cpu = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:5]
            
            process_info = {
                'إجمالي العمليات': len(psutil.pids()),
                'أهم العمليات (CPU)': "\n".join([
                    f"  - `{p['name']}` (CPU: {p['cpu_percent']:.1f}%, RAM: {p['memory_percent']:.1f}%)" for p in top_cpu
                ])
            }
            return process_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات العمليات: {e}")
            return {}

    def get_uptime_info(self) -> dict:
        """جمع معلومات وقت التشغيل للنظام والبوت."""
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            system_uptime = datetime.datetime.now() - boot_time
            bot_uptime = datetime.datetime.now() - self.start_time
            return {
                'مدة تشغيل النظام': str(system_uptime).split('.')[0],
                'مدة تشغيل البوت': str(bot_uptime).split('.')[0],
                'الوقت الحالي': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات وقت التشغيل: {e}")
            return {}

    def get_temperature_info(self) -> dict:
        """جمع معلومات درجة الحرارة (إن توفرت)."""
        temp_info = {}
        if hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                if not temps:
                    return {}
                for name, entries in temps.items():
                    for entry in entries:
                        label = entry.label or 'الأساسي'
                        temp_info[f'{name} - {label}'] = f"{entry.current:.1f}°C"
                return temp_info
            except Exception:
                return {}
        return {}
    
    async def get_full_report(self) -> str:
        """تجميع كل المعلومات في تقرير نصي واحد."""
        sections = {
            '🖥️ *معلومات النظام*': self.get_system_info(),
            '⏰ *معلومات التشغيل*': self.get_uptime_info(),
            '💻 *معلومات المعالج*': self.get_cpu_info(),
            '🧠 *معلومات الذاكرة*': self.get_memory_info(),
            '💾 *معلومات القرص الصلب*': self.get_disk_info(),
            '🌐 *معلومات الشبكة*': self.get_network_info(),
            '⚙️ *معلومات العمليات*': self.get_process_info(),
            '🌡️ *درجات الحرارة*': self.get_temperature_info(),
        }
        
        report_parts = [f"📊 *تقرير حالة السيرفر - {platform.node()}*"]
        
        for title, data in sections.items():
            if data:
                report_parts.append(f"\n{title}")
                for key, value in data.items():
                    if "\n" in str(value):
                         report_parts.append(f"  - *{key}:*\n{value}")
                    else:
                         report_parts.append(f"  - *{key}:* `{value}`")

        return "\n".join(report_parts)

class TelegramVPSBot:
    """
    هذا الكلاس مسؤول عن تشغيل بوت التليجرام ومعالجة الأوامر.
    """
    def __init__(self, token: str, admin_chat_id: int):
        """إعداد البوت بالتوكن ومعرف الأدمن."""
        if not token or not isinstance(admin_chat_id, int):
            raise ValueError("Token and Admin Chat ID must be set correctly.")
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.monitor = VPSMonitor()
        self.application = Application.builder().token(self.token).build()

    async def is_admin(self, update: Update) -> bool:
        """التحقق مما إذا كان المستخدم هو الأدمن."""
        if update.effective_user.id == self.admin_chat_id:
            return True
        else:
            await update.message.reply_text("⛔ *غير مصرح لك باستخدام هذا البوت*", parse_mode=ParseMode.MARKDOWN)
            logger.warning(f"محاولة وصول غير مصرح بها من المستخدم: {update.effective_user.id}")
            return False

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأوامر /start و /status."""
        if not await self.is_admin(update):
            return

        await update.message.reply_text("🔄 جاري جمع بيانات السيرفر، يرجى الانتظار...", parse_mode=ParseMode.MARKDOWN)
        report = await self.monitor.get_full_report()
        
        # تقسيم الرسالة إذا كانت طويلة جداً لتجنب خطأ تليجرام
        if len(report) > 4096:
            for i in range(0, len(report), 4096):
                await update.message.reply_text(report[i:i + 4096], parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

    async def send_startup_message(self):
        """إرسال رسالة عند بدء تشغيل البوت."""
        try:
            bot = Bot(token=self.token)
            startup_msg = (
                f"✅ *البوت بدأ العمل بنجاح!*\n\n"
                f"🖥️ *السيرفر:* `{platform.node()}`\n"
                f"⏰ *وقت البدء:* `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                f"📊 استخدم `/status` لعرض الإحصائيات الكاملة."
            )
            await bot.send_message(
                chat_id=self.admin_chat_id,
                text=startup_msg,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info("تم إرسال رسالة بدء التشغيل بنجاح.")
        except Exception as e:
            logger.error(f"فشل في إرسال رسالة بدء التشغيل: {e}")

    def run(self):
        """تشغيل البوت."""
        # إضافة معالجات الأوامر
        self.application.add_handler(CommandHandler("start", self.status_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # إرسال رسالة بدء التشغيل في الخلفية
        asyncio.create_task(self.send_startup_message())
        
        # تشغيل البوت
        logger.info("البوت يعمل الآن...")
        self.application.run_polling()


def main():
    """الدالة الرئيسية لتشغيل البرنامج."""
    # التأكد من وجود المتغيرات المطلوبة
    if not BOT_TOKEN:
        logger.critical("❌ خطأ فادح: متغير BOT_TOKEN غير موجود. يرجى إضافته.")
        return
    
    if not ADMIN_CHAT_ID:
        logger.critical("❌ خطأ فادح: متغير ADMIN_CHAT_ID غير صحيح. يرجى تعديله.")
        return

    try:
        bot = TelegramVPSBot(BOT_TOKEN, ADMIN_CHAT_ID)
        bot.run()
    except ValueError as e:
        logger.critical(f"خطأ في الإعدادات: {e}")
    except Exception as e:
        logger.error(f"حدث خطأ غير متوقع عند تشغيل البوت: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم.")

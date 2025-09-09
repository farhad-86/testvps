#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import psutil
import platform
import datetime
import subprocess
import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

BOT_TOKEN = "8062387392:AAHq6rc0Tw9Dih5ZLcGgueoHYSQ1jPLW3fk"
ADMIN_CHAT_ID = 1689039862

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- VPS Monitor ----------------
class VPSMonitor:
    def __init__(self):
        self.start_time = datetime.datetime.now()

    def bytes_to_human(self, bytes_value: int) -> str:
        try:
            power = 1024
            n = 0
            power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
            while bytes_value >= power and n < len(power_labels):
                bytes_value /= power
                n += 1
            return f"{bytes_value:.2f} {power_labels[n]}B"
        except:
            return "N/A"

    def get_system_info(self):
        info = {
            'نظام التشغيل': f"{platform.system()} {platform.release()}",
            'إصدار النظام': platform.version(),
            'معمارية النظام': platform.machine(),
            'اسم المضيف': platform.node(),
            'المعالج': platform.processor() or "غير معروف"
        }
        try:
            output = subprocess.check_output(['lscpu'], universal_newlines=True)
            for line in output.split('\n'):
                if 'Model name' in line:
                    info['نموذج المعالج'] = line.split(':')[1].strip()
                    break
        except:
            pass
        return info

    def get_cpu_info(self):
        cpu_info = {
            'نسبة استخدام المعالج': f"{psutil.cpu_percent(interval=1):.1f}%",
            'عدد النوى الفيزيائية': psutil.cpu_count(logical=False),
            'عدد النوى المنطقية': psutil.cpu_count(logical=True)
        }
        freq = psutil.cpu_freq()
        if freq:
            cpu_info.update({
                'تردد المعالج الحالي': f"{freq.current:.0f} MHz",
                'أقصى تردد': f"{freq.max:.0f} MHz",
                'أقل تردد': f"{freq.min:.0f} MHz"
            })
        return cpu_info

    def get_memory_info(self):
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            'إجمالي الذاكرة': self.bytes_to_human(mem.total),
            'الذاكرة المستخدمة': self.bytes_to_human(mem.used),
            'الذاكرة المتاحة': self.bytes_to_human(mem.available),
            'نسبة استخدام الذاكرة': f"{mem.percent:.1f}%",
            'Swap الإجمالي': self.bytes_to_human(swap.total),
            'Swap المستخدم': self.bytes_to_human(swap.used),
            'نسبة استخدام Swap': f"{swap.percent:.1f}%"
        }

    def get_disk_info(self):
        disks = {}
        for i, p in enumerate(psutil.disk_partitions(), 1):
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks[f'القرص {i} ({p.device})'] = f"الحجم: {self.bytes_to_human(usage.total)}, المستخدم: {self.bytes_to_human(usage.used)} ({usage.percent}%)"
            except:
                continue
        io = psutil.disk_io_counters()
        if io:
            disks['إحصائيات I/O'] = f"قراءة: {self.bytes_to_human(io.read_bytes)}, كتابة: {self.bytes_to_human(io.write_bytes)}"
        return disks

    def get_network_info(self):
        net = {}
        io = psutil.net_io_counters()
        net['البيانات المرسلة'] = self.bytes_to_human(io.bytes_sent)
        net['البيانات المستقبلة'] = self.bytes_to_human(io.bytes_recv)
        for name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == 2:
                    net[f'واجهة {name}'] = f"IP: {addr.address}"
                    break
        return net

    def get_process_info(self):
        processes = [p.info for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent'])]
        top_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
        return {
            'إجمالي العمليات': len(psutil.pids()),
            'أهم العمليات (CPU)': "\n".join([f" - `{p['name']}` CPU: {p['cpu_percent']:.1f}%, RAM: {p['memory_percent']:.1f}%" for p in top_cpu])
        }

    def get_uptime_info(self):
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        return {
            'مدة تشغيل النظام': str(datetime.datetime.now() - boot).split('.')[0],
            'مدة تشغيل البوت': str(datetime.datetime.now() - self.start_time).split('.')[0],
            'الوقت الحالي': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def get_temperature_info(self):
        temp_info = {}
        if hasattr(psutil, "sensors_temperatures"):
            try:
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    for entry in entries:
                        label = entry.label or 'الأساسي'
                        temp_info[f'{name} - {label}'] = f"{entry.current:.1f}°C"
            except:
                pass
        return temp_info

    async def get_full_report(self):
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
        parts = [f"📊 *تقرير حالة السيرفر - {platform.node()}*"]
        for title, data in sections.items():
            if data:
                parts.append(f"\n{title}")
                for key, value in data.items():
                    if "\n" in str(value):
                        parts.append(f" - *{key}:*\n{value}")
                    else:
                        parts.append(f" - *{key}:* `{value}`")
        return "\n".join(parts)

# ---------------- Telegram Bot ----------------
class TelegramVPSBot:
    def __init__(self, token, admin_chat_id):
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.monitor = VPSMonitor()
        self.application = Application.builder().token(self.token).build()

    async def is_admin(self, update: Update) -> bool:
        if update.effective_user.id == self.admin_chat_id:
            return True
        await update.message.reply_text("⛔ *غير مصرح لك*", parse_mode=ParseMode.MARKDOWN)
        return False

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_admin(update):
            return
        await update.message.reply_text("🔄 جاري جمع بيانات السيرفر...", parse_mode=ParseMode.MARKDOWN)
        report = await self.monitor.get_full_report()
        if len(report) > 4096:
            for i in range(0, len(report), 4096):
                await update.message.reply_text(report[i:i+4096], parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

    async def send_startup_message(self):
        bot = Bot(token=self.token)
        msg = f"✅ *البوت بدأ العمل بنجاح!*\n🖥️ `{platform.node()}`\n⏰ `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n📊 استخدم /status"
        await bot.send_message(chat_id=self.admin_chat_id, text=msg, parse_mode=ParseMode.MARKDOWN)

    def run(self):
        self.application.add_handler(CommandHandler("start", self.status_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        # تشغيل رسالة بدء التشغيل في الخلفية
        self.application.create_task(self.send_startup_message())
        self.application.run_polling()

# ---------------- Main ----------------
def main():
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.critical("❌ BOT_TOKEN أو ADMIN_CHAT_ID غير محدد!")
        return
    bot = TelegramVPSBot(BOT_TOKEN, ADMIN_CHAT_ID)
    bot.run()

if __name__ == "__main__":
    main()

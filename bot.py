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

# ==================================================================
# == إعدادات البوت - BOT CONFIGURATION ==
# ==================================================================
BOT_TOKEN = "8062387392:AAHq6rc0Tw9Dih5ZLcGgueoHYSQ1jPLW3fk"
ADMIN_CHAT_ID = 1689039862
# ==================================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VPSMonitor:
    def __init__(self):
        self.start_time = datetime.datetime.now()

    def bytes_to_human(self, bytes_value: int) -> str:
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
                pass
            return system_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات النظام: {e}")
            return {}

    def get_cpu_info(self) -> dict:
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
            return disk_info

    def get_network_info(self) -> dict:
        try:
            net_io = psutil.net_io_counters()
            network_info = {
                'البيانات المرسلة': self.bytes_to_human(net_io.bytes_sent),
                'البيانات المستقبلة': self.bytes_to_human(net_io.bytes_recv),
            }
            interfaces = psutil.net_if_addrs()
            for name, addrs in interfaces.items():
                for addr in addrs:
                    if addr.family == 2:
                        network_info[f'واجهة {name}'] = f"IP: {addr.address}"
                        break
            return network_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات الشبكة: {e}")
            return {}

    def get_process_info(self) -> dict:
        try:
            processes = [p.info for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent', 'pid'])]
            top_cpu = sorted(processes, key=lambda p: p['cpu_percent'], reverse=True)[:5]
            process_info = {
                'إجمالي العمليات': len(psutil.pids()),
                'أهم العمليات (CPU)': "\n".join([
                    f" - `{p['name']}` (CPU: {p['cpu_percent']:.1f}%, RAM: {p['memory_percent']:.1f}%)" for p in top_cpu
                ])
            }
            return process_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات العمليات: {e}")
            return {}

    def get_uptime_info(self) -> dict:
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
                for

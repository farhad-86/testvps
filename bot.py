#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram VPS Monitoring Bot
A simple bot that sends comprehensive VPS statistics
"""

import asyncio
import psutil
import platform
import datetime
import os
import subprocess
import json
import aiohttp
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class VPSMonitor:
    def __init__(self):
        self.start_time = datetime.datetime.now()
    
    def get_system_info(self):
        """جمع معلومات النظام الأساسية"""
        try:
            # معلومات النظام
            system_info = {
                'نظام التشغيل': f"{platform.system()} {platform.release()}",
                'إصدار النظام': platform.version(),
                'معمارية النظام': platform.machine(),
                'اسم المضيف': platform.node(),
                'المعالج': platform.processor() or "غير معروف"
            }
            
            # معلومات إضافية عن المعالج
            try:
                cpu_info = subprocess.check_output(['lscpu'], universal_newlines=True)
                cpu_lines = cpu_info.split('\n')
                for line in cpu_lines:
                    if 'Model name' in line:
                        system_info['نموذج المعالج'] = line.split(':')[1].strip()
                        break
            except:
                pass
                
            return system_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات النظام: {e}")
            return {}
    
    def get_cpu_info(self):
        """معلومات المعالج"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            
            cpu_info = {
                'نسبة استخدام المعالج': f"{cpu_percent:.1f}%",
                'عدد النوى الفيزيائية': cpu_count,
                'عدد النوى المنطقية': cpu_count_logical,
            }
            
            if cpu_freq:
                cpu_info['تردد المعالج الحالي'] = f"{cpu_freq.current:.0f} MHz"
                cpu_info['أقصى تردد'] = f"{cpu_freq.max:.0f} MHz"
                cpu_info['أقل تردد'] = f"{cpu_freq.min:.0f} MHz"
            
            # معلومات إضافية عن كل نواة
            cpu_per_core = psutil.cpu_percent(percpu=True, interval=1)
            for i, percent in enumerate(cpu_per_core):
                cpu_info[f'النواة {i+1}'] = f"{percent:.1f}%"
                
            return cpu_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات المعالج: {e}")
            return {}
    
    def get_memory_info(self):
        """معلومات الذاكرة"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_info = {
                'إجمالي الذاكرة': self.bytes_to_human(memory.total),
                'الذاكرة المستخدمة': self.bytes_to_human(memory.used),
                'الذاكرة المتاحة': self.bytes_to_human(memory.available),
                'نسبة استخدام الذاكرة': f"{memory.percent:.1f}%",
                'Swap الإجمالي': self.bytes_to_human(swap.total),
                'Swap المستخدم': self.bytes_to_human(swap.used),
                'نسبة استخدام Swap': f"{swap.percent:.1f}%"
            }
            
            return memory_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات الذاكرة: {e}")
            return {}
    
    def get_disk_info(self):
        """معلومات القرص الصلب"""
        try:
            disk_info = {}
            
            # معلومات الأقراص
            partitions = psutil.disk_partitions()
            for i, partition in enumerate(partitions):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info[f'القرص {i+1} ({partition.device})'] = {
                        'نقطة التحميل': partition.mountpoint,
                        'نظام الملفات': partition.fstype,
                        'الحجم الكامل': self.bytes_to_human(usage.total),
                        'المستخدم': self.bytes_to_human(usage.used),
                        'المتاح': self.bytes_to_human(usage.free),
                        'نسبة الاستخدام': f"{(usage.used / usage.total) * 100:.1f}%"
                    }
                except PermissionError:
                    continue
            
            # معلومات I/O للقرص
            disk_io = psutil.disk_io_counters()
            if disk_io:
                disk_info['إحصائيات I/O'] = {
                    'عدد القراءات': disk_io.read_count,
                    'عدد الكتابات': disk_io.write_count,
                    'البيانات المقروءة': self.bytes_to_human(disk_io.read_bytes),
                    'البيانات المكتوبة': self.bytes_to_human(disk_io.write_bytes),
                }
            
            return disk_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات القرص: {e}")
            return {}
    
    def get_network_info(self):
        """معلومات الشبكة"""
        try:
            network_info = {}
            
            # إحصائيات الشبكة
            net_io = psutil.net_io_counters()
            if net_io:
                network_info['إحصائيات الشبكة'] = {
                    'البيانات المرسلة': self.bytes_to_human(net_io.bytes_sent),
                    'البيانات المستقبلة': self.bytes_to_human(net_io.bytes_recv),
                    'الحزم المرسلة': net_io.packets_sent,
                    'الحزم المستقبلة': net_io.packets_recv,
                    'أخطاء الإرسال': net_io.errin,
                    'أخطاء الاستقبال': net_io.errout
                }
            
            # معلومات واجهات الشبكة
            interfaces = psutil.net_if_addrs()
            for interface_name, addresses in interfaces.items():
                if interface_name != 'lo':  # تجاهل loopback
                    for addr in addresses:
                        if addr.family == 2:  # IPv4
                            network_info[f'واجهة {interface_name}'] = {
                                'عنوان IP': addr.address,
                                'القناع الشبكي': addr.netmask
                            }
                            break
            
            return network_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات الشبكة: {e}")
            return {}
    
    def get_process_info(self):
        """معلومات العمليات"""
        try:
            process_info = {
                'إجمالي العمليات': len(psutil.pids()),
                'العمليات النشطة': len([p for p in psutil.process_iter() if p.status() == psutil.STATUS_RUNNING]),
            }
            
            # أهم 5 عمليات حسب استخدام المعالج
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc.info['cpu_percent'] = proc.cpu_percent()
                    processes.append(proc.info)
                except:
                    pass
            
            # ترتيب العمليات حسب استخدام المعالج
            top_processes = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:5]
            
            process_info['أهم العمليات (CPU)'] = {}
            for i, proc in enumerate(top_processes, 1):
                process_info['أهم العمليات (CPU)'][f'{i}. {proc["name"]}'] = {
                    'PID': proc['pid'],
                    'CPU': f"{proc['cpu_percent']:.1f}%",
                    'الذاكرة': f"{proc['memory_percent']:.1f}%"
                }
            
            return process_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات العمليات: {e}")
            return {}
    
    def get_uptime_info(self):
        """معلومات وقت التشغيل"""
        try:
            # وقت تشغيل النظام
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            system_uptime = datetime.datetime.now() - boot_time
            
            # وقت تشغيل البوت
            bot_uptime = datetime.datetime.now() - self.start_time
            
            uptime_info = {
                'وقت بدء تشغيل النظام': boot_time.strftime('%Y-%m-%d %H:%M:%S'),
                'مدة تشغيل النظام': str(system_uptime).split('.')[0],
                'وقت بدء تشغيل البوت': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'مدة تشغيل البوت': str(bot_uptime).split('.')[0],
                'الوقت الحالي': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return uptime_info
        except Exception as e:
            logger.error(f"خطأ في جمع معلومات وقت التشغيل: {e}")
            return {}
    
    def get_temperature_info(self):
        """معلومات درجة الحرارة (إن توفرت)"""
        try:
            temps = psutil.sensors_temperatures()
            temp_info = {}
            
            for name, entries in temps.items():
                for entry in entries:
                    temp_info[f'{name} - {entry.label or "الأساسي"}'] = f"{entry.current:.1f}°C"
            
            return temp_info
        except:
            return {}
    
    def bytes_to_human(self, bytes_value):
        """تحويل البايتات إلى وحدات قابلة للقراءة"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    async def get_full_report(self):
        """تجميع التقرير الكامل"""
        sections = [
            ('🖥️ معلومات النظام', self.get_system_info()),
            ('⏰ معلومات التشغيل', self.get_uptime_info()),
            ('💻 معلومات المعالج', self.get_cpu_info()),
            ('🧠 معلومات الذاكرة', self.get_memory_info()),
            ('💾 معلومات القرص الصلب', self.get_disk_info()),
            ('🌐 معلومات الشبكة', self.get_network_info()),
            ('⚙️ معلومات العمليات', self.get_process_info()),
            ('🌡️ درجات الحرارة', self.get_temperature_info()),
        ]
        
        report = "📊 *تقرير حالة السيرفر - VPS Monitoring*\n"
        report += "=" * 50 + "\n\n"
        
        for section_title, section_data in sections:
            if section_data:
                report += f"{section_title}\n"
                report += "-" * 30 + "\n"
                
                for key, value in section_data.items():
                    if isinstance(value, dict):
                        report += f"  📋 *{key}:*\n"
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, dict):
                                report += f"    • *{sub_key}:*\n"
                                for sub_sub_key, sub_sub_value in sub_value.items():
                                    report += f"      ◦ {sub_sub_key}: `{sub_sub_value}`\n"
                            else:
                                report += f"      ◦ {sub_key}: `{sub_value}`\n"
                    else:
                        report += f"  • {key}: `{value}`\n"
                report += "\n"
        
        report += "🤖 *البوت يعمل بشكل طبيعي*\n"
        report += f"📅 آخر تحديث: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        
        return report

class TelegramVPSBot:
    def __init__(self, token: str, admin_chat_id: int):
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.monitor = VPSMonitor()
        self.sent_startup_message = False
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        user_id = update.effective_user.id
        
        if user_id == self.admin_chat_id:
            report = await self.monitor.get_full_report()
            
            # تقسيم الرسالة إذا كانت طويلة جداً
            if len(report) > 4096:
                # تقسيم الرسالة إلى أجزاء
                parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
                for i, part in enumerate(parts):
                    if i == 0:
                        await update.message.reply_text(
                            part, 
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            f"🔄 *الجزء {i+1}:*\n\n{part}", 
                            parse_mode='Markdown'
                        )
            else:
                await update.message.reply_text(
                    report, 
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text("⛔ غير مصرح لك باستخدام هذا البوت")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /status"""
        await self.start_command(update, context)
    
    async def send_startup_message(self):
        """إرسال رسالة بدء التشغيل"""
        if not self.sent_startup_message:
            try:
                bot = Bot(token=self.token)
                startup_msg = f"🟢 *البوت بدأ العمل!*\n\n"
                startup_msg += f"⏰ وقت البدء: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
                startup_msg += f"🖥️ السيرفر: `{platform.node()}`\n"
                startup_msg += f"💻 النظام: `{platform.system()} {platform.release()}`\n\n"
                startup_msg += "📊 استخدم /start أو /status لعرض الإحصائيات الكاملة"
                
                await bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=startup_msg,
                    parse_mode='Markdown'
                )
                
                self.sent_startup_message = True
                logger.info("تم إرسال رسالة بدء التشغيل")
                
            except Exception as e:
                logger.error(f"خطأ في إرسال رسالة بدء التشغيل: {e}")
    
    async def run(self):
        """تشغيل البوت"""
        try:
            # إنشاء التطبيق
            application = Application.builder().token(self.token).build()
            
            # إضافة معالجات الأوامر
            application.add_handler(CommandHandler("start", self.start_command))
            application.add_handler(CommandHandler("status", self.status_command))
            
            # إرسال رسالة بدء التشغيل
            await self.send_startup_message()
            
            # تشغيل البوت
            logger.info("البوت يعمل الآن...")
            await application.run_polling()
            
        except Exception as e:
            logger.error(f"خطأ في تشغيل البوت: {e}")

async def main():
    # قراءة المتغيرات البيئية
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))
    
    if not BOT_TOKEN:
        print("❌ خطأ: متغير BOT_TOKEN غير موجود")
        return
    
    if not ADMIN_CHAT_ID:
        print("❌ خطأ: متغير ADMIN_CHAT_ID غير صحيح")
        return
    
    # إنشاء وتشغيل البوت
    bot = TelegramVPSBot(BOT_TOKEN, ADMIN_CHAT_ID)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"خطأ عام: {e}")

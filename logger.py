import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class SystemLogger:
    """نظام تسجيل شامل لتتبع كل العمليات"""
    
    def __init__(self, log_file='logs/system_logs.json'):
        self.log_file = log_file
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """إنشاء ملف السجلات إذا لم يكن موجوداً"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _generate_log_id(self) -> str:
        """توليد معرّف فريد للسجل"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"log_{timestamp}"
    
    def _save_log(self, log_entry: Dict[str, Any]):
        """حفظ سجل جديد"""
        try:
            logs = self.get_logs()
            logs.append(log_entry)
            
            # الحفاظ على آخر 10000 سجل فقط
            if len(logs) > 10000:
                logs = logs[-10000:]
            
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ خطأ في حفظ السجل: {e}")
    
    def log(self, log_type: str, category: str, message: str, details: Optional[Dict] = None):
        """دالة موحدة للتسجيل - للتوافق مع telegram_receiver.py الجديد"""
        log_entry = {
            "id": self._generate_log_id(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": log_type.upper(),
            "category": category,
            "message": message,
            "details": details or {},
            "icon": self._get_icon(log_type)
        }
        self._save_log(log_entry)
        print(f"{log_entry['icon']} [{log_type.upper()}] {message}")
    
    def _get_icon(self, log_type: str) -> str:
        """الحصول على الأيقونة المناسبة"""
        icons = {
            "INFO": "📘",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "TRANSFER": "💰"
        }
        return icons.get(log_type.upper(), "📝")
    
    def get_logs(self, limit: Optional[int] = None) -> list:
        """جلب السجلات"""
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
                if limit:
                    return logs[-limit:]
                return logs
        except:
            return []
    
    def get_recent_logs(self, hours: int = 24, limit: int = 1000) -> list:
        """جلب السجلات الأخيرة - الأحدث أولاً"""
        logs = self.get_logs()
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent = []
        for log in reversed(logs):  # البدء من الأحدث
            try:
                log_time = datetime.strptime(log['timestamp'], "%Y-%m-%d %H:%M:%S")
                if log_time >= cutoff_time:
                    recent.append(log)  # ✅ append بدلاً من insert(0)
                if len(recent) >= limit:
                    break
            except:
                continue
        
        return recent  # الأحدث أولاً
    
    def log_info(self, category: str, message: str, details: Optional[Dict] = None):
        """تسجيل معلومة عامة"""
        self.log("INFO", category, message, details)
    
    def log_success(self, category: str, message: str, details: Optional[Dict] = None):
        """تسجيل نجاح عملية"""
        self.log("SUCCESS", category, message, details)
    
    def log_warning(self, category: str, message: str, details: Optional[Dict] = None):
        """تسجيل تحذير"""
        self.log("WARNING", category, message, details)
    
    def log_error(self, category: str, message: str, details: Optional[Dict] = None):
        """تسجيل خطأ"""
        self.log("ERROR", category, message, details)
    
    def log_transfer(self, message: str, details: Optional[Dict] = None):
        """تسجيل عملية حوالة"""
        self.log("TRANSFER", "transfer_operation", message, details)
    
    def search_logs(self, query: str, log_type: Optional[str] = None, 
                   category: Optional[str] = None, limit: int = 100) -> list:
        """البحث في السجلات"""
        logs = self.get_logs()
        results = []
        
        query_lower = query.lower()
        
        for log in reversed(logs):  # البحث من الأحدث للأقدم
            # فلترة حسب النوع
            if log_type and log.get('type') != log_type:
                continue
            
            # فلترة حسب الفئة
            if category and log.get('category') != category:
                continue
            
            # البحث في المحتوى
            if query:
                searchable_text = (
                    str(log.get('message', '')).lower() +
                    str(log.get('details', {})).lower() +
                    str(log.get('timestamp', '')).lower()
                )
                
                if query_lower not in searchable_text:
                    continue
            
            results.append(log)
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_statistics(self, hours: int = 24) -> Dict:
        """إحصائيات السجلات"""
        logs = self.get_logs()
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        stats = {
            "total": 0,
            "info": 0,
            "success": 0,
            "warning": 0,
            "error": 0,
            "transfer": 0,
            "by_category": {}
        }
        
        for log in logs:
            try:
                log_time = datetime.strptime(log['timestamp'], "%Y-%m-%d %H:%M:%S")
                if log_time < cutoff_time:
                    continue
                
                stats["total"] += 1
                log_type = log.get('type', '').lower()
                stats[log_type] = stats.get(log_type, 0) + 1
                
                category = log.get('category', 'unknown')
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            except:
                continue
        
        return stats


# إنشاء نسخة عامة
logger = SystemLogger()

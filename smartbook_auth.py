"""
SmartBook Authentication & Contacts Manager
============================================
مسؤول عن:
- تسجيل الدخول إلى SmartBook
- جلب جهات الاتصال المسموحة
- تخزين واسترجاع التوكن والجهات
- التحقق من صلاحية الجلسة
"""

import requests
import json
import os
from datetime import datetime


class SmartBookAuth:
    """إدارة المصادقة وجهات الاتصال مع SmartBook API"""

    def __init__(self):
        # ✅ URL الصحيح الوحيد
        self.api_base_url = "http://smartbook.selfip.com:8080/api"
        self.api_login_url = f"{self.api_base_url}/login"
        self.api_contacts_url = f"{self.api_base_url}/get_contacts"
        
        self.token_file = "smartbook_token.json"
        self.contacts_file = "allowed_numbers.json"
        self.token = None
        self.contacts = []
        self.load_token()
        self.load_contacts()

    def login(self, username, password):
        """تسجيل الدخول إلى SmartBook"""
        try:
            payload = {
                "username": username,
                "password": password
            }

            print(f"🔄 محاولة تسجيل الدخول إلى: {self.api_login_url}")
            
            response = requests.post(
                self.api_login_url,
                json=payload,
                timeout=15
            )

            print(f"📥 Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                token = data.get('token')

                if token:
                    self.token = token
                    self.save_token(username, token)
                    print(f"✅ تم الحصول على Token بنجاح")
                    
                    # جلب جهات الاتصال مباشرة
                    contacts_result = self.fetch_contacts()

                    return {
                        'success': True,
                        'token': token,
                        'contacts_fetched': contacts_result['success'],
                        'contacts_count': len(self.contacts),
                        'message': 'تم تسجيل الدخول وجلب جهات الاتصال بنجاح'
                    }
                else:
                    return {'success': False, 'message': 'فشل الحصول على التوكن من الاستجابة'}

            elif response.status_code == 401:
                return {'success': False, 'message': 'اسم المستخدم أو كلمة المرور غير صحيحة'}
            else:
                return {'success': False, 'message': f'خطأ في الخادم: {response.status_code}'}

        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'انتهت مهلة الاتصال بالخادم (15 ثانية)'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'message': f'فشل الاتصال بـ {self.api_base_url}. تأكد من أن SmartBook يعمل.'}
        except Exception as e:
            return {'success': False, 'message': f'خطأ غير متوقع: {str(e)}'}

    def fetch_contacts(self):
        """جلب جهات الاتصال المسموحة من SmartBook"""
        if not self.token:
            return {'success': False, 'message': 'لا يوجد توكن، سجل دخول أولاً'}

        try:
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            print(f"🔄 جلب جهات الاتصال من: {self.api_contacts_url}")
            print(f"🔑 Token: {self.token[:20]}...")

            response = requests.get(
                self.api_contacts_url, 
                headers=headers, 
                timeout=20
            )

            print(f"📥 Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                
                # ✅ التحقق من structure الصحيح
                if not data.get('status'):
                    return {'success': False, 'message': 'API returned status: false'}
                
                contacts_list = data.get('contacts', [])
                
                if not isinstance(contacts_list, list):
                    return {'success': False, 'message': 'contacts ليس array'}

                print(f"📊 تم جلب {len(contacts_list)} جهة اتصال")

                # ✅ معالجة الجهات بشكل صحيح
                allowed_contacts = []
                
                for contact in contacts_list:
                    mobile = str(contact.get('mobile', '')).strip()
                    
                    if not mobile:
                        continue
                    
                    # ✅ تصحيح الرقم
                    if mobile.startswith('0'):
                        mobile = '+967' + mobile[1:]  # حذف 0 وإضافة +967
                    elif mobile.startswith('967'):
                        mobile = '+' + mobile
                    elif not mobile.startswith('+'):
                        mobile = '+967' + mobile
                    
                     # ✅ حفظ الحقول المطلوبة مع الاسم
                    allowed_contacts.append({
                        'mobile': mobile,
                        'name': str(contact.get('name', '')).strip() or 'بدون اسم',  # 🆕 إضافة الاسم
                        'active': bool(contact.get('active', False)),
                        'allowed_in_groups': bool(contact.get('allowed_in_groups', False))
                    })




                self.contacts = allowed_contacts
                self.save_contacts()

                print(f"✅ تم معالجة وحفظ {len(allowed_contacts)} جهة اتصال")

                return {
                    'success': True, 
                    'count': len(allowed_contacts), 
                    'message': f'تم جلب {len(allowed_contacts)} جهة اتصال'
                }
                
            elif response.status_code == 401:
                return {'success': False, 'message': 'التوكن منتهي الصلاحية، سجل دخول مرة أخرى'}
            else:
                error_text = response.text[:200]
                return {'success': False, 'message': f'خطأ {response.status_code}: {error_text}'}

        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'انتهت مهلة الاتصال (20 ثانية)'}
        except requests.exceptions.ConnectionError:
            return {'success': False, 'message': f'فشل الاتصال بـ {self.api_contacts_url}'}
        except Exception as e:
            return {'success': False, 'message': f'خطأ في جلب جهات الاتصال: {str(e)}'}

    def save_token(self, username, token):
        """حفظ التوكن في ملف"""
        data = {
            'username': username,
            'token': token,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(self.token_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 تم حفظ Token في {self.token_file}")

    def load_token(self):
        """تحميل التوكن من الملف"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.token = data.get('token')
                    print(f"✅ تم تحميل Token من الملف")
                    return data
            except:
                print("⚠️ فشل تحميل Token")
                return None
        return None

    def save_contacts(self):
        """💾 حفظ جهات الاتصال في allowed_numbers.json بشكل صحيح"""
        
        # تحميل الملف الحالي
        if os.path.exists(self.contacts_file):
            try:
                with open(self.contacts_file, 'r', encoding='utf-8') as f:
                    contacts_data = json.load(f)
            except:
                contacts_data = {'private_chat': [], 'groups': []}
        else:
            contacts_data = {'private_chat': [], 'groups': []}
        
        # ✅ إضافة الجهات الجديدة فقط
        added_private = 0
        added_groups = 0
        
        for contact in self.contacts:
            mobile = contact.get('mobile', '').strip()
            if not mobile:
                continue

            # إضافة للمحادثات الخاصة إذا كان active
            if contact.get('active', False):
                if mobile not in contacts_data['private_chat']:
                    contacts_data['private_chat'].append(mobile)
                    added_private += 1

            # إضافة للمجموعات إذا كان مسموح
            if contact.get('allowed_in_groups', False):
                if mobile not in contacts_data['groups']:
                    contacts_data['groups'].append(mobile)
                    added_groups += 1
        
        # إضافة metadata
        contacts_data['smartbook_sync'] = {
            'last_sync': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_contacts': len(self.contacts),
            'contacts': self.contacts
        }

        # حفظ الملف
        with open(self.contacts_file, 'w', encoding='utf-8') as f:
            json.dump(contacts_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ تم حفظ: {added_private} خاص، {added_groups} مجموعات")
        print(f"📊 الإجمالي: {len(contacts_data['private_chat'])} خاص، {len(contacts_data['groups'])} مجموعات")

    def load_contacts(self):
        """تحميل جهات الاتصال من الملف"""
        if os.path.exists(self.contacts_file):
            try:
                with open(self.contacts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.contacts = data.get('smartbook_sync', {}).get('contacts', [])
                    print(f"✅ تم تحميل {len(self.contacts)} جهة اتصال من الملف")
                    return data
            except:
                print("⚠️ فشل تحميل جهات الاتصال")
                return None
        return None

    def is_logged_in(self):
        """التحقق من وجود جلسة نشطة"""
        return self.token is not None

    def get_token(self):
        """الحصول على التوكن الحالي"""
        return self.token

    def get_contacts(self):
        """الحصول على جهات الاتصال الحالية"""
        return self.contacts


    def get_contact_name(self, mobile):
        """الحصول على اسم جهة الاتصال من رقم الهاتف"""
        mobile = str(mobile).strip()
        for contact in self.contacts:
            if contact.get('mobile') == mobile:
                return contact.get('name', 'بدون اسم')
        return 'غير معروف'

    

    def sync_contacts(self):
        """🔄 مزامنة جهات الاتصال مع SmartBook"""
        return self.fetch_contacts()

    def logout(self):
        """🚪 تسجيل الخروج وحذف جميع البيانات"""
        try:
            # 1️⃣ حذف Token
            self.token = None
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                print("✅ تم حذف SmartBook Token")
            
            # 2️⃣ حذف جهات الاتصال من الذاكرة
            self.contacts = []
            
            # 3️⃣ تفريغ allowed_numbers.json بالكامل
            empty_data = {
                "private_chat": [],
                "groups": []
            }
            
            with open(self.contacts_file, 'w', encoding='utf-8') as f:
                json.dump(empty_data, f, ensure_ascii=False, indent=2)
            
            print("✅ تم حذف جميع الأرقام المسموحة")
            print("📊 المحادثات الخاصة: 0")
            print("📊 المجموعات: 0")
            print("✅ تم تسجيل الخروج من SmartBook بنجاح")
            
            return {
                'success': True, 
                'message': 'تم تسجيل الخروج وحذف جميع الأرقام بنجاح'
            }
            
        except Exception as e:
            print(f"⚠️ خطأ في Logout: {e}")
            # حتى لو حدث خطأ، نتأكد من تنظيف البيانات
            self.token = None
            self.contacts = []
            
            # محاولة حذف الملفات على أي حال
            try:
                if os.path.exists(self.token_file):
                    os.remove(self.token_file)
            except:
                pass
            
            try:
                with open(self.contacts_file, 'w', encoding='utf-8') as f:
                    json.dump({"private_chat": [], "groups": []}, f)
            except:
                pass
            
            return {
                'success': True, 
                'message': 'تم تسجيل الخروج (مع بعض التحذيرات)'
            }




# إنشاء نسخة واحدة (Singleton)
smartbook_auth = SmartBookAuth()
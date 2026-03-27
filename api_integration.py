import requests
import json
from datetime import datetime

class HawalaAPI:
    """
    كلاس للتكامل مع نظام الصراف
    جاهز للتعديل حسب API الفعلي
    """
    
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or "YOUR_API_KEY_HERE"
        self.base_url = base_url or "https://api.hawala-system.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def check_transfer(self, transfer_number):
        """
        التحقق من وجود الحوالة في النظام
        
        Returns:
            dict: {"exists": True/False, "data": {...}}
        """
        try:
            # المثال - سيتم تعديله حسب API الفعلي
            url = f"{self.base_url}/api/transfer/check/{transfer_number}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "exists": True,
                    "data": data
                }
            elif response.status_code == 404:
                return {
                    "success": True,
                    "exists": False,
                    "message": "الحوالة غير موجودة"
                }
            else:
                return {
                    "success": False,
                    "error": f"خطأ في الاتصال: {response.status_code}"
                }
        
        except requests.exceptions.Timeout:
            return {"success": False, "error": "انتهت مهلة الاتصال"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "فشل الاتصال بالسيرفر"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_transfer_details(self, transfer_number):
        """
        استخراج تفاصيل الحوالة
        
        Returns:
            dict: {
                "transfer_number": "123456789",
                "amount": 1000,
                "sender_name": "أحمد",
                "sender_phone": "+967777777777",
                "receiver_name": "محمد",
                "receiver_phone": "+967777777778",
                "status": "pending",
                "created_at": "2026-01-02 08:00:00"
            }
        """
        try:
            url = f"{self.base_url}/api/transfer/{transfer_number}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "data": data
                }
            else:
                return {
                    "success": False,
                    "error": f"فشل الاستعلام: {response.status_code}"
                }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def claim_transfer(self, transfer_number, receiver_phone):
        """
        استلام الحوالة تلقائياً
        
        Args:
            transfer_number: رقم الحوالة
            receiver_phone: رقم هاتف المستلم للتأكيد
        
        Returns:
            dict: {"success": True/False, "message": "..."}
        """
        try:
            url = f"{self.base_url}/api/transfer/claim"
            payload = {
                "transfer_number": transfer_number,
                "receiver_phone": receiver_phone,
                "claimed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": "تم استلام الحوالة بنجاح",
                    "data": data
                }
            elif response.status_code == 400:
                return {
                    "success": False,
                    "error": "الحوالة مستلمة مسبقاً أو غير صالحة"
                }
            else:
                return {
                    "success": False,
                    "error": f"فشل الاستلام: {response.status_code}"
                }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_receiver(self, transfer_number, phone):
        """
        التحقق من أن رقم الهاتف مطابق للمستلم
        
        Returns:
            dict: {"verified": True/False}
        """
        details = self.get_transfer_details(transfer_number)
        
        if not details["success"]:
            return {"verified": False, "error": "فشل الاستعلام"}
        
        receiver_phone = details["data"].get("receiver_phone", "")
        
        # إزالة المسافات والرموز للمقارنة
        phone_clean = phone.replace("+", "").replace(" ", "")
        receiver_clean = receiver_phone.replace("+", "").replace(" ", "")
        
        return {
            "verified": phone_clean == receiver_clean,
            "receiver_phone": receiver_phone
        }


# دالة للاختبار بدون API حقيقي
class MockHawalaAPI(HawalaAPI):
    """
    نسخة تجريبية للاختبار بدون API حقيقي
    احذف هذا الكلاس عند استخدام API الفعلي
    """
    
    def __init__(self):
        super().__init__()
        # قاعدة بيانات وهمية للاختبار
        self.fake_transfers = {
            "123456789": {
                "transfer_number": "123456789",
                "amount": 1000,
                "sender_name": "أحمد علي",
                "sender_phone": "+967777777777",
                "receiver_name": "محمد موسى",
                "receiver_phone": "+967717202209",
                "status": "pending",
                "created_at": "2026-01-02 08:00:00"
            },
            "987654321": {
                "transfer_number": "987654321",
                "amount": 5000,
                "sender_name": "سالم حسن",
                "sender_phone": "+967788888888",
                "receiver_name": "محمد موسى",
                "receiver_phone": "+967717202209",
                "status": "pending",
                "created_at": "2026-01-02 07:30:00"
            }
        }
    
    def check_transfer(self, transfer_number):
        if transfer_number in self.fake_transfers:
            return {
                "success": True,
                "exists": True,
                "data": self.fake_transfers[transfer_number]
            }
        else:
            return {
                "success": True,
                "exists": False,
                "message": "الحوالة غير موجودة في النظام"
            }
    
    def get_transfer_details(self, transfer_number):
        if transfer_number in self.fake_transfers:
            return {
                "success": True,
                "data": self.fake_transfers[transfer_number]
            }
        else:
            return {
                "success": False,
                "error": "الحوالة غير موجودة"
            }
    
    def claim_transfer(self, transfer_number, receiver_phone):
        if transfer_number in self.fake_transfers:
            transfer = self.fake_transfers[transfer_number]
            
            if transfer["status"] == "claimed":
                return {
                    "success": False,
                    "error": "الحوالة مستلمة مسبقاً"
                }
            
            # التحقق من رقم المستلم
            phone_clean = receiver_phone.replace("+", "").replace(" ", "")
            receiver_clean = transfer["receiver_phone"].replace("+", "").replace(" ", "")
            
            if phone_clean != receiver_clean:
                return {
                    "success": False,
                    "error": "رقم الهاتف غير مطابق للمستلم"
                }
            
            # استلام الحوالة
            transfer["status"] = "claimed"
            transfer["claimed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            return {
                "success": True,
                "message": "تم استلام الحوالة بنجاح",
                "data": transfer
            }
        else:
            return {
                "success": False,
                "error": "الحوالة غير موجودة"
            }


# للاستخدام:
# من MockHawalaAPI للتجربة بدون API
# أو من HawalaAPI عند توفر API حقيقي

# مثال:
# api = MockHawalaAPI()  # للتجربة
# api = HawalaAPI(api_key="your_key", base_url="https://api.example.com")  # للاستخدام الفعلي

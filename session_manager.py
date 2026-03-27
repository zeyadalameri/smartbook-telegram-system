import json
import os
import threading
import time
from dotenv import load_dotenv

from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

load_dotenv()

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_NAME = os.getenv('SESSION_NAME', 'telegram_session')



class SessionManager:
    def __init__(self):
        self.session_file = 'current_session.json'
        self.current_account = self.load_current_account()
        self._lock = threading.Lock()
        self._phone_code_hash = {}

    def load_current_account(self):
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except:
                    return None
        return None

    def save_current_account(self, account_data):
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(account_data, f, ensure_ascii=False, indent=2)
        self.current_account = account_data

    def get_current_account(self):
        self.current_account = self.load_current_account()
        return self.current_account

    def is_logged_in(self):
        """
        ✅ تحقق حقيقي: هل الجلسة Authorized في تيليجرام؟
        """
        try:
            session_path = f"{SESSION_NAME}.session"
            if not os.path.exists(session_path):
                return False

            client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

            async def check_auth():
                await client.connect()
                ok = await client.is_user_authorized()
                await client.disconnect()
                return ok

            return self._run_sync(check_auth, timeout=10)

        except Exception:
            return False



    def logout(self):
        try:
            with self._lock:
                self.current_account = None
                self._phone_code_hash = {}

                try:
                    session_path = f"{SESSION_NAME}.session"
                    if os.path.exists(session_path):
                        os.remove(session_path)
                except:
                    pass

                try:
                    journal_path = f"{SESSION_NAME}.session-journal"
                    if os.path.exists(journal_path):
                        os.remove(journal_path)
                except:
                    pass

                try:
                    if os.path.exists(self.session_file):
                        os.remove(self.session_file)
                except:
                    pass

                return {"status": "success", "message": "تم تسجيل الخروج بنجاح"}
        except Exception:
            self.current_account = None
            self._phone_code_hash = {}
            return {"status": "success", "message": "تم تسجيل الخروج بنجاح"}

    # ✅ يطلب من telegram_receiver.py يفصل مؤقتاً
    def _request_receiver_pause(self, wait_seconds=1):
        try:
            with open("login.flag", "w", encoding="utf-8") as f:
                f.write("login")
            time.sleep(wait_seconds)
        except:
            pass

    # ✅ ينتظر لين تنفك session فعلاً (حل database locked نهائي)
    def _wait_session_unlock(self, timeout=10):
        start = time.time()
        while time.time() - start < timeout:
            try:
                test_client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
                test_client.connect()
                test_client.disconnect()
                return True
            except Exception as e:
                if "database is locked" in str(e).lower():
                    time.sleep(0.5)
                    continue
                return False
        return False

    def add_account(self, phone):
        try:
            with self._lock:
                if self.is_logged_in():
                    return {"status": "error", "message": "يوجد حساب نشط. سجل خروج أولاً."}

                # ✅ اطلب من receiver يفصل مؤقتاً
                self._request_receiver_pause(wait_seconds=1)

                # ✅ انتظر لين ينفك قفل session
                if not self._wait_session_unlock(timeout=10):
                    return {
                        "status": "error",
                        "message": "⚠️ الجلسة مقفلة حالياً.. انتظر 3 ثواني وحاول مرة أخرى"
                    }

                for attempt in range(1, 3):
                    try:
                        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

                        client.connect()
                        result = client.send_code_request(phone)
                        client.disconnect()

                        self._phone_code_hash[phone] = result.phone_code_hash
                        return {"status": "code_sent", "message": "تم إرسال كود التحقق", "phone": phone}

                    except Exception as retry_error:
                        error_msg = str(retry_error)

                        try:
                            client.disconnect()
                        except:
                            pass

                        if attempt == 2:
                            raise retry_error

                        if "disconnected" in error_msg.lower() or "cannot send" in error_msg.lower():
                            print(f"⏳ محاولة {attempt}/2 فشلت، إعادة المحاولة...")
                            time.sleep(2)
                            continue
                        else:
                            raise retry_error

        except Exception as e:
            error_msg = str(e)
            if "database is locked" in error_msg.lower():
                return {
                    "status": "error",
                    "message": "⚠️ الجلسة مقفلة مؤقتاً.. انتظر ثانيتين وحاول مرة أخرى"
                }
            if "انتهت مهلة" in error_msg:
                return {"status": "error", "message": error_msg}
            if "disconnected" in error_msg.lower() or "cannot send" in error_msg.lower():
                return {"status": "error", "message": "⚠️ حاول مرة أخرى بعد 5 ثوانٍ"}
            return {"status": "error", "message": f"خطأ: {error_msg}"}

    def verify_code(self, phone, code, password=None):
        try:
            with self._lock:
                phone_code_hash = self._phone_code_hash.get(phone)
                if not phone_code_hash:
                    return {"status": "error", "message": "انتهت صلاحية الكود. أعد إرسال الكود."}

                # ✅ اطلب من receiver يفصل مؤقتاً
                self._request_receiver_pause(wait_seconds=1)

                # ✅ انتظر لين ينفك قفل session
                if not self._wait_session_unlock(timeout=10):
                    return {
                        "status": "error",
                        "message": "⚠️ الجلسة مقفلة حالياً.. انتظر 3 ثواني وحاول مرة أخرى"
                    }

                client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

                client.connect()
                try:
                    try:
                        client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                    except SessionPasswordNeededError:
                        if not password:
                            client.disconnect()
                            return {"status": "password_required", "message": "هذا الحساب محمي بكلمة مرور"}
                        client.sign_in(password=password)

                    me = client.get_me()
                    client.disconnect()

                    account_data = {
                        "name": me.first_name or "Unknown",
                        "phone": phone,
                        "username": f"@{me.username}" if me.username else "No username",
                        "user_id": me.id,
                        "logged_in_at": self._get_timestamp()
                    }

                    self._clear_old_data()
                    self.save_current_account(account_data)

                    if phone in self._phone_code_hash:
                        del self._phone_code_hash[phone]

                    return {"status": "success", "message": "تم تسجيل الدخول بنجاح", "account": account_data}

                except Exception as e:
                    try:
                        client.disconnect()
                    except:
                        pass
                    raise e

        except Exception as e:
            error_msg = str(e)
            if "database is locked" in error_msg.lower():
                return {
                    "status": "error",
                    "message": "⚠️ الجلسة مقفلة مؤقتاً.. انتظر ثانيتين وحاول مرة أخرى"
                }
            return {"status": "error", "message": f"كود خاطئ: {error_msg}"}

    def get_client(self):
        if not self.is_logged_in():
            return None
        return TelegramClient(SESSION_NAME, API_ID, API_HASH)

    def _get_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _clear_old_data(self):
        try:
            os.makedirs('messages_data', exist_ok=True)

            messages_file = 'messages_data/messages.json'
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump([], f)

            stats_file = 'messages_data/statistics.json'
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

            print("✅ تم مسح البيانات القديمة - بداية جديدة")
        except Exception as e:
            print(f"⚠️ خطأ في مسح البيانات: {e}")


session_manager = SessionManager()

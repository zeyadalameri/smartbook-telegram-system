from telethon import TelegramClient, events
import asyncio
from logger import logger
from datetime import datetime
import json
import os
import re
from api_integration import MockHawalaAPI
from dotenv import load_dotenv
from session_manager import session_manager
import requests
import time

# تحميل .env
load_dotenv()

# معلومات API من .env
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_NAME = os.getenv('SESSION_NAME', 'telegram_session')


# معلومات SmartBook API
PARTNER_API_URL = os.getenv('PARTNER_API_URL')
ENABLE_PARTNER_API = os.getenv('ENABLE_PARTNER_API', 'false').lower() == 'true'

# ✅ مهم جداً: لا ننشئ client ثابت هنا
client = None

def create_client():
    """إنشاء TelegramClient جديد (حل مشاكل session locked / key not registered)"""
    return TelegramClient(SESSION_NAME, API_ID, API_HASH)

# (موجود لكنه غير مستخدم الآن – نظام الحوالات معطّل)
hawala_api = MockHawalaAPI()

# إنشاء المجلدات
os.makedirs('messages_data', exist_ok=True)
os.makedirs('images', exist_ok=True)

# إنشاء ملف الأرقام المسموحة الافتراضي
if not os.path.exists('allowed_numbers.json'):
    with open('allowed_numbers.json', 'w', encoding='utf-8') as f:
        json.dump({
            "private_chat": ["+967717202209"],
            "groups": []
        }, f, ensure_ascii=False, indent=2)


# ====================== دوال المساعدة الأساسية ======================

def extract_transfer_numbers(text: str):
    """استخراج أرقام الحوالات من النص (موقوف حالياً)"""
    patterns = [
        r'رقم الحوالة[:\s]*(\d+)',
        r'حوالة رقم[:\s]*(\d+)',
        r'الرقم المرجعي[:\s]*(\d+)',
        r'رقم مرجعي[:\s]*(\d+)',
        r'Reference[:\s]*(\d+)',
        r'MT[:\s]*(\d+)',
        r'TRN[:\s]*(\d+)',
        r'(\d{8,})',
    ]
    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        numbers.extend(matches)
    return list(set(numbers))


def save_transfer(transfer_data: dict):
    """حفظ بيانات الحوالة (النظام معطّل حالياً لكن الدالة موجودة)"""
    transfers = []
    path = 'messages_data/transfers.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                transfers = json.load(f)
            except Exception:
                transfers = []
    transfers.append(transfer_data)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(transfers, f, ensure_ascii=False, indent=2)


def load_allowed_numbers():
    with open('allowed_numbers.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def load_messages():
    path = 'messages_data/messages.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []


# ====================== SmartBook Token & Contacts ======================

def get_smartbook_token():
    """
    قراءة Token من smartbook_token.json
    وإذا فشل يرجع من .env
    """
    try:
        if os.path.exists('smartbook_token.json'):
            with open('smartbook_token.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                token = data.get('token')
                if token:
                    return token
    except Exception as e:
        print(f"⚠️ خطأ في قراءة Token: {e}")

    return os.getenv('PARTNER_API_TOKEN')


def get_allowed_contacts_from_smartbook():
    """
    جلب جهات الاتصال من SmartBook وتحويلها إلى dict {رقم_منظَّف: اسم}
    """
    try:
        token = get_smartbook_token()
        if not token:
            return {}

        contacts_url = "http://smartbook.selfip.com:8080/api/get_contacts"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(contacts_url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.log_error(
                "smartbook_contacts_failed",
                f"فشل جلب جهات الاتصال: {response.status_code}",
                {"status_code": response.status_code}
            )
            return {}

        contacts = response.json()
        allowed_contacts = {}

        for contact in contacts.get('contacts', []):
            phone = contact.get('phone', '').strip()
            name = contact.get('name', '').strip()
            if phone:
                clean_phone = re.sub(r'[^\d]', '', phone)
                allowed_contacts[clean_phone] = name

        logger.log_info(
            "smartbook_contacts_loaded",
            f"📞 تم تحميل {len(allowed_contacts)} جهة اتصال من SmartBook",
            {"count": len(allowed_contacts)}
        )
        return allowed_contacts

    except Exception as e:
        logger.log_error(
            "smartbook_contacts_failed",
            f"❌ فشل جلب جهات الاتصال: {str(e)}",
            {"error": str(e)}
        )
        return {}


# تحميل جهات الاتصال عند بدء التشغيل
smartbook_contacts = get_allowed_contacts_from_smartbook()


def update_allowed_contacts():
    """تحديث جهات الاتصال يدوياً (يمكن مناداته لاحقاً إذا احتجت)"""
    global smartbook_contacts
    smartbook_contacts = get_allowed_contacts_from_smartbook()


def map_message_to_api_payload(message_data: dict):
    """
    تحويل رسالة Telegram → تنسيق SmartBook Raw Notifications API
    """
    from datetime import datetime as dt, timezone

    sender_phone = message_data['sender']['phone']
    sender_name = message_data['sender']['name']
    message_text = message_data.get('message', '')
    chat_type = message_data['chat_type']

    clean_phone = re.sub(r'[^\d]', '', sender_phone or '')

    if clean_phone.startswith('00967'):
        clean_phone = clean_phone[5:]
    elif clean_phone.startswith('967'):
        clean_phone = clean_phone[3:]

    smartbook_name = smartbook_contacts.get(clean_phone, sender_name)

    user_id = message_data['sender']['user_id']
    ts = int(time.time())
    event_key = f"tg_{user_id}_{ts}"
    event_timestamp = dt.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    is_group = (chat_type == 'group')
    is_private = (chat_type == 'private')

    group_name = None
    group_id = None
    if is_group:
        group_name = message_data.get('group_name', 'Unknown Group')
        group_id = str(message_data.get('chat_id', ''))

    payload = {
        "original_content": message_text,
        "sender_phone_number_from_device_contacts": clean_phone,
        "sender_display_name_from_notification": smartbook_name,
        "source_package_name": "org.telegram.messenger",
        "client_event_key": event_key,
        "event_timestamp_utc": event_timestamp,
        "from_group": is_group,
        "from_private": is_private,
        "groupName": group_name,
        "group_id": group_id,
    }

    return payload


async def send_to_smartbook_api(message_data: dict) -> bool:
    """
    إرسال الرسالة إلى SmartBook Raw Notifications API
    """
    if not ENABLE_PARTNER_API:
        logger.log_info("smartbook_api_disabled", "إرسال SmartBook API معطّل في .env")
        return False

    if not PARTNER_API_URL:
        logger.log_error("smartbook_api_no_url", "PARTNER_API_URL غير موجود في .env")
        return False

    token = get_smartbook_token()
    if not token:
        logger.log_error(
            "smartbook_api_no_token",
            "Token غير موجود في smartbook_token.json ولا في .env",
            {"check_files": ["smartbook_token.json", ".env"]}
        )
        return False

    logger.log_info(
        "smartbook_api_token_loaded",
        f"تم تحميل Token: {token[:20]}...",
        {"token_length": len(token)}
    )

    try:
        payload = map_message_to_api_payload(message_data)
        logger.log_info(
            "smartbook_api_payload_created",
            "تم إنشاء Payload للإرسال",
            {
                "sender": payload['sender_phone_number_from_device_contacts'],
                "content_length": len(payload['original_content']),
                "from_group": payload['from_group'],
                "from_private": payload['from_private'],
                "group_name": payload['groupName'],
            }
        )
    except Exception as e:
        logger.log_error(
            "smartbook_api_payload_failed",
            f"فشل في بناء Payload: {str(e)}",
            {"error": str(e), "message_data_keys": list(message_data.keys())}
        )
        return False

    content_length = len(payload['original_content'].strip())
    if content_length < 20:
        logger.log_warning(
            "smartbook_api_short_message",
            f"رسالة قصيرة ({content_length} حرف) - لن تُرسل",
            {
                "min_required": 20,
                "actual_length": content_length,
                "sender": payload['sender_phone_number_from_device_contacts'],
                "content_preview": payload['original_content'][:50],
            }
        )
        print(f"⚠️ رسالة قصيرة جداً: {content_length} حرف (الحد الأدنى: 20)")
        return False

    try:
        logger.log_info(
            "smartbook_api_sending",
            "إرسال request إلى SmartBook API...",
            {
                "url": PARTNER_API_URL,
                "method": "POST",
                "sender": payload['sender_phone_number_from_device_contacts'],
            }
        )

        response = requests.post(
            PARTNER_API_URL,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            json=payload,
            timeout=10
        )

        if response.status_code == 201:
            try:
                response_data = response.json()
            except Exception:
                response_data = {"raw": response.text[:100]}

            logger.log_success(
                "smartbook_api_success",
                "تم إرسال الرسالة بنجاح إلى SmartBook",
                {
                    "status_code": 201,
                    "sender": payload['sender_phone_number_from_device_contacts'],
                    "sender_name": payload['sender_display_name_from_notification'],
                    "chat_type": "مجموعة" if payload['from_group'] else "خاص",
                    "group_name": payload['groupName'],
                    "api_response": response_data,
                }
            )
            print(f"✅ SmartBook API: تم إرسال رسالة من {payload['sender_display_name_from_notification']}")
            return True

        elif response.status_code == 422:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"raw_response": response.text}

            logger.log_warning(
                "smartbook_api_rejected",
                "SmartBook API رفض الرسالة (422)",
                {
                    "status_code": 422,
                    "reason": "validation_failed",
                    "errors": error_data,
                    "sender": payload['sender_phone_number_from_device_contacts'],
                }
            )
            print(f"⚠️ SmartBook API رفض: {error_data}")
            return False

        elif response.status_code == 403:
            logger.log_error(
                "smartbook_api_forbidden",
                "Token غير صالح أو منتهي (403 Forbidden)",
                {
                    "status_code": 403,
                    "token_used": f"{token[:20]}...",
                    "url": PARTNER_API_URL,
                    "suggestion": "تحقق من smartbook_token.json أو سجل دخول جديد",
                }
            )
            print("❌ Token خاطئ! سجل دخول SmartBook مرة أخرى")
            return False

        elif response.status_code == 500:
            logger.log_error(
                "smartbook_api_server_error",
                "خطأ في سيرفر SmartBook (500)",
                {
                    "status_code": 500,
                    "response": response.text[:200],
                    "url": PARTNER_API_URL,
                }
            )
            print("❌ خطأ في سيرفر SmartBook")
            return False

        else:
            logger.log_error(
                "smartbook_api_unexpected_status",
                f"رد غير متوقع من SmartBook API: {response.status_code}",
                {
                    "status_code": response.status_code,
                    "response_text": response.text[:200],
                    "url": PARTNER_API_URL,
                }
            )
            print(f"❌ خطأ غير متوقع: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        logger.log_error(
            "smartbook_api_timeout",
            "انتهت مهلة الاتصال (10 ثواني)",
            {
                "timeout": 10,
                "url": PARTNER_API_URL,
                "suggestion": "تحقق من الإنترنت أو زيادة timeout",
            }
        )
        print("⏱️ Timeout: SmartBook لم يستجب خلال 10 ثواني")
        return False

    except requests.exceptions.ConnectionError as e:
        logger.log_error(
            "smartbook_api_connection_error",
            "فشل الاتصال بـ SmartBook",
            {
                "url": PARTNER_API_URL,
                "error": str(e),
                "suggestion": "تحقق من URL أو أن SmartBook يعمل",
            }
        )
        print("🌐 فشل الاتصال بـ SmartBook")
        return False

    except Exception as e:
        logger.log_error(
            "smartbook_api_exception",
            f"خطأ غير متوقع: {str(e)}",
            {"error": str(e), "error_type": type(e).__name__}
        )
        print(f"❌ خطأ: {str(e)}")
        return False


# ====================== حفظ الرسائل والإحصائيات ======================

def save_message(msg: dict):
    messages = load_messages()
    messages.append(msg)
    with open('messages_data/messages.json', 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def load_stats():
    path = 'messages_data/statistics.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}


def update_stats(phone: str, name: str, chat_type: str):
    stats = load_stats()
    if phone not in stats:
        stats[phone] = {
            "name": name,
            "total_messages": 0,
            "private_chat": 0,
            "groups": 0,
            "last_message": None,
        }

    stats[phone]["total_messages"] += 1
    stats[phone]["name"] = name
    stats[phone]["last_message"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if chat_type == "private":
        stats[phone]["private_chat"] += 1
    else:
        stats[phone]["groups"] += 1

    with open('messages_data/statistics.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


# ====================== استقبال الرسائل من Telegram ======================

async def handler(event):
    global client
    try:
        sender = await event.get_sender()
        chat = await event.get_chat()

        if not sender or sender.__class__.__name__ == 'Channel':
            return

        allowed = load_allowed_numbers()

        sender_phone = None
        sender_username = None
        sender_user_id = str(sender.id)

        if hasattr(sender, 'phone') and sender.phone:
            sender_phone = f"+{sender.phone}"
        if hasattr(sender, 'username') and sender.username:
            sender_username = f"@{sender.username}"

        user_identifiers = []
        if sender_phone:
            user_identifiers.append(sender_phone)
        if sender_username:
            user_identifiers.append(sender_username)
        user_identifiers.append(sender_user_id)

        display_identifier = sender_phone or sender_username or sender_user_id

        is_private = hasattr(chat, 'first_name') and not hasattr(chat, 'title')

        if is_private:
            is_allowed = any(identifier in allowed['private_chat'] for identifier in user_identifiers)
            if not is_allowed:
                logger.log(
                    "WARNING",
                    "blocked_sender",
                    f"تجاهل رسالة خاصة من رقم غير مسموح: {display_identifier}",
                    {"identifiers": user_identifiers, "reason": "not_in_private_allowed_list"}
                )
                print(f"⛔ رقم محظور (محادثة خاصة): {display_identifier} (ID: {sender_user_id})")
                return
            chat_type = "private"
            group_name = f"{getattr(chat, 'first_name', '')} {getattr(chat, 'last_name', '')}".strip()
        else:
            is_allowed = any(identifier in allowed['groups'] for identifier in user_identifiers)
            if not is_allowed:
                logger.log(
                    "WARNING",
                    "blocked_sender",
                    f"تجاهل رسالة من مجموعة - رقم غير مسموح: {display_identifier}",
                    {"identifiers": user_identifiers, "reason": "not_in_group_allowed_list"}
                )
                print(f"⛔ رقم محظور (مجموعة): {display_identifier} (ID: {sender_user_id})")
                return
            chat_type = "group"
            group_name = getattr(chat, 'title', '')

        sender_phone = sender_phone or display_identifier
        message_text = event.message.message or ""
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        name = f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip() or "بدون اسم"
        username = f"@{sender.username}" if hasattr(sender, 'username') and sender.username else "لا يوجد"

        image_path = None
        if event.message.photo:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"images/image_{ts}_{sender.id}.jpg"
            await event.message.download_media(file=image_path)
            logger.log(
                "INFO",
                "image_received",
                f"استلام صورة من {name}",
                {"sender_phone": sender_phone, "image_path": image_path}
            )

        logger.log(
            "INFO",
            "message_received",
            f"استلام رسالة من {name}",
            {
                "sender_phone": sender_phone,
                "sender_name": name,
                "chat_type": chat_type,
                "group_name": group_name,
                "message_length": len(message_text),
                "has_image": bool(image_path),
            }
        )

        print("\n" + "=" * 50)
        print("✅ رسالة جديدة")
        print(f"⏰ {time_now}")
        print(f"👥 {chat_type}: {group_name}")
        print(f"👤 {name}")
        print(f"📱 {sender_phone}")
        if message_text:
            print(f"💬 {message_text}")
        if image_path:
            print(f"📸 {image_path}")
        print("=" * 50)

        message_data = {
            "timestamp": time_now,
            "chat_type": chat_type,
            "group_name": group_name,
            "sender": {
                "name": name,
                "phone": sender_phone or "N/A",
                "username": sender_username.lstrip('@') if sender_username else (username or "N/A"),
                "user_id": sender.id,
            },
            "message": message_text,
            "image": image_path,
            "chat_id": event.chat_id,
        }

        save_message(message_data)
        await send_to_smartbook_api(message_data)
        update_stats(display_identifier, name, chat_type)

        print("💾 تم الحفظ بنجاح\n")

    except Exception as e:
        logger.log(
            "ERROR",
            "handler_exception",
            f"خطأ في معالجة الرسالة: {str(e)}",
            {"error": str(e), "error_type": type(e).__name__}
        )
        print(f"❌ خطأ في handler: {e}")
        import traceback
        traceback.print_exc()


# ====================== فحص طابور الإرسال ======================

async def check_queue():
    """فحص قائمة الإرسال كل ثانيتين"""
    global client
    while True:
        try:
            if os.path.exists('send_queue.json'):
                with open('send_queue.json', 'r', encoding='utf-8') as f:
                    try:
                        queue = json.load(f)
                    except Exception:
                        queue = []

                for item in queue:
                    if item.get('status') != 'pending':
                        continue

                    try:
                        recipient = item.get('recipient')
                        message = item.get('message', '')
                        image = item.get('image')
                        recipient_type = item.get('recipient_type', 'phone')

                        logger.log(
                            "INFO",
                            "sending_message",
                            f"جاري إرسال رسالة إلى {recipient}",
                            {
                                "recipient": recipient,
                                "recipient_type": recipient_type,
                                "has_image": bool(image),
                                "message_length": len(message),
                            }
                        )

                        target = None

                        if recipient_type == 'group':
                            dialogs = await client.get_dialogs()
                            group_found = False
                            for dialog in dialogs:
                                if not hasattr(dialog.entity, 'title'):
                                    continue
                                dialog_name = dialog.entity.title
                                dialog_id = str(dialog.entity.id)

                                if (
                                    recipient.lower() == dialog_name.lower()
                                    or recipient == dialog_id
                                    or recipient.lstrip('-') == dialog_id.lstrip('-')
                                    or recipient.lower() in dialog_name.lower()
                                ):
                                    target = dialog.entity
                                    group_found = True
                                    logger.log(
                                        "INFO",
                                        "group_found",
                                        f"تم العثور على المجموعة: {dialog_name}",
                                        {"group_name": dialog_name, "group_id": dialog_id}
                                    )
                                    print(f"✅ تم العثور على المجموعة: {dialog_name}")
                                    break

                            if not group_found:
                                error_msg = f"لم يتم العثور على المجموعة: {recipient}"
                                logger.log(
                                    "ERROR",
                                    "group_not_found",
                                    error_msg,
                                    {"recipient": recipient}
                                )
                                print(f"❌ {error_msg}")
                                item['status'] = 'failed'
                                item['error'] = 'group_not_found'
                                continue

                        elif str(recipient).startswith('-') or (
                            str(recipient).replace('-', '').isdigit()
                            and len(str(recipient)) > 6
                        ):
                            try:
                                target = int(recipient)
                            except Exception:
                                target = recipient

                        elif str(recipient).startswith('@'):
                            target = recipient

                        elif recipient_type == 'phone':
                            target = recipient if str(recipient).startswith('+') else f"+{recipient}"

                        else:
                            target = f"@{recipient}" if not str(recipient).startswith('@') else recipient

                        if not target:
                            logger.log(
                                "ERROR",
                                "invalid_recipient",
                                f"مستلم غير صالح: {recipient}",
                                {"recipient": recipient, "recipient_type": recipient_type}
                            )
                            print(f"❌ خطأ: مستلم غير صالح {recipient}")
                            item['status'] = 'failed'
                            item['error'] = 'invalid_recipient'
                            continue

                        if image and os.path.exists(image):
                            await client.send_file(target, image, caption=message or '')
                            print(f"✅ تم إرسال صورة إلى {recipient}")
                            logger.log(
                                "SUCCESS",
                                "message_sent",
                                f"تم إرسال رسالة بنجاح إلى {recipient}",
                                {"recipient": str(recipient), "image": image}
                            )
                        elif message:
                            await client.send_message(target, message)
                            print(f"✅ تم إرسال رسالة إلى {recipient}")
                            logger.log(
                                "SUCCESS",
                                "message_sent",
                                f"تم إرسال رسالة بنجاح إلى {recipient}",
                                {"recipient": str(recipient), "message_preview": message[:50]}
                            )
                        else:
                            logger.log(
                                "WARNING",
                                "empty_message",
                                "محاولة إرسال رسالة فارغة",
                                {"recipient": str(recipient)}
                            )
                            print("⚠️ رسالة فارغة...")
                            item['status'] = 'failed'
                            item['error'] = 'empty_message'
                            continue

                        sent_message_data = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "chat_type": "مجموعة 📢" if recipient_type == "group" else "محادثة خاصة 💬",
                            "group_name": recipient if recipient_type == 'group' else "N/A",
                            "sender": {
                                "name": "أنت (النظام)",
                                "phone": recipient if recipient_type == "phone" and str(recipient).startswith("+") else "system",
                                "username": "@bot",
                                "user_id": 0,
                            },
                            "message": message,
                            "image": image,
                            "chat_id": str(target) if not isinstance(target, int) else target,
                        }

                        save_message(sent_message_data)

                        if recipient_type == "phone" and str(recipient).startswith("+"):
                            update_stats(recipient, "مُرسَل إليه", "محادثة خاصة")

                        print("💾 تم حفظ الرسالة المرسلة في messages.json")
                        item['status'] = 'sent'
                        item['sent_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    except Exception as e:
                        error_msg = f"فشل الإرسال إلى {recipient}: {e}"
                        logger.log(
                            "ERROR",
                            "send_failed",
                            error_msg,
                            {
                                "recipient": recipient,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                        )
                        print(f"❌ {error_msg}")
                        item['status'] = 'failed'
                        item['error'] = str(e)

                with open('send_queue.json', 'w', encoding='utf-8') as f:
                    json.dump(queue, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.log(
                "ERROR",
                "queue_check_error",
                f"خطأ في فحص قائمة الإرسال: {e}",
                {"error": str(e)}
            )
            print(f"❌ خطأ في check_queue: {e}")
            import traceback
            traceback.print_exc()

        await asyncio.sleep(2)


# ====================== تسجيل الخروج (احترافي بدون إغلاق البرنامج) ======================

async def check_logout_flag():
    """فحص ملف logout.flag كل 5 ثواني"""
    global client
    while True:
        try:
            if os.path.exists('logout.flag'):
                logger.log_info(
                    "telegram_logout_detected",
                    "🚪 تم اكتشاف طلب تسجيل خروج - سيتم تنفيذ logout بدون إغلاق البرنامج"
                )
                print("\n" + "=" * 60)
                print("🚪 طلب تسجيل خروج من Dashboard")
                print("🔄 جاري قطع الاتصال وحذف الجلسة (بدون إغلاق CMD)...")
                print("=" * 60 + "\n")

                # 1️⃣ حذف ملف الـ flag أولاً
                try:
                    os.remove('logout.flag')
                    print("✅ تم حذف logout.flag")
                except:
                    pass

                # 2️⃣ قطع الاتصال من Telegram (هذا يغلق الملف)
                try:
                    if client:
                        await client.disconnect()
                        try:
                            client.session.close()
                        except:
                            pass

                    print("✅ تم قطع الاتصال من Telegram")
                except:
                    pass

                # 3️⃣ انتظار ثانية لضمان إغلاق الملف
                await asyncio.sleep(1)

                # 4️⃣ حذف ملفات الـ session
                session_files = [
                    f'{SESSION_NAME}.session',
                    f'{SESSION_NAME}.session-journal'
                ]
                for sf in session_files:
                    try:
                        if os.path.exists(sf):
                            os.remove(sf)
                            print(f"✅ تم حذف {sf}")
                    except Exception as e:
                        print(f"⚠️ تعذر حذف {sf}: {e}")

                # 5️⃣ حذف current_session.json
                try:
                    if os.path.exists('current_session.json'):
                        os.remove('current_session.json')
                        print("✅ تم حذف current_session.json")
                except:
                    pass

                print("\n✅ تم تسجيل الخروج بنجاح!")
                print("⏳ البوت الآن ينتظر تسجيل دخول جديد من Dashboard...\n")

                # 6️⃣ انتظار تسجيل دخول جديد ثم إعادة الاتصال تلقائياً
                while not os.path.exists("current_session.json"):
                    await asyncio.sleep(3)

                print("\n✅ تم اكتشاف تسجيل دخول جديد! إعادة الاتصال...\n")
                print("🔄 سيتم إعادة الاتصال تلقائياً من main()...")

        except Exception as e:
            logger.log_error(
                "logout_check_error",
                f"خطأ في فحص logout.flag: {str(e)}",
                {"error": str(e)}
            )

        await asyncio.sleep(5)


# ====================== login.flag (تحرير sqlite فقط) ======================

async def check_login_flag():
    global client
    while True:
        try:
            if os.path.exists('login.flag'):
                print("\n🔓 تم اكتشاف login.flag - فصل مؤقت لتحرير session")

                # حذف الفلاق فوراً لمنع التكرار
                try:
                    os.remove('login.flag')
                    print("✅ تم حذف login.flag")
                except:
                    pass

                # فصل الاتصال
                try:
                    if client and client.is_connected():
                        await client.disconnect()
                        print("✅ تم فصل الاتصال مؤقتاً")
                except Exception as e:
                    print(f"⚠️ فشل disconnect: {e}")

                # إغلاق sqlite
                try:
                    if client:
                        client.session.close()
                        print("✅ تم إغلاق session (تحرير sqlite)")
                except:
                    pass

                # انتظار أطول قليلاً للداشبورد
                print("⏳ انتظار 8 ثواني للسماح للداشبورد باستخدام الجلسة...")
                await asyncio.sleep(8)

                # مهم: لا تعمل connect هنا
                print("✅ تم تحرير الجلسة.. main() سيعيد الاتصال تلقائياً\n")

        except Exception as e:
            print(f"❌ خطأ في check_login_flag: {e}")

        await asyncio.sleep(1)


# ====================== Main (احترافي دائم) ======================

async def main():
    global client

    print("=" * 60)
    print("🚀 Telegram Monitor - بدء التشغيل")
    print("=" * 60)

    asyncio.create_task(check_queue())
    asyncio.create_task(check_logout_flag())
    asyncio.create_task(check_login_flag())

    while True:
        try:
            # الاعتماد على current_session.json كدليل دخول (أثبت من session file)
            if not os.path.exists("current_session.json"):
                print("\n❌ لا يوجد حساب نشط!")
                print("📌 افتح Dashboard وسجل دخول:")
                print("   http://localhost:5000")
                print("=" * 60)
                print("⏳ في انتظار تسجيل الدخول من Dashboard...\n")

                while not os.path.exists("current_session.json"):
                    await asyncio.sleep(3)

                print("\n✅ تم اكتشاف تسجيل دخول جديد! جاري الاتصال...\n")

            account = session_manager.get_current_account()
            if account:
                print("\n✅ الحساب النشط:")
                print(f"   📱 {account.get('name')} - {account.get('phone')}")
                print(f"   👤 {account.get('username')}")

            allowed = load_allowed_numbers()
            print(f"\n📱 محادثات خاصة مسموحة: {len(allowed['private_chat'])}")
            for num in allowed['private_chat']:
                print(f"   ✓ {num}")

            print(f"\n👥 مجموعات مسموحة: {len(allowed['groups'])}")
            for num in allowed['groups']:
                print(f"   ✓ {num}")

            print("\n" + "=" * 60)
            print("📩 في انتظار الرسائل...")
            print("=" * 60 + "\n")

            # ✅ إنشاء Client جديد كل دورة (أهم نقطة)
            client = create_client()
            client.add_event_handler(handler, events.NewMessage)

            # الاتصال فقط إذا الجلسة جاهزة 100%
            if not client.is_connected():
                await client.connect()

            if not await client.is_user_authorized():
                print("⏳ الجلسة غير جاهزة - dashboard ما خلص تسجيل الدخول")
                await asyncio.sleep(2)
                continue

            if not await client.is_user_authorized():
                print("❌ الجلسة غير جاهزة بعد - انتظر تسجيل الدخول من الداشبورد")
                await asyncio.sleep(2)
                continue

            await client.run_until_disconnected()

            print("⚠️ تم قطع الاتصال... إعادة المحاولة خلال 3 ثواني")
            await asyncio.sleep(3)

        except Exception as e:
            print(f"❌ خطأ في main loop: {e}")
            await asyncio.sleep(3)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("⏹️ تم إيقاف البوت")
        print("=" * 60)

from flask import Flask, jsonify, request, render_template, send_file, redirect, url_for
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
from logger import logger
from dotenv import load_dotenv
from session_manager import session_manager
import shutil


# ✨ استيراد SmartBook Routes
from smartbook_routes import smartbook_bp
from smartbook_auth import smartbook_auth



# تحميل المتغيرات من .env
load_dotenv()



import os
import sys
from flask import Flask

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

TEMPLATES_DIR = resource_path("templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)
CORS(app)


# ✨ تسجيل SmartBook Blueprint
app.register_blueprint(smartbook_bp)



# ========================================
# دوال المساعدة
# ========================================



def load_messages():
    if os.path.exists('messages_data/messages.json'):
        with open('messages_data/messages.json', 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []



def load_stats():
    if os.path.exists('messages_data/statistics.json'):
        with open('messages_data/statistics.json', 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}



def load_allowed():
    if os.path.exists('allowed_numbers.json'):
        with open('allowed_numbers.json', 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return {"private_chat": [], "groups": []}
    return {"private_chat": [], "groups": []}



def save_allowed(data):
    with open('allowed_numbers.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



def load_transfers():
    """📥 تحميل الحوالات من الملف"""
    if os.path.exists('messages_data/transfers.json'):
        with open('messages_data/transfers.json', 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []



def save_transfers(transfers):
    """💾 حفظ الحوالات في الملف"""
    os.makedirs('messages_data', exist_ok=True)
    with open('messages_data/transfers.json', 'w', encoding='utf-8') as f:
        json.dump(transfers, f, ensure_ascii=False, indent=2)



def clear_all_data():
    """🔥 حذف جميع البيانات القديمة"""
    try:
        files_to_clear = [
            'messages_data/messages.json',
            'messages_data/statistics.json',
            'messages_data/logs.json',
            'messages_data/transfers.json',
            'send_queue.json',
            'logs/system_logs.json'
        ]


        for file_path in files_to_clear:
            if os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    if file_path.endswith('statistics.json'):
                        json.dump({}, f)
                    else:
                        json.dump([], f)
                print(f"✅ تم تفريغ: {file_path}")


        if os.path.exists('images'):
            for filename in os.listdir('images'):
                file_path = os.path.join('images', filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                        print(f"✅ تم حذف صورة: {filename}")
                except Exception as e:
                    print(f"❌ خطأ في حذف {file_path}: {e}")


        print("🎉 تم حذف جميع البيانات والسجلات والصور بنجاح!")


    except Exception as e:
        print(f"❌ خطأ في حذف البيانات: {e}")



# ========================================
# 🔐 Middleware للتحقق من SmartBook
# ========================================


@app.before_request
def check_smartbook_auth():
    """التحقق من تسجيل الدخول لـ SmartBook قبل بعض الطلبات فقط"""

    # 1) السماح دائماً بالواجهات الأمامية:
    # - صفحة SmartBook login
    # - صفحة Telegram login + Dashboard (index.html)
    # - الملفات الثابتة
    allowed_paths = [
        '/smartbook-login',
        '/',            # index.html (Telegram login + Dashboard)
        '/static/'
    ]
    if any(request.path.startswith(path) for path in allowed_paths):
        return None

    # 2) السماح بجميع مسارات SmartBook نفسها
    if request.path.startswith('/api/smartbook/'):
        return None

    # 3) حماية فقط باقي REST APIs إذا ما في توكن SmartBook
    if request.path.startswith('/api/'):
        if not smartbook_auth.is_logged_in():
            return jsonify({
                'success': False,
                'message': 'يجب تسجيل الدخول إلى SmartBook أولاً'
            }), 401

    return None




# ========================================
# Routes الأساسية
# ========================================


@app.route('/smartbook-login')
def smartbook_login_page():
    """صفحة تسجيل الدخول إلى SmartBook"""
    return render_template('smartbook_login.html')



@app.route('/')
def index():
    """الصفحة الرئيسية للبوت (بعد تسجيل الدخول)"""
    return render_template('index.html')



@app.route('/api/statistics')
def get_statistics():
    messages = load_messages()
    stats = load_stats()


    today = datetime.now().date()
    today_messages = sum(1 for msg in messages 
                        if datetime.strptime(msg['timestamp'], "%Y-%m-%d %H:%M:%S").date() == today)


    unique_numbers = len(set(msg['sender']['phone'] for msg in messages))
    images_count = sum(1 for msg in messages if msg.get('image'))


    return jsonify({
        'total_messages': len(messages),
        'today_messages': today_messages,
        'unique_numbers': unique_numbers,
        'images': images_count
    })



@app.route('/api/messages')
def get_messages():
    messages = load_messages()
    chat_type = request.args.get('type', 'all')
    search = request.args.get('search', '').lower()


    filtered = messages


    if chat_type != 'all':
        type_map = {'private': 'محادثة خاصة', 'group': 'مجموعة'}
        filtered = [m for m in filtered if m['chat_type'] == type_map.get(chat_type)]


    if search:
        filtered = [m for m in filtered if 
                   search in m.get('message', '').lower() or
                   search in m['sender']['name'].lower() or
                   search in m['sender']['phone'].lower()]


    return jsonify(filtered)



@app.route('/api/numbers')
def get_numbers():
    """جلب إحصائيات الأرقام من الرسائل مباشرة"""
    try:
        messages = load_messages()
        stats = {}


        for msg in messages:
            phone = msg.get('sender', {}).get('phone', 'unknown')


            if phone == 'system' or phone == 'unknown':
                continue


            name = msg.get('sender', {}).get('name', 'غير معروف')
            chat_type = msg.get('chat_type', '')


            if phone not in stats:
                stats[phone] = {
                    'name': name,
                    'phone': phone,
                    'total_messages': 0,
                    'private_chat': 0,
                    'groups': 0,
                    'last_message': msg.get('timestamp', '')
                }


            stats[phone]['total_messages'] += 1
            stats[phone]['last_message'] = msg.get('timestamp', '')
            stats[phone]['name'] = name


            # ✅ التحقق الصحيح (يدعم العربي والإنجليزي)
            if chat_type in ['private', 'محادثة خاصة'] or 'خاصة' in chat_type:
                stats[phone]['private_chat'] += 1
            else:
                stats[phone]['groups'] += 1



        return jsonify(stats)


    except Exception as e:
        print(f"❌ خطأ في جلب الأرقام: {e}")
        return jsonify({})



@app.route('/api/allowed')
def get_allowed():
    return jsonify(load_allowed())

@app.route('/api/allowed-with-names')
def get_allowed_with_names():
    """جلب الأرقام المسموحة مع الأسماء"""
    try:
        allowed = load_allowed()
        
        # إنشاء قاموس للأسماء من smartbook_sync
        contacts_map = {}
        if 'smartbook_sync' in allowed and 'contacts' in allowed['smartbook_sync']:
            for contact in allowed['smartbook_sync']['contacts']:
                mobile = contact.get('mobile')
                if mobile:
                    contacts_map[mobile] = contact.get('name', 'بدون اسم')
        
        # إنشاء القوائم مع الأسماء
        private_with_names = []
        for mobile in allowed.get('private_chat', []):
            private_with_names.append({
                'mobile': mobile,
                'name': contacts_map.get(mobile, 'بدون اسم')
            })
        
        groups_with_names = []
        for mobile in allowed.get('groups', []):
            groups_with_names.append({
                'mobile': mobile,
                'name': contacts_map.get(mobile, 'بدون اسم')
            })
        
        return jsonify({
            'private_chat': private_with_names,
            'groups': groups_with_names
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.route('/api/allowed/add', methods=['POST'])
def add_allowed():
    """إضافة رقم مسموح"""
    try:
        data = request.json
        allowed = load_allowed()
        number_type = data.get('type')
        number = data.get('number')
        name = data.get('name', '').strip() or 'بدون اسم'  # 🆕 إضافة الاسم
        
        if not number:
            return jsonify({'status': 'error', 'message': 'الرقم مطلوب'}), 400
        
        # إضافة للقائمة المناسبة
        if number_type == 'private':
            if number not in allowed['private_chat']:
                allowed['private_chat'].append(number)
                logger.log('SUCCESS', 'number_added', 
                          f'تم إضافة رقم: {name} ({number}) للمحادثات الخاصة',  # 🆕 الاسم في السجل
                          {'type': 'private', 'number': number, 'name': name})
            else:
                return jsonify({'status': 'error', 'message': 'الرقم موجود بالفعل'}), 400
                
        elif number_type == 'group':
            if number not in allowed['groups']:
                allowed['groups'].append(number)
                logger.log('SUCCESS', 'number_added', 
                          f'تم إضافة رقم: {name} ({number}) للمجموعات',  # 🆕 الاسم في السجل
                          {'type': 'group', 'number': number, 'name': name})
            else:
                return jsonify({'status': 'error', 'message': 'الرقم موجود بالفعل'}), 400
        else:
            return jsonify({'status': 'error', 'message': 'نوع غير صحيح'}), 400
        
        # 🆕 حفظ الاسم في smartbook_sync أيضاً
        if 'smartbook_sync' not in allowed:
            allowed['smartbook_sync'] = {'last_sync': 'يدوي', 'total_contacts': 0, 'contacts': []}
        
        # البحث عن الرقم في contacts
        existing = next((c for c in allowed['smartbook_sync']['contacts'] if c.get('mobile') == number), None)
        
        if existing:
            # تحديث الاسم والحالة
            existing['name'] = name
            if number_type == 'private':
                existing['active'] = True
            if number_type == 'group':
                existing['allowed_in_groups'] = True
        else:
            # إضافة جديد
            allowed['smartbook_sync']['contacts'].append({
                'mobile': number,
                'name': name,
                'active': number_type == 'private',
                'allowed_in_groups': number_type == 'group'
            })
        
        save_allowed(allowed)
        return jsonify({
            'status': 'success', 
            'message': f'تم إضافة {name} ({number}) بنجاح'
        })
        
    except Exception as e:
        logger.log('ERROR', 'add_number_failed', f'فشل إضافة رقم: {str(e)}', {'error': str(e)})
        return jsonify({'status': 'error', 'message': str(e)}), 500




@app.route('/api/allowed/delete', methods=['POST'])
def delete_allowed():
    """✅ حذف رقم من القائمة المسموحة"""
    try:
        data = request.json
        allowed = load_allowed()

        number_type = data.get('type')
        number = data.get('number')

        if not number:
            return jsonify({'status': 'error', 'message': 'الرقم مطلوب'}), 400

        # 🆕 البحث عن الاسم من smartbook_sync
        name = 'بدون اسم'
        if 'smartbook_sync' in allowed and 'contacts' in allowed['smartbook_sync']:
            contact = next((c for c in allowed['smartbook_sync']['contacts'] if c.get('mobile') == number), None)
            if contact:
                name = contact.get('name', 'بدون اسم')

        if number_type == 'private':
            if number in allowed['private_chat']:
                allowed['private_chat'].remove(number)
                logger.log("SUCCESS", "number_deleted",
                          f"تم حذف رقم خاص: {name} ({number})",  # 🆕 إضافة الاسم
                          {"type": "private", "number": number, "name": name})  # 🆕 الاسم في details
            else:
                return jsonify({'status': 'error', 'message': 'الرقم غير موجود'}), 400

        elif number_type == 'group':
            if number in allowed['groups']:
                allowed['groups'].remove(number)
                logger.log("SUCCESS", "number_deleted",
                          f"تم حذف رقم مجموعة: {name} ({number})",  # 🆕 إضافة الاسم
                          {"type": "group", "number": number, "name": name})  # 🆕 الاسم في details
            else:
                return jsonify({'status': 'error', 'message': 'الرقم غير موجود'}), 400
        else:
            return jsonify({'status': 'error', 'message': 'نوع غير صالح'}), 400

        save_allowed(allowed)
        return jsonify({'status': 'success', 'message': f'تم حذف {name} بنجاح'})  # 🆕 الاسم في الرسالة

    except Exception as e:
        logger.log("ERROR", "delete_number_failed",
                  f"فشل حذف رقم: {str(e)}",
                  {"error": str(e)})
        return jsonify({'status': 'error', 'message': str(e)}), 500




@app.route('/api/send', methods=['POST'])
def send_message():
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            recipient = request.form.get('recipient')
            message = request.form.get('message', '')
            recipient_type = request.form.get('recipient_type', 'phone')
            image = request.files.get('image')
        else:
            data = request.get_json()
            recipient = data.get('recipient')
            message = data.get('message', '')
            recipient_type = data.get('recipient_type', 'phone')
            image = None


        if not recipient:
            return jsonify({'status': 'error', 'message': 'المستلم مطلوب'}), 400


        image_path = None
        if image:
            os.makedirs('images', exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"images/image_{timestamp}.jpg"
            image.save(image_path)


        queue = []
        if os.path.exists('send_queue.json'):
            with open('send_queue.json', 'r', encoding='utf-8') as f:
                try:
                    queue = json.load(f)
                except:
                    queue = []


        queue.append({
            'recipient': recipient,
            'message': message,
            'image': image_path,
            'recipient_type': recipient_type,
            'status': 'pending',
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })


        with open('send_queue.json', 'w', encoding='utf-8') as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)


        return jsonify({'status': 'success', 'message': 'تم إضافة الرسالة للطابور'})


    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/api/logs')
def get_logs():
    try:
        search = request.args.get('search', '').lower()
        log_type = request.args.get('type', '')
        category = request.args.get('category', '')
        limit = int(request.args.get('limit', 100))


        logs = logger.get_recent_logs(hours=24, limit=limit)


        if search:
            logs = [log for log in logs if 
                   search in log.get('message', '').lower() or
                   search in log.get('category', '').lower()]


        if log_type:
            logs = [log for log in logs if log.get('type') == log_type]


        if category:
            logs = [log for log in logs if log.get('category') == category]


        return jsonify(logs)


    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/logs/statistics')
def get_log_statistics():
    try:
        hours = int(request.args.get('hours', 24))
        stats = logger.get_statistics(hours=hours)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/logs/export')
def export_logs():
    try:
        format_type = request.args.get('format', 'json')
        hours = int(request.args.get('hours', 24))


        logs = logger.get_recent_logs(hours=hours, limit=10000)


        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


        if format_type == 'json':
            filename = f'logs_export_{timestamp}.json'
            filepath = os.path.join('logs', filename)


            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)


            return send_file(filepath, as_attachment=True)


        elif format_type == 'csv':
            import csv
            filename = f'logs_export_{timestamp}.csv'
            filepath = os.path.join('logs', filename)


            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if logs:
                    writer = csv.DictWriter(f, fieldnames=['timestamp', 'type', 'category', 'message'])
                    writer.writeheader()
                    for log in logs:
                        writer.writerow({
                            'timestamp': log.get('timestamp'),
                            'type': log.get('type'),
                            'category': log.get('category'),
                            'message': log.get('message')
                        })


            return send_file(filepath, as_attachment=True)


        return jsonify({'error': 'Invalid format'}), 400


    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ========================================
# 💰 Transfers APIs
# ========================================


@app.route('/api/transfers')
def get_transfers():
    """📥 جلب جميع الحوالات"""
    try:
        transfers = load_transfers()
        transfers.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(transfers)
    except Exception as e:
        logger.log("ERROR", "transfers_load_failed", 
                  f"فشل جلب الحوالات: {str(e)}", 
                  {"error": str(e)})
        return jsonify([])



@app.route('/api/transfers/statistics')
def get_transfers_statistics():
    """📊 إحصائيات الحوالات"""
    try:
        transfers = load_transfers()


        today = datetime.now().date()


        stats = {
            'total': len(transfers),
            'claimed': sum(1 for t in transfers if t.get('status') == 'claimed'),
            'pending': sum(1 for t in transfers if t.get('status') == 'pending'),
            'failed': sum(1 for t in transfers if t.get('status') == 'failed'),
            'today': sum(1 for t in transfers 
                        if datetime.strptime(t['timestamp'], "%Y-%m-%d %H:%M:%S").date() == today),
            'total_amount': sum(t.get('transfer_details', {}).get('amount', 0) 
                               for t in transfers if t.get('status') == 'claimed')
        }


        return jsonify(stats)


    except Exception as e:
        logger.log("ERROR", "transfers_stats_failed",
                  f"فشل جلب إحصائيات الحوالات: {str(e)}",
                  {"error": str(e)})
        return jsonify({'error': str(e)}), 500



@app.route('/api/manual-claim', methods=['POST'])
def manual_claim():
    """💰 استلام حوالة يدوياً"""
    try:
        data = request.json
        transfer_number = data.get('transfer_number', '').strip()
        receiver_phone = data.get('receiver_phone', '').strip()


        if not transfer_number or not receiver_phone:
            return jsonify({
                'success': False, 
                'error': 'رقم الحوالة ورقم الهاتف مطلوبان'
            }), 400


        try:
            from api_integration import MockHawalaAPI
            api = MockHawalaAPI()
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'فشل تحميل نظام الحوالات'
            }), 500


        check = api.check_transfer(transfer_number)
        if not check.get('success') or not check.get('exists'):
            logger.log("WARNING", "transfer_not_found",
                      f"الحوالة غير موجودة: {transfer_number}",
                      {"transfer_number": transfer_number})
            return jsonify({
                'success': False,
                'error': 'الحوالة غير موجودة في النظام'
            })


        result = api.claim_transfer(transfer_number, receiver_phone)


        if result.get('success'):
            transfer_record = {
                'transfer_number': transfer_number,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'sender': {
                    'name': 'استلام يدوي',
                    'phone': receiver_phone,
                    'username': ''
                },
                'transfer_details': result.get('data', {}),
                'status': 'claimed',
                'claimed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'manual': True,
                'message': f'تم استلام الحوالة يدوياً: {transfer_number}'
            }


            transfers = load_transfers()


            existing = next((t for t in transfers if t.get('transfer_number') == transfer_number), None)
            if existing:
                logger.log("WARNING", "duplicate_transfer",
                          f"الحوالة مستلمة مسبقاً: {transfer_number}",
                          {"transfer_number": transfer_number})
                return jsonify({
                    'success': False,
                    'error': 'الحوالة مستلمة مسبقاً'
                })


            transfers.append(transfer_record)
            save_transfers(transfers)


            logger.log("SUCCESS", "transfer_claimed",
                      f"تم استلام حوالة يدوياً: {transfer_number} - المبلغ: {result.get('data', {}).get('amount')} ريال",
                      {
                          "transfer_number": transfer_number,
                          "amount": result.get('data', {}).get('amount'),
                          "receiver_phone": receiver_phone,
                          "manual": True
                      })


            return jsonify({
                'success': True,
                'message': 'تم استلام الحوالة بنجاح',
                'amount': result.get('data', {}).get('amount'),
                'transfer_number': transfer_number
            })
        else:
            logger.log("ERROR", "transfer_claim_failed",
                      f"فشل استلام الحوالة: {transfer_number} - {result.get('error')}",
                      {"transfer_number": transfer_number, "error": result.get('error')})
            return jsonify({
                'success': False,
                'error': result.get('error', 'فشل استلام الحوالة')
            })


    except Exception as e:
        logger.log("ERROR", "manual_claim_error",
                  f"خطأ في الاستلام اليدوي: {str(e)}",
                  {"error": str(e)})
        return jsonify({
            'success': False,
            'error': f'خطأ: {str(e)}'
        }), 500



@app.route('/api/transfers/export')
def export_transfers():
    """📥 تصدير الحوالات CSV"""
    try:
        import csv
        transfers = load_transfers()


        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'transfers_export_{timestamp}.csv'
        filepath = os.path.join('messages_data', filename)


        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['رقم الحوالة', 'المبلغ', 'المرسل', 'رقم المرسل', 
                         'المستلم', 'رقم المستلم', 'التاريخ', 'الحالة', 'يدوي']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


            for t in transfers:
                writer.writerow({
                    'رقم الحوالة': t.get('transfer_number', ''),
                    'المبلغ': t.get('transfer_details', {}).get('amount', 0),
                    'المرسل': t.get('transfer_details', {}).get('sender_name', ''),
                    'رقم المرسل': t.get('transfer_details', {}).get('sender_phone', ''),
                    'المستلم': t.get('sender', {}).get('name', ''),
                    'رقم المستلم': t.get('sender', {}).get('phone', ''),
                    'التاريخ': t.get('timestamp', ''),
                    'الحالة': t.get('status', ''),
                    'يدوي': 'نعم' if t.get('manual') else 'لا'
                })


        return send_file(filepath, as_attachment=True, download_name=filename)


    except Exception as e:
        logger.log("ERROR", "export_failed",
                  f"فشل تصدير الحوالات: {str(e)}",
                  {"error": str(e)})
        return jsonify({'error': str(e)}), 500



# ========================================
# Session Management APIs
# ========================================


@app.route('/api/session/current')
def get_current_session():
    account = session_manager.get_current_account()
    return jsonify({
        "logged_in": bool(account),
        "account": account
    })

@app.route('/api/session/status', methods=['GET'])
def session_status():
    try:
        account = session_manager.get_current_account()
        return jsonify({
            "logged_in": bool(account),
            "account": account
        })
    except Exception:
        return jsonify({"logged_in": False, "account": None})


@app.route('/api/smartbook/status', methods=['GET'])
def smartbook_status():
    """حالة تسجيل الدخول في SmartBook"""
    return jsonify({
        'logged_in': smartbook_auth.is_logged_in(),
        'has_token': smartbook_auth.get_token() is not None
    })


@app.route('/api/session/login', methods=['POST'])
def session_login():
    """إرسال كود التحقق - مع حذف البيانات إذا كان رقم جديد"""
    try:
        data = request.json
        phone = data.get('phone')


        if not phone:
            return jsonify({"status": "error", "message": "رقم الهاتف مطلوب"}), 400


        current_account = session_manager.get_current_account()
        if current_account and current_account.get('phone') != phone:
            print(f"🔄 رقم جديد تم اكتشافه: {phone} (السابق: {current_account.get('phone')})")
            print("🗑️ جاري حذف البيانات القديمة...")
            clear_all_data()
            logger.log("INFO", "data_cleared", 
                      f"تم حذف البيانات القديمة بسبب تسجيل دخول برقم جديد: {phone}",
                      {"old_phone": current_account.get('phone'), "new_phone": phone})

        with open("login.flag", "w", encoding="utf-8") as f:
            f.write("login")

        result = session_manager.add_account(phone)

        return jsonify(result)


    except Exception as e:
        logger.log("ERROR", "login_failed",
                  f"فشل إرسال كود التحقق: {str(e)}",
                  {"error": str(e)})
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/api/session/verify', methods=['POST'])
def session_verify():
    """التحقق من الكود وتسجيل الدخول"""
    try:
        data = request.json
        phone = data.get('phone')
        code = data.get('code')
        password = data.get('password')


        if not phone or not code:
            return jsonify({"status": "error", "message": "البيانات غير كاملة"}), 400

        with open("login.flag", "w", encoding="utf-8") as f:
            f.write("login")
        
        result = session_manager.verify_code(phone, code, password)


        if result.get('status') == 'success':
            logger.log("SUCCESS", "login_success",
                      f"تم تسجيل دخول بنجاح: {phone}",
                      {"phone": phone})


        return jsonify(result)


    except Exception as e:
        logger.log("ERROR", "verify_failed",
                  f"فشل التحقق من الكود: {str(e)}",
                  {"error": str(e)})
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/api/session/logout', methods=['POST'])
def session_logout():
    """🔥 تسجيل خروج - مع حذف جميع البيانات وإشعار البوت"""
    try:
        current_account = session_manager.get_current_account()
        result = session_manager.logout()
        
        if result.get('status') == 'success':
            print("🗑️ جاري حذف جميع البيانات...")
            clear_all_data()
            
            # 🆕 إنشاء ملف logout.flag لإشعار البوت
            try:
                with open('logout.flag', 'w', encoding='utf-8') as f:
                    f.write('logout_requested')
                print("✅ تم إنشاء ملف logout.flag")
                print("📢 البوت سيكتشفه ويعيد تشغيل نفسه خلال 5-10 ثواني")
            except Exception as flag_error:
                print(f"⚠️ فشل إنشاء logout.flag: {flag_error}")
            
            logger.log("INFO", "logout_success",
                      "تم تسجيل خروج وطلب إعادة تشغيل البوت",
                      {"phone": current_account.get('phone') if current_account else None})
        
        return jsonify(result)
    
    except Exception as e:
        logger.log("ERROR", "logout_failed",
                  f"فشل تسجيل الخروج: {str(e)}",
                  {"error": str(e)})
        return jsonify({"status": "error", "message": str(e)}), 500




@app.route('/api/allowed-numbers', methods=['GET'])
def get_allowed_numbers():
    """جلب الأرقام المسموحة مع الأسماء"""
    try:
        # تحميل الملف
        if os.path.exists('allowed_numbers.json'):
            with open('allowed_numbers.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # جلب البيانات من smartbook_sync
            contacts = data.get('smartbook_sync', {}).get('contacts', [])
            
            # إنشاء قواميس للبحث السريع
            contacts_map = {}
            for contact in contacts:
                mobile = contact.get('mobile')
                if mobile:
                    contacts_map[mobile] = {
                        'name': contact.get('name', 'بدون اسم'),
                        'active': contact.get('active', False),
                        'allowed_in_groups': contact.get('allowed_in_groups', False)
                    }
            
            # إنشاء القوائم مع الأسماء
            private_chat_list = []
            for mobile in data.get('private_chat', []):
                info = contacts_map.get(mobile, {})
                private_chat_list.append({
                    'mobile': mobile,
                    'name': info.get('name', 'بدون اسم')
                })
            
            groups_list = []
            for mobile in data.get('groups', []):
                info = contacts_map.get(mobile, {})
                groups_list.append({
                    'mobile': mobile,
                    'name': info.get('name', 'بدون اسم')
                })
            
            return jsonify({
                'success': True,
                'private_chat': private_chat_list,
                'groups': groups_list,
                'last_sync': data.get('smartbook_sync', {}).get('last_sync', 'غير معروف')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'لا توجد جهات اتصال محفوظة'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ: {str(e)}'
        })







# ========================================
# تشغيل التطبيق
# ========================================


if __name__ == '__main__':
    os.makedirs('messages_data', exist_ok=True)
    os.makedirs('images', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)


    print("\n" + "="*60)
    print("🌐 Dashboard متاح على: http://localhost:5000")
    print(f"📌 API ID: {os.getenv('API_ID')}")
    print(f"📌 Session: {os.getenv('SESSION_NAME')}")
    print("🔐 SmartBook: http://localhost:5000/smartbook-login")
    print("🔄 ✅ زر تحديث جهات الاتصال يعمل الآن بدون أخطاء SSL!")
    print("="*60 + "\n")


    app.run(debug=False, host='127.0.0.1', port=5000, threaded=False, use_reloader=False)

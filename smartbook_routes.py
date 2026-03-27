from flask import Blueprint, jsonify, request

import json
import os
from smartbook_auth import smartbook_auth
from datetime import datetime

smartbook_bp = Blueprint('smartbook', __name__, url_prefix='/api/smartbook')


@smartbook_bp.route('/test', methods=['GET'])
def test_connection():
    """🧪 اختبار الربط"""
    return jsonify({"success": True, "msg": "SmartBook API جاهز!"})


@smartbook_bp.route('/login', methods=['POST'])
def login():
    """🔐 تسجيل الدخول إلى SmartBook"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                'success': False,
                'message': 'اسم المستخدم وكلمة المرور مطلوبان'
            }), 400

        result = smartbook_auth.login(username, password)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 401

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تسجيل الدخول: {str(e)}'
        }), 500


@smartbook_bp.route('/sync-contacts', methods=['GET'])
def sync_contacts():
    """🔄 مزامنة جهات الاتصال من SmartBook"""
    
    if not smartbook_auth.is_logged_in():
        return jsonify({
            'success': False,
            'error': 'يجب تسجيل الدخول أولاً',
            'message': 'الرجاء تسجيل الدخول إلى SmartBook أولاً'
        }), 401

    try:
        result = smartbook_auth.fetch_contacts()
        
        if result['success']:
            # تحميل البيانات المحفوظة
            contacts_file = 'allowed_numbers.json'
            if os.path.exists(contacts_file):
                with open(contacts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'private_chat': [], 'groups': []}

            return jsonify({
                'success': True,
                'message': result['message'],
                'count': result['count'],
                'source_url': smartbook_auth.api_contacts_url,
                'added': {
                    'private': len([c for c in smartbook_auth.contacts if c.get('active')]),
                    'groups': len([c for c in smartbook_auth.contacts if c.get('allowed_in_groups')])
                },
                'total_allowed': {
                    'private': len(data.get('private_chat', [])),
                    'groups': len(data.get('groups', []))
                },
                'sample': smartbook_auth.contacts[:3] if smartbook_auth.contacts else []
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result['message'],
                'message': result['message']
            }), 502

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'خطأ في المزامنة: {str(e)}'
        }), 500


@smartbook_bp.route('/status', methods=['GET'])
def status():
    """📊 التحقق من حالة تسجيل الدخول"""
    return jsonify({
        'logged_in': smartbook_auth.is_logged_in(),
        'has_token': smartbook_auth.token is not None,
        'contacts_count': len(smartbook_auth.contacts)
    })


@smartbook_bp.route('/logout', methods=['POST'])
def logout():
    """🚪 تسجيل الخروج وحذف جميع البيانات"""
    try:
        result = smartbook_auth.logout()
        
        # ✅ إضافة Logging للعملية
        from logger import logger
        logger.log_info(
            "smartbook_logout", 
            "تم تسجيل الخروج من SmartBook وحذف جميع الأرقام",
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "contacts_cleared": True
            }
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في تسجيل الخروج: {str(e)}'
        }), 500

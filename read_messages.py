import json

# قراءة الرسائل
with open('messages_data/messages.json', 'r', encoding='utf-8') as f:
    messages = json.load(f)

# طباعة منظمة
print(f"إجمالي الرسائل: {len(messages)}\n")
print("="*70)

for i, msg in enumerate(messages, 1):
    print(f"\n📩 رسالة #{i}")
    print(f"⏰ {msg['timestamp']}")
    print(f"👥 {msg['chat_type']}: {msg['group_name']}")
    print(f"👤 {msg['sender']['name']} ({msg['sender']['phone']})")
    print(f"💬 {msg['message']}")
    if msg['image']:
        print(f"📸 {msg['image']}")
    print("-"*70)

import json
import os

if not os.path.exists('messages_data/statistics.json'):
    print("❌ لا توجد إحصائيات بعد!")
    print("شغّل telegram_receiver.py وانتظر رسائل.")
    exit()

with open('messages_data/statistics.json', 'r', encoding='utf-8') as f:
    stats = json.load(f)

if not stats:
    print("📭 لا توجد إحصائيات بعد!")
    exit()

# ترتيب حسب عدد الرسائل
sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total_messages'], reverse=True)

print("="*80)
print("                        📊 إحصائيات الرسائل")
print("="*80)
print(f"\nإجمالي الأرقام: {len(stats)}")
print(f"إجمالي الرسائل: {sum(s['total_messages'] for s in stats.values())}\n")

print("─"*80)
print(f"{'الرقم':<18} {'الاسم':<20} {'المجموع':<10} {'خاص':<8} {'مجموعة':<10} {'آخر رسالة':<20}")
print("─"*80)

for phone, data in sorted_stats:
    print(f"{phone:<18} {data['name']:<20} {data['total_messages']:<10} "
          f"{data['private_chat']:<8} {data['groups']:<10} {data['last_message']:<20}")

print("─"*80)

# أكثر 3 نشاطًا
print("\n🏆 الأكثر نشاطًا:")
for i, (phone, data) in enumerate(sorted_stats[:3], 1):
    print(f"{i}. {data['name']} ({phone}): {data['total_messages']} رسالة")

print("\n✅ انتهى!")

import telebot
from telebot import types
import sqlite3
from datetime import datetime
import random
import time

# توكن البوت ومعرف الأدمن/المالك الرئيسي للبوت
TOKEN = '8879763429:AAGX5sNAU8nxI5iKSTZg5pu1V5gujnJp0ec'
ADMIN_ID = 7397855956  

bot = telebot.TeleBot(TOKEN)

# تفعيل محاولة إعادة الاتصال التلقائي لتجنب مشاكل البروكسي
telebot.apihelper.CONNECT_TIMEOUT = 20
telebot.apihelper.READ_TIMEOUT = 20

PRICES = {
    'ios_365': 500.0,
    'android_1d': 50.0,
    'android_7d': 200.0,
    'android_15d': 400.0,
    'android_30d': 500.0,
    'ios_service_1d': 50.0,
    'ios_service_7d': 200.0,
    'ios_service_15d': 400.0,
    'ios_service_30d': 500.0,
    'pc_1d': 50.0,
    'pc_7d': 200.0,
    'pc_15d': 400.0,
    'pc_30d': 500.0,
}

def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            referrals INTEGER DEFAULT 0,
            joined_date TEXT,
            last_spin TEXT,
            referred_by INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            key_code TEXT,
            is_used INTEGER DEFAULT 0
        )
    ''')
    
    columns_to_add = [
        ("referrals", "INTEGER DEFAULT 0"),
        ("joined_date", "TEXT"),
        ("last_spin", "TEXT"),
        ("referred_by", "INTEGER DEFAULT 0")
    ]
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except:
            pass

    conn.commit()
    conn.close()

init_db()

# --- أمر تفريغ الخزنة ---
@bot.message_handler(commands=['clearstock'])
def clear_stock(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM keys_stock')
    conn.commit()
    conn.close()
    
    bot.reply_to(message, "🗑️ All keys stock has been completely cleared!")

# --- أمر فحص الخزنة ---
@bot.message_handler(commands=['stock'])
def check_stock_admin(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    report = "📦 CURRENT VAULT STOCK REPORT\n\n"
    for cat in PRICES.keys():
        cursor.execute('SELECT COUNT(*) FROM keys_stock WHERE category = ? AND is_used = 0', (cat,))
        count = cursor.fetchone()[0]
        report += f"┣ {cat}: {count} available\n"
        
    conn.close()
    bot.reply_to(message, report)

# --- أمر إضافة كود فردي ---
@bot.message_handler(commands=['addkey'])
def add_single_key(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = message.text.strip().split()
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ Usage: /addkey <category> <key_code>")
            return
        
        category = parts[1]
        key_code = parts[2]

        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO keys_stock (category, key_code, is_used) VALUES (?, ?, 0)', (category, key_code))
        conn.commit()
        conn.close()

        bot.reply_to(message, f"✅ Key {key_code} successfully added to {category} vault!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# --- أمر إضافة أكواد بالجملة ---
@bot.message_handler(commands=['addkeys'])
def add_bulk_keys(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        lines = message.text.strip().split('\n')
        first_line = lines[0].split()
        
        if len(first_line) < 2:
            bot.reply_to(message, "⚠️ Usage:\n/addkeys <category>\n(followed by keys line by line)")
            return
            
        category = first_line[1]
        keys_list = [line.strip() for line in lines[1:] if line.strip()]
        
        if not keys_list:
            bot.reply_to(message, "⚠️ No keys found! Paste keys line by line under the command.")
            return

        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        
        count = 0
        for k in keys_list:
            cursor.execute('INSERT INTO keys_stock (category, key_code, is_used) VALUES (?, ?, 0)', (category, k))
            count += 1
            
        conn.commit()
        conn.close()

        bot.reply_to(message, f"✅ Successfully added {count} keys to {category} vault!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error adding keys: {e}")

# --- Start Command ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    joined_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    command_args = message.text.split()
    referrer_id = 0
    if len(command_args) > 1 and command_args[1].startswith('ref_'):
        try:
            referrer_id = int(command_args[1].replace('ref_', ''))
        except:
            referrer_id = 0

    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute('INSERT INTO users (user_id, username, balance, referrals, joined_date, last_spin, referred_by) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                           (user_id, username, 0.0, 0, joined_now, "", referrer_id))
            conn.commit()
            
            if referrer_id and referrer_id != user_id:
                cursor.execute('UPDATE users SET referrals = referrals + 1, balance = balance + 3.0 WHERE user_id = ?', (referrer_id,))
                conn.commit()
                try:
                    bot.send_message(referrer_id, "🎉 New Referral! Someone joined using your link. You earned 3.0 EGP!")
                except:
                    pass
    except:
        pass
    conn.close()

    welcome_text = (
        "🔥 — SMOKE SHOP — 🔥\n\n"
        "👋 Welcome, Customer!\n\n"
        "⭐ — STORE HIGHLIGHTS — ⭐\n\n"
        "🔑 Premium Game Keys\n"
        "⚡ Instant Delivery 24/7\n"
        "🔒 100% Secure Payment\n"
        "💰 Best Prices Guaranteed\n"
        "🎁 Referral Rewards\n"
        "📞 Professional Support\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 Tap Shop Now to Start!"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton('💎 Shop Now', callback_data='shop_now'))
    markup.add(types.InlineKeyboardButton('🧾 My Orders', callback_data='my_orders'), types.InlineKeyboardButton('👑 Profile', callback_data='profile'))
    markup.add(types.InlineKeyboardButton('💳 Add Balance', callback_data='add_balance'), types.InlineKeyboardButton('🤝 Referral', callback_data='referral'))
    markup.add(types.InlineKeyboardButton('🍀 Lucky Spin', callback_data='lucky_spin'))
    markup.add(types.InlineKeyboardButton('🎓 How to Use', callback_data='how_to_use'))
    markup.add(types.InlineKeyboardButton('💬 Support', callback_data='support'))

    bot.reply_to(message, welcome_text, reply_markup=markup)

# --- Callback Handler ---
@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    user_id = call.from_user.id
    username = call.from_user.username or call.from_user.first_name

    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        joined_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('INSERT INTO users (user_id, username, balance, referrals, joined_date, last_spin, referred_by) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                       (user_id, username, 0.0, 0, joined_now, "", 0))
        conn.commit()
    conn.close()

    if call.data.startswith('approve_'):
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return

        target_user_id = int(call.data.split('_')[1])
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton('🇪🇬 Vodafone Cash', callback_data=f'paymethod_vf_{target_user_id}'),
            types.InlineKeyboardButton('🌐 Binance Pay', callback_data=f'paymethod_bn_{target_user_id}'),
            types.InlineKeyboardButton('❌ Cancel', callback_data='cancel_action')
        )
        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error updating markup: {e}")
        return

    elif call.data.startswith('paymethod_'):
        if call.from_user.id != ADMIN_ID:
            return
        
        parts = call.data.split('_')
        method = parts[1]
        target_user_id = int(parts[2])
        bot.answer_callback_query(call.id)

        markup = types.InlineKeyboardMarkup(row_width=2)
        if method == 'vf':
            markup.add(
                types.InlineKeyboardButton('50 EGP', callback_data=f'addbal_{target_user_id}_50'),
                types.InlineKeyboardButton('100 EGP', callback_data=f'addbal_{target_user_id}_100'),
                types.InlineKeyboardButton('200 EGP', callback_data=f'addbal_{target_user_id}_200'),
                types.InlineKeyboardButton('300 EGP', callback_data=f'addbal_{target_user_id}_300'),
                types.InlineKeyboardButton('400 EGP', callback_data=f'addbal_{target_user_id}_400'),
                types.InlineKeyboardButton('500 EGP', callback_data=f'addbal_{target_user_id}_500'),
            )
        else:
            markup.add(
                types.InlineKeyboardButton('1$ (50 EGP)', callback_data=f'addbal_{target_user_id}_50'),
                types.InlineKeyboardButton('2$ (100 EGP)', callback_data=f'addbal_{target_user_id}_100'),
                types.InlineKeyboardButton('4$ (200 EGP)', callback_data=f'addbal_{target_user_id}_200'),
                types.InlineKeyboardButton('6$ (300 EGP)', callback_data=f'addbal_{target_user_id}_300'),
                types.InlineKeyboardButton('8$ (400 EGP)', callback_data=f'addbal_{target_user_id}_400'),
                types.InlineKeyboardButton('10$ (500 EGP)', callback_data=f'addbal_{target_user_id}_500'),
            )
        markup.add(types.InlineKeyboardButton('🔙 Back', callback_data=f'approve_{target_user_id}'))

        try:
            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Error updating markup: {e}")
        return

    elif call.data.startswith('addbal_'):
        if call.from_user.id != ADMIN_ID:
            return
        
        parts = call.data.split('_')
        target_user_id = int(parts[1])
        amount = float(parts[2])

        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (target_user_id,))
        row = cursor.fetchone()
        if not row:
            joined_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('INSERT INTO users (user_id, username, balance, referrals, joined_date, last_spin, referred_by) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                           (target_user_id, "User", amount, 0, joined_now, "", 0))
        else:
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, target_user_id))
            
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, f"✅ Successfully added {amount} EGP!")
        
        try:
            bot.send_message(target_user_id, f"🎉 Congratulations! Your payment receipt has been Approved by the admin. {amount} EGP has been added to your balance!")
        except Exception as e:
            print(f"Error notifying user: {e}")
        
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"{call.message.caption}\n\n✅ Status: APPROVED ({amount} EGP Added)",
                reply_markup=None
            )
        except Exception as e:
            print(f"Error editing caption: {e}")
        return

    elif call.data.startswith('reject_'):
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ You are not authorized!", show_alert=True)
            return

        target_user_id = int(call.data.split('_')[1])
        bot.answer_callback_query(call.id, "❌ Deposit Rejected.")
        try:
            bot.send_message(target_user_id, "❌ Sorry! Your payment receipt was Rejected. Please check your payment and try again.")
        except:
            pass
        
        try:
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"{call.message.caption}\n\n❌ Status: REJECTED BY ADMIN",
                reply_markup=None
            )
        except:
            pass
        return

    elif call.data == 'cancel_action':
        try:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
        except:
            pass
        return

    if call.data == 'shop_now':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton('🍏 iOS Certificates (365 Days)', callback_data='ios_certs'),
            types.InlineKeyboardButton('🤖 Android Mods (PHANTOM)', callback_data='android_mods'),
            types.InlineKeyboardButton('📱 iOS Service & Mods (PHANTOM)', callback_data='ios_service_mods'),
            types.InlineKeyboardButton('💻 PC Board Mods (PHANTOM)', callback_data='pc_mods'),
            types.InlineKeyboardButton('🔙 Back to Main Menu', callback_data='main_menu')
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔥 — SMOKE SHOP — 🔥\n🛍️ Categories:\n\nSelect your required section below:",
            reply_markup=markup
        )

    elif call.data == 'ios_certs':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton('🔑 [365 Days] » 10$ / 500 EGP', callback_data='buy_ios_365'),
            types.InlineKeyboardButton('🔙 Back to Categories', callback_data='shop_now')
        )
        text_content = (
            "🔥 — SMOKE SHOP — 🔥\n"
            "🍏 IOS CERTIFICATES (365 DAYS)\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ SERVICE: iOS Service\n"
            "📊 Status: ✅ In Stock\n"
            "🏷️ Price: 10$ / 500 EGP\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 Select your plan below:"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text_content, reply_markup=markup)

    elif call.data in ['android_mods', 'ios_service_mods', 'pc_mods']:
        bot.answer_callback_query(call.id)
        if call.data == 'android_mods':
            section_name, prefix = "ANDROID MODS", "android"
        elif call.data == 'ios_service_mods':
            section_name, prefix = "IOS SERVICE & MODS", "ios_service"
        else:
            section_name, prefix = "PC BOARD MODS", "pc"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton('🔑 [1 Day] » 1$ / 50 EGP', callback_data=f'buy_{prefix}_1d'),
            types.InlineKeyboardButton('🔑 [7 Days] » 4$ / 200 EGP', callback_data=f'buy_{prefix}_7d'),
            types.InlineKeyboardButton('🔑 [15 Days] » 8$ / 400 EGP', callback_data=f'buy_{prefix}_15d'),
            types.InlineKeyboardButton('🔑 [30 Days] » 10$ / 500 EGP', callback_data=f'buy_{prefix}_30d'),
            types.InlineKeyboardButton('🔙 Back to Categories', callback_data='shop_now')
        )
        
        text_content = (
            f"🔥 — SMOKE SHOP — 🔥\n"
            f"🎮 {section_name}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ PANEL: PHANTOM Panel\n"
            "Select your required duration below:\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🎯 Select your plan below:"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text_content, reply_markup=markup)

    # --- معالجة الشراء والتسليم المباشر ---
    elif call.data.startswith('buy_'):
        category = call.data.replace('buy_', '')
        price = PRICES.get(category, 50.0)

        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        user_balance = row[0] if row else 0.0

        if user_balance < price:
            bot.answer_callback_query(call.id, "❌ Insufficient balance!", show_alert=True)
            bot.send_message(call.message.chat.id, f"❌ Insufficient Balance!\n\nRequired: {price} EGP\nYour Balance: {user_balance} EGP\n\nPlease add balance first.")
            conn.close()
            return

        cursor.execute('SELECT id, key_code FROM keys_stock WHERE category = ? AND is_used = 0 LIMIT 1', (category,))
        key_row = cursor.fetchone()

        if not key_row:
            bot.answer_callback_query(call.id, "⚠️ Out of Stock!", show_alert=True)
            bot.send_message(call.message.chat.id, "⚠️ Out of Stock! This item is currently out of stock in our vault.")
            conn.close()
            return

        key_id, key_code = key_row[0], key_row[1]

        cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
        cursor.execute('UPDATE keys_stock SET is_used = 1 WHERE id = ?', (key_id,))
        conn.commit()
        conn.close()

        bot.answer_callback_query(call.id, "🎉 Purchase Successful!")
        delivery_text = (
            "🎉 PURCHASE SUCCESSFUL! 🎉\n\n"
            f"📦 Product: {category}\n"
            f"💰 Price Paid: {price} EGP\n\n"
            f"🔑 YOUR KEY:\n{key_code}\n\n"
            "📌 Thank you for shopping with SMOKE SHOP!"
        )
        bot.send_message(call.message.chat.id, delivery_text)

    elif call.data == 'my_orders':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔙 Back to Menu', callback_data='main_menu'))
        orders_text = (
            "🛍️ — MY ORDERS — 🛍️\n\n"
            "🛒 All your purchased keys are delivered securely in chat upon purchase!"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=orders_text, reply_markup=markup)

    elif call.data == 'profile':
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT balance, referrals, joined_date FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        balance = user[0] if user else 0.0
        refs = user[1] if user else 0
        joined = user[2] if user else "2026-01-14 09:25:11"
        conn.close()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('🔙 Back to Menu', callback_data='main_menu'))
        profile_text = (
            "👤 — YOUR PROFILE — 👤\n\n"
            f"🆔 User ID: {user_id}\n"
            f"👤 Name: {username}\n"
            f"👑 Account: Regular\n\n"
            "💰 — Balance —\n"
            f"💳 Current: {balance:.2f} EGP\n\n"
            "📊 — Statistics —\n"
            f"👥 Referrals: {refs}\n\n"
            f"📅 Joined: {joined}"
        )
        bot.send_message(call.message.chat.id, profile_text, reply_markup=markup)

    elif call.data == 'add_balance':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('💵 50 EGP', callback_data='pay_vodafone_direct'),
            types.InlineKeyboardButton('💵 100 EGP', callback_data='pay_vodafone_direct'),
            types.InlineKeyboardButton('💵 200 EGP', callback_data='pay_vodafone_direct'),
            types.InlineKeyboardButton('💵 300 EGP', callback_data='pay_vodafone_direct'),
            types.InlineKeyboardButton('💵 400 EGP', callback_data='pay_vodafone_direct'),
            types.InlineKeyboardButton('💵 500 EGP', callback_data='pay_vodafone_direct'),
            types.InlineKeyboardButton('🌐 1 $ Binance', callback_data='pay_binance_direct'),
            types.InlineKeyboardButton('🌐 2 $ Binance', callback_data='pay_binance_direct'),
            types.InlineKeyboardButton('🌐 4 $ Binance', callback_data='pay_binance_direct'),
            types.InlineKeyboardButton('🌐 6 $ Binance', callback_data='pay_binance_direct'),
            types.InlineKeyboardButton('🌐 8 $ Binance', callback_data='pay_binance_direct'),
            types.InlineKeyboardButton('🌐 10 $ Binance', callback_data='pay_binance_direct'),
            types.InlineKeyboardButton('👑 Reseller Upgrade', callback_data='reseller_up'),
            types.InlineKeyboardButton('🔙 Back to Menu', callback_data='main_menu')
        )
        balance_text = (
            "💰 — ADD BALANCE — 💰\n\n"
            "💳 Available Payment Methods:\n"
            "🇪🇬 Vodafone Cash: 01151511056\n"
            "🌐 Binance Pay ID: 1120705568\n\n"
            "Select your package amount and send your receipt below:"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=balance_text, reply_markup=markup)

    elif call.data == 'referral':
        bot.answer_callback_query(call.id)
        
        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT referrals FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        ref_count = user_row[0] if user_row else 0
        earned_amount = ref_count * 3.0
        conn.close()

        ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{user_id}"
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton('👥 My Referrals List', callback_data='ref_list'),
            types.InlineKeyboardButton('🔍 Search Referral', callback_data='ref_search'),
            types.InlineKeyboardButton('🔗 Share Product Link', callback_data='ref_share'),
            types.InlineKeyboardButton('💰 View Balance', callback_data='add_balance'),
            types.InlineKeyboardButton('🔙 Back to Menu', callback_data='main_menu')
        )
        ref_text = (
            "🎁 REFERRAL PROGRAM\n\n"
            "✅ Status: ACTIVE\n"
            "💰 Reward Rate: 3.0 EGP Per User\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 YOUR STATS:\n"
            f"┣ 👥 Total Referrals: {ref_count}\n"
            f"┣ 🎁 Signup Earned: {earned_amount:.2f} EGP\n"
            f"┗ 📊 Total Earned: {earned_amount:.2f} EGP\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔗 Your Referral Link:\n"
            f"{ref_link}\n\n"
            "📱 How it works:\n"
            "1. Share your referral link\n"
            "2. Friend joins using your link\n"
            "3. You instantly earn 3.0 EGP!"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=ref_text, reply_markup=markup)

    elif call.data == 'ref_list':
        bot.answer_callback_query(call.id)
        conn = sqlite3.connect('bot_database.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT referrals FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        ref_count = user_row[0] if user_row else 0
        conn.close()
        bot.send_message(call.message.chat.id, f"👥 My Referrals List:\n\nYou have invited {ref_count} users through your referral link.")

    elif call.data == 'ref_search':
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔍 Search Referral:\n\nSend the User ID or username of your friend.")

    elif call.data == 'ref_share':
        bot.answer_callback_query(call.id)
        ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{user_id}"
        bot.send_message(call.message.chat.id, f"🔗 Share Product / Store Link:\n\nCopy your direct referral link below:\n{ref_link}")

    elif call.data == 'lucky_spin':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton('🎰 Spin Now!', callback_data='do_spin'),
            types.InlineKeyboardButton('🔙 Back to Menu', callback_data='main_menu')
        )
        spin_text = (
            "🎰 — LUCKY SPIN — 🎰\n\n"
            "🎁 Possible Rewards:\n"
            "┣ 💰 Free Balance: 1 to 3 EGP Max\n"
            "┣ 🍀 Better Luck Tomorrow\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 You can spin once per day!\n"
            "Click the button below to try your luck!"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=spin_text, reply_markup=markup)

    elif call.data == 'do_spin':
        outcome = random.choices([0, 1, 2, 3], weights=[70, 10, 10, 10], k=1)[0]
        if outcome > 0:
            win_amount = float(outcome)
            conn = sqlite3.connect('bot_database.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (win_amount, user_id))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, f"🎉 Congratulations! You won {win_amount} EGP!", show_alert=True)
            bot.send_message(call.message.chat.id, f"🎉 Amazing Luck! You won {win_amount} EGP added directly to your balance!")
        else:
            bot.answer_callback_query(call.id, "🍀 Better luck tomorrow!", show_alert=True)
            bot.send_message(call.message.chat.id, "🍀 Better luck tomorrow! You didn't win this time, keep trying every day.")

    elif call.data == 'how_to_use':
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton('🔙 Back to Menu', callback_data='main_menu')
        )
        howto_text = (
            "📖 How to Use — Instructions\n\n"
            "Welcome to SMOKE SHOP!\n\n"
            "1. Select 'Shop Now' to view products.\n"
            "2. Choose your preferred category and duration.\n"
            "3. Ensure you have enough balance or tap 'Add Balance' to top up.\n"
            "4. Your key will be delivered instantly after purchase!"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=howto_text, reply_markup=markup)

    elif call.data == 'support':
        bot.answer_callback_query(call.id)
        support_markup = types.InlineKeyboardMarkup()
        support_markup.add(types.InlineKeyboardButton('💬 Contact Admin', url='https://t.me/Phantom_Owner1'))
        support_markup.add(types.InlineKeyboardButton('🔙 Back to Menu', callback_data='main_menu'))
        bot.send_message(call.message.chat.id, "📞 Customer Support\n\nFor any assistance or payment verification, click below to contact the store admin directly:", reply_markup=support_markup)

    elif call.data == 'main_menu':
        bot.answer_callback_query(call.id)
        welcome_text = (
            "🔥 — SMOKE SHOP — 🔥\n\n"
            "👋 Welcome, Customer!\n\n"
            "⭐ — STORE HIGHLIGHTS — ⭐\n\n"
            "🔑 Premium Game Keys\n"
            "⚡ Instant Delivery 24/7\n"
            "🔒 100% Secure Payment\n"
            "💰 Best Prices Guaranteed\n"
            "🎁 Referral Rewards\n"
            "📞 Professional Support\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 Tap Shop Now to Start!"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton('💎 Shop Now', callback_data='shop_now'))
        markup.add(types.InlineKeyboardButton('🧾 My Orders', callback_data='my_orders'), types.InlineKeyboardButton('👑 Profile', callback_data='profile'))
        markup.add(types.InlineKeyboardButton('💳 Add Balance', callback_data='add_balance'), types.InlineKeyboardButton('🤝 Referral', callback_data='referral'))
        markup.add(types.InlineKeyboardButton('🍀 Lucky Spin', callback_data='lucky_spin'))
        markup.add(types.InlineKeyboardButton('🎓 How to Use', callback_data='how_to_use'))
        markup.add(types.InlineKeyboardButton('💬 Support', callback_data='support'))
        
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=welcome_text, reply_markup=markup)

    elif call.data in ['pay_vodafone_direct', 'pay_binance_direct', 'reseller_up']:
        if 'vodafone' in call.data:
            pay_text = (
                "💳 Payment Method: Vodafone Cash\n"
                "📱 Number: 01151511056\n\n"
                "📌 Please transfer the required amount and send your receipt screenshot here for verification."
            )
        elif 'binance' in call.data:
            pay_text = (
                "🌐 Payment Method: Binance Pay\n"
                "🆔 ID: 1120705568\n\n"
                "📌 Please transfer the required amount and send your receipt screenshot here for verification."
            )
        else:
            pay_text = "👑 Reseller Upgrade\n\nContact store admin directly for upgrade options."

        bot.answer_callback_query(call.id, "Payment details loaded.")
        bot.send_message(
            call.message.chat.id, 
            pay_text
        )

@bot.message_handler(content_types=['photo'])
def handle_docs_photo(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    if user_id == ADMIN_ID:
        bot.reply_to(message, "This is a receipt image. Use the buttons under incoming requests.")
        return

    photo_file_id = message.photo[-1].file_id
    
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
    )

    try:
        bot.send_photo(
            ADMIN_ID, 
            photo_file_id, 
            caption=f"🔔 New Payment Receipt!\n\n👤 Username: @{username}\n🆔 ID: {user_id}\n📦 Target: iOS Service / PHANTOM",
            reply_markup=markup
        )
        bot.reply_to(message, "⏳ Your receipt has been received successfully. It will be reviewed and processed soon.")
    except Exception as e:
        print(f"Error sending photo to admin: {e}")

# --- تشغيل آمن ومستقر مع معالجة الأخطاء التلقائية ---
print("Bot is running perfectly on PythonAnywhere...")

while True:
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Connection error: {e}")
        time.sleep(15)

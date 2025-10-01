import telebot
from telebot import types
import json
import os
import csv
from datetime import datetime
import requests
import time

# ================== СОЗДАНИЕ БОТА ==================
try:
    bot = telebot.TeleBot('8377973620:AAEcq9MEsqyOSYrCVwo3tTbLRy7x09YHSW4')
    bot_info = bot.get_me()
    print(f"✅ Бот {bot_info.first_name} создан успешно")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    exit(1)

# ================== КОНФИГУРАЦИЯ ==================
USERS_FILE = 'users.json'
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1qsffjxK5k8RZpAViVctPW8_hGmxVxGyrFbcGiBxeh18/edit#gid=0"
SUGGESTIONS_CHANNEL = '-1003025188845'
PASSWORD = "admin123"
CREDIT_CHANNEL = '-1003025188845'

user_states = {}

# ================== ДАННЫЕ МАГАЗИНА ==================
PRODUCTS = {
    "Подарок малый": {
        "name": "🎁 Подарок в Telegram малый",
        "description": "Любой подарок в Telegram на ваш вкус\n\n• Максимальное количество: 100 ⭐",
        "price": 250,
        "category": "🎁 Подарки в Telegram"
    },
    "Подарок большой": {
        "name": "🎁 Подарок в Telegram большой",
        "description": "Любой подарок в Telegram на ваш вкус\n\n• Максимальное количество: 100 ⭐",
        "price": 320,
        "category": "🎁 Подарки в Telegram"
    },
    "Урок": {
        "name": "💬 Консультация",
        "description": "Индивидуальный урок с Никитой по любым темам, которые трудно даются\n\n• Длительность: 1,5-2 часа\n• Формат: онлайн\n• Запись: предоставляется",
        "price": 200,
        "category": "👥 Персональные"
    },
    "Подписка": {
        "name": "💎 Telegram-Премиум",
        "description": "Подарочная платная подписка, которая открывает доступ к расширенному функционалу мессенджера\n\n• Длительность: 3 месяца",
        "price": 600,
        "category": "🎁 Подарки в Telegram"
    },
    "Сертификат 500 руб": {
        "name": "🎫 Сертификат №1",
        "description": "Сертификат, который позволяет оплатить покупку на маркет-плейсах\n\n• Максимальная цена: 500 рублей\n• Озон/ Золотое яблоко/ Л'Этуаль\n• Длительность: бессрочные",
        "price": 360,
        "category": "📜 Сертификаты"
    },
    "Сертификат 1000 руб": {
        "name": "🎫 Сертификат №2",
        "description": "Сертификат, который позволяет оплатить покупку на маркет-плейсах\n\n• Максимальная цена: 1000 рублей\n• Озон/ Золотое яблоко/ Л'Этуаль\n• Длительность: бессрочные",
        "price": 550,
        "category": "📜 Сертификаты"
    },
    "Сладости": {
        "name": "🍬 Сладости",
        "description": "Вкусняшки на ваш вкус, которые заказываются курьерской доставкой (например, Самокат)\n\n• Максимальная цена: 500 рублей",
        "price": 340,
        "category": "👥 Персональные"
    },
    "Сходка": {
        "name": "🥳 Сходка",
        "description": "Если вы идете на сходку - можете воспользоваться данной услугой вместо оплаты квеста\n\n• Квест оплачивается за вас\n• В данной опции включен перекус до 500 рублей после квеста (по традиции)",
        "price": 790,
        "category": "👥 Персональные"
    },
    "Мерч": {
        "name": "🔥 Мерч нооfuck'а",
        "description": "Эклюзивный контент, разработанный командой нооfuck'а\n\n• Версия ограничена по количеству\n• Уточняйте наличие перед покупкой",
        "price": 300,
        "category": "👥 Персональные"}
}
# ================= БАЗА ДАННЫХ БАЛАНСОВ ==================
import sqlite3

BALANCE_DB = 'user_balances.db'


def init_balance_db():
    """Инициализация базы данных для балансов"""
    try:
        conn = sqlite3.connect(BALANCE_DB)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                amount INTEGER,
                type TEXT,
                description TEXT,
                product_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ База данных балансов инициализирована")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")


init_balance_db()


# ================== ФУНКЦИИ БАЗЫ ДАННЫХ ==================
def get_user_balance(user_id):
    """Получает баланс пользователя из локальной БД"""
    try:
        conn = sqlite3.connect(BALANCE_DB)
        cursor = conn.cursor()

        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (str(user_id),))
        result = cursor.fetchone()

        conn.close()

        if result:
            return result[0]
        else:
            return create_user_in_db(user_id)

    except Exception as e:
        print(f"❌ Ошибка получения баланса: {e}")
        return 0


def create_user_in_db(user_id):
    """Создает пользователя в БД с начальным балансом из Google таблицы"""
    try:
        initial_balance = calculate_balance_from_google(user_id)

        conn = sqlite3.connect(BALANCE_DB)
        cursor = conn.cursor()

        cursor.execute(
            'INSERT INTO users (user_id, balance) VALUES (?, ?)',
            (str(user_id), initial_balance)
        )

        cursor.execute(
            'INSERT INTO transactions (user_id, amount, type, description) VALUES (?, ?, ?, ?)',
            (str(user_id), initial_balance, 'initial', 'Начальный баланс из Google таблицы')
        )

        conn.commit()
        conn.close()

        print(f"✅ Создан пользователь {user_id} с балансом {initial_balance}")
        return initial_balance

    except Exception as e:
        print(f"❌ Ошибка создания пользователя в БД: {e}")
        return 0


def update_user_balance(user_id, amount, description, product_id=None):
    """Обновляет баланс пользователя в локальной БД"""
    try:
        conn = sqlite3.connect(BALANCE_DB)
        cursor = conn.cursor()

        cursor.execute('SELECT balance FROM users WHERE user_id = ?', (str(user_id),))
        result = cursor.fetchone()

        if not result:
            create_user_in_db(user_id)
            cursor.execute('SELECT balance FROM users WHERE user_id = ?', (str(user_id),))
            result = cursor.fetchone()

        current_balance = result[0]
        new_balance = current_balance + amount

        cursor.execute(
            'UPDATE users SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?',
            (new_balance, str(user_id))
        )

        transaction_type = 'purchase' if amount < 0 else 'credit' if amount > 0 else 'other'
        cursor.execute(
            'INSERT INTO transactions (user_id, amount, type, description, product_id) VALUES (?, ?, ?, ?, ?)',
            (str(user_id), amount, transaction_type, description, product_id)
        )

        conn.commit()
        conn.close()

        print(f"✅ Баланс обновлен: {user_id} {amount:+} = {new_balance} ({description})")
        return True

    except Exception as e:
        print(f"❌ Ошибка обновления баланса: {e}")
        return False


def get_user_transactions(user_id, limit=10):
    """Получает историю транзакций пользователя"""
    try:
        conn = sqlite3.connect(BALANCE_DB)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT amount, type, description, created_at 
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (str(user_id), limit))

        transactions = cursor.fetchall()
        conn.close()

        return transactions

    except Exception as e:
        print(f"❌ Ошибка получения транзакций: {e}")
        return []


# ================== ФУНКЦИИ GOOGLE ТАБЛИЦ ==================
def load_google_sheets_data():
    """Загружает и парсит данные из Google Sheets"""
    try:
        sheet_id = GOOGLE_SHEETS_URL.split('/d/')[1].split('/')[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"

        print(f"📥 Загружаем данные из: {csv_url}")
        response = requests.get(csv_url, timeout=30)

        if response.status_code == 200:
            response.encoding = 'utf-8'
            csv_data = response.text

            if '����' in csv_data or 'Ð' in csv_data:
                response.encoding = 'cp1251'
                csv_data = response.text

            lines = csv_data.strip().split('\n')
            print(f"📊 Получено строк: {len(lines)}")

            users_data = {}
            headers = []

            for i, line in enumerate(lines):
                cells = []
                current_cell = ""
                in_quotes = False

                for char in line:
                    if char == '"':
                        in_quotes = not in_quotes
                    elif char == ',' and not in_quotes:
                        cells.append(current_cell.strip())
                        current_cell = ""
                    else:
                        current_cell += char

                if current_cell:
                    cells.append(current_cell.strip())

                cells = [cell.strip('"') for cell in cells]

                if i == 0:
                    headers = cells
                    continue

                if not any(cells) or len(cells) < 4:
                    continue

                user_id = cells[1] if len(cells) > 1 else None

                if user_id and user_id.isdigit():
                    user_name = cells[2] if len(cells) > 2 else "Неизвестно"

                    credit_column_index = 3
                    if len(cells) > credit_column_index:
                        credit_value = cells[credit_column_index]
                        try:
                            credit_amount = float(credit_value) if credit_value.strip() else 0
                        except ValueError:
                            credit_amount = 0
                    else:
                        credit_amount = 0

                    scores = {}
                    total_score = 0
                    count_3_4 = 0
                    penalty_applied = 0

                    for j in range(5, len(cells)):
                        if j < len(headers) and j < len(cells):
                            column_name = headers[j] if j < len(headers) else f"Column_{j}"
                            cell_value = cells[j]

                            if cell_value and cell_value.strip():
                                try:
                                    numeric_value = int(cell_value)
                                    points = 0

                                    if numeric_value == 1:
                                        points = 10
                                    elif numeric_value == 2:
                                        points = 5
                                    elif numeric_value in [3, 4]:
                                        points = 0
                                        count_3_4 += 1
                                        if count_3_4 > 2:
                                            points = -20
                                            penalty_applied += 1
                                    elif numeric_value == 5:
                                        points = 15
                                    elif numeric_value == 6:
                                        points = 8
                                    elif numeric_value == 7:
                                        points = 20
                                    elif numeric_value == 8:
                                        points = -20
                                    elif numeric_value in [9, 10]:
                                        points = 15
                                    elif numeric_value == 11:
                                        points = 8
                                    elif numeric_value == 12:
                                        points = 30
                                    elif numeric_value == 13:
                                        points = -30
                                    elif numeric_value == 14:
                                        points = -15
                                    elif numeric_value == 15:
                                        points = -10
                                    elif numeric_value == 16:
                                        points = -15
                                    elif numeric_value in [17, 18]:
                                        points = -20
                                    elif numeric_value == 19:
                                        points = 15
                                    elif numeric_value == 20:
                                        points = -10
                                    elif numeric_value == 21:
                                        points = 25
                                    elif numeric_value == 22:
                                        points = -25
                                    elif numeric_value == 23:
                                        points = 5
                                    elif numeric_value == 24:
                                        points = 3
                                    else:
                                        points = 0

                                    scores[column_name] = {
                                        'value': numeric_value,
                                        'points': points,
                                        'description': f'Оценка {numeric_value} -> {points} баллов'
                                    }
                                    total_score += points

                                except ValueError:
                                    scores[column_name] = {
                                        'value': cell_value,
                                        'points': 0,
                                        'description': f'Текстовое значение: {cell_value}'
                                    }

                    if penalty_applied > 0:
                        scores['penalty_info'] = {
                            'value': f'Штрафы за просроченные ДД',
                            'points': -20 * penalty_applied,
                            'description': f'Штраф -20 баллов за {penalty_applied} просроченных ДД после лимита'
                        }

                    users_data[user_id] = {
                        'name': user_name,
                        'scores': scores,
                        'total_score': total_score,
                        'count_3_4': count_3_4,
                        'penalty_applied': penalty_applied,
                        'credit': credit_amount,
                        'raw_data': cells
                    }

            print(f"✅ Обработано пользователей: {len(users_data)}")
            return users_data

        else:
            print(f"❌ Ошибка загрузки: HTTP {response.status_code}")
            return {}

    except Exception as e:
        print(f"❌ Ошибка загрузки из Google Sheets: {e}")
        return {}


def get_user_history(user_id):
    """Получает историю конкретного пользователя"""
    users_data = load_google_sheets_data()
    user_id_str = str(user_id)

    if user_id_str in users_data:
        user_data = users_data[user_id_str]
        history = []

        for task_name, score_info in user_data['scores'].items():
            if task_name == 'penalty_info':
                history.append({
                    'task': 'Штраф за просроченные ДД',
                    'score': score_info['points'],
                    'date': '2024-2025',
                    'description': score_info['description']
                })
            elif isinstance(score_info, dict) and 'points' in score_info:
                history.append({
                    'task': task_name,
                    'score': score_info['points'],
                    'date': '2024-2025',
                    'description': score_info['description'],
                    'original_value': score_info['value']
                })

        history.sort(key=lambda x: x['score'], reverse=True)
        return history
    else:
        return []


def calculate_balance_from_google(user_id):
    """Рассчитывает баланс из Google таблицы"""
    try:
        users_data = load_google_sheets_data()
        user_id_str = str(user_id)

        if user_id_str in users_data:
            return users_data[user_id_str]['total_score']
        else:
            return 0
    except Exception as e:
        print(f"❌ Ошибка расчета баланса из Google: {e}")
        return 0


def get_user_credit(user_id):
    """Получает сумму кредита пользователя"""
    users_data = load_google_sheets_data()
    user_data = users_data.get(str(user_id), {})
    return user_data.get('credit', 0)


def get_total_available_balance(user_id):
    """Получает общий доступный баланс (баллы + кредит)"""
    balance = get_user_balance(user_id)
    credit = get_user_credit(user_id)
    return balance + credit


# ================== БАЗОВЫЕ ФУНКЦИИ ==================
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_users(users_dict):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения пользователей: {e}")


def send_suggestion_to_channel(user_info, suggestion_text):
    try:
        message_text = f"💡 НОВОЕ ПРЕДЛОЖЕНИЕ\n\n👤 От: {user_info['first_name']}\n🆔 ID: {user_info['user_id']}\n"
        if user_info.get('username'):
            message_text += f"📱 Username: @{user_info['username']}\n"
        message_text += f"📅 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n📝 Предложение:\n{suggestion_text}"

        bot.send_message(SUGGESTIONS_CHANNEL, message_text)
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки в канал: {e}")
        return False


# ================== ЗАГРУЗКА ДАННЫХ ==================
print("📂 Загружаем данные...")
users = load_users()
print("✅ Данные загружены")


# ================== ОСНОВНЫЕ ОБРАБОТЧИКИ ==================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    first_name = message.from_user.first_name or "Пользователь"

    if user_id not in users:
        users[user_id] = {
            'first_name': first_name,
            'username': message.from_user.username or "не указан",
            'is_new': True,
            'visit_count': 1,
            'registered_at': datetime.now().isoformat()
        }
    else:
        users[user_id]['visit_count'] += 1
        users[user_id]['is_new'] = False

    save_users(users)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "👤 Профиль", "📊 История зачислений", "💡 Предложения",
        "⭐ Отзывы", "📋 Правила", "⚡ Штрафы", "🛒 Покупки",
        "📋 Список ID", "💰 Кредит", "🎯 Викторины"  # Добавляем кнопку викторин
    ]
    for btn_text in buttons:
        markup.add(types.KeyboardButton(btn_text))

    bot.send_message(user_id, f"👋 Привет, {first_name}!\n\nВыберите раздел:", reply_markup=markup)


@bot.message_handler(content_types=['text'])
def handle_messages(message):
    user_id = str(message.from_user.id)

    # Обработка состояний (ДОЛЖНО БЫТЬ ПЕРВЫМ!)
    if user_id in user_states:
        if user_states[user_id] == 'waiting_suggestion':
            handle_suggestion(message)
            return
        elif user_states[user_id] == 'waiting_password':
            handle_password(message)
            return
        elif user_states[user_id] == 'waiting_credit_amount':
            handle_credit_amount(message)  # Обработка ввода суммы кредита
            return
        elif user_states[user_id] == 'shopping':
            handle_shop_selection(message)
            return

    # Обработка викторин
    if user_id in user_quiz_progress:
        handle_quiz_selection(message)
        return

    # Проверяем, не выбрана ли викторина
    for quiz_id, quiz_data in QUIZZES.items():
        if message.text == quiz_data["name"] or message.text == f"✅ {quiz_data['name']} (Пройдена)":
            handle_quiz_selection(message)
            return

    # ОБРАБОТКА КНОПКИ "📝 ВЗЯТЬ КРЕДИТ" (добавляем перед основными командами)
    if message.text == "📝 Взять кредит":
        show_credit_menu(message)
        return

    # Проверяем, не выбрана ли несуществующая викторина
    if "Викторина" in message.text and "№" in message.text:
        quiz_found = False
        for quiz_id, quiz_data in QUIZZES.items():
            if message.text == quiz_data["name"]:
                quiz_found = True
                break

        if not quiz_found:
            bot.send_message(user_id, "❌ Викторина пока еще не загружена")
            show_quizzes_menu(message)
            return

    if message.text in ["🚀 Начать викторину", "🔙 Прервать викторину"]:
        handle_quiz_selection(message)
        return

    # Обработка основных команд
    handlers = {
        "👤 Профиль": show_profile,
        "📊 История зачислений": show_history,
        "💡 Предложения": show_suggestions_menu,
        "⭐ Отзывы": show_reviews,
        "📋 Правила": show_rules,
        "⚡ Штрафы": show_penalties,
        "🛒 Покупки": lambda msg: enter_shop(msg),
        "📋 Список ID": show_password_prompt,
        "💰 Кредит": show_credit_menu,
        "🎯 Викторины": show_quizzes_menu,
        "🔙 Назад": start,
        "🔙 В меню": start,
        "🔙 В магазин": show_purchases,
        "🔙 Назад к викторинам": show_quizzes_menu
    }

    # Добавляем обработчики для категорий товаров
    categories = set(product["category"] for product in PRODUCTS.values())
    if message.text in categories:
        handle_shop_selection(message)
        return

    # Добавляем обработчики для названий товаров
    for product_id, product in PRODUCTS.items():
        if message.text == product["name"]:
            handle_shop_selection(message)
            return

    # Обработчик для кнопок оплаты
    if message.text.startswith("💳 Оплатить"):
        handle_shop_selection(message)
        return

    if message.text in handlers:
        handlers[message.text](message)

def save_completed_quizzes():
    """Сохраняет данные о завершенных викторинах в файл"""
    try:
        with open('completed_quizzes.json', 'w', encoding='utf-8') as f:
            # Преобразуем datetime в строку для JSON
            serializable_data = {}
            for user_id, quizzes in user_completed_quizzes.items():
                serializable_data[user_id] = {}
                for quiz_id, data in quizzes.items():
                    serializable_data[user_id][quiz_id] = {
                        'score': data['score'],
                        'total_questions': data['total_questions'],
                        'completion_time': data['completion_time'].isoformat(),
                        'answers': data['answers']
                    }
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения завершенных викторин: {e}")

def load_completed_quizzes():
    """Загружает данные о завершенных викторинах из файла"""
    try:
        if os.path.exists('completed_quizzes.json'):
            with open('completed_quizzes.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Восстанавливаем datetime из строки
                for user_id, quizzes in data.items():
                    user_completed_quizzes[user_id] = {}
                    for quiz_id, quiz_data in quizzes.items():
                        user_completed_quizzes[user_id][quiz_id] = {
                            'score': quiz_data['score'],
                            'total_questions': quiz_data['total_questions'],
                            'completion_time': datetime.fromisoformat(quiz_data['completion_time']),
                            'answers': quiz_data['answers']
                        }
            print("✅ Данные о завершенных викторинах загружены")
    except Exception as e:
        print(f"❌ Ошибка загрузки завершенных викторин: {e}")

# Загружаем данные при запуске
load_completed_quizzes()

# ================== ФУНКЦИИ ПРОФИЛЯ И ИСТОРИИ ==================
def show_profile(message):
    user_id = str(message.from_user.id)
    balance = get_user_balance(user_id)
    credit = get_user_credit(user_id)
    total_available = balance + credit
    transactions = get_user_transactions(user_id, 5)

    users_data = load_google_sheets_data()
    user_data = users_data.get(user_id, {})

    profile_text = f"👤 Ваш профиль\n\n"
    profile_text += f"🆔 ID: {user_id}\n"
    profile_text += f"👤 Имя: {message.from_user.first_name or 'Не указано'}\n"
    profile_text += f"📱 Username: @{message.from_user.username or 'не указан'}\n"
    profile_text += f"💼 Ваши средства:\n"
    profile_text += f"   💰 Доступные баллы: {balance}\n"
    profile_text += f"   🏦 Кредитные средства: {credit}\n"
    profile_text += f"   💳 Всего: {total_available} баллов\n"

    if user_data:
        count_3_4 = user_data.get('count_3_4', 0)
        penalty_applied = user_data.get('penalty_applied', 0)

        profile_text += f"⚠️ Количество просроченных ДД: {count_3_4}\n"
        if penalty_applied > 0:
            profile_text += f"🚫 Штрафов применено: {penalty_applied}\n"
        profile_text += "\n"

    if transactions:
        profile_text += "📊 Последние операции:\n"
        for amount, t_type, description, date in transactions:
            sign = "➕" if amount > 0 else "➖"
            date_str = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m')
            profile_text += f"{sign} {abs(amount)} - {description} ({date_str})\n"
    else:
        profile_text += "📊 История операций пуста\n"

    bot.send_message(user_id, profile_text)


def show_history(message):
    user_id = str(message.from_user.id)

    bot.send_message(user_id, "🔄 Загружаем историю из Google Sheets...")

    history = get_user_history(user_id)

    if history:
        history_text = f"📊 Полная история начислений\n\n"
        history_text += f"Всего записей: {len(history)}\n"
        history_text += f"Общий балл: {calculate_balance_from_google(user_id)}\n\n"

        for i, record in enumerate(history, 1):
            task = record.get('task', 'Неизвестное задание')
            score = record.get('score', 0)
            description = record.get('description', '')
            original_value = record.get('original_value', '')

            if score > 0:
                emoji = "🟢"
            elif score < 0:
                emoji = "🔴"
            else:
                emoji = "⚪"

            history_text += f"{i}. {emoji} {task}\n"
            history_text += f"   ⭐ Баллы: {score:+.0f}\n"

            if description:
                history_text += f"   📝 {description}\n"

            history_text += "\n"

    else:
        history_text = "📊 История начислений\n\n"
        history_text += "Данные не найдены.\n\n"
        history_text += f"🆔 Ваш ID: {user_id}\n"
        history_text += "💡 Используйте кнопку '📋 Список ID' чтобы увидеть доступные ID"

    if len(history_text) > 4000:
        parts = [history_text[i:i + 4000] for i in range(0, len(history_text), 4000)]
        for part in parts:
            bot.send_message(user_id, part)
            time.sleep(0.5)
    else:
        bot.send_message(user_id, history_text)


# ================== СИСТЕМА ПРЕДЛОЖЕНИЙ ==================
def show_suggestions_menu(message):
    user_id = str(message.from_user.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Назад"))
    user_states[user_id] = 'waiting_suggestion'
    bot.send_message(user_id, "💡 Напишите ваше предложение:", reply_markup=markup)


def handle_suggestion(message):
    user_id = str(message.from_user.id)
    suggestion_text = message.text

    if suggestion_text == "🔙 Назад":
        user_states[user_id] = None
        start(message)
        return

    if len(suggestion_text.strip()) < 10:
        bot.send_message(user_id, "❌ Предложение слишком короткое.")
        return

    user_info = {
        'user_id': user_id,
        'first_name': message.from_user.first_name or "Неизвестно",
        'username': message.from_user.username or "не указан"
    }

    if send_suggestion_to_channel(user_info, suggestion_text):
        bot.send_message(user_id, "✅ Спасибо! Ваше предложение отправлено.")
    else:
        bot.send_message(user_id, "❌ Ошибка отправки.")

    user_states[user_id] = None
    start(message)


# ================== СИСТЕМА КРЕДИТОВ ==================
def show_credit_menu(message):
    """Меню кредита"""
    user_id = str(message.from_user.id)

    # Если пользователь нажал "📝 Взять кредит" из меню кредита
    if message.text == "📝 Взять кредит":
        user_states[user_id] = 'waiting_credit_amount'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔙 Назад"))
        bot.send_message(user_id, "💳 Введите сумму кредита (максимум 250 баллов):", reply_markup=markup)
        return

    # Если пользователь нажал "🔙 Назад" из меню кредита
    if message.text == "🔙 Назад":
        user_states[user_id] = None
        start(message)
        return

    # Показываем меню кредита только если это первый вход
    credit_info = """💰 СИСТЕМА КРЕДИТОВ 💰

Условия кредита:
• 🏦 Максимальная сумма: 250 баллов
• 📈 Проценты: 14% каждые 504 часа (21 день)
• 💸 Платеж: 1/12 от суммы каждые 168 часов (7 дней)
• ⏱️ Полное погашение: 12 недель

Пример расчета:
Кредит 120 баллов:
• Еженедельный платеж: 10 баллов
• Проценты каждые 3 недели: 16.8 баллов

⚠️ Внимание: Кредит списывается автоматически!"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📝 Взять кредит"))
    markup.add(types.KeyboardButton("🔙 Назад"))

    bot.send_message(user_id, credit_info, reply_markup=markup)


def handle_credit_amount(message):
    """Обработка ввода суммы кредита"""
    user_id = str(message.from_user.id)

    if message.text == "🔙 Назад":
        user_states[user_id] = None
        show_credit_menu(message)
        return

    try:
        amount = int(message.text)

        if amount <= 0:
            bot.send_message(user_id, "❌ Сумма должна быть положительной!")
            return

        if amount > 250:
            bot.send_message(user_id, "❌ Максимальная сумма кредита - 250 баллов!")
            return

        # Отправляем заявку в канал
        if send_credit_application(user_id, amount, message.from_user):
            user_states[user_id] = None
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton("🔙 В меню"))
            bot.send_message(user_id,
                             f"✅ Заявка на кредит {amount} баллов отправлена администратору!\n\nОжидайте одобрения.",
                             reply_markup=markup)
        else:
            bot.send_message(user_id, "❌ Ошибка при отправке заявки. Попробуйте позже.")

    except ValueError:
        bot.send_message(user_id, "❌ Пожалуйста, введите число!")
    except Exception as e:
        bot.send_message(user_id, "❌ Ошибка при обработке заявки")
        print(f"Credit error: {e}")


def send_credit_application(user_id, amount, user):
    """Отправляет заявку на кредит в канал"""
    try:
        message_text = f"""🏦 НОВАЯ ЗАЯВКА НА КРЕДИТ 🏦

👤 Клиент: {user.first_name or 'Неизвестно'}
🆔 ID: {user_id}
📱 Username: @{user.username or 'не указан'}
💳 Сумма: {amount} баллов
📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Условия:
• Проценты: 14% каждые 504 часа
• Платежи: 1/12 суммы каждые 168 часов
• Срок: 12 недель

⚠️ Для одобрения: 
Внесите запись в колонку 'Кредиты' в таблице"""

        bot.send_message(CREDIT_CHANNEL, message_text)
        print(f"✅ Заявка на кредит отправлена в канал")
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки заявки на кредит: {e}")
        return False


# ================== СИСТЕМА МАГАЗИНА ==================
def enter_shop(message):
    user_id = str(message.from_user.id)
    user_states[user_id] = 'shopping'
    show_purchases(message)


def show_purchases(message):
    user_id = str(message.from_user.id)
    balance = get_user_balance(user_id)
    credit = get_user_credit(user_id)
    total_available = balance + credit

    shop_text = f"""🛒 МАГАЗИН БАЛЛОВ

Здесь вы можете обменять баллы на полезные товары и услуги!

💼 Ваши средства:
💰 Доступные баллы: {balance}
🏦 Кредитные средства: {credit}
💳 Всего доступно: {total_available} баллов

Выберите категорию:"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    categories = set(product["category"] for product in PRODUCTS.values())
    for category in categories:
        markup.add(types.KeyboardButton(category))

    markup.add(types.KeyboardButton("🔙 Назад"))

    bot.send_message(user_id, shop_text, reply_markup=markup)


def handle_shop_selection(message):
    user_id = str(message.from_user.id)

    if message.text == "🔙 Назад":
        user_states[user_id] = None
        start(message)
        return

    categories = set(product["category"] for product in PRODUCTS.values())
    if message.text in categories:
        show_products_in_category(message, message.text)
        return

    for product_id, product in PRODUCTS.items():
        if message.text == product["name"]:
            show_product_details(message, product_id)
            return

    if message.text.startswith("💳 Оплатить"):
        product_id = message.text.replace("💳 Оплатить ", "")
        process_payment(message, product_id)
        return

    show_purchases(message)


def show_products_in_category(message, category):
    user_id = str(message.from_user.id)

    category_products = {pid: prod for pid, prod in PRODUCTS.items() if prod["category"] == category}

    products_text = f"{category}\n\n"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)

    for product_id, product in category_products.items():
        products_text += f"{product['name']} - {product['price']} баллов\n"
        markup.add(types.KeyboardButton(product['name']))

    markup.add(types.KeyboardButton("🔙 В магазин"))

    bot.send_message(user_id, products_text, reply_markup=markup)


def show_product_details(message, product_id):
    user_id = str(message.from_user.id)
    product = PRODUCTS[product_id]
    balance = get_user_balance(user_id)
    credit = get_user_credit(user_id)
    total_available = balance + credit

    product_text = f"""🎁 {product['name']}

{product['description']}

💰 Цена: {product['price']} баллов

💼 Ваши средства:
• Доступные баллы: {balance}
• Кредитные средства: {credit}
• Всего доступно: {total_available}"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if total_available >= product['price']:
        amount_from_balance = min(balance, product['price'])
        amount_from_credit = product['price'] - amount_from_balance

        product_text += f"\n\n✅ Достаточно средств для покупки!"
        product_text += f"\n💸 Будет списано:"

        if amount_from_balance > 0:
            product_text += f"\n   • {amount_from_balance} из ваших баллов"
        if amount_from_credit > 0:
            product_text += f"\n   • {amount_from_credit} из кредитных средств"

        markup.add(types.KeyboardButton(f"💳 Оплатить {product_id}"))
    else:
        product_text += f"\n\n❌ Недостаточно средств. Не хватает: {product['price'] - total_available} баллов"

    markup.add(types.KeyboardButton("🔙 В магазин"))

    bot.send_message(user_id, product_text, reply_markup=markup)


def process_payment(message, product_id):
    user_id = str(message.from_user.id)
    product = PRODUCTS[product_id]

    total_available = get_total_available_balance(user_id)
    balance = get_user_balance(user_id)
    credit = get_user_credit(user_id)

    if total_available < product['price']:
        bot.send_message(user_id, "❌ Недостаточно средств для покупки!")
        show_purchases(message)
        return

    processing_msg = bot.send_message(user_id, "⏳ Обрабатываем платеж...")

    amount_from_balance = min(balance, product['price'])
    amount_from_credit = product['price'] - amount_from_balance

    success = True
    description_parts = []

    if amount_from_balance > 0:
        success_balance = update_user_balance(
            user_id,
            -amount_from_balance,
            f"Покупка: {product['name']} (часть из баллов)",
            product['name']
        )
        success = success and success_balance
        description_parts.append(f"{amount_from_balance} из баллов")

    if amount_from_credit > 0:
        success_credit = update_credit_in_google(user_id, -amount_from_credit, product['name'])
        success = success and success_credit
        description_parts.append(f"{amount_from_credit} из кредита")

    bot.delete_message(user_id, processing_msg.message_id)

    if success:
        new_balance = get_user_balance(user_id)
        new_credit = get_user_credit(user_id)

        payment_description = " и ".join(description_parts)

        bot.send_message(user_id,
                         f"✅ Покупка успешно совершена!\n\n"
                         f"🎁 Товар: {product['name']}\n"
                         f"💰 Списано: {product['price']} баллов\n"
                         f"💸 Списание: {payment_description}\n"
                         f"💳 Новый баланс: {new_balance} баллов\n"
                         f"🏦 Остаток кредита: {new_credit} баллов\n"
                         f"📦 Товар будет выдан в ближайшее время")

        send_purchase_notification_with_credit(
            user_id, product, message.from_user,
            amount_from_balance, amount_from_credit,
            new_balance, new_credit
        )
    else:
        bot.send_message(user_id, "❌ Ошибка при списании баллов. Попробуйте позже.")

    show_purchases(message)


def update_credit_in_google(user_id, amount, product_name):
    try:
        print(f"💰 Обновление кредита: {user_id} {amount:+} за {product_name}")
        return True
    except Exception as e:
        print(f"❌ Ошибка обновления кредита: {e}")
        return False


def send_purchase_notification_with_credit(user_id, product, user, amount_from_balance, amount_from_credit, new_balance,
                                           new_credit):
    try:
        payment_parts = []
        if amount_from_balance > 0:
            payment_parts.append(f"{amount_from_balance} из баллов")
        if amount_from_credit > 0:
            payment_parts.append(f"{amount_from_credit} из кредита")

        payment_description = " + ".join(payment_parts)

        message_text = f"""🛒 СООБЩЕНИЕ О ПОКУПКЕ

👤 Покупатель: {user.first_name or 'Неизвестно'}
🆔 ID: {user_id}
📱 Username: @{user.username or 'не указан'}

🎁 Товар: {product['name']}
💰 Стоимость: {product['price']} баллов
💸 Списание: {payment_description}

📊 Новые балансы:
• Баланс: {new_balance} баллов
• Кредит: {new_credit} баллов
• Всего: {new_balance + new_credit} баллов

📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}

✅ Баллы автоматически списаны
⚠️ Необходимо выдать товар пользователю"""

        bot.send_message(SUGGESTIONS_CHANNEL, message_text)
        return True

    except Exception as e:
        print(f"❌ Ошибка отправки уведомления о покупке: {e}")
        return False


# ================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==================
def show_password_prompt(message):
    user_id = str(message.from_user.id)
    user_states[user_id] = 'waiting_password'
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Назад"))
    bot.send_message(user_id, "🔐 Для доступа к списку ID введите пароль:", reply_markup=markup)


def handle_password(message):
    user_id = str(message.from_user.id)
    password_attempt = message.text

    if password_attempt == "🔙 Назад":
        user_states[user_id] = None
        start(message)
        return

    if password_attempt == PASSWORD:
        user_states[user_id] = None
        show_available_ids(message)
    else:
        bot.send_message(user_id, "❌ Неверный пароль. Попробуйте еще раз:")


def show_available_ids(message):
    """Показывает все ID которые есть в таблице (только после ввода пароля)"""
    user_id = str(message.from_user.id)

    bot.send_message(user_id, "🔄 Загружаем список ID из таблицы...")

    users_data = load_google_sheets_data()

    if users_data:
        ids_text = "📋 ПОЛНЫЙ СПИСОК ID В ТАБЛИЦЕ:\n\n"

        # Сортируем пользователей по ID
        sorted_users = sorted(users_data.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)

        for i, (uid, data) in enumerate(sorted_users, 1):
            name = data.get('name', 'Неизвестно')
            total = data.get('total_score', 0)
            count_3_4 = data.get('count_3_4', 0)
            penalty_applied = data.get('penalty_applied', 0)

            ids_text += f"{i}. 🆔 {uid} - {name}\n"
            ids_text += f"   💰 Всего баллов: {total}\n"
            ids_text += f"   ⚠️ Просроченных ДД: {count_3_4}\n"
            if penalty_applied > 0:
                ids_text += f"   🚫 Штрафов: {penalty_applied}\n"
            ids_text += "\n"

        ids_text += f"🔍 Всего пользователей: {len(users_data)}\n"
        ids_text += f"👤 Ваш ID: {user_id}"

    else:
        ids_text = "❌ Не удалось загрузить данные из таблицы"

    # Если текст очень длинный, разбиваем на части
    if len(ids_text) > 4000:
        parts = []
        current_part = ""
        lines = ids_text.split('\n')

        for line in lines:
            if len(current_part + line + '\n') > 4000:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'

        if current_part:
            parts.append(current_part)

        for part in parts:
            bot.send_message(user_id, part)
            time.sleep(0.5)
    else:
        bot.send_message(user_id, ids_text)

    start(message)  # Возвращаем к основному меню


def show_reviews(message):
    user_id = str(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("⭐ Оставить отзыв", url="https://t.me/noofuck_feedback")
    markup.add(btn)
    bot.send_message(user_id, "⭐ Отзывы\n\nОставьте отзыв о нашей системе:", reply_markup=markup)


def show_rules(message):
    rules_text = "📋 Правила начисления баллов\n\n 🚀  Правила начисления баллов \n\n Здесь ты узнаешь, как зарабатывать очки в нашей системе мотивации. Активничай, учись и получай за это заслуженные баллы!\n\n --- ✨ ---\n\n 📚 Учеба и дисциплина\n\n→ Прислал(а) ДЗ в дедлайн →  + 10 баллов \n\n → Сдал(а) ДЗ после дедлайна → + 5 баллов \n\n → Пробник сдан в срок → + 15 баллов \n\n → Пробник сдан после дедлайна → + 8 баллов \n\n 🏆 Достижения и активность \n\n → Успешно закрыл(а) зачёт → + 20 баллов \n\n → Пришёл(шла) на сходку → + 15 баллов \n\n → Победил(а) в викторине → + 15 баллов \n\n → Участвовал(а) в викторине → + 8 баллов \n\n 💎 Фирменные активности от Никиты \n\n → Решил(а) авторский пробник → + 30 баллов \n\n → Посетил(а) и активно участвовал(а) на доп. вебинаре → + 15 баллов \n\n 🪅 Фирменные активности от Гели \n\n → Решил(а) авторский пробник → + 30 баллов \n\n → Посетил(а) и активно участвовал(а) на доп. вебинаре → + 15 баллов \n\n → Решил(а) домашнее задание повышенного уровня верно → + 5 баллов \n\n Решил(а) домашнее задание повышенного уровня неверно → + 3 балла \n\n 🚀 Крупные победы \n\n → Успешно сдал(а) рубежную аттестацию →  + 25 баллов \n\n --- ✨ --- \n\n Участвуй, действуй и покоряй новые высоты! 💪"
    bot.send_message(message.from_user.id, rules_text)


def show_penalties(message):
    penalties_text = """⚡ Штрафы

🔴 НАРУШЕНИЯ И ШТРАФЫ 

*В этом разделе вы сможете посмотреть за что начисляются штрафные санкции в системе мотивации 🚀 нооFuck'а*

━━━━━━━━━━━━━━━━━━━━

📋 КАТЕГОРИИ ШТРАФОВ:

❌ Просроченные ДД:
   • Первые 2 просрочки → 0 баллов
   • Каждая последующая → 🔴 -20 баллов

🚫 Серьезные нарушения:
   • Несданный зачет → 🔴 -20 баллов
   • Несданный авторский пробник → 🔴 -30 баллов
   • Пропущен дедлайн от куратора → 🔴 -15 баллов
   • Перенос дедлайна ДЗ без предупреждения → 🔴 -10 баллов
   • Перенос дедлайна пробника без предупреждения → 🔴 -15 баллов
   • Нет ответа в ЛС за 24 часа → 🔴 -20 баллов
   • Перенос ДЗ более двух раз → 🔴 -20 баллов
   • Неверная кодовая фраза → 🔴 -10 баллов
   • Не сдана рубежная аттестация → 🔴 -25 баллов

━━━━━━━━━━━━━━━━━━━━

💡 ПОЛЕЗНАЯ ИНФОРМАЦИЯ:

✅ Как избежать штрафов?
   • Своевременно выполнять ДЗ
   • Следить за сроками
   • Консультироваться при трудностях

📊 Где посмотреть историю?
   • Раздел "История зачислений"
   • В вашем профиле "Профиль"""
    bot.send_message(message.from_user.id, penalties_text)


def show_purchases_old(message):
    purchases_text = "🛒 Покупки за баллы\n\n🎁 Бонусы..."
    bot.send_message(message.from_user.id, purchases_text)


# Данные викторин
QUIZZES = {
    "quiz1": {
        "name": "🧠 Викторина №1: Общая химия",
        "description": "Протестируйте уровень знаний по общей химии",
        "questions": [
    {
        "question": "Вопрос №1: Какой из изотопов водорода самый радиоактивный?",
        "options": [
            "H1",
            "протий",
            "дейтерий",
            "тритий",
            "ниобий"
        ],
        "correct_answer": 3
    },
    {
        "question": "Вопрос №2: Какое явление характеризует двойственную природу электрона?",
        "options": [
            "электромагнитный дуализм",
            "корпускулярно-волновой дуализм",
            "волновой дуализм",
            "двойственный дуализм",
            "электронно-магнитный дуализм"
        ],
        "correct_answer": 1
    },
    {
        "question": "Вопрос №3: Из указанных в ряду элементов выберите такие, которые в основном состоянии содержат одинаковое количество валентных электронов.",
        "options": [
            "S",
            "Ba",
            "Cr",
            "Cl",
            "B"
        ],
        "input_type": "text",
        "correct_answer": "34"
    },
    {
        "question": "Вопрос №4: Из указанных в ряду элементов выберите три элемента-неметалла. Расположите выбранные элементы в порядке уменьшения длины связи в соединении данных элементов с водородом.",
        "options": [
            "S",
            "Ba",
            "Cr",
            "Cl",
            "B"
        ],
        "input_type": "text",
        "correct_answer": "415"
    },
    {
        "question": "Вопрос №5: Из указанных в ряду элементов выберите два, у которых одинакова сумма высшей и низшей степеней окисления.",
        "options": [
            "Al",
            "Br",
            "S",
            "Ge",
            "K"
        ],
        "input_type": "text",
        "correct_answer": "34"
    },
    {
        "question": "Вопрос №6: Из предложенного перечня выберите условия, которые должны соблюдаться при образовании водородных связей.",
        "options": [
            "наличие атома водорода",
            "связь между атомом водорода и сильно ЭО атома внутри молекулы",
            "молекулярная кристаллическая решетка",
            "связи, образованные по ДА-механизму",
            "ионное строение"
        ],
        "input_type": "text",
        "correct_answer": "13"
    },
    {
        "question": "Вопрос №7: Где можно посмотреть конкретное значение электроотрицательности любого элемента?",
        "options": [
            "в шкале Полинга",
            "в системе Фарадея",
            "в таблице Менделеева",
            "в классификации по Блэку",
            "в шкале Малликена"
        ],
        "correct_answer": 0
    },
    {
        "question": "Вопрос №8: Из предложенного перечня выберите свойства, которые характеризуют вещества с атомной кристаллической решеткой.",
        "options": [
            "хрупкие",
            "почти растворимы в воде",
            "не проводят электрический ток",
            "высокие температуры кипения",
            "летучие"
        ],
        "input_type": "text",
        "correct_answer": "134"
    },
    {
        "question": "Вопрос №9: В каких соединениях у кислорода степень окисления -1/3?",
        "options": [
            "пероксиды",
            "соединения кислорода со фтором",
            "озониды",
            "надпероксиды",
            "супероксиды"
        ],
        "input_type": "text",
        "correct_answer": "3"
    },
    {
        "question": "Вопрос №10: Какие из этих степеней окисления хлор не проявляет?",
        "options": [
            "-2",
            "+4",
            "+5",
            "+7",
            "+2"
        ],
        "input_type": "text",
        "correct_answer": "15"
    },
    {
        "question": "Вопрос №11: При смешивании двух растворов одной той же соли с массовыми долями 18% и 12% был получен раствор массой 180 г с массовой долей 16%. Определите массу соли, которая содержалась в исходном растворе с меньшей массовой долей. Ответ укажите с точностью до десятых.",
        "input_type": "text",
        "correct_answer": "7,2"
    },
    {
        "question": "Вопрос №12: Из предложенного перечня выберите аллотропные модификации углерода.",
        "options": [
            "корунд",
            "графит",
            "фуллерен",
            "алмаз",
            "пемза"
        ],
        "input_type": "text",
        "correct_answer": "234"
    },
    {
        "question": "Вопрос №13: Из предложенного перечня выберите кислые соли.",
        "options": [
            "CsH₂PO₂",
            "Rb₂HPO₃",
            "NaH₂PO₃",
            "NaH₂PO₄",
            "NH₄HSO₃"
        ],
        "input_type": "text",
        "correct_answer": "345"
    },
    {
        "question": "Вопрос №14: Из предложенного перечня выберите кислоты средней силы.",
        "options": [
            "ортофосфорная кислота",
            "плавиковая кислота",
            "уксусная кислота",
            "сернистая кислота",
            "угольная кислота"
        ],
        "input_type": "text",
        "correct_answer": "1234"
    },
    {
        "question": "Вопрос №15: Из предложенного перечня выберите обратимые реакции.",
        "options": [
            "синтез хлороводорода",
            "дегидрирование",
            "этерификация",
            "гидратация",
            "кислотный гидролиз карбидов"
        ],
        "input_type": "text",
        "correct_answer": "234"
    }
        ]
    }
}

# Словарь для хранения прогресса викторин
user_quiz_progress = {}


def show_quizzes_menu(message):
    """Показывает меню викторин"""
    user_id = str(message.from_user.id)

    quizzes_text = """🎯 ВИКТОРИНЫ

Список актуальных викторин, при участии в которых ты можешь заработать дополнительные баллы!

📊 За каждую викторину можно получить:
• Правильный ответ: +1 балл
• Неправильный ответ: 0 баллов

Выберите викторину:"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)

    # Добавляем кнопки для каждой викторины
    for quiz_id, quiz_data in QUIZZES.items():
        # Проверяем, прошел ли пользователь уже эту викторину
        if user_id in user_completed_quizzes and quiz_id in user_completed_quizzes[user_id]:
            markup.add(types.KeyboardButton(f"✅ {quiz_data['name']} (Пройдена)"))
        else:
            markup.add(types.KeyboardButton(quiz_data["name"]))

    markup.add(types.KeyboardButton("🔙 Назад"))

    bot.send_message(user_id, quizzes_text, reply_markup=markup)


def start_quiz(message, quiz_id):
    """Начинает викторину"""
    user_id = str(message.from_user.id)

    # Проверяем, существует ли викторина
    if quiz_id not in QUIZZES:
        bot.send_message(user_id, "❌ Викторина пока еще не загружена")
        show_quizzes_menu(message)
        return

    # Проверяем, не прошел ли пользователь уже эту викторину
    if user_id in user_completed_quizzes and quiz_id in user_completed_quizzes[user_id]:
        bot.send_message(user_id, "✅ Ты уже прошел эту викторину, жди остальные!")
        show_quizzes_menu(message)
        return

    quiz = QUIZZES[quiz_id]

    # Инициализируем прогресс пользователя
    user_quiz_progress[user_id] = {
        'quiz_id': quiz_id,
        'current_question': 0,
        'score': 0,
        'answers': [],
        'start_time': datetime.now()
    }

    # Показываем описание викторины
    intro_text = f"""🎯 {quiz['name']}

{quiz['description']}

📝 Всего вопросов: {len(quiz['questions'])}
⏱️ Время прохождения: ~{len(quiz['questions']) * 2} минут

💡 Отвечайте внимательно! Удачи!"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🚀 Начать викторину"))
    markup.add(types.KeyboardButton("🔙 Назад к викторинам"))

    bot.send_message(user_id, intro_text, reply_markup=markup)


def send_question(user_id):
    """Отправляет текущий вопрос пользователю"""
    progress = user_quiz_progress.get(user_id)
    if not progress:
        return

    quiz_id = progress['quiz_id']
    quiz = QUIZZES[quiz_id]
    question_index = progress['current_question']

    if question_index >= len(quiz['questions']):
        finish_quiz(user_id)
        return

    question_data = quiz['questions'][question_index]

    # Определяем тип вопроса по наличию input_type
    if 'input_type' in question_data and question_data['input_type'] == 'text':
        question_type = 'text'
    else:
        question_type = 'choice'

    question_text = f"""❓ Вопрос {question_index + 1}/{len(quiz['questions'])}

{question_data['question']}"""

    if question_type == 'choice':
        # Вопрос с выбором ответа - показываем кнопки
        question_text += "\n\nВыберите правильный вариант:"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

        for i, option in enumerate(question_data['options']):
            button_text = f"{i + 1}. {option}"
            markup.add(types.KeyboardButton(button_text))

        bot.send_message(user_id, question_text, reply_markup=markup)

    else:
        # Текстовый вопрос - просим ввести ответ
        if 'options' in question_data:
            question_text += "\n\nВарианты для выбора:"
            options_text = "\n".join([f"{i + 1}. {option}" for i, option in enumerate(question_data['options'])])
            question_text += f"\n{options_text}"
            question_text += "\n\nВведите номера выбранных вариантов (например: 123 или 45):"
        else:
            question_text += "\n\nВведите ваш ответ:"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        bot.send_message(user_id, question_text, reply_markup=markup)


def handle_quiz_answer(message):
    """Обрабатывает ответ на вопрос викторины"""
    user_id = str(message.from_user.id)
    progress = user_quiz_progress.get(user_id)

    if not progress:
        bot.send_message(user_id, "❌ Викторина не начата или завершена")
        show_quizzes_menu(message)
        return

    quiz_id = progress['quiz_id']
    quiz = QUIZZES[quiz_id]
    question_index = progress['current_question']
    question_data = quiz['questions'][question_index]

    # Определяем тип вопроса по наличию input_type
    if 'input_type' in question_data and question_data['input_type'] == 'text':
        question_type = 'text'
    else:
        question_type = 'choice'

    if question_type == 'choice':
        # Обработка вопросов с выбором ответа
        try:
            answer_text = message.text
            if answer_text and answer_text[0].isdigit():
                user_answer = int(answer_text[0]) - 1  # Преобразуем в индекс (0-based)
            else:
                # Поиск по тексту варианта
                for i, option in enumerate(question_data['options']):
                    clean_option = option[3:] if len(option) > 3 and option[1] == ')' else option
                    if answer_text.lower() in clean_option.lower():
                        user_answer = i
                        break
                else:
                    bot.send_message(user_id, "❌ Пожалуйста, выберите вариант ответа из предложенных")
                    return

            # Проверяем корректность индекса
            if user_answer < 0 or user_answer >= len(question_data['options']):
                bot.send_message(user_id, "❌ Пожалуйста, выберите вариант ответа из предложенных")
                return

            # Для вопросов с выбором correct_answer всегда число (индекс)
            correct_answer = question_data['correct_answer']
            is_correct = (user_answer == correct_answer)
            score_change = 1 if is_correct else 0

        except (ValueError, IndexError, KeyError) as e:
            print(f"Ошибка обработки ответа: {e}")
            bot.send_message(user_id, "❌ Пожалуйста, выберите вариант ответа из предложенных")
            return

    else:
        # Обработка текстовых вопросов
        user_answer = message.text.strip()
        correct_answer = str(question_data['correct_answer'])

        # Для текстовых вопросов сравниваем строки
        is_correct = (user_answer == correct_answer)
        score_change = 1 if is_correct else 0

    # Сохраняем ответ
    progress['answers'].append({
        'question': question_data['question'],
        'user_answer': user_answer,
        'correct_answer': question_data['correct_answer'],
        'is_correct': is_correct,
        'options': question_data.get('options', []),
        'type': question_type
    })

    progress['score'] += score_change
    progress['current_question'] += 1

    # Показываем результат ответа
    if is_correct:
        result_text = "✅ Правильно! +1 балл"
    else:
        if question_type == 'choice':
            # Для вопросов с выбором показываем правильный вариант
            correct_index = question_data['correct_answer']
            if 0 <= correct_index < len(question_data['options']):
                correct_option = question_data['options'][correct_index]
                result_text = f"❌ Неправильно. Правильный ответ: {correct_option}"
            else:
                result_text = f"❌ Неправильно. Правильный ответ: {correct_index}"
        else:
            # Для текстовых вопросов показываем правильный текст
            result_text = f"❌ Неправильно. Правильный ответ: {question_data['correct_answer']}"

    bot.send_message(user_id, result_text)

    # Небольшая пауза перед следующим вопросом
    time.sleep(1)

    # Отправляем следующий вопрос или завершаем викторину
    send_question(user_id)
def finish_quiz(user_id):
    """Завершает викторину и показывает результаты"""
    progress = user_quiz_progress.get(user_id)
    if not progress:
        return

    quiz_id = progress['quiz_id']
    quiz = QUIZZES[quiz_id]
    total_questions = len(quiz['questions'])
    score = progress['score']

    # Сохраняем информацию о завершенной викторине
    if user_id not in user_completed_quizzes:
        user_completed_quizzes[user_id] = {}
    user_completed_quizzes[user_id][quiz_id] = {
        'score': score,
        'total_questions': total_questions,
        'completion_time': datetime.now(),
        'answers': progress['answers']
    }

    # Рассчитываем процент правильных ответов
    percentage = (score / total_questions) * 100

    # Формируем текст результатов
    result_text = f"""🎉 ВИКТОРИНА ЗАВЕРШЕНА!

📊 Результаты:
• Правильных ответов: {score}/{total_questions}
• Процент выполнения: {percentage:.1f}%
• Набрано баллов: {score}

"""

    # Добавляем оценку в зависимости от результата
    if percentage >= 90:
        result_text += "🏆 Отличный результат! Вы настоящий эксперт!"
    elif percentage >= 70:
        result_text += "👍 Хороший результат! Продолжайте в том же духе!"
    elif percentage >= 50:
        result_text += "👌 Неплохой результат! Есть куда расти!"
    else:
        result_text += "💪 Не расстраивайтесь! Попробуйте еще раз после подготовки!"

    # Отправляем результаты
    bot.send_message(user_id, result_text)

    # Отправляем уведомление в канал
    send_quiz_results_to_channel(user_id, progress)

    # Очищаем прогресс
    del user_quiz_progress[user_id]

    # Возвращаем в меню викторин (УПРОЩЕННАЯ ВЕРСИЯ)
    time.sleep(3)
    # Просто отправляем сообщение с меню вместо создания сложного объекта
    show_quizzes_simple(user_id)


def show_quizzes_simple(user_id):
    """Упрощенная версия показа меню викторин (без объекта message)"""
    quizzes_text = """🎯 ВИКТОРИНЫ

Список актуальных викторин, при участии в которых ты можешь заработать дополнительные баллы!

📊 За каждую викторину можно получить:
• Правильный ответ: +1 балл
• Неправильный ответ: 0 баллов

Выберите викторину:"""

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)

    # Добавляем кнопки для каждой викторины
    for quiz_id, quiz_data in QUIZZES.items():
        # Проверяем, прошел ли пользователь уже эту викторину
        if user_id in user_completed_quizzes and quiz_id in user_completed_quizzes[user_id]:
            markup.add(types.KeyboardButton(f"✅ {quiz_data['name']} (Пройдена)"))
        else:
            markup.add(types.KeyboardButton(quiz_data["name"]))

    markup.add(types.KeyboardButton("🔙 Назад"))

    bot.send_message(user_id, quizzes_text, reply_markup=markup)

def cancel_quiz(user_id):
    """Отменяет викторину"""
    if user_id in user_quiz_progress:
        del user_quiz_progress[user_id]
    bot.send_message(user_id, "❌ Викторина прервана")


def send_quiz_results_to_channel(user_id, progress):
    """Отправляет результаты викторины в канал"""
    try:
        user = bot.get_chat(user_id)
        quiz_id = progress['quiz_id']
        quiz = QUIZZES[quiz_id]

        # Формируем детали ответов
        answers_details = ""
        for i, answer in enumerate(progress['answers']):
            status = "✅" if answer['is_correct'] else "❌"

            # Определяем тип вопроса
            question_type = answer.get('type', 'choice')

            if question_type == 'choice':
                # Вопрос с выбором ответа
                try:
                    user_answer_text = answer['options'][answer['user_answer']]
                    correct_answer_text = answer['options'][answer['correct_answer']]
                except (IndexError, KeyError, TypeError):
                    # Если возникла ошибка с индексами, используем запасной вариант
                    user_answer_text = str(answer.get('user_answer', 'Нет ответа'))
                    correct_answer_text = str(answer.get('correct_answer', 'Неизвестно'))

                answers_details += f"\n{i + 1}. {answer['question']}\n"
                answers_details += f"   Ответ: {user_answer_text} {status}\n"
                if not answer['is_correct']:
                    answers_details += f"   Правильно: {correct_answer_text}\n"
            else:
                # Текстовый вопрос
                user_answer_text = str(answer.get('user_answer', 'Нет ответа'))
                correct_answer_text = str(answer.get('correct_answer', 'Неизвестно'))

                answers_details += f"\n{i + 1}. {answer['question']}\n"
                answers_details += f"   Ответ: {user_answer_text} {status}\n"
                if not answer['is_correct']:
                    answers_details += f"   Правильно: {correct_answer_text}\n"  # Исправлено здесь

            answers_details += "   " + "-" * 30 + "\n"

        message_text = f"""🎯 РЕЗУЛЬТАТ ВИКТОРИНЫ

👤 Участник: {user.first_name or 'Неизвестно'}
🆔 ID: {user_id}
📱 Username: @{user.username or 'не указан'}

📝 Викторина: {quiz['name']}
📊 Результат: {progress['score']}/{len(quiz['questions'])} баллов
⏱️ Время начала: {progress['start_time'].strftime('%d.%m.%Y %H:%M')}
⏰ Длительность: {str(datetime.now() - progress['start_time']).split('.')[0]}

📋 Ответы участника:
{answers_details}

📈 Процент выполнения: {(progress['score'] / len(quiz['questions'])) * 100:.1f}%"""

        bot.send_message(SUGGESTIONS_CHANNEL, message_text)

        # Сохраняем данные о завершенной викторине
        save_completed_quizzes()

        print(f"✅ Результаты викторины отправлены в канал")
        return True

    except Exception as e:
        print(f"❌ Ошибка отправки результатов викторины: {e}")
        import traceback
        print(f"Детали ошибки: {traceback.format_exc()}")
        return False

def handle_quiz_selection(message):
    """Обрабатывает выбор викторины"""
    user_id = str(message.from_user.id)

    if message.text == "🔙 Назад":
        user_states[user_id] = None
        start(message)
        return

    if message.text == "🔙 Назад к викторинам":
        show_quizzes_menu(message)
        return

    if message.text == "🚀 Начать викторину":
        progress = user_quiz_progress.get(user_id)
        if progress:
            send_question(user_id)
        return

    # Ищем выбранную викторину
    for quiz_id, quiz_data in QUIZZES.items():
        if message.text == quiz_data["name"] or message.text == f"✅ {quiz_data['name']} (Пройдена)":
            start_quiz(message, quiz_id)
            return

    # Проверяем, не выбрана ли несуществующая викторина
    if "Викторина" in message.text:
        bot.send_message(user_id, "❌ Викторина пока еще не загружена")
        show_quizzes_menu(message)
        return

    # Если это ответ на вопрос викторины
    if user_id in user_quiz_progress:
        handle_quiz_answer(message)
        return

    show_quizzes_menu(message)
# Словарь для хранения завершенных викторин
user_completed_quizzes = {}
# ================== ЗАПУСК БОТА ==================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 БОТ ЗАПУЩЕН")
    print("=" * 50)

    test_data = load_google_sheets_data()
    print(f"📊 Загружено пользователей: {len(test_data)}")

    # Удаляем вебхук на всякий случай
    bot.remove_webhook()
    
    print("✅ Бот запускается в режиме long-polling...")
    
    # Бесконечный цикл с перезапуском при ошибках
    while True:
        try:
            print("🔄 Запуск polling...")
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
            
        except Exception as e:
            print(f"❌ Ошибка в polling: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)


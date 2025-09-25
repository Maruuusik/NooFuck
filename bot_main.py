import telebot
from telebot import types
import json
import os
import csv
from datetime import datetime
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import re


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

user_states = {}


# ================== УЛУЧШЕННЫЙ ПАРСИНГ ТАБЛИЦЫ ==================
def load_google_sheets_data():
    """Загружает и парсит данные из Google Sheets"""
    try:
        # Преобразуем URL в CSV экспорт
        sheet_id = GOOGLE_SHEETS_URL.split('/d/')[1].split('/')[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"

        print(f"📥 Загружаем данные из: {csv_url}")
        response = requests.get(csv_url, timeout=30)

        if response.status_code == 200:
            # Читаем CSV данные
            csv_data = response.text
            lines = csv_data.strip().split('\n')

            print(f"📊 Получено строк: {len(lines)}")

            # Анализируем структуру таблицы
            users_data = {}
            headers = []

            for i, line in enumerate(lines):
                # Убираем лишние кавычки и разбиваем на ячейки
                cells = [cell.strip().strip('"') for cell in line.split(',')]

                # Первые строки - заголовки
                if i == 0:
                    print(f"📋 Заголовки: {cells[:10]}...")  # Первые 10 колонок
                    headers = cells
                    continue

                # Пропускаем пустые строки
                if not any(cells) or len(cells) < 3:
                    continue

                # Ищем ID во второй колонке (индекс 1)
                user_id = cells[1] if len(cells) > 1 else None

                if user_id and user_id.isdigit():
                    user_name = cells[2] if len(cells) > 2 else "Неизвестно"

                    print(f"👤 Найден пользователь: ID={user_id}, Name={user_name}")

                    # Собираем все баллы пользователя
                    scores = {}
                    total_score = 0

                    # Баллы начинаются с 5й колонки (индекс 4)
                    for j in range(4, len(cells)):
                        if j < len(headers) and j < len(cells):
                            column_name = headers[j] if j < len(headers) else f"Column_{j}"
                            cell_value = cells[j]

                            if cell_value and cell_value.strip():
                                try:
                                    score = float(cell_value.replace(',', '.'))
                                    scores[column_name] = score
                                    total_score += score
                                    print(f"   📊 {column_name}: {score} баллов")
                                except ValueError:
                                    # Если не число, сохраняем как текст
                                    scores[column_name] = cell_value

                    users_data[user_id] = {
                        'name': user_name,
                        'scores': scores,
                        'total_score': total_score,
                        'raw_data': cells  # Сохраняем сырые данные для отладки
                    }

            print(f"✅ Обработано пользователей: {len(users_data)}")
            return users_data

        else:
            print(f"❌ Ошибка загрузки: HTTP {response.status_code}")
            return {}

    except Exception as e:
        print(f"❌ Ошибка загрузки из Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return {}


def get_user_history(user_id):
    """Получает историю конкретного пользователя"""
    users_data = load_google_sheets_data()
    user_id_str = str(user_id)

    print(f"🔍 Поиск пользователя с ID: {user_id_str}")
    print(f"📋 Доступные ID: {list(users_data.keys())}")

    if user_id_str in users_data:
        user_data = users_data[user_id_str]
        history = []

        for task_name, score in user_data['scores'].items():
            if isinstance(score, (int, float)):
                history.append({
                    'task': task_name,
                    'score': score,
                    'date': '2024-2025',
                    'description': f'Выполнение задания "{task_name}"'
                })

        # Сортируем по убыванию баллов
        history.sort(key=lambda x: x['score'], reverse=True)

        print(f"✅ Найдено записей для {user_id_str}: {len(history)}")
        return history
    else:
        print(f"❌ Пользователь {user_id_str} не найден в таблице")
        print(f"💡 Доступные ID: {list(users_data.keys())}")
        return []


def calculate_balance(user_id):
    """Расчет общего баланса баллов"""
    history = get_user_history(user_id)
    return sum(record['score'] for record in history)


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


# ================== ОБРАБОТЧИКИ КОМАНД ==================
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
        "🔄 Обновить", "🐛 Отладка", "📋 Список ID"
    ]
    for btn_text in buttons:
        markup.add(types.KeyboardButton(btn_text))

    bot.send_message(user_id, f"👋 Привет, {first_name}!\n\nВыберите раздел:", reply_markup=markup)


@bot.message_handler(content_types=['text'])
def handle_messages(message):
    user_id = str(message.from_user.id)

    if user_id in user_states and user_states[user_id] == 'waiting_suggestion':
        handle_suggestion(message)
        return

    handlers = {
        "👤 Профиль": show_profile,
        "📊 История зачислений": show_history,
        "💡 Предложения": show_suggestions_menu,
        "⭐ Отзывы": show_reviews,
        "📋 Правила": show_rules,
        "⚡ Штрафы": show_penalties,
        "🛒 Покупки": show_purchases,
        "🔄 Обновить": lambda msg: bot.send_message(user_id, "✅ Данные обновляются автоматически"),
        "🐛 Отладка": show_debug_info,
        "📋 Список ID": show_available_ids
    }

    if message.text in handlers:
        handlers[message.text](message)


def show_profile(message):
    user_id = str(message.from_user.id)
    balance = calculate_balance(user_id)
    history = get_user_history(user_id)

    profile_text = f"👤 Ваш профиль\n\n"
    profile_text += f"🆔 ID: {user_id}\n"
    profile_text += f"👤 Имя: {message.from_user.first_name or 'Не указано'}\n"
    profile_text += f"📱 Username: @{message.from_user.username or 'не указан'}\n"
    profile_text += f"💰 Общий балл: {balance}\n"
    profile_text += f"📊 Выполнено заданий: {len(history)}\n\n"

    if history:
        profile_text += "✅ Вы найдены в системе баллов"
    else:
        profile_text += "❌ Вы не найдены в системе баллов\n"
        profile_text += "💡 Проверьте, что ваш ID совпадает с таблицей"

    bot.send_message(user_id, profile_text)


def show_history(message):
    user_id = str(message.from_user.id)

    bot.send_message(user_id, "🔄 Загружаем историю из Google Sheets...")

    history = get_user_history(user_id)

    if history:
        history_text = f"📊 История начислений\n\n"
        history_text += f"Всего заданий: {len(history)}\n"
        history_text += f"Общий балл: {calculate_balance(user_id)}\n\n"

        for i, record in enumerate(history, 1):
            task = record.get('task', 'Неизвестное задание')
            score = record.get('score', 0)

            history_text += f"{i}. 🎯 {task}\n"
            history_text += f"   ⭐ Баллы: {score}\n\n"

            # Ограничиваем вывод 10 записями
            if i >= 10:
                history_text += f"... и еще {len(history) - 10} заданий\n"
                break

    else:
        history_text = "📊 История начислений\n\n"
        history_text += "Данные не найдены.\n\n"
        history_text += f"🆔 Ваш ID: {user_id}\n"
        history_text += "💡 Используйте кнопку '📋 Список ID' чтобы увидеть доступные ID"

    bot.send_message(user_id, history_text)


def show_available_ids(message):
    """Показывает все ID которые есть в таблице"""
    user_id = str(message.from_user.id)

    bot.send_message(user_id, "🔄 Загружаем список ID из таблицы...")

    users_data = load_google_sheets_data()

    if users_data:
        ids_text = "📋 Список ID в таблице:\n\n"

        for i, (uid, data) in enumerate(users_data.items(), 1):
            name = data.get('name', 'Неизвестно')
            total = data.get('total_score', 0)
            ids_text += f"{i}. 🆔 {uid} - {name} (всего: {total} баллов)\n"

            if i >= 15:  # Ограничиваем вывод
                ids_text += f"\n... и еще {len(users_data) - 15} пользователей"
                break

        ids_text += f"\n\n🔍 Ваш ID: {user_id}"
        if user_id in users_data:
            ids_text += " ✅ НАЙДЕН В ТАБЛИЦЕ"
        else:
            ids_text += " ❌ НЕ НАЙДЕН В ТАБЛИЦЕ"

    else:
        ids_text = "❌ Не удалось загрузить данные из таблицы"

    bot.send_message(user_id, ids_text)


def show_debug_info(message):
    """Показывает отладочную информацию"""
    user_id = str(message.from_user.id)

    debug_text = "🐛 ОТЛАДОЧНАЯ ИНФОРМАЦИЯ\n\n"
    debug_text += f"🆔 Ваш ID: {user_id}\n"

    users_data = load_google_sheets_data()
    debug_text += f"📊 Пользователей в таблице: {len(users_data)}\n"

    if user_id in users_data:
        user_data = users_data[user_id]
        debug_text += f"✅ Вы найдены в таблице как: {user_data.get('name', 'Неизвестно')}\n"
        debug_text += f"📈 Всего баллов: {user_data.get('total_score', 0)}\n"
        debug_text += f"📋 Заданий: {len(user_data.get('scores', {}))}\n"

        # Показываем первые 3 задания
        scores = user_data.get('scores', {})
        if scores:
            debug_text += "\nПримеры заданий:\n"
            for i, (task, score) in enumerate(list(scores.items())[:3], 1):
                debug_text += f"{i}. {task}: {score}\n"
    else:
        debug_text += "❌ Вы НЕ найдены в таблице\n"
        debug_text += f"💡 Доступные ID: {', '.join(list(users_data.keys())[:10])}"

    bot.send_message(user_id, debug_text)


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


def show_reviews(message):
    user_id = str(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("⭐ Оставить отзыв", url="https://t.me/sovunia_1")
    markup.add(btn)
    bot.send_message(user_id, "⭐ Отзывы\n\nОставьте отзыв о нашей системе:", reply_markup=markup)


def show_rules(message):
    rules_text = "📋 Правила начисления баллов\n\n🎓 За обучение..."
    bot.send_message(message.from_user.id, rules_text)


def show_penalties(message):
    penalties_text = "⚡ Штрафы\n\n⚠️ Нарушения..."
    bot.send_message(message.from_user.id, penalties_text)


def show_purchases(message):
    purchases_text = "🛒 Покупки за баллы\n\n🎁 Бонусы..."
    bot.send_message(message.from_user.id, purchases_text)


# ================== ЗАПУСК БОТА ==================
if __name__ == '__main__':
    print("=" * 50)
    print("🚀 БОТ С УЛУЧШЕННЫМ ПОИСКОМ ID")
    print("=" * 50)

    # Тестовая загрузка данных
    print("🧪 Тестируем загрузку таблицы...")
    test_data = load_google_sheets_data()
    print(f"📊 Загружено пользователей: {len(test_data)}")
    if test_data:
        print(f"📋 Примеры ID: {list(test_data.keys())[:5]}")

    try:
        bot.polling(none_stop=True, interval=3, timeout=60)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
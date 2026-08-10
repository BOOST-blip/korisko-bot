import asyncio
import sqlite3
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ===== ТВОИ ДАННЫЕ =====
BOT_TOKEN = "8885270679:AAE8B16MlQqpTJO6LYIj8FfUHzepq9DP7Dg"
ADMIN_CHAT_ID = 7016593651
MAIN_CHANNEL = "https://t.me/korisik"
SUPPORT_CHANNEL = "https://t.me/+Tb0ApUMbBsgwYzYy"

# ===== БАЗА ДАННЫХ (ИСПРАВЛЕНО) =====
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    reg_date TEXT,
    credits INTEGER DEFAULT 0,
    boost_active TEXT DEFAULT 'Нет',
    boost_end TEXT DEFAULT 'Нет',
    invited INTEGER DEFAULT 0
)
""")
conn.commit()

# ===== БОТ =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== СОСТОЯНИЯ =====
class OrderState(StatesGroup):
    waiting_count = State()
    waiting_link = State()

class SupportState(StatesGroup):
    waiting_answer = State()

# ===== КЛАВИАТУРЫ =====
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Профиль", callback_data="profile"),
         InlineKeyboardButton(text="🛒 Сделать заказ", callback_data="order")],
        [InlineKeyboardButton(text="🚀 BOOST", callback_data="boost"),
         InlineKeyboardButton(text="💰 Заработать", callback_data="earn")],
        [InlineKeyboardButton(text="📢 Реферальная ссылка", callback_data="ref")],
        [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support"),
         InlineKeyboardButton(text="📰 Новости", callback_data="news")]
    ])

def back_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def order_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Накрутить реакции", callback_data="order_reactions")],
        [InlineKeyboardButton(text="👥 Накрутить подписчиков", callback_data="order_subs")],
        [InlineKeyboardButton(text="💬 Накрутить комментарии", callback_data="order_comments")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

# ===== СТАРТ =====
@dp.message(Command("start"))
async def start(message: types.Message):
    user = message.from_user
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, username, first_name, reg_date) VALUES (?, ?, ?, ?)",
            (user.id, user.username or "Нет", user.first_name, datetime.now().strftime("%d %B %Y"))
        )
        conn.commit()

    try:
        member = await bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user.id)
        if member.status in ["left", "kicked"]:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 Подписаться на канал", url=MAIN_CHANNEL)],
                [InlineKeyboardButton(text="✅ Проверить доступ", callback_data="check_sub")]
            ])
            await message.answer("🌸 Добро пожаловать!\n\nПодпишитесь на каналы, чтобы продолжить использование.", reply_markup=kb)
            return
    except:
        pass

    await message.answer(f"✨ Привет, {user.first_name}! ✨\n\nВыбери действие:", reply_markup=main_menu())

# ===== ПРОВЕРКА ПОДПИСКИ =====
@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub(callback: types.CallbackQuery):
    user = callback.from_user
    try:
        member = await bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user.id)
        if member.status in ["left", "kicked"]:
            await callback.answer("❌ Вы не подписаны на все каналы!", show_alert=True)
            return
    except:
        await callback.answer("❌ Ошибка проверки!", show_alert=True)
        return
    await callback.message.edit_text(f"✅ Добро пожаловать, {user.first_name}!", reply_markup=main_menu())
    await callback.answer()

# ===== ПРОФИЛЬ =====
@dp.callback_query(lambda c: c.data == "profile")
async def profile(callback: types.CallbackQuery):
    user = callback.from_user
    cursor.execute("SELECT credits, boost_active, boost_end, reg_date, invited FROM users WHERE user_id=?", (user.id,))
    data = cursor.fetchone()
    credits, boost, boost_end, reg_date, invited = data

    boost_text = "🚀 Подписка BOOST\n✅ Активна" if boost == "Да" else "🚀 Подписка BOOST\n❌ Не доступна"
    if boost == "Да" and boost_end != "Нет":
        boost_text += f"\n⏳ До {boost_end}"

    text = f"""👤 **Профиль**

🆔 ID: `{user.id}` (трёхзначное: {str(user.id)[:3]})

💎 Кредиты: {credits}

{boost_text}

📅 Дата регистрации: {reg_date}"""

    await callback.message.edit_text(text, reply_markup=back_btn(), parse_mode="Markdown")
    await callback.answer()

# ===== ЗАКАЗ =====
@dp.callback_query(lambda c: c.data == "order")
async def order(callback: types.CallbackQuery):
    await callback.message.edit_text("🛒 **Выберите тип заказа:**", reply_markup=order_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["order_reactions", "order_subs", "order_comments"])
async def order_type(callback: types.CallbackQuery, state: FSMContext):
    order_type = callback.data.replace("order_", "")
    type_names = {"reactions": "реакций", "subs": "подписчиков", "comments": "комментариев"}
    await callback.message.edit_text(f"📝 Напишите количество {type_names[order_type]} (число):")
    await state.update_data(order_type=order_type)
    await state.set_state(OrderState.waiting_count)
    await callback.answer()

@dp.message(OrderState.waiting_count)
async def get_count(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите число!")
        return
    count = int(message.text)
    if count <= 0:
        await message.answer("❌ Введите число больше 0!")
        return
    await state.update_data(count=count)
    await message.answer("🔗 Теперь скиньте ссылку на канал:")
    await state.set_state(OrderState.waiting_link)

@dp.message(OrderState.waiting_link)
async def get_link(message: types.Message, state: FSMContext):
    link = message.text
    if not link.startswith("https://t.me/"):
        await message.answer("❌ Это не ссылка на Telegram канал!")
        return
    data = await state.get_data()
    order_type = data["order_type"]
    count = data["count"]
    price = count
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ Оплатить звёздами ({price}⭐)", callback_data=f"pay_stars_{order_type}_{count}_{price}_{link}")],
        [InlineKeyboardButton(text=f"💎 Оплатить кредитами ({price}💎)", callback_data=f"pay_credits_{order_type}_{count}_{price}_{link}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await message.answer(f"💳 Выберите тип оплаты:\n\nСумма: {price}⭐ или {price}💎", reply_markup=kb)

# ===== ОПЛАТА =====
@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def payment(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    pay_type = parts[1]
    order_type = parts[2]
    count = int(parts[3])
    price = int(parts[4])
    link = "_".join(parts[5:])

    user = callback.from_user
    type_names = {"reactions": "реакций", "subs": "подписчиков", "comments": "комментариев"}

    if pay_type == "credits":
        cursor.execute("SELECT credits FROM users WHERE user_id=?", (user.id,))
        bal = cursor.fetchone()[0]
        if bal < price:
            await callback.answer("❌ Недостаточно кредитов!", show_alert=True)
            return
        cursor.execute("UPDATE users SET credits = credits - ? WHERE user_id=?", (price, user.id))
        conn.commit()
        await callback.answer("✅ Оплачено кредитами!", show_alert=True)

    admin_text = f"""🆕 **Новый заказ!**

👤 ID пользователя: `{user.id}`
📦 Тип: {type_names[order_type]}
🔢 Количество: {count}
💳 Оплата: {'⭐ Звёзды' if pay_type == 'stars' else '💎 Кредиты'}
🔗 Ссылка: {link}"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"done_{user.id}")]
    ])
    await bot.send_message(ADMIN_CHAT_ID, admin_text, parse_mode="Markdown", reply_markup=kb)
    await callback.message.edit_text("✅ Ваш заказ принят! Ожидайте выполнения.", reply_markup=back_btn())
    await callback.answer()

# ===== BOOST =====
@dp.callback_query(lambda c: c.data == "boost")
async def boost(callback: types.CallbackQuery):
    text = """🚀 **Подписка BOOST**

✅ Гарантия 365 дней
👑 VIP статус
💰 Скидка 10% на все заказы

Цена: 50⭐ / месяц
Или 30 000💎 / месяц"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Купить за 50 звёзд", callback_data="buy_boost_stars")],
        [InlineKeyboardButton(text="💎 Купить за 30 000 кредитов", callback_data="buy_boost_credits")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "buy_boost_credits")
async def buy_boost_credits(callback: types.CallbackQuery):
    user = callback.from_user
    cursor.execute("SELECT credits FROM users WHERE user_id=?", (user.id,))
    bal = cursor.fetchone()[0]
    if bal < 30000:
        await callback.answer("❌ Недостаточно кредитов!", show_alert=True)
        return
    cursor.execute("UPDATE users SET credits = credits - 30000, boost_active = 'Да', boost_end = '2027-08-10' WHERE user_id=?", (user.id,))
    conn.commit()
    await callback.message.edit_text("✅ Подписка BOOST активирована на месяц!", reply_markup=back_btn())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "buy_boost_stars")
async def buy_boost_stars(callback: types.CallbackQuery):
    await callback.answer("⭐ Оплатите 50 звёзд через Telegram Stars", show_alert=True)

# ===== ЗАРАБОТАТЬ =====
@dp.callback_query(lambda c: c.data == "earn")
async def earn(callback: types.CallbackQuery):
    tasks = [{"name": "📢 Подпишитесь на @korisik", "link": MAIN_CHANNEL, "reward": 4000}]
    text = "💰 **Заработай кредиты!**\n\nВыполни задания:\n"
    for t in tasks:
        text += f"\n📌 {t['name']} (+{t['reward']}💎)"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=tasks[0]['link']),
         InlineKeyboardButton(text="✅ Проверить", callback_data="check_task")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "check_task")
async def check_task(callback: types.CallbackQuery):
    user = callback.from_user
    try:
        member = await bot.get_chat_member(chat_id=MAIN_CHANNEL, user_id=user.id)
        if member.status in ["left", "kicked"]:
            await callback.answer("❌ Вы не подписаны!", show_alert=True)
            return
    except:
        await callback.answer("❌ Ошибка проверки!", show_alert=True)
        return
    cursor.execute("UPDATE users SET credits = credits + 4000 WHERE user_id=?", (user.id,))
    conn.commit()
    await callback.message.edit_text("✅ Вы получили 4000 кредитов за подписку!", reply_markup=back_btn())
    await callback.answer()

# ===== РЕФЕРАЛКА =====
@dp.callback_query(lambda c: c.data == "ref")
async def ref(callback: types.CallbackQuery):
    user = callback.from_user
    cursor.execute("SELECT invited FROM users WHERE user_id=?", (user.id,))
    invited = cursor.fetchone()[0]
    bot_username = (await bot.me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"
    text = f"📢 **Реферальная программа**\n\nПригласи друзей и получай 4000 кредитов за каждого!\n\n👥 Приглашено: {invited}\n\n🔗 Твоя ссылка:\n`{ref_link}`"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пригласить друга", url=f"tg://resolve?domain={bot_username}&start=ref_{user.id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ===== ПОДДЕРЖКА =====
@dp.callback_query(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    await callback.message.edit_text("🆘 **Виртуальный помощник korisko**\n\nНапишите ваш вопрос, и я передам его модераторам.", reply_markup=back_btn())
    await callback.answer()

@dp.message(F.text & ~F.text.startswith("/"))
async def support_msg(message: types.Message):
    user = message.from_user
    if message.chat.type == "private" and not message.text.startswith("/"):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Ответить", callback_data=f"ans_{user.id}")],
            [InlineKeyboardButton(text="❌ Отказаться", callback_data=f"reject_{user.id}")]
        ])
        await bot.send_message(ADMIN_CHAT_ID, f"🆕 Новый вопрос от {user.id}:\n{message.text}", reply_markup=kb)
        await message.answer("✅ Ваш вопрос отправлен модераторам!")

@dp.callback_query(lambda c: c.data.startswith("ans_"))
async def answer_question(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[1])
    await state.update_data(reply_to=user_id)
    await state.set_state(SupportState.waiting_answer)
    await callback.answer("Напишите ответ в следующем сообщении:")

@dp.message(SupportState.waiting_answer)
async def send_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data["reply_to"]
    await bot.send_message(user_id, f"📩 Вам ответил администратор:\n\n{message.text}")
    await message.answer("✅ Ответ отправлен!")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_question(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await bot.send_message(user_id, "❌ От вашего вопроса отказались.")
    await callback.answer("✅ Отказано")

# ===== НОВОСТИ =====
@dp.callback_query(lambda c: c.data == "news")
async def news(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти в канал", url=MAIN_CHANNEL)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    await callback.message.edit_text("📰 **Следите за свежими новостями бота!**", reply_markup=kb)
    await callback.answer()

# ===== НАЗАД =====
@dp.callback_query(lambda c: c.data == "back")
async def back(callback: types.CallbackQuery):
    await callback.message.edit_text("✨ **Главное меню** ✨", reply_markup=main_menu())
    await callback.answer()

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

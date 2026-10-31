import asyncio
import logging
import re
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, CHANNEL_ID, PLACE_ID
import database as db

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Инициализация бота ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- Состояния (FSM) ---
class LinkState(StatesGroup):
    waiting_for_link = State()
    confirming = State()

# --- Клавиатура главного меню ---
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Магазин", url="https://t.me/shoplexi"),
            InlineKeyboardButton(text="📢 Реклама", url="https://t.me/reklamaLexi")
        ],
        [
            InlineKeyboardButton(text="🚫 Разбан", url="https://t.me/rasbankanal"),
            InlineKeyboardButton(text="❓ Вопрос", url="https://t.me/vopros_lexi_bot")
        ],
        [
            InlineKeyboardButton(text="📦 Позинг", url="https://t.me/pozingLexi")
        ],
        [
            InlineKeyboardButton(text="‼️ ОТПРАВИТЬ ССЫЛКУ НА ВИП-СЕРВЕР ‼️", callback_data="send_link")
        ]
    ])
    return keyboard

# --- Хендлер /start ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "✨ <b>Добро пожаловать в бот канала @koralnimb!</b> ✨\n"
        "───────────────────────────\n\n"
        "🤖 <b>Что я умею:</b>\n"
        "• 🛒 <b>Магазин</b> — покупка товаров и услуг\n"
        "• 📢 <b>Реклама</b> — заказ рекламы в канале\n"
        "• 🚫 <b>Разбан</b> — восстановление доступа\n"
        "• ❓ <b>Вопрос</b> — связь с поддержкой\n"
        "• 📦 <b>Позинг</b> — заказ позингов\n\n"
        "‼️ <b>Главная фишка:</b>\n"
        "Ты можешь отправить ссылку на свой <b>VIP-сервер Tower of Hell</b>, и я сразу опубликую её в канале!\n\n"
        "───────────────────────────\n"
        "👇 <i>Выбери нужный раздел ниже:</i>"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu(),
        disable_web_page_preview=True
    )

# --- Хендлер нажатия на кнопку "Отправить ссылку" ---
@dp.callback_query(F.data == "send_link")
async def process_send_link(callback: CallbackQuery, state: FSMContext):
    # Проверка кулдауна
    cooldown = await db.get_cooldown(callback.from_user.id)
    if cooldown > 0:
        await callback.message.answer(
            f"⏳ Вы сможете отправить ссылку снова через <b>{db.format_time(cooldown)}</b>."
        )
        await callback.answer()
        return

    await state.set_state(LinkState.waiting_for_link)
    await callback.message.answer(
        "Отправь ссылку на вип-сервер.\n\n"
        "❗️ <b>Пример:</b> <code>https://www.roblox.com/share?code=...&type=Server</code>\n\n"
        "Ссылка должна быть на игру Tower of Hell."
    )
    await callback.answer()

# --- Проверка ссылки ---
async def is_valid_link(link: str) -> bool:
    # 1. Проверка формата
    pattern = r"https://www\.roblox\.com/share\?code=.*&type=Server"
    if not re.match(pattern, link):
        return False
    
    # 2. Проверка доступности и ID плейса
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(link, timeout=10) as response:
                if response.status != 200:
                    return False
                html = await response.text()
                # Ищем ID плейса в коде страницы
                if str(PLACE_ID) not in html:
                    return False
    except Exception as e:
        logger.error(f"Ошибка проверки ссылки: {e}")
        return False # Если не удалось проверить - отклоняем
    
    return True

# --- Хендлер получения ссылки ---
@dp.message(LinkState.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    link = message.text.strip()
    
    # Валидация
    if not await is_valid_link(link):
        await message.answer(
            "❌ <b>Неверная ссылка!</b>\n\n"
            "Убедись, что это ссылка на приватный сервер Tower of Hell и она не закрыта. Попробуй снова."
        )
        return

    # Сохраняем ссылку в состояние и спрашиваем подтверждение
    await state.update_data(link=link)
    await state.set_state(LinkState.confirming)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, отправить", callback_data="confirm_yes")],
        [InlineKeyboardButton(text="❌ Нет, отменить", callback_data="confirm_no")]
    ])
    
    await message.answer(
        f"Отправить эту ссылку в канал?\n\n{link}",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# --- Хендлер подтверждения ---
@dp.callback_query(LinkState.confirming, F.data.startswith("confirm_"))
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[1]
    
    if action == "no":
        await state.clear()
        await callback.message.edit_text("❌ Отправка отменена.")
        await callback.answer()
        return

    data = await state.get_data()
    link = data.get("link")
    
    # Текст для канала
    channel_text = (
        "‼️🤖ПОИСК САБОТЕРА 4/40‼️🤖\n"
        "‼️ДР НЕ ПРИНИМАЕМ‼️\n\n"
        f"{link}\n\n"
        "❕ПРАВИЛА СЕРВЕРА❕\n"
        "➤  АФК 1 раунд - бан\n"
        "➤  Снять все эффекты (тропы, дым и тд)\n"
        "➤  НЕ УСКОРЯТЬ САБОТЕР,не трогать рычаги\n"
        "➤  не заходить если уже есть карминовый нимб\n"
        "➤  Обязательно проходим 5 уровней, НЕ играть в мини игры\n"
        "➤  НЕ покупать негативные эффекты\n"
        "➤ ПОДНИМАТЬСЯ ДАЛЬШЕ ДВЕРЕЙ САБОТЕРА НЕЛЬЗЯ,сразу бан\n"
        "➤ Прячьтесь под лестницей или в магазине- БАН\n\n"
        "Удачных поисков 🤍\n\n"
        "А так же напоминание! Если вы забыли снять эффекты, завис интернет, отошли и прочие плюшки— исключительно ваша проблема!\n\n"
        "‼️‼️если ссылка не доступна значит сервер закрыт‼️‼️\n\n"
        "ТАК ЖЕ!!!! Когда видите саботер, СРАЗУ ПОКУПАЙТЕ ВСЕ НЕОБХОДИМЫЕ ВЕЩИ ( Мутаторы, катушки, шпатели и т.д), ИБО МАГАЗИН БУДЕТ СРАЗУ ЗАКРЫТ В ТЕЧЕНИИ 30 СЕКУНД ПОСЛЕ ОБНАРУЖЕНИЯ САБОТЕРА"
    )

    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=channel_text, disable_web_page_preview=True)
        await db.set_cooldown(callback.from_user.id)
        await callback.message.edit_text("✅ Ссылка успешно отправлена в канал!")
    except Exception as e:
        logger.error(f"Ошибка отправки в канал: {e}")
        await callback.message.edit_text("❌ Ошибка отправки в канал. Проверь права бота.")
    
    await state.clear()
    await callback.answer()

# --- Запуск ---
async def main():
    await db.init_db()
    logger.info("Бот запущен.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
import os
import zipfile
from datetime import datetime
from typing import Dict, List
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import FSInputFile
from PIL import Image

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

# ================== CONFIG ==================
BOT_TOKEN = "BOT_TOKEN"
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


# ================== MAJBURIY KANALLAR ==================
CHANNELS = [
    "@Code_Devs"
]


# ================== BOT ==================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)
user_states = {}
user_files = {}  # Ko'p fayllar uchun saqlash



# ================== MAJBURIY KANAL FUNKSIYALARI ==================
async def check_all_subscriptions(bot, user_id: int) -> bool:
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ("member", "administrator", "creator"):
                return False
        except TelegramBadRequest:
            return False
    return True


def subscribe_keyboard():
    buttons = []

    for channel in CHANNELS:
        buttons.append([
            InlineKeyboardButton(
                text=f"📢 {channel}",
                url=f"https://t.me/{channel[1:]}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="✅ Tekshirish",
            callback_data="check_sub"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)



# ================== YORDAMCHI FUNKSIYALAR ==================
def clean_temp():
    """Temp fayllarni tozalash"""
    for file in os.listdir(TEMP_DIR):
        try:
            file_path = os.path.join(TEMP_DIR, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                import shutil
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Temp tozalash xatosi: {e}")


def create_pdf_from_images(image_paths: List[str], output_filename: str) -> str:
    """Bir nechta rasmlardan PDF yaratish"""
    try:
        if not image_paths:
            return None

        pdf_path = os.path.join(TEMP_DIR, output_filename)

        # Bitta rasm bo'lsa
        if len(image_paths) == 1:
            img = Image.open(image_paths[0])
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(pdf_path, "PDF", resolution=100.0, quality=95)
            return pdf_path

        # Bir nechta rasm bo'lsa
        images = []
        for img_path in image_paths:
            img = Image.open(img_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)

        images[0].save(
            pdf_path,
            "PDF",
            resolution=100.0,
            save_all=True,
            append_images=images[1:],
            quality=95
        )

        return pdf_path

    except Exception as e:
        print(f"Rasmlardan PDF yaratishda xato: {e}")
        return None


def zip_files(file_paths: List[str], output_filename: str) -> str:
    """Fayllarni ZIP faylga aylantirish"""
    try:
        zip_path = os.path.join(TEMP_DIR, output_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)

        return zip_path if os.path.exists(zip_path) else None

    except Exception as e:
        print(f"ZIP yaratishda xato: {e}")
        return None


# ================== MENYULAR ==================
def main_menu():
    kb = ReplyKeyboardBuilder()

    # Asosiy tugmalar
    kb.button(text="🖼 Rasm → PDF")
    kb.button(text="📦 Fayl → ZIP")
    kb.button(text="📅 Taqvim")
    kb.button(text="⏰ Vaqt")
    kb.button(text="ℹ️ Yordam")

    kb.adjust(2, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def back_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="⬅️ Asosiy menyu")
    return kb.as_markup(resize_keyboard=True)


def collection_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Tayyorlash")
    kb.button(text="➕ Qo'shish")
    kb.button(text="❌ Bekor qilish")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


# ================== START ==================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id

    # 🔒 majburiy kanal tekshiruvi
    if not await check_all_subscriptions(bot, user_id):
        await message.answer(
            "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling 👇",
            reply_markup=subscribe_keyboard()
        )
        return

    user_states[user_id] = "main"
    user_files.pop(user_id, None)

    await message.answer(
        "👋 Assalomu alaykum!\n\n👇 Kerakli funksiyani tanlang!",
        reply_markup=main_menu()
    )


@dp.callback_query(F.data == "check_sub")
async def recheck_subscription(call: types.CallbackQuery):
    if await check_all_subscriptions(bot, call.from_user.id):
        await call.message.answer(
            "✅ Rahmat! Endi botdan foydalanishingiz mumkin.",
            reply_markup=main_menu()
        )
    else:
        await call.answer("❌ Hali barcha kanallarga obuna bo‘lmadingiz", show_alert=True)




# ================== TUGMA HANDLERLARI ==================
@dp.message(F.text == "🖼 Rasm → PDF")
async def image_to_pdf(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = "image_pdf"
    user_files[user_id] = []  # Rasmlar ro'yxati

    await message.answer(
        "🖼 *RASM → PDF KONVERTOR*\n\n"
        "PDF ga aylantirish uchun rasmlar yuboring:\n\n"
        "*Qo'llab-quvvatlanadigan formatlar:*\n"
        "• JPG/JPEG, PNG, BMP, GIF\n"
        "• Har bir rasm 20 MB dan oshmasin\n\n"
        "*Qanday ishlaydi:*\n"
        "1. Barcha rasmlarni yuboring\n"
        "2. '✅ Tayyorlash' tugmasini bosing\n"
        "3. Barcha rasmlar bitta PDF faylga aylanadi\n\n"
        "Rasm yuboring yoki tugmalardan birini tanlang:",
        reply_markup=collection_menu()
    )


@dp.message(F.text == "📦 Fayl → ZIP")
async def file_to_zip(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = "file_zip"
    user_files[user_id] = []  # Fayllar ro'yxati

    await message.answer(
        "📦 *FAYL → ZIP KONVERTOR*\n\n"
        "ZIP arxiviga aylantirish uchun fayllar yuboring:\n\n"
        "*Qo'llab-quvvatlanadigan formatlar:*\n"
        "• Har qanday format\n"
        "• Har bir fayl 20 MB dan oshmasin\n"
        "• Hammasi bo'lib 50 MB dan oshmasin\n\n"
        "Fayl yuboring yoki tugmalardan birini tanlang:",
        reply_markup=collection_menu()
    )


@dp.message(F.text == "📅 Taqvim")
async def calendar(message: types.Message):
    now = datetime.now()
    hijri_year = now.year - 622
    hijri_month = (now.month + 9) % 12 or 12

    hijri_months = [
        "Muharram", "Safar", "Rabiul-avval", "Rabiussani",
        "Jumadil-avval", "Jumadissani", "Rajab", "Sha'bon",
        "Ramazon", "Shavvol", "Zul-qa'da", "Zul-hijja"
    ]

    hijri_month_name = hijri_months[hijri_month - 1]
    week_days = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

    calendar_text = f"""
📅 *TAQVIM MA'LUMOTLARI*

🕒 *Hozirgi vaqt:* {now.strftime('%H:%M:%S')}

📆 *MILODIY TAQVIM:*
• Sana: {now.strftime('%d-%B, %Y')}
• Hafta kuni: {week_days[now.weekday()]}
• Yilning {now.strftime('%j')}-kuni
• Oy: {now.strftime('%B')}

🌙 *HIJRIY TAQVIM* (taxminiy):
• Sana: {now.day} {hijri_month_name} {hijri_year} H
• Oy: {hijri_month_name}
• Yil: {hijri_year} hijriy

📊 *STATISTIKA:*
• Hafta oxiri: {7 - now.weekday()} kun qoldi
• Oy oxiri: {30 - now.day if now.day <= 30 else 0} kun qoldi
• Yil oxiri: {365 - int(now.strftime('%j'))} kun qoldi
"""
    await message.answer(calendar_text, reply_markup=back_menu())


@dp.message(F.text == "⏰ Vaqt")
async def world_time(message: types.Message):

    import pytz
    from datetime import datetime

    time_zones = {
        "🇺🇿 Toshkent": pytz.timezone('Asia/Tashkent'),
        "🇷🇺 Moskva": pytz.timezone('Europe/Moscow'),
        "🇬🇧 London": pytz.timezone('Europe/London'),
        "🇺🇸 Nyu-York": pytz.timezone('America/New_York'),
        "🇨🇳 Pekin": pytz.timezone('Asia/Shanghai'),
        "🇯🇵 Tokio": pytz.timezone('Asia/Tokyo'),
        "🇹🇷 Istanbul": pytz.timezone('Europe/Istanbul'),
        "🇸🇦 Ar-Riyod": pytz.timezone('Asia/Riyadh'),
        "🇮🇳 Dehli": pytz.timezone('Asia/Kolkata'),
        "🇦🇺 Sidney": pytz.timezone('Australia/Sydney'),
    }

    time_text = "🕒 *DUNYO VAQTI*\n\n"

    for city, tz in time_zones.items():
        city_time = datetime.now(tz)
        time_str = city_time.strftime("%H:%M:%S")
        time_text += f"{city}: {time_str}\n"

    time_text += f"\n🌍 *UTC vaqti:* {datetime.utcnow().strftime('%H:%M:%S')}"

    await message.answer(time_text, reply_markup=back_menu())


@dp.message(F.text == "ℹ️ Yordam")
async def help_command(message: types.Message):
    help_text = """
📘 *BOT HAQIDA YORDAM*

🤖 *UNIVERSAL FILE CONVERTER BOT*

🔄 *ASOSIY FUNKSIYALAR:*

📁 **Fayl amallari:**
• Rasm → PDF - Rasmlarni PDF formatiga (ko'p rasm qabul qiladi)
• Fayl → ZIP - Fayllarni ZIP arxiviga aylantirish

📅 **Qo'shimcha:**
• Taqvim va vaqt ma'lumotlari

⚙️ **QO'LLANISH:**
1. /start - botni ishga tushirish
2. Kerakli funksiya tugmasini bosing
3. Fayl yoki rasm yuboring
4. '✅ Tayyorlash' tugmasini bosing
5. Natijani oling

⚠️ **CHEKLOVLAR:**
• Maksimal fayl hajmi: 20 MB
• Rasm formatlari: JPG, PNG, BMP, GIF
• ZIP uchun: har qanday format

📞 **QO'LLAB-QUVVATLASH:**
• Xatolar haqida xabar bering
• Taklif va mulohazalar

❤️ *RAHMAT FOYDALANGANINGIZ UCHUN!*
"""
    await message.answer(help_text, reply_markup=back_menu())


@dp.message(F.text == "⬅️ Asosiy menyu")
async def back_to_main(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = "main"

    if user_id in user_files:
        del user_files[user_id]

    await message.answer("🏠 Asosiy menyuga qaytingiz", reply_markup=main_menu())


# ================== RASM XABARLARNI QAYTA ISHLASH ==================
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if not state:
        await message.answer("Iltimos, avval funksiya tanlang 👆", reply_markup=main_menu())
        return

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        input_path = os.path.join(TEMP_DIR, f"input_{timestamp}.jpg")
        await bot.download_file(file_info.file_path, input_path)

        # Rasm → PDF
        if state == "image_pdf":
            if user_id not in user_files:
                user_files[user_id] = []

            user_files[user_id].append(input_path)

            await message.answer(
                f"✅ Rasm qo'shildi!\n"
                f"Jami rasmlar: {len(user_files[user_id])} ta\n\n"
                f"Yana rasm yuboring yoki '✅ Tayyorlash' tugmasini bosing.",
                reply_markup=collection_menu()
            )

        # Clean up
        await asyncio.sleep(1)

    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)[:200]}", reply_markup=back_menu())


# ================== DOKUMENT XABARLARNI QAYTA ISHLASH ==================
@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)
    document = message.document

    if not state:
        await message.answer("Iltimos, avval funksiya tanlang 👆", reply_markup=main_menu())
        return

    try:
        file_name = document.file_name or "unknown"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        input_path = os.path.join(TEMP_DIR, f"input_{timestamp}_{file_name}")

        file_info = await bot.get_file(document.file_id)
        await bot.download_file(file_info.file_path, input_path)

        # Fayl → ZIP
        if state == "file_zip":
            if user_id not in user_files:
                user_files[user_id] = []

            user_files[user_id].append(input_path)

            await message.answer(
                f"✅ Fayl qo'shildi: {file_name}\n"
                f"Jami fayllar: {len(user_files[user_id])} ta\n\n"
                f"Yana fayl yuboring yoki '✅ Tayyorlash' tugmasini bosing.",
                reply_markup=collection_menu()
            )

        else:
            await message.answer(f"❌ Noto'g'ri fayl formati yoki funksiya.", reply_markup=back_menu())

    except Exception as e:
        await message.answer(f"❌ Xato: {str(e)[:200]}", reply_markup=back_menu())


# ================== TUGMALAR HANDLERLARI ==================
@dp.message(F.text == "✅ Tayyorlash")
async def prepare_file(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state == "image_pdf" and user_id in user_files and user_files[user_id]:
        images = user_files[user_id]

        if len(images) == 0:
            await message.answer("❌ Hech qanday rasm yuborilmagan.", reply_markup=back_menu())
            return

        await message.answer(f"📊 {len(images)} ta rasmdan PDF yaratilmoqda...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"images_{timestamp}.pdf"

        pdf_path = create_pdf_from_images(images, output_filename)

        if pdf_path and os.path.exists(pdf_path):
            await message.answer_document(
                FSInputFile(pdf_path, filename=f"rasmlar_{len(images)}.pdf"),
                caption=f"✅ {len(images)} ta rasm PDF ga aylantirildi!",
                reply_markup=back_menu()
            )

            # Tozalash
            if user_id in user_files:
                del user_files[user_id]
            user_states[user_id] = "main"
        else:
            await message.answer("❌ PDF yaratishda xato.", reply_markup=back_menu())

    elif state == "file_zip" and user_id in user_files and user_files[user_id]:
        files = user_files[user_id]

        if len(files) == 0:
            await message.answer("❌ Hech qanday fayl yuborilmagan.", reply_markup=back_menu())
            return

        await message.answer(f"📦 {len(files)} ta fayldan ZIP arxiv yaratilmoqda...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"archive_{timestamp}.zip"

        zip_path = zip_files(files, output_filename)

        if zip_path and os.path.exists(zip_path):
            await message.answer_document(
                FSInputFile(zip_path, filename=f"fayllar_{len(files)}.zip"),
                caption=f"✅ {len(files)} ta fayl ZIP arxivga aylantirildi!",
                reply_markup=back_menu()
            )

            # Tozalash
            if user_id in user_files:
                del user_files[user_id]
            user_states[user_id] = "main"
        else:
            await message.answer("❌ ZIP arxiv yaratishda xato.", reply_markup=back_menu())

    else:
        await message.answer("❌ Hech qanday fayl yuborilmagan.", reply_markup=back_menu())


@dp.message(F.text == "➕ Qo'shish")
async def add_more_files(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if state in ["image_pdf", "file_zip"]:
        if state == "image_pdf":
            text = "Rasm yuboring:"
        else:
            text = "Fayl yuboring:"

        await message.answer(text, reply_markup=collection_menu())
    else:
        await message.answer("❌ Funksiya tanlanmagan.", reply_markup=back_menu())


@dp.message(F.text == "❌ Bekor qilish")
async def cancel_collection(message: types.Message):
    user_id = message.from_user.id

    if user_id in user_files:
        del user_files[user_id]

    user_states[user_id] = "main"
    await message.answer("❌ Jarayon bekor qilindi.", reply_markup=main_menu())


# ================== RUN ==================
async def main():
    print("=" * 60)
    print("🤖 UNIVERSAL FILE CONVERTER BOT ISHGA TUSHIRILDI")
    print("=" * 60)
    print("🔄 ASOSIY FUNKSIYALAR:")
    print("1. 🖼 Rasm → PDF (ko'p rasm)")
    print("2. 📦 Fayl → ZIP")
    print("3. 📅 Taqvim va Vaqt")
    print("=" * 60)

    clean_temp()

    try:
        await dp.start_polling(bot, skip_updates=True)
    except KeyboardInterrupt:
        print("\n🛑 Bot to'xtatildi")
        clean_temp()
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        clean_temp()


if __name__ == "__main__":
    asyncio.run(main())

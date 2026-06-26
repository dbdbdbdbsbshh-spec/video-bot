import asyncio
import os
import re
import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

# ===== ВСТАВЬТЕ СЮДА ВАШ НОВЫЙ ТОКЕН =====
BOT_TOKEN = "8985639316:AAF1QSILcpZ_Acg0xi8rjVRylrOtuh_DXmY"
# ==========================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Режим MP3 для каждого пользователя
mp3_mode: dict[int, bool] = {}

SUPPORTED_DOMAINS = [
    "youtube.com", "youtu.be", "tiktok.com",
    "instagram.com", "vk.com", "twitter.com", "x.com"
]


def is_valid_url(text: str) -> bool:
    return any(domain in text for domain in SUPPORTED_DOMAINS)


def get_ydl_opts_video(output_path: str) -> dict:
    return {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }


def get_ydl_opts_audio(output_path: str) -> dict:
    return {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я скачиваю видео и аудио.\n\n"
        "📎 Просто отправь ссылку — скачаю видео в лучшем качестве.\n"
        "🎵 Напиши /mp3 — следующая ссылка скачается как MP3.\n\n"
        "Поддерживаю: YouTube, TikTok, Instagram, VK, Twitter/X"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 Как пользоваться:\n\n"
        "1. Отправь ссылку на видео — получишь видео\n"
        "2. Напиши /mp3, потом ссылку — получишь MP3\n\n"
        "✅ Поддерживаемые сайты:\n"
        "• YouTube и YouTube Shorts\n"
        "• TikTok (без водяного знака)\n"
        "• Instagram Reels\n"
        "• VK Видео\n"
        "• Twitter / X"
    )


@dp.message(Command("mp3"))
async def cmd_mp3(message: Message):
    mp3_mode[message.from_user.id] = True
    await message.answer("🎵 Режим MP3 включён.\nОтправь ссылку — скачаю как аудио.")


@dp.message(F.text)
async def handle_link(message: Message):
    text = message.text.strip()

    if not is_valid_url(text):
        await message.answer("❗ Отправь ссылку на видео.\nПример: https://youtube.com/...")
        return

    user_id = message.from_user.id
    is_mp3 = mp3_mode.pop(user_id, False)

    if is_mp3:
        status = await message.answer("🎵 Скачиваю аудио...")
    else:
        status = await message.answer("📥 Скачиваю видео...")

    # Temp file path
    tmp_dir = "downloads"
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_base = os.path.join(tmp_dir, f"{user_id}")

    try:
        if is_mp3:
            opts = get_ydl_opts_audio(tmp_base + ".%(ext)s")
        else:
            opts = get_ydl_opts_video(tmp_base + ".%(ext)s")

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(text, download=True)
            title = info.get("title", "video")

        # Find downloaded file
        downloaded = None
        ext = "mp3" if is_mp3 else "mp4"
        for f in os.listdir(tmp_dir):
            if f.startswith(str(user_id)) and f.endswith(f".{ext}"):
                downloaded = os.path.join(tmp_dir, f)
                break

        if not downloaded or not os.path.exists(downloaded):
            await status.edit_text("❌ Не удалось скачать файл.")
            return

        file_size = os.path.getsize(downloaded)
        max_size = 50 * 1024 * 1024  # 50 MB — лимит Telegram

        if file_size > max_size:
            await status.edit_text(
                "❌ Файл слишком большой для Telegram (больше 50 MB).\n"
                "Попробуй видео покороче."
            )
            os.remove(downloaded)
            return

        await status.edit_text("📤 Отправляю...")

        input_file = FSInputFile(downloaded, filename=f"{title[:50]}.{ext}")

        if is_mp3:
            await message.answer_audio(
                audio=input_file,
                title=title[:64],
                caption=f"🎵 {title[:200]}"
            )
        else:
            await message.answer_video(
                video=input_file,
                caption=f"🎬 {title[:200]}"
            )

        await status.delete()

    except yt_dlp.utils.DownloadError as e:
        err = str(e)
        if "Private" in err or "private" in err:
            await status.edit_text("❌ Видео приватное — не могу скачать.")
        elif "age" in err.lower():
            await status.edit_text("❌ Видео с возрастным ограничением.")
        else:
            await status.edit_text(f"❌ Ошибка скачивания.\nПроверь ссылку и попробуй снова.")
    except Exception as e:
        await status.edit_text("❌ Что-то пошло не так. Попробуй ещё раз.")
    finally:
        # Cleanup
        for f in os.listdir(tmp_dir):
            if f.startswith(str(user_id)):
                try:
                    os.remove(os.path.join(tmp_dir, f))
                except Exception:
                    pass


async def main():
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

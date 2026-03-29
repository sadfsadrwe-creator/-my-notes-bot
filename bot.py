import json
import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(level=logging.WARNING)

NOTES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.json")
MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

WAITING_TEXT = 1
WAITING_DELETE_NUM = 2

SECTIONS = {
    "text": "📝 Текст",
    "photo": "🖼 Фото",
    "video": "🎬 Видео",
    "voice": "🎤 Голосовые",
    "video_note": "⭕ Кружки",
    "audio": "🎵 Аудио",
    "document": "📄 Файлы",
    "sticker": "😀 Стикеры",
    "animation": "🎞 Гифки",
}


def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_notes(data):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_notes(uid):
    return load_notes().get(str(uid), [])


def save_user(uid, notes):
    d = load_notes()
    d[str(uid)] = notes
    save_notes(d)


def menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📝 Текст"), KeyboardButton("🖼 Фото")],
            [KeyboardButton("🎬 Видео"), KeyboardButton("🎤 Голосовые")],
            [KeyboardButton("⭕ Кружки"), KeyboardButton("📄 Файлы")],
            [KeyboardButton("🎵 Аудио"), KeyboardButton("😀 Стикеры")],
            [KeyboardButton("📋 Все"), KeyboardButton("🗑 Удалить")],
            [KeyboardButton("💾 Экспорт"), KeyboardButton("ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


async def start(update: Update, ctx):
    await update.message.reply_text(
        "📦 ХРАНИЛИЩЕ\n\n"
        "Кидай сюда что угодно — я сам рассортирую:\n"
        "⭕ Кружки → Кружки\n"
        "🎤 Голосовые → Голосовые\n"
        "🖼 Фото → Фото\n"
        "🎬 Видео → Видео\n"
        "📄 Файлы → Файлы\n\n"
        "Нажми кнопку чтобы посмотреть раздел:",
        reply_markup=menu(),
    )
    return ConversationHandler.END


async def help_cmd(update: Update, ctx):
    await update.message.reply_text(
        "📖 ПОМОЩЬ\n\n"
        "Просто кидай:\n"
        "- текст, фото, видео\n"
        "- голосовые, кружки\n"
        "- файлы, стикеры, гифки, музыку\n\n"
        "Кнопки:\n"
        "Любая из кнопок выше — показать раздел\n"
        "📋 Все — полный список\n"
        "🗑 Удалить — удалить по номеру\n"
        "💾 Экспорт — скачать текстом",
        reply_markup=menu(),
    )
    return ConversationHandler.END


async def _save(update, ctx, note_type, file_id=None, file_ext="", text=""):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    num = len(notes) + 1
    note = {
        "id": num,
        "type": note_type,
        "text": text,
        "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    if file_id:
        tg_file = await (await ctx.bot.get_file(file_id)).download_to_drive(
            custom_path=os.path.join(MEDIA_DIR, f"{uid}_{num}{file_ext}")
        )
        note["file_path"] = str(tg_file)
        note["file_id"] = file_id
    notes.append(note)
    save_user(uid, notes)
    label = SECTIONS.get(note_type, note_type)
    await update.message.reply_text(f"✅ {label} #{num} сохранён", reply_markup=menu())


async def save_text_start(update, ctx):
    await update.message.reply_text("✏️ Введи текст:")
    return WAITING_TEXT


async def save_text(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    notes.append(
        {
            "id": len(notes) + 1,
            "type": "text",
            "text": update.message.text,
            "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
    )
    save_user(uid, notes)
    await update.message.reply_text(
        f"✅ Текст #{len(notes)} сохранён", reply_markup=menu()
    )
    return ConversationHandler.END


async def save_photo(update, ctx):
    p = update.message.photo[-1]
    await _save(update, ctx, "photo", p.file_id, ".jpg", update.message.caption or "")


async def save_video(update, ctx):
    v = update.message.video
    ext = os.path.splitext(v.file_name or ".mp4")[1]
    await _save(update, ctx, "video", v.file_id, ext, update.message.caption or "")


async def save_voice(update, ctx):
    await _save(update, ctx, "voice", update.message.voice.file_id, ".ogg")


async def save_krug(update, ctx):
    await _save(update, ctx, "video_note", update.message.video_note.file_id, ".mp4")


async def save_audio(update, ctx):
    a = update.message.audio
    ext = os.path.splitext(a.file_name or ".mp3")[1]
    await _save(
        update, ctx, "audio", a.file_id, ext, update.message.caption or a.title or ""
    )


async def save_doc(update, ctx):
    d = update.message.document
    fname = d.file_name or "file"
    ext = os.path.splitext(fname)[1]
    await _save(
        update, ctx, "document", d.file_id, f"_{fname}", update.message.caption or fname
    )


async def save_sticker(update, ctx):
    await _save(update, ctx, "sticker", update.message.sticker.file_id, ".webp")


async def save_gif(update, ctx):
    await _save(update, ctx, "animation", update.message.animation.file_id, ".mp4")


async def show_section(update, ctx, note_type):
    uid = str(update.effective_user.id)
    filtered = [n for n in get_notes(uid) if n["type"] == note_type]
    label = SECTIONS.get(note_type, note_type)
    if not filtered:
        await update.message.reply_text(f"📭 {label} — пусто", reply_markup=menu())
        return
    lines = [f"#{n['id']} | {n['created']} | {n['text'][:30]}" for n in filtered]
    await update.message.reply_text(
        f"{label} ({len(filtered)}):\n\n" + "\n".join(lines), reply_markup=menu()
    )


async def show_all(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    if not notes:
        await update.message.reply_text("📭 Пусто", reply_markup=menu())
        return
    sections = {}
    for n in notes:
        t = n["type"]
        sections.setdefault(t, []).append(n)
    parts = []
    for t, items in sections.items():
        label = SECTIONS.get(t, t)
        lines = [f"  #{n['id']} | {n['text'][:30]}" for n in items]
        parts.append(f"{label} ({len(items)}):\n" + "\n".join(lines))
    msg = "\n\n".join(parts)
    if len(msg) > 4000:
        for i in range(0, len(msg), 4000):
            await update.message.reply_text(msg[i : i + 4000], reply_markup=menu())
    else:
        await update.message.reply_text(msg, reply_markup=menu())


async def delete_start(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    if not notes:
        await update.message.reply_text("📭 Удалять нечего", reply_markup=menu())
        return ConversationHandler.END
    lines = [
        f"#{n['id']} {SECTIONS.get(n['type'], '')} {n['text'][:20]}" for n in notes
    ]
    await update.message.reply_text("Введи номер:\n\n" + "\n".join(lines))
    return WAITING_DELETE_NUM


async def delete_note(update, ctx):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Введи номер:", reply_markup=menu())
        return WAITING_DELETE_NUM
    nid = int(text)
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    target = next((n for n in notes if n["id"] == nid), None)
    if not target:
        await update.message.reply_text(f"❌ #{nid} не найден", reply_markup=menu())
        return ConversationHandler.END
    if "file_path" in target and os.path.exists(target["file_path"]):
        os.remove(target["file_path"])
    new_notes = [n for n in notes if n["id"] != nid]
    save_user(uid, new_notes)
    await update.message.reply_text(f"🗑 #{nid} удалён", reply_markup=menu())
    return ConversationHandler.END


async def export_notes(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    if not notes:
        await update.message.reply_text("📭 Нечего экспортировать", reply_markup=menu())
        return
    sections = {}
    for n in notes:
        sections.setdefault(n["type"], []).append(n)
    lines = ["=== ЭКСПОРТ ЗАМЕТОК ===\n"]
    for t, items in sections.items():
        label = SECTIONS.get(t, t)
        lines.append(f"\n--- {label} ---")
        for n in items:
            lines.append(f"#{n['id']} {n['created']}")
            if n["text"]:
                lines.append(f"  {n['text']}")
    path = os.path.join(MEDIA_DIR, f"export_{uid}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    await update.message.reply_document(
        document=open(path, "rb"),
        filename="notes.txt",
        caption=f"💾 {len(notes)} заметок",
    )


async def button_handler(update, ctx):
    t = update.message.text
    mapping = {
        "📝 Текст": "text",
        "🖼 Фото": "photo",
        "🎬 Видео": "video",
        "🎤 Голосовые": "voice",
        "⭕ Кружки": "video_note",
        "📄 Файлы": "document",
        "🎵 Аудио": "audio",
        "😀 Стикеры": "sticker",
    }
    if t in mapping:
        return await show_section(update, ctx, mapping[t])
    if t == "📋 Все":
        return await show_all(update, ctx)
    if t == "🗑 Удалить":
        return await delete_start(update, ctx)
    if t == "💾 Экспорт":
        return await export_notes(update, ctx)
    if t == "ℹ️ Помощь":
        return await help_cmd(update, ctx)
    if t == "📝 Сохранить текст":
        return await save_text_start(update, ctx)


def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    app = Application.builder().token(TOKEN).build()

    text_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Текст$"), save_text_start)],
        states={
            WAITING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_text)]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    del_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗑 Удалить$"), delete_start)],
        states={
            WAITING_DELETE_NUM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_note)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(text_conv)
    app.add_handler(del_conv)
    app.add_handler(MessageHandler(filters.PHOTO, save_photo))
    app.add_handler(MessageHandler(filters.VIDEO, save_video))
    app.add_handler(MessageHandler(filters.VOICE, save_voice))
    app.add_handler(MessageHandler(filters.VIDEO_NOTE, save_krug))
    app.add_handler(MessageHandler(filters.AUDIO, save_audio))
    app.add_handler(MessageHandler(filters.Document.ALL, save_doc))
    app.add_handler(MessageHandler(filters.Sticker.ALL, save_sticker))
    app.add_handler(MessageHandler(filters.ANIMATION, save_gif))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))

    print("Bot started!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

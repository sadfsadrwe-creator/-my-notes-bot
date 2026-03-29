import json
import os
import logging
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(level=logging.WARNING)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NOTES_FILE = os.path.join(BASE_DIR, "notes.json")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

WAITING_TEXT = 1
WAITING_VIEW_NUM = 2
WAITING_DELETE_NUM = 3
WAITING_CLEAR_TYPE = 4

TYPES = {
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

TYPE_BUTTONS = {v: k for k, v in TYPES.items()}


def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_notes(data):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def get_notes(uid):
    return load_notes().get(str(uid), [])


def save_user(uid, notes):
    d = load_notes()
    d[str(uid)] = notes
    save_notes(d)


def menu():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("📋 Все"), KeyboardButton("📊 По категориям")],
            [KeyboardButton("👀 Посмотреть"), KeyboardButton("🗑 Удалить")],
            [KeyboardButton("🧹 Очистить"), KeyboardButton("💾 Экспорт")],
            [KeyboardButton("ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


TYPE_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🧹 Текст"), KeyboardButton("🧹 Фото")],
        [KeyboardButton("🧹 Видео"), KeyboardButton("🧹 Голосовые")],
        [KeyboardButton("🧹 Кружки"), KeyboardButton("🧹 Файлы")],
        [KeyboardButton("🧹 Аудио"), KeyboardButton("🧹 Стикеры")],
        [KeyboardButton("🧹 Всё сразу"), KeyboardButton("◀️ Назад")],
    ],
    resize_keyboard=True,
)


async def start(update: Update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    counts = {}
    for n in notes:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    stat = " | ".join(f"{TYPES.get(t, t)}: {c}" for t, c in counts.items()) or "пусто"
    await update.message.reply_text(
        f"📦 ХРАНИЛИЩЕ [{len(notes)}]\n{stat}\n\nКидай что угодно или жми кнопки:",
        reply_markup=menu(),
    )
    return ConversationHandler.END


async def help_cmd(update: Update, ctx):
    await update.message.reply_text(
        "Кидай фото, видео, кружки, голосовые, файлы — я рассортирую.\n\n"
        "👀 Посмотреть — введи номер и я пришлю файл\n"
        "🗑 Удалить — удали по номеру\n"
        "🧹 Очистить — удалить по категориям\n"
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
        note["file_id"] = file_id
    notes.append(note)
    save_user(uid, notes)
    label = TYPES.get(note_type, note_type)
    await update.message.reply_text(f"✅ {label} #{num}", reply_markup=menu())


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
    await update.message.reply_text(f"✅ Текст #{len(notes)}", reply_markup=menu())
    return ConversationHandler.END


async def save_photo(update, ctx):
    await _save(
        update,
        ctx,
        "photo",
        update.message.photo[-1].file_id,
        ".jpg",
        update.message.caption or "",
    )


async def save_video(update, ctx):
    v = update.message.video
    await _save(
        update,
        ctx,
        "video",
        v.file_id,
        os.path.splitext(v.file_name or ".mp4")[1],
        update.message.caption or "",
    )


async def save_voice(update, ctx):
    await _save(update, ctx, "voice", update.message.voice.file_id, ".ogg")


async def save_krug(update, ctx):
    await _save(update, ctx, "video_note", update.message.video_note.file_id, ".mp4")


async def save_audio(update, ctx):
    a = update.message.audio
    await _save(
        update,
        ctx,
        "audio",
        a.file_id,
        os.path.splitext(a.file_name or ".mp3")[1],
        update.message.caption or a.title or "",
    )


async def save_doc(update, ctx):
    d = update.message.document
    fname = d.file_name or "file"
    await _save(
        update, ctx, "document", d.file_id, f"_{fname}", update.message.caption or fname
    )


async def save_sticker(update, ctx):
    await _save(update, ctx, "sticker", update.message.sticker.file_id, ".webp")


async def save_gif(update, ctx):
    await _save(update, ctx, "animation", update.message.animation.file_id, ".mp4")


async def show_all(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    if not notes:
        await update.message.reply_text("📭 Пусто", reply_markup=menu())
        return
    sections = {}
    for n in notes:
        sections.setdefault(n["type"], []).append(n)
    parts = []
    for t, items in sections.items():
        label = TYPES.get(t, t)
        lines = [f"  #{n['id']} | {n['text'][:25]}" for n in items]
        parts.append(f"{label} ({len(items)}):\n" + "\n".join(lines))
    msg = "\n\n".join(parts)
    if len(msg) > 4000:
        for i in range(0, len(msg), 4000):
            await update.message.reply_text(msg[i : i + 4000], reply_markup=menu())
    else:
        await update.message.reply_text(msg, reply_markup=menu())


async def show_categories(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    if not notes:
        await update.message.reply_text("📭 Пусто", reply_markup=menu())
        return
    counts = {}
    for n in notes:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    lines = [f"{TYPES.get(t, t)}: {c}" for t, c in counts.items()]
    await update.message.reply_text(
        f"📊 Всего: {len(notes)}\n\n" + "\n".join(lines), reply_markup=menu()
    )


async def view_start(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    if not notes:
        await update.message.reply_text("📭 Нечего смотреть", reply_markup=menu())
        return ConversationHandler.END
    lines = [f"#{n['id']} {TYPES.get(n['type'], '')} {n['text'][:20]}" for n in notes]
    await update.message.reply_text("Введи номер:\n\n" + "\n".join(lines))
    return WAITING_VIEW_NUM


async def view_note(update, ctx):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Введи число:", reply_markup=menu())
        return WAITING_VIEW_NUM
    nid = int(text)
    uid = str(update.effective_user.id)
    note = next((n for n in get_notes(uid) if n["id"] == nid), None)
    if not note:
        await update.message.reply_text(f"❌ #{nid} не найден", reply_markup=menu())
        return ConversationHandler.END

    file_id = note.get("file_id")
    note_type = note["type"]
    caption = note["text"] if note["text"] else None

    try:
        if note_type == "photo" and file_id:
            await update.message.reply_photo(photo=file_id, caption=caption)
        elif note_type == "video" and file_id:
            await update.message.reply_video(video=file_id, caption=caption)
        elif note_type == "voice" and file_id:
            await update.message.reply_voice(voice=file_id)
        elif note_type == "video_note" and file_id:
            await update.message.reply_video_note(video_note=file_id)
        elif note_type == "audio" and file_id:
            await update.message.reply_audio(audio=file_id, caption=caption)
        elif note_type == "document" and file_id:
            await update.message.reply_document(document=file_id, caption=caption)
        elif note_type == "sticker" and file_id:
            await update.message.reply_sticker(sticker=file_id)
        elif note_type == "animation" and file_id:
            await update.message.reply_animation(animation=file_id)
        elif note_type == "text":
            await update.message.reply_text(f"📝 #{nid}:\n\n{note['text']}")
        else:
            await update.message.reply_text(f"❌ Файл не найден")
    except Exception:
        await update.message.reply_text(
            f"❌ Не удалось отправить #{nid}", reply_markup=menu()
        )

    await update.message.reply_text("Готово", reply_markup=menu())
    return ConversationHandler.END


async def delete_start(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    if not notes:
        await update.message.reply_text("📭 Удалять нечего", reply_markup=menu())
        return ConversationHandler.END
    lines = [f"#{n['id']} {TYPES.get(n['type'], '')} {n['text'][:20]}" for n in notes]
    await update.message.reply_text("Введи номер:\n\n" + "\n".join(lines))
    return WAITING_DELETE_NUM


async def delete_note(update, ctx):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Введи число:", reply_markup=menu())
        return WAITING_DELETE_NUM
    nid = int(text)
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    target = next((n for n in notes if n["id"] == nid), None)
    if not target:
        await update.message.reply_text(f"❌ #{nid} не найден", reply_markup=menu())
        return ConversationHandler.END
    save_user(uid, [n for n in notes if n["id"] != nid])
    await update.message.reply_text(f"🗑 #{nid} удалён", reply_markup=menu())
    return ConversationHandler.END


async def clear_start(update, ctx):
    await update.message.reply_text("Что очистить?", reply_markup=TYPE_MENU)
    return WAITING_CLEAR_TYPE


async def clear_type(update, ctx):
    text = update.message.text.strip()
    uid = str(update.effective_user.id)

    if text == "◀️ Назад":
        await update.message.reply_text("Ок", reply_markup=menu())
        return ConversationHandler.END

    if text == "🧹 Всё сразу":
        notes = get_notes(uid)
        if not notes:
            await update.message.reply_text("📭 И так пусто", reply_markup=menu())
            return ConversationHandler.END
        save_user(uid, [])
        await update.message.reply_text(
            f"🧹 Всё удалено ({len(notes)})", reply_markup=menu()
        )
        return ConversationHandler.END

    clear_map = {
        "🧹 Текст": "text",
        "🧹 Фото": "photo",
        "🧹 Видео": "video",
        "🧹 Голосовые": "voice",
        "🧹 Кружки": "video_note",
        "🧹 Файлы": "document",
        "🧹 Аудио": "audio",
        "🧹 Стикеры": "sticker",
    }

    if text in clear_map:
        note_type = clear_map[text]
        notes = get_notes(uid)
        to_del = [n for n in notes if n["type"] == note_type]
        if not to_del:
            await update.message.reply_text("📭 Уже пусто", reply_markup=menu())
            return ConversationHandler.END
        save_user(uid, [n for n in notes if n["type"] != note_type])
        label = TYPES.get(note_type, note_type)
        await update.message.reply_text(
            f"🧹 {label} очищен ({len(to_del)})", reply_markup=menu()
        )
        return ConversationHandler.END

    await update.message.reply_text("Выбери кнопку", reply_markup=TYPE_MENU)
    return WAITING_CLEAR_TYPE


async def export_notes(update, ctx):
    uid = str(update.effective_user.id)
    notes = get_notes(uid)
    if not notes:
        await update.message.reply_text("📭 Нечего экспортировать", reply_markup=menu())
        return
    sections = {}
    for n in notes:
        sections.setdefault(n["type"], []).append(n)
    lines = ["=== ЗАМЕТКИ ===\n"]
    for t, items in sections.items():
        lines.append(f"\n--- {TYPES.get(t, t)} ---")
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
    if t == "📋 Все":
        return await show_all(update, ctx)
    if t == "📊 По категориям":
        return await show_categories(update, ctx)
    if t == "👀 Посмотреть":
        return await view_start(update, ctx)
    if t == "🗑 Удалить":
        return await delete_start(update, ctx)
    if t == "🧹 Очистить":
        return await clear_start(update, ctx)
    if t == "💾 Экспорт":
        return await export_notes(update, ctx)
    if t == "ℹ️ Помощь":
        return await help_cmd(update, ctx)


def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    app = Application.builder().token(TOKEN).build()

    view_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^👀 Посмотреть$"), view_start)],
        states={
            WAITING_VIEW_NUM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, view_note)
            ]
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

    clear_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🧹 Очистить$"), clear_start)],
        states={
            WAITING_CLEAR_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, clear_type)
            ]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    text_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Текст$"), save_text_start)],
        states={
            WAITING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_text)]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(text_conv)
    app.add_handler(view_conv)
    app.add_handler(del_conv)
    app.add_handler(clear_conv)
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

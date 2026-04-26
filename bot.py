from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

from watermark_processor import TransformState, WatermarkSettings, render_watermarked_image


@dataclass
class Session:
    image_bytes: bytes
    state: TransformState


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SHIFT_STEP_PX = int(os.getenv("SHIFT_STEP_PX", "24"))

SETTINGS = WatermarkSettings(
    watermark_path=Path(os.getenv("WATERMARK_PATH", "assets/watermark.png")),
    anchor=os.getenv("WATERMARK_ANCHOR", "top_right"),  # type: ignore[arg-type]
    width_percent=float(os.getenv("WATERMARK_WIDTH_PERCENT", "18")),
    margin_percent=float(os.getenv("WATERMARK_MARGIN_PERCENT", "4")),
    top_margin_percent=float(os.getenv("WATERMARK_TOP_MARGIN_PERCENT", "0")),
    opacity=float(os.getenv("WATERMARK_OPACITY", "1")),
)

router = Router()
sessions: dict[int, Session] = {}


def editor_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="←", callback_data="shift_left"),
                InlineKeyboardButton(text="→", callback_data="shift_right"),
                InlineKeyboardButton(text="Зеркалить", callback_data="mirror"),
            ],
            [
                InlineKeyboardButton(text="Сброс", callback_data="reset"),
                InlineKeyboardButton(text="Готово", callback_data="done"),
            ],
        ]
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Пришлите изображение как фото или файл. Я наложу логотип канала, "
        "а кнопками можно будет сдвинуть водяной знак и зеркалить изображение."
    )


@router.message(F.photo | (F.document.mime_type.startswith("image/")))
async def handle_image(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id if message.from_user else message.chat.id
    image_bytes = await download_image(message, bot)
    sessions[user_id] = Session(image_bytes=image_bytes, state=TransformState())
    await send_preview(message, user_id)


@router.callback_query(F.data.in_({"shift_left", "shift_right", "mirror", "reset", "done"}))
async def handle_action(callback: CallbackQuery) -> None:
    if not callback.message:
        await callback.answer()
        return

    user_id = callback.from_user.id
    session = sessions.get(user_id)
    if not session:
        await callback.answer("Сначала пришлите изображение.", show_alert=True)
        return

    match callback.data:
        case "shift_left":
            session.state = TransformState(
                offset_x=session.state.offset_x - SHIFT_STEP_PX,
                mirrored=session.state.mirrored,
            )
        case "shift_right":
            session.state = TransformState(
                offset_x=session.state.offset_x + SHIFT_STEP_PX,
                mirrored=session.state.mirrored,
            )
        case "mirror":
            session.state = TransformState(
                offset_x=session.state.offset_x,
                mirrored=not session.state.mirrored,
            )
        case "reset":
            session.state = TransformState()
        case "done":
            rendered = render_watermarked_image(session.image_bytes, SETTINGS, session.state)
            sessions.pop(user_id, None)
            await callback.message.answer_document(
                BufferedInputFile(rendered, filename="watermarked.jpg"),
                caption="Готово. Отправляю файлом, чтобы Telegram меньше сжимал изображение.",
            )
            await callback.answer()
            return

    await send_preview(callback.message, user_id, edit_existing=True)
    await callback.answer()


async def download_image(message: Message, bot: Bot) -> bytes:
    buffer = BytesIO()

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    else:
        raise ValueError("Message does not contain an image.")

    await bot.download(file_id, destination=buffer)
    return buffer.getvalue()


async def send_preview(message: Message, user_id: int, edit_existing: bool = False) -> None:
    session = sessions[user_id]
    try:
        rendered = render_watermarked_image(session.image_bytes, SETTINGS, session.state)
    except FileNotFoundError as error:
        await message.answer(str(error))
        return

    status = (
        f"Сдвиг: {session.state.offset_x}px\n"
        f"Зеркально: {'да' if session.state.mirrored else 'нет'}"
    )
    photo = BufferedInputFile(rendered, filename="preview.jpg")
    keyboard = editor_keyboard()

    if edit_existing:
        try:
            await message.edit_media(
                InputMediaPhoto(media=photo, caption=status),
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest:
            pass

    await message.answer_photo(photo, caption=status, reply_markup=keyboard)


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty. Create .env from .env.example and add the token.")

    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

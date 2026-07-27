import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from sqlalchemy.orm import Session

import config
from database import init_db, SessionLocal, User, Profile, ResetStatus
from seed_profiles import seed

logging.basicConfig(level=logging.INFO)

if not config.BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN or BOT_TOKEN is missing in environment variables.")

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# --- Helper DB Middleware / Functions ---
def get_or_create_user(db: Session, telegram_id: int, username: str = None) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# --- Handlers ---

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    db = SessionLocal()
    user = get_or_create_user(db, message.from_user.id, message.from_user.username)

    if user.selected_profile_id:
        profile = db.query(Profile).filter(Profile.id == user.selected_profile_id).first()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Request Reset Selection", callback_data="request_reset")]
        ])
        await message.answer(
            f"🔒 **You have already selected {profile.name}.**\n\n"
            f"You cannot select another profile on your own.\n"
            f"You can now send messages here to chat or request a selection reset.",
            parse_mode="Markdown",
            reply_markup=kb
        )
    else:
        await message.answer("👋 Welcome to the Directory Bot!\n\nBrowse profiles below and select one person to chat with:")
        await show_directory(message.chat.id, db)
    
    db.close()

async def show_directory(chat_id: int, db: Session):
    profiles = db.query(Profile).all()
    
    # Dynamically get the absolute path to the directory where bot.py lives
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for prof in profiles:
        caption = (
            f"👤 **Name:** {prof.name}\n"
            f"🎂 **Age:** {prof.age}\n"
            f"💍 **Marital Status:** {prof.marital_status}\n"
            f"🌍 **Country:** {prof.country}\n"
            f"🎨 **Hobbies:** {prof.hobbies}"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✨ Select {prof.name}", callback_data=f"select_{prof.id}")]
        ])
        
        # Join the base directory with the image path stored in the database
        absolute_image_path = os.path.join(base_dir, prof.image_path)
        
        if os.path.exists(absolute_image_path):
            photo = FSInputFile(absolute_image_path)
            await bot.send_photo(chat_id, photo=photo, caption=caption, parse_mode="Markdown", reply_markup=kb)
        else:
            # Print a warning to your Railway logs if the path is wrong
            logging.warning(f"IMAGE NOT FOUND AT: {absolute_image_path}")
            await bot.send_message(chat_id, text=caption, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data.startswith("select_"))
async def handle_selection(callback: types.CallbackQuery):
    profile_id = int(callback.data.split("_")[1])
    db = SessionLocal()
    user = get_or_create_user(db, callback.from_user.id, callback.from_user.username)

    if user.selected_profile_id:
        await callback.answer("❌ You have already selected a profile! Use /reset to request a reset.", show_alert=True)
        db.close()
        return

    # Lock selection
    user.selected_profile_id = profile_id
    db.commit()

    profile = db.query(Profile).filter(Profile.id == profile_id).first()
    db.close()

    await callback.message.edit_reply_markup(reply_markup=None)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Request Reset Selection", callback_data="request_reset")]
    ])
    
    await callback.message.answer(
        f"✅ **Successfully selected {profile.name}!**\n\n"
        f"Your choice is locked and saved. Even if the system restarts, your selection remains active.",
        parse_mode="Markdown",
        reply_markup=kb
    )
    await callback.answer()

@dp.callback_query(F.data == "request_reset")
@dp.message(Command("reset"))
async def handle_reset_request(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == user_id).first()

    if not user or not user.selected_profile_id:
        msg_text = "⚠️ You haven't selected any profile yet."
        if isinstance(event, types.CallbackQuery):
            await event.answer(msg_text, show_alert=True)
        else:
            await event.answer(msg_text)
        db.close()
        return

    if user.reset_status == ResetStatus.PENDING.value:
        msg_text = "⏳ Your reset request is already pending Admin approval."
        if isinstance(event, types.CallbackQuery):
            await event.answer(msg_text, show_alert=True)
        else:
            await event.answer(msg_text)
        db.close()
        return

    # Mark reset as pending
    user.reset_status = ResetStatus.PENDING.value
    db.commit()

    profile = db.query(Profile).filter(Profile.id == user.selected_profile_id).first()
    db.close()

    # Notify user
    confirm_msg = "📩 Your request to reset your selection has been sent to the Admin. Please wait for approval."
    if isinstance(event, types.CallbackQuery):
        await event.answer("Reset request submitted!", show_alert=True)
        await event.message.answer(confirm_msg)
    else:
        await event.answer(confirm_msg)

    # Send Notification to Admin
    if config.ADMIN_ID:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve_{user_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_{user_id}")
            ]
        ])
        await bot.send_message(
            config.ADMIN_ID,
            f"🔔 **Reset Request Received**\n\n"
            f"👤 **User:** @{event.from_user.username or 'NoUsername'} (`{user_id}`)\n"
            f"📌 **Current Selection:** {profile.name}",
            parse_mode="Markdown",
            reply_markup=admin_kb
        )

# --- Admin Handlers ---

@dp.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve(callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Unauthorized.", show_alert=True)
        return

    target_user_id = int(callback.data.split("_")[2])
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == target_user_id).first()

    if user:
        user.selected_profile_id = None
        user.reset_status = ResetStatus.NONE.value
        db.commit()

        # Notify target user
        try:
            await bot.send_message(
                target_user_id,
                "🎉 **Your reset request was APPROVED by the Admin!**\n\nUse /start to choose a new profile.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    db.close()
    await callback.message.edit_text(callback.message.text + "\n\n✅ **Status: APPROVED**")
    await callback.answer("Request Approved.")

@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(callback: types.CallbackQuery):
    if callback.from_user.id != config.ADMIN_ID:
        await callback.answer("Unauthorized.", show_alert=True)
        return

    target_user_id = int(callback.data.split("_")[2])
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == target_user_id).first()

    if user:
        user.reset_status = ResetStatus.REJECTED.value
        db.commit()

        # Notify target user
        try:
            await bot.send_message(
                target_user_id,
                "❌ **Your reset request was DECLINED by the Admin.**\n\nYour current selection remains active.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    db.close()
    await callback.message.edit_text(callback.message.text + "\n\n❌ **Status: REJECTED**")
    await callback.answer("Request Rejected.")

# --- Main Entry Point ---

async def main():
    print("Initializing Database...")
    init_db()
    seed()
    
    print("Deleting webhooks and starting Long Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

from telegram import Update, InputMediaVideo, InputMediaDocument
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os

# States for conversation
WAITING_FOR_MEDIA, WAITING_FOR_THUMBNAIL = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a video or file to change its thumbnail. Then send a new thumbnail image.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video or update.message.document:
        # Store the file ID temporarily
        context.user_data['file_id'] = update.message.video.file_id if update.message.video else update.message.document.file_id
        context.user_data['file_type'] = 'video' if update.message.video else 'document'
        await update.message.reply_text("Got the file. Now send me the new thumbnail image.")
        return WAITING_FOR_THUMBNAIL
    else:
        await update.message.reply_text("Please send a video or file first.")
        return WAITING_FOR_MEDIA

async def handle_thumbnail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        # Get the thumbnail file ID
        thumbnail_file_id = update.message.photo[-1].file_id  # Highest resolution
        file_id = context.user_data.get('file_id')
        file_type = context.user_data.get('file_type')
        
        if file_id and file_type:
            # Download and re-upload with new thumbnail (Telegram API requires this)
            file = await context.bot.get_file(file_id)
            thumbnail = await context.bot.get_file(thumbnail_file_id)
            
            # Temporary paths (clean up after)
            media_path = f"temp_{file_id}"
            thumb_path = f"temp_thumb_{thumbnail_file_id}"
            
            await file.download_to_drive(media_path)
            await thumbnail.download_to_drive(thumb_path)
            
            # Re-upload with new thumbnail
            if file_type == 'video':
                with open(media_path, 'rb') as media, open(thumb_path, 'rb') as thumb:
                    await update.message.reply_video(video=media, thumbnail=thumb, caption="Updated thumbnail!")
            else:  # document
                with open(media_path, 'rb') as media, open(thumb_path, 'rb') as thumb:
                    await update.message.reply_document(document=media, thumbnail=thumb, caption="Updated thumbnail!")
            
            # Clean up temp files
            os.remove(media_path)
            os.remove(thumb_path)
            
            await update.message.reply_text("Thumbnail changed and re-uploaded!")
        else:
            await update.message.reply_text("No file to update. Start over with /start.")
    else:
        await update.message.reply_text("Please send an image for the thumbnail.")
        return WAITING_FOR_THUMBNAIL
    
    return ConversationHandler.END

# Set up the bot
app = ApplicationBuilder().token("YOUR_API_TOKEN_HERE").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        WAITING_FOR_MEDIA: [MessageHandler(filters.VIDEO | filters.Document.ALL, handle_media)],
        WAITING_FOR_THUMBNAIL: [MessageHandler(filters.PHOTO, handle_thumbnail)],
    },
    fallbacks=[CommandHandler("start", start)],
)

app.add_handler(conv_handler)
app.run_polling()
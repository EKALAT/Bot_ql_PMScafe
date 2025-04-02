#!/usr/bin/env python
"""
Simple launcher for the Telegram bot
"""
import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ConversationHandler, CallbackQueryHandler, ContextTypes,
    filters
)
from dotenv import load_dotenv
from bot import (
    start, menu_handler, show_menu_categories, show_category_items,
    MAIN_MENU, ADMIN_MENU, VIEW_MENU, ORDER_ITEMS, CONFIRM_ORDER,
    ADD_PRODUCT, EDIT_PRODUCT, VIEW_ORDERS, MANAGE_TABLES,
    EDIT_PRODUCT_NAME, EDIT_PRODUCT_PRICE, EDIT_PRODUCT_CATEGORY, 
    EDIT_PRODUCT_DESCRIPTION, EDIT_PRODUCT_AVAILABILITY,
    error_handler, add_product, edit_product, update_product,
    save_product_name, save_product_price, save_product_category,
    save_product_description, show_tables, reserve_table, show_category_products,
    add_to_cart, view_cart, clear_cart, confirm_order
)

# Load token from environment
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    # Fallback to direct token if not in environment variables
    TOKEN = '7705072328:AAElGoUVLaXNnbwsMyBg59tWOCXNdVtHkz4'

async def main():
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        level=logging.INFO
    )
    
    # Build application
    application = Application.builder().token(TOKEN).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(menu_handler)
            ],
            ADMIN_MENU: [
                CallbackQueryHandler(menu_handler)
            ],
            VIEW_MENU: [
                CallbackQueryHandler(show_menu_categories, pattern='^view_menu$'),
                CallbackQueryHandler(show_category_items, pattern='^category_'),
                CallbackQueryHandler(menu_handler, pattern='^back_to_main$')
            ],
            ORDER_ITEMS: [
                # Xử lý đặt hàng
                CallbackQueryHandler(show_category_products, pattern='^order_cat_'),
                CallbackQueryHandler(add_to_cart, pattern='^add_item_'),
                CallbackQueryHandler(view_cart, pattern='^view_cart$'),
                CallbackQueryHandler(show_tables, pattern='^reserve_table$'),
                CallbackQueryHandler(menu_handler, pattern='^back_to_main$'),
                CallbackQueryHandler(menu_handler)
            ],
            CONFIRM_ORDER: [
                # Xác nhận đơn hàng
                CallbackQueryHandler(confirm_order, pattern='^confirm_order$'),
                CallbackQueryHandler(clear_cart, pattern='^clear_cart$'),
                CallbackQueryHandler(menu_handler, pattern='^place_order$'),
                CallbackQueryHandler(show_tables, pattern='^reserve_table$'),
                CallbackQueryHandler(menu_handler, pattern='^back_to_main$'),
                CallbackQueryHandler(menu_handler)
            ],
            ADD_PRODUCT: [
                CallbackQueryHandler(menu_handler, pattern='^manage_products$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_product)
            ],
            EDIT_PRODUCT: [
                CallbackQueryHandler(menu_handler)
            ],
            EDIT_PRODUCT_NAME: [
                CallbackQueryHandler(menu_handler, pattern='^edit_product_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_product_name)
            ],
            EDIT_PRODUCT_PRICE: [
                CallbackQueryHandler(menu_handler, pattern='^edit_product_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_product_price)
            ],
            EDIT_PRODUCT_CATEGORY: [
                CallbackQueryHandler(menu_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_product_category)
            ],
            EDIT_PRODUCT_DESCRIPTION: [
                CallbackQueryHandler(menu_handler, pattern='^edit_product_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_product_description)
            ],
            VIEW_ORDERS: [
                # Xử lý xem đơn hàng sẽ được thêm ở đây
                CallbackQueryHandler(menu_handler, pattern='^back_to_main$')
            ],
            MANAGE_TABLES: [
                # Xử lý quản lý bàn sẽ được thêm ở đây
                CallbackQueryHandler(menu_handler, pattern='^back_to_main$')
            ]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("Bot đang khởi động...")
    await application.initialize()
    await application.start()
    print("Bot đã khởi động thành công!")
    
    # Run the bot until the user presses Ctrl-C
    await application.updater.start_polling()
    print("Bot đã bắt đầu lắng nghe...")
    
    # Block until a signal is received
    stop_signal = asyncio.Future()
    
    # Set up signal handling for graceful exit
    try:
        await stop_signal
    except asyncio.CancelledError:
        pass
    finally:
        await application.updater.stop_polling()
        await application.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot đã được dừng bởi người dùng.") 
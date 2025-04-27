import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ConversationHandler, CallbackQueryHandler, ContextTypes,
    filters
)
from dotenv import load_dotenv
from database import init_db, get_session, Product, Order, OrderItem, Table
from sqlalchemy import func
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ConversationHandler, CallbackQueryHandler, ContextTypes
)
from config import BOT_TOKEN, GROUP_CHAT_ID

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import cấu hình từ config.py
from config import BOT_TOKEN, GROUP_CHAT_ID

# Kiểm tra GROUP_CHAT_ID
if not GROUP_CHAT_ID:
    logger.warning("GROUP_CHAT_ID chưa được cấu hình. Nhiều chức năng sẽ không hoạt động đúng!")
else:
    logger.info(f"GROUP_CHAT_ID được cấu hình là: {GROUP_CHAT_ID}")

# Load biến môi trường
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    # Fallback to direct token if not in environment variables
    TOKEN = '8111919258:AAGMe6AV3qOoqq3SVpMvpIR_9v7ja5MWApQ'

# Đọc các ID theo vai trò từ biến môi trường
ADMIN_ID = int(os.getenv('ADMIN_ID', 6079753756))

# Danh sách ID của thu ngân
CASHIER_IDS = os.getenv('CASHIER_IDS', '7686763864')
CASHIER_LIST = [int(id.strip()) for id in CASHIER_IDS.split(',') if id.strip().isdigit()]

# Danh sách ID của nhân viên phục vụ
SERVER_IDS = os.getenv('SERVER_IDS', '')
SERVER_LIST = [int(id.strip()) for id in SERVER_IDS.split(',') if id.strip().isdigit()]

# Trạng thái hội thoại
(MAIN_MENU, ADMIN_MENU, CASHIER_MENU, SERVER_MENU, VIEW_MENU, ORDER_ITEMS, CONFIRM_ORDER, 
 ADD_PRODUCT, EDIT_PRODUCT, VIEW_ORDERS, MANAGE_TABLES,
 EDIT_PRODUCT_NAME, EDIT_PRODUCT_PRICE, EDIT_PRODUCT_CATEGORY, EDIT_PRODUCT_DESCRIPTION, EDIT_PRODUCT_AVAILABILITY,
 ORDER_PREPARATION, BILL_ACTIONS, SELECTING_BILL_TABLE) = range(19)

# Khởi tạo database
init_db()

def initialize_tables():
    """Khởi tạo 5 bàn mặc định nếu chưa có bàn nào trong cơ sở dữ liệu"""
    session = get_session()
    try:
        # Kiểm tra xem đã có bàn nào chưa
        table_count = session.query(Table).count()
        
        if table_count == 0:
            # Tạo 5 bàn mặc định
            default_tables = [
                Table(number=1, capacity=2, is_reserved=False),
                Table(number=2, capacity=4, is_reserved=False),
                Table(number=3, capacity=4, is_reserved=False),
                Table(number=4, capacity=6, is_reserved=False),
                Table(number=5, capacity=8, is_reserved=False)
            ]
            
            for table in default_tables:
                session.add(table)
                
            session.commit()
            logger.info("Đã khởi tạo 5 bàn mặc định")
    except Exception as e:
        session.rollback()
        logger.error(f"Lỗi khi khởi tạo bàn mặc định: {str(e)}")
    finally:
        session.close()

# Khởi tạo bàn mặc định
initialize_tables()

def is_admin(user_id):
    """Kiểm tra xem người dùng có phải là admin hay không"""
    return user_id == ADMIN_ID

def is_cashier(user_id):
    """Kiểm tra xem người dùng có phải là thu ngân hay không"""
    return user_id in CASHIER_LIST

def is_server(user_id):
    """Kiểm tra xem người dùng có phải là nhân viên phục vụ hay không"""
    return user_id in SERVER_LIST

def is_employee(user_id):
    """Kiểm tra xem người dùng có phải là nhân viên của quán hay không"""
    return is_admin(user_id) or is_cashier(user_id) or is_server(user_id)

def get_role(user_id):
    """Lấy vai trò của người dùng"""
    if is_admin(user_id):
        return "admin"
    elif is_cashier(user_id):
        return "cashier"
    elif is_server(user_id):
        return "server"
    else:
        return "unauthorized"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý lệnh /start và hiển thị menu chính"""
    user_id = update.effective_user.id
    
    # Lấy thông tin tên người dùng
    user = update.effective_user
    user_name = user.first_name
    
    # Ghi lại user_id vào log để kiểm tra
    logger.info(f"User {user_id} đã gửi lệnh /start")
    
    # Kiểm tra xem người dùng có phải là nhân viên không
    if is_admin(user_id):
        logger.info(f"User {user_id} đã đăng nhập với vai trò Admin")
        keyboard = [
            [InlineKeyboardButton("👥 Quản lý nhân viên", callback_data='manage_employees')],
            [InlineKeyboardButton("🍽️ Quản lý bàn", callback_data='manage_tables')],
            [InlineKeyboardButton("🍔 Quản lý món ăn", callback_data='manage_products')],
            [InlineKeyboardButton("📊 Thống kê", callback_data='statistics')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            text=f"Chào mừng Admin {user_name}! Vui lòng chọn một trong các tùy chọn sau:",
            reply_markup=reply_markup
        )
        return ADMIN_MENU
    elif is_cashier(user_id):
        logger.info(f"User {user_id} đã đăng nhập với vai trò Thu ngân")
        keyboard = [
            [InlineKeyboardButton("🪑 Quản lý bàn", callback_data='manage_tables')],
            [InlineKeyboardButton("💵 Xem các bill cần thanh toán", callback_data='view_bills')],
            [InlineKeyboardButton("📊 Thống kê", callback_data='statistics')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            text=f"Chào mừng Thu ngân {user_name}! Vui lòng chọn một trong các tùy chọn sau:",
            reply_markup=reply_markup
        )
        return CASHIER_MENU
    elif is_server(user_id):
        logger.info(f"User {user_id} đã đăng nhập với vai trò Phục vụ")
        keyboard = [
            [InlineKeyboardButton("🪑 Đặt bàn", callback_data='reserve_table')],
            [InlineKeyboardButton("🍔 Đặt món", callback_data='place_order')],
            [InlineKeyboardButton("🧾 Yêu cầu xuất bill", callback_data='request_bill')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            text=f"Chào mừng Nhân viên phục vụ {user_name}! Vui lòng chọn một trong các tùy chọn sau:",
            reply_markup=reply_markup
        )
        return SERVER_MENU
    else:
        logger.warning(f"User {user_id} không phải là nhân viên, từ chối truy cập")
        await update.message.reply_text(
            f"⛔ Xin chào {user_name}, bạn không có quyền truy cập hệ thống.\n"
            "Vui lòng liên hệ Admin nếu bạn cho rằng đây là lỗi."
        )
        return ConversationHandler.END

def get_appropriate_menu_state(user_id):
    """Trả về trạng thái menu phù hợp dựa trên vai trò của người dùng"""
    if is_admin(user_id):
        return ADMIN_MENU
    elif is_cashier(user_id):
        return CASHIER_MENU
    elif is_server(user_id):
        return SERVER_MENU
    return ConversationHandler.END

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý lựa chọn menu dựa trên vai trò của người dùng."""
    query = update.callback_query
    user_id = update.effective_user.id
    choice = query.data
    
    # Log lựa chọn của người dùng
    role = "admin" if is_admin(user_id) else "cashier" if is_cashier(user_id) else "server" if is_server(user_id) else "unknown"
    logger.info(f"Người dùng {user_id} (vai trò: {role}) đã chọn: {choice}")
    
    # Xác nhận callback query để Telegram không hiển thị "loading..."
    await query.answer()
    
    # Xử lý lựa chọn quay lại menu chính
    if choice == "back_to_main":
        return await start(update, context)
    
    # Xử lý các common handlers không phụ thuộc vai trò
    common_handlers = {
        "place_order": start_order,            # Bắt đầu đặt món
        "reserve_table": show_tables,          # Hiển thị bàn để đặt
        "view_cart": view_cart,                # Xem giỏ hàng
        "view_menu": show_menu_categories,     # Xem menu
        "confirm_order": confirm_order,        # Xác nhận đặt món
        "clear_cart": clear_cart,              # Xóa giỏ hàng
        "request_bill": request_bill           # Yêu cầu xuất bill
    }
    
    # Nếu lựa chọn thuộc common handlers, xử lý ngay
    if choice in common_handlers:
        return await common_handlers[choice](update, context)
    
    # Xử lý các lựa chọn của Admin
    if is_admin(user_id):
        admin_menu_handlers = {
            "manage_products": admin_manage_products,
            "manage_tables": admin_manage_tables,
            "view_reports": admin_reports,
            "view_bills": view_bills,          # Admin cũng có thể xem và xử lý bill
            "reset_all_tables": reset_all_tables
        }
        handler = admin_menu_handlers.get(choice)
        if handler:
            return await handler(update, context)
    
    # Xử lý các lựa chọn của Thu ngân
    elif is_cashier(user_id):
        cashier_menu_handlers = {
            "manage_tables": admin_manage_tables,
            "view_orders": view_orders,
            "view_bills": view_bills,         # Thu ngân có thể xem và xử lý bill
        }
        handler = cashier_menu_handlers.get(choice)
        if handler:
            return await handler(update, context)
    
    # Xử lý các lựa chọn của Phục vụ
    elif is_server(user_id):
        # Các handler đặc biệt của nhân viên phục vụ đã được xử lý trong common handlers
        pass
    
    # Xử lý các pattern đặc biệt cho callback data
    if choice.startswith("order_cat_"):
        return await show_category_products(update, context)
    elif choice.startswith("category_"):
        return await show_category_items(update, context)
    elif choice.startswith("add_item_"):
        return await add_to_cart(update, context)
    elif choice.startswith("reserve_"):
        return await reserve_table(update, context)
    elif choice.startswith("unreserve_"):
        return await unreserve_table(update, context)
    elif choice.startswith("bill_for_table"):
        return await show_table_bill(update, context)
    elif choice.startswith("send_bill_to_group"):
        return await send_bill_to_group(update, context)
    elif choice.startswith("process_payment"):
        return await process_payment(update, context)
    elif choice.startswith("edit_product_"):
        return await edit_product(update, context)
    elif choice.startswith("confirm_reset_tables"):
        return await confirm_reset_tables(update, context)
    
    # Nếu không trùng khớp với bất kỳ xử lý nào, trả về menu phù hợp
    await query.edit_message_text(
        text=f"Lựa chọn '{choice}' không hợp lệ hoặc không được hỗ trợ. Vui lòng chọn từ menu.",
        reply_markup=get_menu_keyboard(user_id)
    )
    return get_appropriate_menu_state(user_id)

def get_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Tạo bàn phím menu dựa trên vai trò của người dùng."""
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("📋 Quản lý sản phẩm", callback_data="manage_products")],
            [InlineKeyboardButton("🪑 Quản lý bàn", callback_data="manage_tables")],
            [InlineKeyboardButton("👥 Quản lý người dùng", callback_data="manage_users")],
            [InlineKeyboardButton("📊 Xem báo cáo", callback_data="view_reports")],
            [InlineKeyboardButton("🍽️ Quản lý đơn hàng", callback_data="manage_orders")],
            [InlineKeyboardButton("💰 Quản lý thanh toán", callback_data="view_bills")]
        ]
    elif is_cashier(user_id):
        keyboard = [
            [InlineKeyboardButton("🪑 Quản lý bàn", callback_data="manage_tables")],
            [InlineKeyboardButton("🍽️ Xem đơn hàng", callback_data="view_orders")],
            [InlineKeyboardButton("💰 Xử lý thanh toán", callback_data="view_bills")]
        ]
    elif is_server(user_id):
        keyboard = [
            [InlineKeyboardButton("📝 Đặt bàn", callback_data="place_reservation")],
            [InlineKeyboardButton("🍲 Đặt món", callback_data="place_order")],
            [InlineKeyboardButton("🧾 Yêu cầu xuất bill", callback_data="request_bill")]
        ]
    else:
        # Menu mặc định nếu không có vai trò
        keyboard = [
            [InlineKeyboardButton("🔒 Đăng nhập", callback_data="login")]
        ]
    
    return InlineKeyboardMarkup(keyboard)

async def show_menu_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị danh mục sản phẩm"""
    query = update.callback_query
    session = get_session()
    
    try:
        # Lấy các danh mục sản phẩm
        categories = session.query(Product.category).distinct().all()
        categories = [category[0] for category in categories]
        
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(f"{category}", callback_data=f"category_{category}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(text="Chọn danh mục:", reply_markup=reply_markup)
        else:
            await update.message.reply_text(text="Chọn danh mục:", reply_markup=reply_markup)
    finally:
        session.close()
    
    return VIEW_MENU

async def show_category_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị các sản phẩm trong danh mục"""
    query = update.callback_query
    await query.answer()
    
    # Lấy tên danh mục từ callback data
    category = query.data.replace("category_", "")
    
    session = get_session()
    try:
        # Lấy sản phẩm theo danh mục
        products = session.query(Product).filter(
            Product.category == category,
            Product.is_available == True
        ).all()
        
        if not products:
            await query.edit_message_text(
                text=f"Không có sản phẩm nào trong danh mục {category}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='view_menu')]])
            )
            return VIEW_MENU
        
        text = f"*Danh mục: {category}*\n\n"
        for product in products:
            text += f"*{product.name}* - _{product.price:,.0f} VNĐ_\n{product.description or 'Không có mô tả'}\n\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Quay lại", callback_data='view_menu')]]
        if is_admin(update.effective_user.id):
            keyboard.append([InlineKeyboardButton("✏️ Chỉnh sửa danh mục", callback_data=f'edit_category_{category}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')
    finally:
        session.close()
    
    return VIEW_MENU

async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bắt đầu quy trình đặt hàng"""
    query = update.callback_query
    await query.answer()
    
    # Khởi tạo giỏ hàng trống nếu chưa có
    if 'cart' not in context.user_data:
        context.user_data['cart'] = []
    
    # Kiểm tra xem người dùng đã đặt bàn chưa
    selected_table = context.user_data.get('selected_table')
    if selected_table:
        table_info = f"🪑 *ĐANG ĐẶT MÓN CHO BÀN {selected_table['number']}*\n\n"
    else:
        table_info = "⚠️ *CHƯA CHỌN BÀN* - Bạn nên đặt bàn trước khi đặt món!\n\n"
    
    session = get_session()
    try:
        # Lấy danh mục sản phẩm để hiển thị
        categories = session.query(Product.category).distinct().all()
        categories = [category[0] for category in categories]
        
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(f"{category}", callback_data=f"order_cat_{category}")])
        
        # Nếu chưa đặt bàn, hiển thị nút đặt bàn nổi bật
        if not selected_table:
            keyboard.insert(0, [InlineKeyboardButton("⚠️ ĐẶT BÀN TRƯỚC ⚠️", callback_data='reserve_table')])
            
        # Nếu có sản phẩm trong giỏ hàng, hiển thị nút xem giỏ hàng
        if context.user_data.get('cart'):
            cart_count = sum(item['quantity'] for item in context.user_data['cart'])
            keyboard.append([InlineKeyboardButton(f"🛒 Xem giỏ hàng ({cart_count} món)", callback_data='view_cart')])
        else:
            keyboard.append([InlineKeyboardButton("🛒 Giỏ hàng trống", callback_data='view_cart')])
            
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"{table_info}Chọn danh mục để đặt món:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    finally:
        session.close()
    
    return ORDER_ITEMS

async def admin_manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Giao diện quản lý sản phẩm cho admin"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("➕ Thêm sản phẩm mới", callback_data='add_product')],
        [InlineKeyboardButton("📋 Xem & Sửa sản phẩm", callback_data='list_products')],
        [InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="*Quản lý Sản phẩm*\nChọn một tùy chọn:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return ADMIN_MENU

async def admin_manage_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Giao diện quản lý đơn hàng cho admin"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📋 Đơn hàng đang chờ", callback_data='pending_orders')],
        [InlineKeyboardButton("✅ Đơn hàng đã xác nhận", callback_data='confirmed_orders')],
        [InlineKeyboardButton("💯 Đơn hàng đã hoàn thành", callback_data='completed_orders')],
        [InlineKeyboardButton("❌ Đơn hàng đã hủy", callback_data='cancelled_orders')],
        [InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="*Quản lý Đơn hàng*\nChọn danh sách đơn hàng:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return ADMIN_MENU

async def admin_manage_tables(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị menu quản lý bàn"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra nếu người dùng là admin hoặc thu ngân
    user_id = update.effective_user.id
    if not (is_admin(user_id) or is_cashier(user_id)):
        await query.edit_message_text(
            text="⛔ Bạn không có quyền truy cập vào khu vực này.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return MAIN_MENU
    
    # Hiển thị menu quản lý bàn
    keyboard = []
    
    # Chỉ admin có thể thêm/sửa/xóa bàn
    if is_admin(user_id):
        keyboard.extend([
            [InlineKeyboardButton("➕ Thêm bàn mới", callback_data='add_new_table')],
            [InlineKeyboardButton("✏️ Chỉnh sửa thông tin bàn", callback_data='edit_table_info')],
            [InlineKeyboardButton("🗑️ Xóa bàn", callback_data='delete_table')],
        ])
    
    # Cả admin và thu ngân đều có thể quản lý trạng thái bàn
    keyboard.extend([
        [InlineKeyboardButton("🔄 Quản lý trạng thái bàn", callback_data='manage_table_status')],
        [InlineKeyboardButton("💰 Thanh toán nhanh theo bàn", callback_data='quick_payment_by_table')],
    ])
    
    # Chỉ admin có thể reset tất cả bàn
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("🔄 Reset tất cả bàn về trạng thái trống", callback_data='reset_all_tables')])
    
    keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="*QUẢN LÝ BÀN*\nVui lòng chọn chức năng quản lý:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return MANAGE_TABLES

async def add_new_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị giao diện thêm bàn mới"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Chỉ Admin mới có quyền thêm bàn mới.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    
    # Hiển thị form thêm bàn
    keyboard = []
    
    # Tạo các nút chọn số bàn
    for table_number in range(1, 11):
        row = []
        for i in range(5):
            num = table_number + i * 10
            row.append(InlineKeyboardButton(f"{num}", callback_data=f"create_table_{num}_4"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')])
    
    await query.edit_message_text(
        text="*THÊM BÀN MỚI*\n\nChọn số bàn để thêm (mặc định 4 chỗ ngồi):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return MANAGE_TABLES

async def create_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý tạo bàn mới"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Chỉ Admin mới có quyền tạo bàn mới.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    
    # Lấy thông tin từ callback data
    # Format: create_table_<số_bàn>_<số_chỗ>
    parts = query.data.split('_')
    table_number = int(parts[2])
    table_capacity = int(parts[3]) if len(parts) > 3 else 4
    
    conn = get_db_connection()
    try:
        # Kiểm tra xem số bàn đã tồn tại chưa
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tables WHERE name = ?", (f"Bàn {table_number}",))
        existing_table = cursor.fetchone()
        
        if existing_table:
            await query.edit_message_text(
                text=f"❌ Bàn số {table_number} đã tồn tại trong hệ thống!\n\nVui lòng chọn số bàn khác.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='add_new_table')]])
            )
            return MANAGE_TABLES
        
        # Tạo bàn mới
        cursor.execute(
            "INSERT INTO tables (name, capacity, is_reserved) VALUES (?, ?, 0)",
            (f"Bàn {table_number}", table_capacity)
        )
        conn.commit()
        
        # Gửi thông báo đến nhóm
        user = update.effective_user
        user_name = f"{user.first_name} {user.last_name or ''}"
        
        notification_message = (
            f"➕ *THÔNG BÁO THÊM BÀN MỚI*\n\n"
            f"Admin *{user_name}* vừa thêm Bàn {table_number} ({table_capacity} chỗ ngồi) vào hệ thống\n"
            f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        )
        
        # Gửi thông báo không đồng bộ để không làm chậm luồng chính
        asyncio.create_task(send_group_notification(context, notification_message))
        
        # Hiển thị thông báo thành công
        await query.edit_message_text(
            text=f"✅ *Đã thêm bàn thành công!*\n\n"
                f"• Số bàn: {table_number}\n"
                f"• Sức chứa: {table_capacity} người",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Thêm bàn khác", callback_data='add_new_table')],
                [InlineKeyboardButton("🔙 Quay lại quản lý bàn", callback_data='manage_tables')]
            ]),
            parse_mode='Markdown'
        )
        return MANAGE_TABLES
        
    except Exception as e:
        logger.error(f"Lỗi khi tạo bàn mới: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def admin_reports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị báo cáo cho admin"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 Doanh thu hôm nay", callback_data='report_today')],
        [InlineKeyboardButton("📈 Doanh thu tuần này", callback_data='report_week')],
        [InlineKeyboardButton("📉 Doanh thu tháng này", callback_data='report_month')],
        [InlineKeyboardButton("🔝 Sản phẩm bán chạy", callback_data='report_top_products')],
        [InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="*Báo cáo*\nChọn loại báo cáo:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return ADMIN_MENU

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lỗi"""
    logger.error(f"Update {update} caused error {context.error}")

async def show_tables(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị danh sách bàn"""
    query = update.callback_query
    await query.answer()
    
    session = get_session()
    try:
        # Lấy tất cả bàn, bao gồm cả đã đặt và chưa đặt
        tables = session.query(Table).order_by(Table.number).all()
        
        if not tables:
            # Nếu không có bàn nào, thử khởi tạo lại
            session.close()
            initialize_tables()
            session = get_session()
            tables = session.query(Table).order_by(Table.number).all()
            
            if not tables:
                await query.edit_message_text(
                    text="❌ Không thể tìm thấy thông tin bàn. Vui lòng liên hệ quản lý!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
                )
                return MAIN_MENU
        
        # Tìm bàn trống
        available_tables = [table for table in tables if not table.is_reserved]
        
        if not available_tables:
            await query.edit_message_text(
                text="❌ *Hiện tại tất cả các bàn đều đã được đặt!*\n\nVui lòng quay lại sau khi có bàn trống.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
            )
        else:
            # Hiển thị danh sách tất cả các bàn với trạng thái
            text = "*DANH SÁCH BÀN*\n\n"
            for table in tables:
                status = "🔴 Đã đặt" if table.is_reserved else "🟢 Trống"
                text += f"*Bàn {table.number}* - {table.capacity} chỗ - {status}\n"
            
            text += "\nChọn bàn trống để đặt:"
            
            # Tạo nút chỉ cho các bàn trống
            keyboard = []
            for table in available_tables:
                keyboard.append([InlineKeyboardButton(
                    f"🪑 Đặt Bàn {table.number} ({table.capacity} chỗ)", 
                    callback_data=f'reserve_{table.id}'
                )])
            
            keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    finally:
        session.close()
    
    return MAIN_MENU

async def reserve_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý đặt bàn"""
    query = update.callback_query
    await query.answer()
    
    # Lấy ID bàn từ callback data
    table_id = int(query.data.split('_')[1])
    
    session = get_session()
    try:
        table = session.query(Table).get(table_id)
        if not table:
            await query.edit_message_text(
                text="❌ Không tìm thấy bàn này!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='reserve_table')]])
            )
            return MAIN_MENU
        
        if table.is_reserved:
            await query.edit_message_text(
                text="❌ Bàn này đã được đặt! Vui lòng chọn bàn khác.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Xem bàn khác", callback_data='reserve_table')]])
            )
            return MAIN_MENU
        
        # Đặt bàn
        table.is_reserved = True
        session.commit()
        
        # Lưu số bàn vào user_data để sử dụng khi đặt món
        context.user_data['selected_table'] = {
            'id': table.id,
            'number': table.number
        }
        
        # Gửi thông báo đến nhóm
        user = update.effective_user
        user_name = f"{user.first_name} {user.last_name or ''}"
        user_role = get_role(user.id)
        role_text = "Admin" if user_role == "admin" else "Thu ngân" if user_role == "cashier" else "Nhân viên phục vụ"
        
        notification_message = (
            f"🪑 *THÔNG BÁO CÓ KHÁCH ĐẶT BÀN*\n\n"
            f"Bàn *{table.number}* ({table.capacity} chỗ) vừa được đặt\n"
            f"👤 Người phục vụ: *{user_name}* ({role_text})\n"
            f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
            f"⏰ Nhân viên vui lòng chuẩn bị bàn và phục vụ khách!\n"
            f"💡 Nhấn nút 'Đặt món' bên dưới để tiến hành ghi món cho khách."
        )
        
        # Gửi thông báo không đồng bộ để không làm chậm luồng chính
        asyncio.create_task(send_group_notification(context, notification_message))
        
        # Hiển thị tin nhắn thành công và đề xuất đặt món
        keyboard = [
            [InlineKeyboardButton("🍽️ Đặt món ngay", callback_data='place_order')],
            [InlineKeyboardButton("⬅️ Quay lại Menu chính", callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"✅ *Đặt bàn thành công!*\n\n"
                 f"Bạn đã đặt *Bàn {table.number}* - {table.capacity} chỗ.\n\n"
                 f"Bạn có thể đặt món ngay bây giờ hoặc quay lại menu chính.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Điều quan trọng - Thay đổi trạng thái để xử lý đúng callback tiếp theo
        return SERVER_MENU  # Trả về SERVER_MENU thay vì MAIN_MENU
    except Exception as e:
        session.rollback()
        await query.edit_message_text(
            text=f"❌ Có lỗi xảy ra khi đặt bàn: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Thử lại", callback_data='reserve_table')]])
        )
        return SERVER_MENU  # Trả về SERVER_MENU để tiếp tục xử lý
    finally:
        session.close()

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý thêm sản phẩm mới dạng form từng bước"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bạn không có quyền thực hiện chức năng này.")
        return MAIN_MENU

    text = update.message.text
    step = context.user_data.get('add_product_step', 'name')
    
    if step == 'name':
        # Lưu tên sản phẩm
        context.user_data['product_name'] = text
        context.user_data['add_product_step'] = 'price'
        
        await update.message.reply_text(
            "*Thêm sản phẩm mới - Bước 2/4*\n\n"
            f"Tên sản phẩm: *{text}*\n\n"
            "Vui lòng nhập *giá sản phẩm*:\n"
            "• Chỉ nhập số, không cần nhập dấu phẩy hay đơn vị tiền\n"
            "• Ví dụ: 25000 (cho sản phẩm giá 25,000 VNĐ)\n"
            "• Giá phải là số dương",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Hủy thao tác", callback_data='manage_products')]])
        )
        return ADD_PRODUCT
        
    elif step == 'price':
        # Kiểm tra và lưu giá sản phẩm
        try:
            price = int(text)
            if price <= 0:
                raise ValueError("Giá phải là số dương")
            
            context.user_data['product_price'] = price
            context.user_data['add_product_step'] = 'category'
            
            # Lấy các danh mục hiện có để gợi ý
            session = get_session()
            try:
                categories = session.query(Product.category).distinct().all()
                categories = [category[0] for category in categories]
                
                if categories:
                    category_text = "*Các danh mục hiện có:*\n"
                    for category in categories:
                        category_text += f"• {category}\n"
                    
                    category_text += "\n*Lưu ý:*\n• Bạn có thể chọn một danh mục có sẵn hoặc tạo danh mục mới\n• Nên viết đúng chính tả và định dạng của danh mục"
                else:
                    category_text = "*Chưa có danh mục nào được tạo*\nBạn sẽ tạo danh mục đầu tiên cho hệ thống."
            except Exception:
                category_text = ""
            finally:
                session.close()
            
            await update.message.reply_text(
                "*Thêm sản phẩm mới - Bước 3/4*\n\n"
                f"Tên sản phẩm: *{context.user_data['product_name']}*\n"
                f"Giá: *{price:,} VNĐ*\n\n"
                f"Vui lòng nhập *danh mục* cho sản phẩm:\n\n{category_text}",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Hủy thao tác", callback_data='manage_products')]])
            )
            return ADD_PRODUCT
            
        except ValueError:
            await update.message.reply_text(
                "❌ *Lỗi: Giá sản phẩm không hợp lệ!*\n\n"
                "Giá sản phẩm phải là số dương và chỉ chứa các chữ số.\n"
                "Ví dụ: 25000 (cho sản phẩm giá 25,000 VNĐ)\n\n"
                "Vui lòng nhập lại giá sản phẩm:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Hủy thao tác", callback_data='manage_products')]])
            )
            return ADD_PRODUCT
            
    elif step == 'category':
        # Lưu danh mục sản phẩm
        context.user_data['product_category'] = text
        context.user_data['add_product_step'] = 'description'
        
        await update.message.reply_text(
            "*Thêm sản phẩm mới - Bước 4/4*\n\n"
            f"Tên sản phẩm: *{context.user_data['product_name']}*\n"
            f"Giá: *{context.user_data['product_price']:,} VNĐ*\n"
            f"Danh mục: *{text}*\n\n"
            "Vui lòng nhập *mô tả* cho sản phẩm:\n"
            "• Mô tả nên ngắn gọn nhưng đầy đủ thông tin\n"
            "• Nếu không có mô tả, hãy gửi dấu '-'\n"
            "• Ví dụ: Cà phê pha với sữa đặc, vị đắng nhẹ và thơm béo",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Hủy thao tác", callback_data='manage_products')]])
        )
        return ADD_PRODUCT
        
    elif step == 'description':
        # Lưu mô tả sản phẩm và thêm vào database
        description = "" if text == "-" else text
        
        session = get_session()
        try:
            # Tạo sản phẩm mới
            new_product = Product(
                name=context.user_data['product_name'],
                price=context.user_data['product_price'],
                category=context.user_data['product_category'],
                description=description,
                is_available=True
            )
            
            session.add(new_product)
            session.commit()
            
            # Xóa dữ liệu tạm
            product_name = context.user_data['product_name']
            product_price = context.user_data['product_price']
            product_category = context.user_data['product_category']
            
            context.user_data.pop('product_name', None)
            context.user_data.pop('product_price', None)
            context.user_data.pop('product_category', None)
            context.user_data.pop('add_product_step', None)
            
            # Thông báo thành công
            await update.message.reply_text(
                f"✅ *Đã thêm sản phẩm mới thành công!*\n\n"
                f"Tên: *{product_name}*\n"
                f"Giá: *{product_price:,} VNĐ*\n"
                f"Danh mục: *{product_category}*\n"
                f"Mô tả: *{description or 'Không có'}*\n\n"
                f"Sản phẩm đã được thêm vào cơ sở dữ liệu và hiển thị trong menu.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Thêm sản phẩm khác", callback_data='add_product')],
                    [InlineKeyboardButton("📋 Xem danh sách sản phẩm", callback_data='list_products')],
                    [InlineKeyboardButton("⬅️ Quay lại menu quản lý", callback_data='manage_products')]
                ])
            )
            return ADMIN_MENU
            
        except Exception as e:
            session.rollback()
            await update.message.reply_text(
                f"❌ Có lỗi xảy ra khi thêm sản phẩm: {str(e)}\n\n"
                "Vui lòng thử lại sau.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại menu quản lý", callback_data='manage_products')]])
            )
            return ADMIN_MENU
        finally:
            session.close()
    
    # Trường hợp không rơi vào bất kỳ bước nào
    await update.message.reply_text(
        "❌ Có lỗi xảy ra trong quá trình thêm sản phẩm.\n\n"
        "Vui lòng thử lại.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại menu quản lý", callback_data='manage_products')]])
    )
    return ADMIN_MENU

async def edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý chỉnh sửa sản phẩm"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("Bạn không có quyền thực hiện chức năng này.")
        return MAIN_MENU

    query = update.callback_query
    await query.answer()
    
    # Lấy ID sản phẩm từ callback data
    product_id = int(query.data.split('_')[2])
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await query.edit_message_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
            
        # Lưu ID sản phẩm vào context để sử dụng trong các hàm edit_product_*
        context.user_data['editing_product_id'] = product_id
        
        # Hiển thị thông tin sản phẩm và các tùy chọn chỉnh sửa
        status = "✅ Có sẵn" if product.is_available else "❌ Hết hàng"
        text = f"*Chỉnh sửa sản phẩm:*\n\n"
        text += f"*{product.name}*\n"
        text += f"Giá: {product.price:,} VNĐ\n"
        text += f"Danh mục: {product.category}\n"
        text += f"Trạng thái: {status}\n"
        text += f"Mô tả: {product.description or 'Không có'}\n\n"
        text += f"Chọn thông tin bạn muốn chỉnh sửa:"
        
        # Các tùy chọn chỉnh sửa
        keyboard = [
            [InlineKeyboardButton("✏️ Sửa tên", callback_data=f'edit_name_{product_id}')],
            [InlineKeyboardButton("💰 Sửa giá", callback_data=f'edit_price_{product_id}')],
            [InlineKeyboardButton("📂 Sửa danh mục", callback_data=f'edit_category_{product_id}')],
            [InlineKeyboardButton("📝 Sửa mô tả", callback_data=f'edit_description_{product_id}')],
            [InlineKeyboardButton("🔄 Đổi trạng thái", callback_data=f'toggle_availability_{product_id}')],
            [InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return EDIT_PRODUCT
        
    finally:
        session.close()

async def update_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý cập nhật thông tin sản phẩm"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Bạn không có quyền thực hiện chức năng này.")
        return MAIN_MENU

    text = update.message.text
    session = get_session()
    
    try:
        # Lấy ID sản phẩm từ context
        product_id = context.user_data.get('editing_product_id')
        if not product_id:
            await update.message.reply_text(
                "Không tìm thấy thông tin sản phẩm cần chỉnh sửa!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='list_products')]])
            )
            return ADMIN_MENU
            
        product = session.query(Product).get(product_id)
        if not product:
            await update.message.reply_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='list_products')]])
            )
            return ADMIN_MENU

        # Phân tích thông tin mới
        parts = text.split('|')
        if len(parts) < 3:
            await update.message.reply_text(
                "Vui lòng nhập thông tin sản phẩm theo định dạng:\n"
                "Tên mới | Giá mới | Danh mục mới | Mô tả mới\n\n"
                "Ví dụ:\n"
                "Cà phê sữa | 25000 | Đồ uống | Cà phê với sữa đặc",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='list_products')]])
            )
            return EDIT_PRODUCT

        # Cập nhật thông tin sản phẩm
        product.name = parts[0].strip()
        try:
            product.price = int(parts[1].strip())
        except ValueError:
            await update.message.reply_text(
                "Giá sản phẩm phải là số!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='list_products')]])
            )
            return EDIT_PRODUCT
        product.category = parts[2].strip()
        product.description = parts[3].strip() if len(parts) > 3 else ""
        
        session.commit()
        
        # Xóa ID sản phẩm khỏi context sau khi cập nhật thành công
        context.user_data.pop('editing_product_id', None)
        
        await update.message.reply_text(
            f"✅ Đã cập nhật sản phẩm:\n\n"
            f"Tên: {product.name}\n"
            f"Giá: {product.price:,} VNĐ\n"
            f"Danh mục: {product.category}\n"
            f"Mô tả: {product.description}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='list_products')]])
        )
        
        return ADMIN_MENU
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            f"Có lỗi xảy ra: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='list_products')]])
        )
        return EDIT_PRODUCT
    finally:
        session.close()

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị danh sách sản phẩm cho admin"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("Bạn không có quyền thực hiện chức năng này.")
        return MAIN_MENU

    query = update.callback_query
    await query.answer()
    
    session = get_session()
    try:
        # Lấy tất cả sản phẩm
        products = session.query(Product).all()
        
        if not products:
            await query.edit_message_text(
                "Chưa có sản phẩm nào. Hãy thêm sản phẩm mới!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_products')]])
            )
            return ADMIN_MENU
        
        # Tạo danh sách sản phẩm theo danh mục
        text = "*Danh sách sản phẩm:*\n\n"
        keyboard = []
        
        for product in products:
            status = "✅ Có sẵn" if product.is_available else "❌ Hết hàng"
            text += f"*{product.name}*\n"
            text += f"Giá: {product.price:,} VNĐ\n"
            text += f"Danh mục: {product.category}\n"
            text += f"Trạng thái: {status}\n"
            text += f"Mô tả: {product.description or 'Không có'}\n\n"
            
            # Thêm nút chỉnh sửa cho mỗi sản phẩm
            keyboard.append([InlineKeyboardButton(f"✏️ Chỉnh sửa {product.name}", callback_data=f'edit_product_{product.id}')])
        
        # Thêm nút quay lại
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_products')])
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    finally:
        session.close()
    
    return ADMIN_MENU

async def edit_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý chỉnh sửa tên sản phẩm"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[2])
    context.user_data['editing_product_id'] = product_id
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await query.edit_message_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        await query.edit_message_text(
            f"*Đang chỉnh sửa tên sản phẩm*\n\n"
            f"Tên hiện tại: *{product.name}*\n\n"
            f"Vui lòng nhập tên mới cho sản phẩm:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại thông tin sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT_NAME
    finally:
        session.close()

async def edit_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý chỉnh sửa giá sản phẩm"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[2])
    context.user_data['editing_product_id'] = product_id
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await query.edit_message_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        await query.edit_message_text(
            f"*Đang chỉnh sửa giá sản phẩm*\n\n"
            f"Sản phẩm: *{product.name}*\n"
            f"Giá hiện tại: *{product.price:,} VNĐ*\n\n"
            f"Vui lòng nhập giá mới (chỉ nhập số, không có dấu phẩy):",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại thông tin sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT_PRICE
    finally:
        session.close()

async def edit_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý chỉnh sửa danh mục sản phẩm"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[2])
    context.user_data['editing_product_id'] = product_id
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await query.edit_message_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        # Lấy danh sách các danh mục hiện có
        categories = session.query(Product.category).distinct().all()
        categories = [category[0] for category in categories]
        
        text = f"*Đang chỉnh sửa danh mục sản phẩm*\n\n"
        text += f"Sản phẩm: *{product.name}*\n"
        text += f"Danh mục hiện tại: *{product.category}*\n\n"
        text += f"Vui lòng nhập danh mục mới (hoặc chọn từ danh sách):"
        
        # Tạo keyboard với các danh mục hiện có
        keyboard = []
        for category in categories:
            if category != product.category:
                keyboard.append([InlineKeyboardButton(f"{category}", callback_data=f'set_category_{product_id}_{category}')])
        
        keyboard.append([InlineKeyboardButton("🔙 Quay lại thông tin sản phẩm", callback_data=f'edit_product_{product_id}')])
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDIT_PRODUCT_CATEGORY
    finally:
        session.close()

async def edit_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý chỉnh sửa mô tả sản phẩm"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[2])
    context.user_data['editing_product_id'] = product_id
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await query.edit_message_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        await query.edit_message_text(
            f"*Đang chỉnh sửa mô tả sản phẩm*\n\n"
            f"Sản phẩm: *{product.name}*\n"
            f"Mô tả hiện tại: *{product.description or 'Không có'}*\n\n"
            f"Vui lòng nhập mô tả mới cho sản phẩm:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại thông tin sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT_DESCRIPTION
    finally:
        session.close()

async def toggle_product_availability(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Đổi trạng thái sản phẩm (có sẵn/hết hàng)"""
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[2])
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await query.edit_message_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        # Đổi trạng thái sản phẩm
        product.is_available = not product.is_available
        session.commit()
        
        status = "✅ Có sẵn" if product.is_available else "❌ Hết hàng"
        await query.edit_message_text(
            f"✅ Đã đổi trạng thái sản phẩm *{product.name}* thành *{status}*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại thông tin sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT
    finally:
        session.close()

async def save_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lưu tên mới cho sản phẩm"""
    new_name = update.message.text
    product_id = context.user_data.get('editing_product_id')
    
    if not product_id:
        await update.message.reply_text(
            "Không tìm thấy thông tin sản phẩm cần chỉnh sửa!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
        )
        return ADMIN_MENU
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await update.message.reply_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        old_name = product.name
        product.name = new_name
        session.commit()
        
        await update.message.reply_text(
            f"✅ Đã cập nhật tên sản phẩm:\n\n"
            f"Tên cũ: *{old_name}*\n"
            f"Tên mới: *{new_name}*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            f"Có lỗi xảy ra: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Thử lại", callback_data=f'edit_name_{product_id}')]])
        )
        return EDIT_PRODUCT_NAME
    finally:
        session.close()

async def save_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lưu giá mới cho sản phẩm"""
    new_price_text = update.message.text
    product_id = context.user_data.get('editing_product_id')
    
    if not product_id:
        await update.message.reply_text(
            "Không tìm thấy thông tin sản phẩm cần chỉnh sửa!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
        )
        return ADMIN_MENU
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await update.message.reply_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        try:
            new_price = int(new_price_text)
            if new_price <= 0:
                raise ValueError("Giá phải là số dương")
        except ValueError:
            await update.message.reply_text(
                "❌ Giá sản phẩm phải là số dương!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Thử lại", callback_data=f'edit_price_{product_id}')],
                    [InlineKeyboardButton("🔙 Quay lại sản phẩm", callback_data=f'edit_product_{product_id}')]
                ])
            )
            return EDIT_PRODUCT_PRICE
        
        old_price = product.price
        product.price = new_price
        session.commit()
        
        await update.message.reply_text(
            f"✅ Đã cập nhật giá sản phẩm *{product.name}*:\n\n"
            f"Giá cũ: *{old_price:,} VNĐ*\n"
            f"Giá mới: *{new_price:,} VNĐ*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            f"Có lỗi xảy ra: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Thử lại", callback_data=f'edit_price_{product_id}')]])
        )
        return EDIT_PRODUCT_PRICE
    finally:
        session.close()

async def save_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lưu danh mục mới cho sản phẩm"""
    new_category = update.message.text
    product_id = context.user_data.get('editing_product_id')
    
    if not product_id:
        await update.message.reply_text(
            "Không tìm thấy thông tin sản phẩm cần chỉnh sửa!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
        )
        return ADMIN_MENU
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await update.message.reply_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        old_category = product.category
        product.category = new_category
        session.commit()
        
        await update.message.reply_text(
            f"✅ Đã cập nhật danh mục sản phẩm *{product.name}*:\n\n"
            f"Danh mục cũ: *{old_category}*\n"
            f"Danh mục mới: *{new_category}*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            f"Có lỗi xảy ra: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Thử lại", callback_data=f'edit_category_{product_id}')]])
        )
        return EDIT_PRODUCT_CATEGORY
    finally:
        session.close()

async def set_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Đặt danh mục từ danh sách có sẵn"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split('_')
    product_id = int(parts[2])
    new_category = parts[3]
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await query.edit_message_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        old_category = product.category
        product.category = new_category
        session.commit()
        
        await query.edit_message_text(
            f"✅ Đã cập nhật danh mục sản phẩm *{product.name}*:\n\n"
            f"Danh mục cũ: *{old_category}*\n"
            f"Danh mục mới: *{new_category}*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT
    except Exception as e:
        session.rollback()
        await query.edit_message_text(
            f"Có lỗi xảy ra: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Thử lại", callback_data=f'edit_category_{product_id}')]])
        )
        return EDIT_PRODUCT
    finally:
        session.close()

async def save_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lưu mô tả mới cho sản phẩm"""
    new_description = update.message.text
    product_id = context.user_data.get('editing_product_id')
    
    if not product_id:
        await update.message.reply_text(
            "Không tìm thấy thông tin sản phẩm cần chỉnh sửa!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
        )
        return ADMIN_MENU
    
    session = get_session()
    try:
        product = session.query(Product).get(product_id)
        if not product:
            await update.message.reply_text(
                "Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại danh sách", callback_data='list_products')]])
            )
            return ADMIN_MENU
        
        old_description = product.description or "Không có"
        product.description = new_description
        session.commit()
        
        await update.message.reply_text(
            f"✅ Đã cập nhật mô tả sản phẩm *{product.name}*:\n\n"
            f"Mô tả cũ: *{old_description}*\n"
            f"Mô tả mới: *{new_description}*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại sản phẩm", callback_data=f'edit_product_{product_id}')]])
        )
        return EDIT_PRODUCT
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            f"Có lỗi xảy ra: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Thử lại", callback_data=f'edit_description_{product_id}')]])
        )
        return EDIT_PRODUCT_DESCRIPTION
    finally:
        session.close()

async def show_category_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị các sản phẩm trong danh mục để đặt món"""
    query = update.callback_query
    await query.answer()
    
    # Lấy tên danh mục từ callback data hoặc từ context
    if query.data.startswith("order_cat_"):
        category = query.data.replace("order_cat_", "")
        # Lưu lại danh mục để sử dụng sau này
        context.user_data['last_category'] = category
    else:
        # Sử dụng danh mục đã lưu nếu có
        category = context.user_data.get('last_category', '')
    
    session = get_session()
    try:
        # Lấy sản phẩm theo danh mục
        products = session.query(Product).filter(
            Product.category == category,
            Product.is_available == True
        ).all()
        
        if not products:
            await query.edit_message_text(
                text=f"Không có sản phẩm nào trong danh mục {category}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='place_order')]])
            )
            return ORDER_ITEMS
        
        # Hiển thị sản phẩm và cho phép thêm vào giỏ hàng
        text = f"*Danh mục: {category}*\n\n"
        keyboard = []
        
        for product in products:
            text += f"*{product.name}* - _{product.price:,.0f} VNĐ_\n{product.description or 'Không có mô tả'}\n\n"
            # Thêm danh mục vào callback_data
            keyboard.append([InlineKeyboardButton(
                f"➕ Thêm {product.name}", 
                callback_data=f"add_item_{product.id}_{category}"
            )])
        
        # Hiển thị thông tin bàn đã chọn (nếu có)
        selected_table = context.user_data.get('selected_table')
        if selected_table:
            table_info = f"\n🪑 Đang đặt món cho: *Bàn {selected_table['number']}*"
            text += table_info
        
        keyboard.append([InlineKeyboardButton("🛒 Xem giỏ hàng", callback_data='view_cart')])
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='place_order')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ORDER_ITEMS
    finally:
        session.close()

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Thêm sản phẩm vào giỏ hàng"""
    query = update.callback_query
    await query.answer()
    
    # Lấy ID sản phẩm từ callback data
    product_id = int(query.data.split('_')[2])
    
    # Khởi tạo giỏ hàng nếu chưa có
    if 'cart' not in context.user_data:
        context.user_data['cart'] = []
    
    session = get_session()
    try:
        # Lấy thông tin sản phẩm
        product = session.query(Product).get(product_id)
        if not product:
            await query.edit_message_text(
                text="❌ Không tìm thấy sản phẩm!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='place_order')]])
            )
            return ORDER_ITEMS
        
        # Kiểm tra xem sản phẩm đã có trong giỏ hàng chưa
        for item in context.user_data['cart']:
            if item['product_id'] == product_id:
                # Tăng số lượng nếu đã có
                item['quantity'] += 1
                
                # Hiển thị thông báo thành công ngắn và tiếp tục ở trang hiện tại
                await query.answer(f"Đã thêm 1 {product.name} vào giỏ hàng! Tổng: {item['quantity']}")
                
                # Không chuyển trang, chỉ hiển thị thông báo
                category = query.data.split('_')[3] if len(query.data.split('_')) > 3 else None
                if category:
                    # Nếu có thông tin danh mục, trở lại danh mục đó
                    context.user_data['last_category'] = category
                    return await show_category_products(update, context)
                else:
                    # Nếu không, ở lại trang hiện tại
                    return ORDER_ITEMS
        
        # Thêm sản phẩm mới vào giỏ hàng
        context.user_data['cart'].append({
            'product_id': product_id,
            'product_name': product.name,
            'price': product.price,
            'quantity': 1
        })
        
        # Hiển thị thông báo thành công
        await query.answer(f"Đã thêm {product.name} vào giỏ hàng!")
        
        # Lưu lại danh mục hiện tại để quay lại
        category = query.data.split('_')[3] if len(query.data.split('_')) > 3 else None
        if category:
            context.user_data['last_category'] = category
            # Nếu có thông tin danh mục, trở lại danh mục đó
            return await show_category_products(update, context)
        
        # Nếu không có thông tin danh mục, hiển thị thông báo và giữ nguyên màn hình
        return ORDER_ITEMS
        
    except Exception as e:
        logger.error(f"Lỗi khi thêm vào giỏ hàng: {str(e)}")
        await query.answer(f"Lỗi: {str(e)}")
        return ORDER_ITEMS
    finally:
        session.close()

async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xem giỏ hàng"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra xem giỏ hàng có dữ liệu không
    cart = context.user_data.get('cart', [])
    if not cart:
        await query.edit_message_text(
            text="🛒 *Giỏ hàng của bạn đang trống!*\n\nHãy thêm sản phẩm vào giỏ hàng trước khi thanh toán.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🍽️ Đặt món", callback_data='place_order')]])
        )
        return ORDER_ITEMS
    
    # Thông tin bàn đã đặt (nếu có)
    selected_table = context.user_data.get('selected_table')
    table_info = ""
    if selected_table:
        table_info = f"🪑 *ĐƠN HÀNG CHO BÀN {selected_table['number']}*"
    else:
        table_info = "⚠️ *CHƯA CHỌN BÀN* - Vui lòng đặt bàn trước khi xác nhận!"
    
    # Hiển thị thông tin giỏ hàng
    text = f"{table_info}\n\n"
    text += "🛒 *Chi tiết giỏ hàng:*\n\n"
    total = 0
    
    for i, item in enumerate(cart):
        item_total = item['price'] * item['quantity']
        total += item_total
        text += f"{i + 1}. *{item['product_name']}*\n"
        text += f"   Số lượng: {item['quantity']} x {item['price']:,.0f} VNĐ = {item_total:,.0f} VNĐ\n\n"
    
    text += f"*Tổng cộng: {total:,.0f} VNĐ*"
    
    # Tạo các nút điều khiển
    keyboard = [
        [InlineKeyboardButton("✅ Xác nhận đặt món", callback_data='confirm_order')],
        [InlineKeyboardButton("🗑️ Xóa giỏ hàng", callback_data='clear_cart')],
        [InlineKeyboardButton("➕ Thêm món khác", callback_data='place_order')]
    ]
    
    # Nếu chưa đặt bàn, hiển thị nút đặt bàn nổi bật
    if not selected_table:
        keyboard.insert(0, [InlineKeyboardButton("⚠️ ĐẶT BÀN NGAY ⚠️", callback_data='reserve_table')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return CONFIRM_ORDER

async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xóa giỏ hàng"""
    query = update.callback_query
    await query.answer()
    
    # Xóa giỏ hàng
    context.user_data['cart'] = []
    
    await query.edit_message_text(
        text="✅ *Đã xóa giỏ hàng!*\n\nGiỏ hàng của bạn hiện đang trống.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🍽️ Đặt món", callback_data='place_order')],
            [InlineKeyboardButton("⬅️ Quay lại menu chính", callback_data='back_to_main')]
        ])
    )
    
    return ORDER_ITEMS

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xác nhận đặt món"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra xem giỏ hàng có dữ liệu không
    cart = context.user_data.get('cart', [])
    if not cart:
        await query.edit_message_text(
            text="❌ *Giỏ hàng của bạn đang trống!*\n\nHãy thêm sản phẩm vào giỏ hàng trước khi thanh toán.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🍽️ Đặt món", callback_data='place_order')]])
        )
        return ORDER_ITEMS
    
    # Lấy thông tin người dùng
    user = update.effective_user
    user_id = user.id
    username = user.username or f"{user.first_name} {user.last_name or ''}"
    
    # Lấy thông tin bàn (nếu có)
    selected_table = context.user_data.get('selected_table')
    table_number = selected_table['number'] if selected_table else None
    
    # Tính tổng tiền
    total_amount = sum(item['price'] * item['quantity'] for item in cart)
    
    # Chuẩn bị dữ liệu cho thông báo
    food_items = []
    drink_items = []
    other_items = []
    
    session = get_session()
    try:
        # Phân loại các món theo danh mục (đồ ăn, đồ uống) trước khi tạo đơn hàng
        for item in cart:
            product = session.query(Product).get(item['product_id'])
            if product:
                item_info = {
                    'name': product.name,
                    'quantity': item['quantity'],
                    'price': item['price'],
                    'category': product.category.lower() if product.category else ''
                }
                
                # Phân loại món theo danh mục
                category = item_info['category']
                if 'đồ uống' in category or 'nước' in category or 'cà phê' in category or 'cafe' in category or 'coffee' in category or 'tea' in category or 'trà' in category:
                    drink_items.append(item_info)
                elif 'đồ ăn' in category or 'món ăn' in category or 'bánh' in category or 'food' in category or 'cake' in category:
                    food_items.append(item_info)
                else:
                    other_items.append(item_info)
        
        # Tạo đơn hàng mới
        new_order = Order(
            user_id=user_id,
            username=username,
            status='pending',
            table_number=table_number,
            total_amount=total_amount
        )
        
        session.add(new_order)
        session.flush()  # Để lấy ID của đơn hàng mới
        
        # Thêm các sản phẩm vào đơn hàng
        for item in cart:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            session.add(order_item)
        
        # Lưu trữ ID đơn hàng trước khi commit
        order_id = new_order.id
        
        # Commit tất cả các thay đổi
        session.commit()
        
        # Gửi thông báo đến nhóm về đơn hàng mới
        user_name = f"{user.first_name} {user.last_name or ''}"
        user_role = get_role(user_id)
        role_text = "Admin" if user_role == "admin" else "Thu ngân" if user_role == "cashier" else "Nhân viên phục vụ"
        
        # Tạo danh sách món đã đặt
        items_text = ""
        for i, item in enumerate(cart, 1):
            item_total = item['price'] * item['quantity']
            items_text += f"{i}. {item['product_name']} - {item['quantity']} x {item['price']:,.0f}đ = {item_total:,.0f}đ\n"
        
        # Tạo thông báo riêng cho bếp
        kitchen_text = ""
        if food_items:
            kitchen_text += "🍳 *MÓN ĂN CHO BẾP:*\n"
            for i, item in enumerate(food_items, 1):
                kitchen_text += f"{i}. {item['name']} - *SL: {item['quantity']}*\n"
        
        # Tạo thông báo riêng cho quầy bar
        bar_text = ""
        if drink_items:
            bar_text += "🥤 *ĐỒ UỐNG CHO QUẦY BAR:*\n"
            for i, item in enumerate(drink_items, 1):
                bar_text += f"{i}. {item['name']} - *SL: {item['quantity']}*\n"
        
        # Tạo thông báo riêng cho các món khác
        other_text = ""
        if other_items:
            other_text += "📌 *CÁC MÓN KHÁC:*\n"
            for i, item in enumerate(other_items, 1):
                other_text += f"{i}. {item['name']} - *SL: {item['quantity']}*\n"
        
        notification_message = (
            f"🔔 *THÔNG BÁO CÓ KHÁCH ĐẶT MÓN*\n\n"
            f"🪑 Bàn: *{table_number if table_number else 'Chưa chọn bàn'}*\n"
            f"👤 Người phục vụ: *{user_name}* ({role_text})\n"
            f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
            f"📋 *CHI TIẾT ĐƠN HÀNG:*\n{items_text}\n"
        )
        
        if kitchen_text or bar_text or other_text:
            notification_message += "\n🧑‍🍳 *THÔNG BÁO CHO CÁC BỘ PHẬN:*\n"
            if kitchen_text:
                notification_message += f"\n{kitchen_text}"
            if bar_text:
                notification_message += f"\n{bar_text}"
            if other_text:
                notification_message += f"\n{other_text}"
        
        notification_message += f"\n💰 *Tổng tiền: {total_amount:,.0f}đ*\n\n"
        notification_message += "✅ Vui lòng các bộ phận chuẩn bị món theo yêu cầu!\n"
        
        # Tạo inline keyboard với các nút trạng thái
        order_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 ĐANG CHUẨN BỊ", callback_data=f"order_preparing_table_{table_number}_order_{order_id}")]
        ])
        
        # Gửi thông báo không đồng bộ để không làm chậm luồng chính
        msg = await send_group_notification(context, notification_message, reply_markup=order_keyboard)
        
        # Lưu thông tin người phục vụ cho đơn hàng này để gửi thông báo khi hoàn thành
        if 'orders_by_server' not in context.bot_data:
            context.bot_data['orders_by_server'] = {}
        context.bot_data['orders_by_server'][order_id] = user_id
        
        # Lưu thông tin đơn hàng mới thành công
        last_order_info = {
            'order_id': order_id,
            'table_number': table_number,
            'total_amount': total_amount,
            'items': [{'name': item['product_name'], 'quantity': item['quantity'], 'price': item['price']} for item in cart]
        }
        context.user_data['last_order_info'] = last_order_info
        
        # Xóa giỏ hàng sau khi đặt hàng thành công
        context.user_data['cart'] = []
        
        # Thông báo thành công
        text = "✅ *Đặt món thành công!*\n\n"
        text += f"Mã đơn hàng: *#{order_id}*\n"
        
        if table_number:
            text += f"Bàn: *Bàn {table_number}*\n"
        
        text += f"Tổng tiền: *{total_amount:,.0f} VNĐ*\n\n"
        text += "Đơn hàng của bạn đã được gửi đi và đang chờ xác nhận.\n"
        text += "Vui lòng đợi nhân viên phục vụ món ăn của bạn.\n\n"
        text += "Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi! 🙏"
        
        # Gửi trực tiếp tin nhắn xác nhận đến nhân viên phục vụ
        server_confirmation = (
            f"📋 *XÁC NHẬN ĐƠN HÀNG*\n\n"
            f"✅ Đơn hàng *#{order_id}* đã được xác nhận!\n\n"
            f"🪑 *Bàn {table_number}* đã đặt các món sau:\n\n"
        )
        
        # Chi tiết món ăn đã đặt
        if food_items:
            server_confirmation += "*🍽️ Món ăn:*\n"
            for i, item in enumerate(food_items, 1):
                server_confirmation += f"{i}. {item['name']} - SL: {item['quantity']}\n"
            server_confirmation += "\n"
            
        if drink_items:
            server_confirmation += "*🥤 Đồ uống:*\n"
            for i, item in enumerate(drink_items, 1):
                server_confirmation += f"{i}. {item['name']} - SL: {item['quantity']}\n"
            server_confirmation += "\n"
            
        if other_items:
            server_confirmation += "*🧁 Món khác:*\n"
            for i, item in enumerate(other_items, 1):
                server_confirmation += f"{i}. {item['name']} - SL: {item['quantity']}\n"
            server_confirmation += "\n"
        
        server_confirmation += f"💰 *Tổng tiền: {total_amount:,.0f} VNĐ*\n\n"
        server_confirmation += "🕒 Bạn sẽ nhận được thông báo khi nhà bếp đã chuẩn bị xong món."
        
        # Gửi tin nhắn xác nhận đến chính nhân viên đã đặt món
        await context.bot.send_message(
            chat_id=user_id,
            text=server_confirmation,
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🍽️ Đặt thêm món", callback_data='order_more')],
                [InlineKeyboardButton("📋 Xem menu", callback_data='view_menu')],
                [InlineKeyboardButton("⬅️ Quay lại menu chính", callback_data='back_to_main')]
            ])
        )
        
        return MAIN_MENU
    except Exception as e:
        session.rollback()
        await query.edit_message_text(
            text=f"❌ *Có lỗi xảy ra khi đặt món:*\n\n{str(e)}\n\nVui lòng thử lại sau.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Thử lại", callback_data='confirm_order')],
                [InlineKeyboardButton("⬅️ Quay lại", callback_data='view_cart')]
            ])
        )
        return CONFIRM_ORDER
    finally:
        session.close()

async def request_bill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị danh sách bàn đã đặt để yêu cầu xuất bill."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Ghi log hành động
    logger.info(f"Người dùng {user_id} yêu cầu xuất bill")
    
    # Lấy danh sách bàn có đơn hàng
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Chỉ lấy các bàn có đơn hàng chưa thanh toán
        cursor.execute("""
            SELECT DISTINCT t.id, t.name 
            FROM tables t
            JOIN orders o ON t.id = o.table_id
            WHERE o.status IN ('pending', 'confirmed', 'active')
            ORDER BY t.name
        """)
        tables = cursor.fetchall()
        conn.close()
        
        if not tables:
            await query.edit_message_text(
                text="Không có bàn nào cần xuất bill.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")]
                ])
            )
            return get_appropriate_menu_state(user_id)
        
        # Tạo danh sách bàn để chọn
        keyboard = []
        for table_id, table_name in tables:
            keyboard.append([InlineKeyboardButton(
                f"🪑 {table_name}", callback_data=f"bill_for_table_{table_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")])
        
        await query.edit_message_text(
            text="Chọn bàn để xem và yêu cầu xuất bill:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return SELECTING_BILL_TABLE
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bàn: {str(e)}")
        await query.edit_message_text(
            text=f"Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")]
            ])
        )
        return get_appropriate_menu_state(user_id)

async def show_table_bill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị chi tiết hóa đơn của một bàn cụ thể."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Xác nhận callback query để Telegram không hiển thị "loading..."
    await query.answer()
    
    # Lấy ID bàn từ callback data
    callback_data = query.data
    logger.info(f"Callback data nhận được: {callback_data}")
    
    # Xử lý các định dạng callback data
    if callback_data.startswith("bill_for_table_"):
        table_id = int(callback_data.split("_")[-1])
    elif callback_data.startswith("bill_for_table:"):
        table_id = int(callback_data.split(":")[-1])
    else:
        logger.error(f"Định dạng callback data không hợp lệ: {callback_data}")
        await query.edit_message_text(
            text="❌ Có lỗi xảy ra khi xử lý yêu cầu. Vui lòng thử lại.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
            ]])
        )
        return BILL_ACTIONS
    
    # Log thông tin bàn được chọn
    logger.info(f"Hiển thị bill cho bàn có ID: {table_id}")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy thông tin bàn
        cursor.execute("SELECT name FROM tables WHERE id = ?", (table_id,))
        table_result = cursor.fetchone()
        if not table_result:
            await query.edit_message_text(
                text="Không tìm thấy thông tin bàn.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")]
                ])
            )
            return get_appropriate_menu_state(user_id)
            
        table_name = table_result[0]
        
        # Lấy thông tin các món đã đặt
        cursor.execute("""
            SELECT p.name, o.quantity, p.price, (o.quantity * p.price) as item_total
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.table_id = ? AND o.status IN ('pending', 'confirmed', 'active')
            ORDER BY p.name
        """, (table_id,))
        
        items = cursor.fetchall()
        if not items:
            await query.edit_message_text(
                text=f"Bàn {table_name} không có món nào cần thanh toán.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")]
                ])
            )
            return get_appropriate_menu_state(user_id)
        
        # Tính tổng tiền
        total_amount = sum(item[3] for item in items)
        
        # Tạo nội dung bill
        bill_text = f"🧾 *BILL BÀN {table_name}*\n\n"
        bill_text += "📋 *Chi tiết đơn hàng:*\n"
        
        for i, (product_name, quantity, price, item_total) in enumerate(items, 1):
            bill_text += f"{i}. {product_name}\n"
            bill_text += f"   {quantity} x {price:,.0f}đ = {item_total:,.0f}đ\n"
        
        bill_text += f"\n💰 *Tổng cộng: {total_amount:,.0f}đ*"
        
        # Thêm các thông tin khác nếu cần
        bill_text += f"\n\n⏰ Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        
        # Hiển thị bill và các nút tùy chọn
        keyboard = [
            [InlineKeyboardButton("📱 Gửi bill vào nhóm", callback_data=f"send_bill_to_group_{table_id}")],
            [InlineKeyboardButton("💰 Thanh toán", callback_data=f"process_payment_{table_id}")],
            [InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")]
        ]
        
        # Lưu thông tin bill vào context để sử dụng khi gửi bill hoặc thanh toán
        context.user_data['current_bill'] = {
            'table_id': table_id,
            'table_name': table_name,
            'items': items,
            'total_amount': total_amount,
            'bill_text': bill_text
        }
        
        await query.edit_message_text(
            text=bill_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return BILL_ACTIONS
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị bill: {str(e)}")
        await query.edit_message_text(
            text=f"Đã xảy ra lỗi khi hiển thị bill: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")]
            ])
        )
        return get_appropriate_menu_state(user_id)
    finally:
        conn.close()

async def send_group_notification(context: ContextTypes.DEFAULT_TYPE, message: str, reply_markup=None, parse_mode: str = 'Markdown') -> bool:
    """Gửi thông báo vào nhóm Telegram"""
    if not GROUP_CHAT_ID:
        logger.warning("Không thể gửi thông báo vào nhóm: GROUP_CHAT_ID chưa được cấu hình")
        return False
        
    try:
        message_obj = await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=message,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        logger.info(f"Đã gửi thông báo đến nhóm {GROUP_CHAT_ID}")
        return message_obj  # Trả về đối tượng message để có thể sử dụng sau này
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo đến nhóm: {str(e)}")
        return False

async def send_bill_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Gửi thông tin bill vào nhóm Telegram"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Xác nhận callback query
    await query.answer()
    
    # Lấy ID bàn từ callback data
    # Sửa lại cách xử lý callback_data để tương thích với pattern đã định nghĩa
    callback_data = query.data
    if '_' in callback_data:
        # Pattern hiện tại: 'send_bill_to_group_123'
        table_id = int(callback_data.split("_")[-1])
    else:
        # Callback data có thể có định dạng khác
        logger.error(f"Định dạng callback data không hợp lệ: {callback_data}")
        await query.edit_message_text(
            text="❌ Có lỗi xảy ra khi xử lý yêu cầu. Vui lòng thử lại.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
            ]])
        )
        return BILL_ACTIONS
    
    # Lấy thông tin bill từ context
    bill_info = context.user_data.get('current_bill', {})
    if not bill_info or bill_info.get('table_id') != table_id:
        # Nếu không có thông tin bill hoặc ID bàn không khớp, quay lại hiển thị bill
        return await show_table_bill(update, context)
    
    try:
        # Lấy thông tin cần thiết
        table_name = bill_info.get('table_name', f"Bàn {table_id}")
        bill_text = bill_info.get('bill_text', "Không có thông tin chi tiết")
        total_amount = bill_info.get('total_amount', 0)
        
        # Tạo thông báo cho nhóm với emoji và định dạng rõ ràng hơn
        group_message = f"📢 *THÔNG BÁO YÊU CẦU XUẤT BILL*\n\n"
        group_message += f"🪑 *Bàn {table_name}* yêu cầu thanh toán\n"
        group_message += f"👤 Người phục vụ: {update.effective_user.first_name} {update.effective_user.last_name or ''}\n"
        group_message += f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
        group_message += bill_text
        
        group_message += f"\n\n⚡ Đề nghị thu ngân kiểm tra và tiến hành thanh toán cho khách!"
        
        # Gửi thông báo vào nhóm
        success = await send_group_notification(context, group_message)
        
        # Hiển thị kết quả cho người dùng
        if success:
            await query.edit_message_text(
                text=f"✅ Đã gửi bill cho Bàn {table_name} vào nhóm Telegram thành công!\n\n"
                    f"Tổng tiền: {total_amount:,.0f} VNĐ",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data=f"bill_for_table_{table_id}")
                ]]),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                text=f"⚠️ Không thể gửi bill vào nhóm Telegram.\n"
                    f"Vui lòng kiểm tra cấu hình GROUP_CHAT_ID ({GROUP_CHAT_ID}) hoặc quản trị viên về quyền của bot trong nhóm.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data=f"bill_for_table_{table_id}")
                ]]),
                parse_mode='Markdown'
            )
        
        return BILL_ACTIONS
    except Exception as e:
        logger.error(f"Lỗi khi gửi bill vào nhóm: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi khi gửi bill vào nhóm: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Quay lại", callback_data=f"bill_for_table_{table_id}")
            ]]),
            parse_mode='Markdown'
        )
        return BILL_ACTIONS

async def view_bills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị danh sách các bàn cần thanh toán."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Xác nhận callback query
    await query.answer()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy danh sách bàn có đơn hàng cần thanh toán
        cursor.execute("""
            SELECT t.id, t.name, 
                  (SELECT SUM(o.quantity * p.price) 
                   FROM orders o 
                   JOIN products p ON o.product_id = p.id 
                   WHERE o.table_id = t.id AND o.status IN ('pending', 'confirmed')) as total_amount
            FROM tables t
            WHERE t.id IN (
                SELECT DISTINCT table_id FROM orders WHERE status IN ('pending', 'confirmed')
            )
            ORDER BY t.name
        """)
        tables = cursor.fetchall()
        
        if not tables:
            await query.edit_message_text(
                text="Không có bàn nào cần thanh toán.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")
                ]])
            )
            return get_appropriate_menu_state(user_id)
        
        # Tạo danh sách các bàn cần thanh toán
        message_text = "📋 *DANH SÁCH BÀN CẦN THANH TOÁN*\n\n"
        
        keyboard = []
        for table_id, table_name, total_amount in tables:
            # Bỏ qua các bàn không có đơn hàng
            if total_amount is None:
                continue
                
            message_text += f"• Bàn {table_name}: {format_currency(total_amount)}\n"
            keyboard.append([InlineKeyboardButton(
                f"Xem bill Bàn {table_name}", callback_data=f"bill_for_table_{table_id}"
            )])
        
        # Thêm nút quay lại
        keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")])
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        return SELECTING_BILL_TABLE
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị danh sách bill: {str(e)}")
        await query.edit_message_text(
            text=f"Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Quay lại", callback_data="back_to_main")
            ]])
        )
        return get_appropriate_menu_state(user_id)
    finally:
        conn.close()

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý thanh toán cho một bàn."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Xác nhận callback query
    await query.answer()
    
    # Kiểm tra quyền truy cập - chỉ Admin và Thu ngân có thể thanh toán
    if not (is_admin(user_id) or is_cashier(user_id)):
        await query.edit_message_text(
            text="⛔ Chỉ Admin và Thu ngân mới có quyền xử lý thanh toán.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")]
            ])
        )
        return BILL_ACTIONS
    
    # Lấy ID bàn từ callback data
    callback_data = query.data
    logger.info(f"Callback process_payment nhận được: {callback_data}")
    
    try:
        if callback_data.startswith("process_payment_"):
            table_id = int(callback_data.split("_")[-1])
        else:
            logger.error(f"Định dạng callback data không hợp lệ: {callback_data}")
            await query.edit_message_text(
                text="❌ Có lỗi xảy ra khi xử lý yêu cầu thanh toán. Vui lòng thử lại.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
                ]])
            )
            return BILL_ACTIONS
            
        # Lấy thông tin bill từ context
        bill_info = context.user_data.get('current_bill', {})
        
        # Nếu không có thông tin bill hoặc ID bàn không khớp, quay lại hiển thị bill
        if not bill_info or bill_info.get('table_id') != table_id:
            await query.edit_message_text(
                text="❌ Không tìm thấy thông tin hóa đơn cho bàn này hoặc thông tin đã hết hạn.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
                ]])
            )
            return BILL_ACTIONS
        
        # Lấy thông tin bàn
        table_name = bill_info.get('table_name', f"Bàn {table_id}")
        total_amount = bill_info.get('total_amount', 0)
        items = bill_info.get('items', [])
        
        # Tạo hóa đơn chi tiết cho bàn
        bill_text = f"*HÓA ĐƠN BÀN {table_name}*\n\n"
        bill_text += f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
        bill_text += f"👤 Thu ngân: {update.effective_user.first_name}\n\n"
        
        # Tổng hợp tất cả các mục từ tất cả các đơn hàng
        items_text = ""
        
        # Kiểm tra xem items là list hay tuple
        if items and isinstance(items[0], tuple):
            # Format từ tuple (tên, số lượng, giá, tổng tiền)
            for i, (product_name, quantity, price, item_total) in enumerate(items, 1):
                items_text += f"{i}. {product_name}: {quantity} x {price:,.0f}đ = {item_total:,.0f}đ\n"
        else:
            # Format từ dict
            for i, item in enumerate(items, 1):
                items_text += f"{i}. {item['name']}: {item['quantity']} x {item['price']:,.0f}đ = {item['quantity'] * item['price']:,.0f}đ\n"
        
        bill_text += "*CHI TIẾT SẢN PHẨM:*\n"
        bill_text += items_text
        
        bill_text += f"\n💰 *Tổng tiền: {total_amount:,.0f}đ*\n\n"
        bill_text += "✅ Bạn có muốn xác nhận thanh toán cho bàn này không?"
        
        # Tạo bàn phím với nút xác nhận thanh toán
        keyboard = [
            [InlineKeyboardButton("✅ XÁC NHẬN THANH TOÁN", callback_data=f"confirm_pay_table_{table_id}")],
            [InlineKeyboardButton("❌ HỦY", callback_data=f"bill_for_table_{table_id}")]
        ]
        
        await query.edit_message_text(
            text=bill_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return BILL_ACTIONS
    except Exception as e:
        logger.error(f"Lỗi khi xử lý thanh toán: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi khi xử lý thanh toán: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
            ]])
        )
        return BILL_ACTIONS

async def confirm_pay_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xác nhận thanh toán và giải phóng bàn"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    # Chỉ cho phép Admin và Thu ngân truy cập
    if not (is_admin(user_id) or is_cashier(user_id)):
        await query.edit_message_text(
            text="⛔ Chỉ Admin và Thu ngân mới có quyền thanh toán.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return MAIN_MENU
    
    # Lấy số bàn từ callback data
    callback_data = query.data
    logger.info(f"Callback confirm_pay_table nhận được: {callback_data}")
    
    try:
        if callback_data.startswith("confirm_pay_table_"):
            table_id = int(callback_data.split("_")[-1])
        else:
            logger.error(f"Định dạng callback data không hợp lệ: {callback_data}")
            await query.edit_message_text(
                text="❌ Có lỗi xảy ra khi xử lý yêu cầu thanh toán. Vui lòng thử lại.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
                ]])
            )
            return BILL_ACTIONS
        
        # Lấy thông tin bill từ context
        bill_info = context.user_data.get('current_bill', {})
        
        # Nếu không có thông tin bill hoặc ID bàn không khớp, quay lại hiển thị bill
        if not bill_info or bill_info.get('table_id') != table_id:
            await query.edit_message_text(
                text="❌ Không tìm thấy thông tin hóa đơn cho bàn này hoặc thông tin đã hết hạn.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
                ]])
            )
            return BILL_ACTIONS
            
        # Kết nối database
        conn = get_db_connection()
        try:
            # Bắt đầu transaction
            conn.execute("BEGIN TRANSACTION")
            cursor = conn.cursor()
            
            # Lấy thông tin bàn
            table_name = bill_info.get('table_name', f"Bàn {table_id}")
            items = bill_info.get('items', [])
            total_amount = bill_info.get('total_amount', 0)
            
            # Cập nhật trạng thái đơn hàng thành 'completed' (đã thanh toán)
            cursor.execute("""
                UPDATE orders
                SET status = 'completed', payment_time = ?
                WHERE table_id = ? AND status IN ('pending', 'confirmed', 'active')
            """, (datetime.now().isoformat(), table_id))
            
            # Kiểm tra số lượng row đã cập nhật
            rows_updated = cursor.rowcount
            logger.info(f"Đã cập nhật {rows_updated} đơn hàng cho bàn {table_id}")
            
            if rows_updated == 0:
                # Nếu không có đơn hàng nào được cập nhật, có thể đã được thanh toán trước đó
                logger.warning(f"Không có đơn hàng nào được cập nhật khi thanh toán cho bàn {table_id}")
                
                # Kiểm tra xem có đơn hàng nào đã hoàn thành trước đó không
                cursor.execute("""
                    SELECT COUNT(*) FROM orders 
                    WHERE table_id = ? AND status = 'completed'
                """, (table_id,))
                completed_count = cursor.fetchone()[0]
                
                if completed_count > 0:
                    await query.edit_message_text(
                        text=f"⚠️ Đơn hàng cho {table_name} đã được thanh toán trước đó!",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
                        ]]),
                        parse_mode='Markdown'
                    )
                    conn.rollback()
                    return BILL_ACTIONS
            
            # Đặt lại trạng thái bàn thành "trống"
            cursor.execute("""
                UPDATE tables SET is_reserved = 0 WHERE id = ?
            """, (table_id,))
            
            # Commit transaction
            conn.commit()
            
            # Xóa thông tin bill từ context vì đã thanh toán xong
            if 'current_bill' in context.user_data:
                del context.user_data['current_bill']
            
            # Gửi thông báo đến nhóm về việc thanh toán
            if items:
                user = update.effective_user
                user_name = f"{user.first_name} {user.last_name or ''}"
                user_role = get_role(user_id)
                role_text = "Admin" if user_role == "admin" else "Thu ngân" if user_role == "cashier" else "Nhân viên phục vụ"
                
                # Tạo danh sách món đã thanh toán
                items_text = ""
                
                # Kiểm tra xem items là list hay tuple
                if items and isinstance(items[0], tuple):
                    # Format từ tuple (tên, số lượng, giá, tổng tiền)
                    for i, (product_name, quantity, price, item_total) in enumerate(items, 1):
                        items_text += f"{i}. {product_name}: {quantity} x {price:,.0f}đ = {item_total:,.0f}đ\n"
                else:
                    # Format từ dict
                    for i, item in enumerate(items, 1):
                        items_text += f"{i}. {item['name']}: {item['quantity']} x {item['price']:,.0f}đ = {item['quantity'] * item['price']:,.0f}đ\n"
                
                notification_message = (
                    f"💰 *THÔNG BÁO HOÀN TẤT THANH TOÁN*\n\n"
                    f"🪑 Bàn: *{table_name}*\n"
                    f"👤 Thu ngân: *{user_name}* ({role_text})\n"
                    f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
                    f"📋 *Chi tiết hóa đơn:*\n{items_text}\n"
                    f"💰 *Tổng tiền: {total_amount:,.0f}đ*\n\n"
                    f"✅ *Khách đã thanh toán và rời đi.*\n"
                    f"✅ Bàn đã được giải phóng và sẵn sàng phục vụ khách mới."
                )
                
                # Gửi thông báo không đồng bộ để không làm chậm luồng chính
                asyncio.create_task(send_group_notification(context, notification_message))
            
            # Hiển thị thông báo thành công
            await query.edit_message_text(
                text=f"✅ *Thanh toán thành công!*\n\n"
                    f"Bàn: *{table_name}*\n"
                    f"Tổng tiền: *{total_amount:,.0f}đ*\n\n"
                    f"Bàn đã được đặt lại trạng thái trống và sẵn sàng phục vụ khách mới.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại menu", callback_data="back_to_main")
                ]]),
                parse_mode='Markdown'
            )
            
            return get_appropriate_menu_state(user_id)
        except Exception as e:
            # Rollback transaction nếu có lỗi
            if conn:
                conn.rollback()
            logger.error(f"Lỗi khi thanh toán: {str(e)}")
            
            await query.edit_message_text(
                text=f"❌ Đã xảy ra lỗi khi thanh toán: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
                ]]),
                parse_mode='Markdown'
            )
            return BILL_ACTIONS
        finally:
            if conn:
                conn.close()
    except Exception as e:
        logger.error(f"Lỗi khi xử lý thanh toán: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi khi xử lý thanh toán: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Quay lại", callback_data="request_bill")
            ]]),
            parse_mode='Markdown'
        )
        return BILL_ACTIONS

async def unreserve_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hủy đặt bàn"""
    if not is_admin(update.effective_user.id) and not is_cashier(update.effective_user.id):
        await update.callback_query.answer("Bạn không có quyền thực hiện chức năng này.")
        return MAIN_MENU

    query = update.callback_query
    await query.answer()
    
    # Lấy ID bàn từ callback data
    table_id = int(query.data.split('_')[1])
    
    session = get_session()
    try:
        table = session.query(Table).get(table_id)
        if not table:
            await query.edit_message_text(
                text="❌ Không tìm thấy bàn này!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
            )
            return ADMIN_MENU
        
        # Hủy đặt bàn
        table.is_reserved = False
        session.commit()
        
        # Gửi thông báo đến nhóm
        user = update.effective_user
        user_name = f"{user.first_name} {user.last_name or ''}"
        user_role = get_role(user.id)
        role_text = "Admin" if user_role == "admin" else "Thu ngân" if user_role == "cashier" else "Nhân viên phục vụ"
        
        notification_message = (
            f"🪑 *THÔNG BÁO HỦY ĐẶT BÀN*\n\n"
            f"Bàn *{table.number}* ({table.capacity} chỗ) vừa được hủy đặt\n"
            f"👤 Người hủy: *{user_name}* ({role_text})\n"
            f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        )
        
        # Gửi thông báo không đồng bộ để không làm chậm luồng chính
        asyncio.create_task(send_group_notification(context, notification_message))
        
        # Hiển thị thông báo thành công và quay lại quản lý bàn
        await query.edit_message_text(
            text=f"✅ *Đã hủy đặt Bàn {table.number} thành công!*\n\nBàn này đã được đặt về trạng thái trống.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại quản lý bàn", callback_data='manage_tables')]])
        )
        
        return ADMIN_MENU
    except Exception as e:
        session.rollback()
        await query.edit_message_text(
            text=f"❌ Có lỗi xảy ra khi hủy đặt bàn: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Thử lại", callback_data='manage_tables')]])
        )
        return ADMIN_MENU
    finally:
        session.close()

async def reset_all_tables(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset tất cả bàn về trạng thái trống"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("Chỉ Admin mới có quyền reset tất cả các bàn.")
        return ADMIN_MENU

    query = update.callback_query
    await query.answer()
    
    # Hiện thông báo xác nhận trước khi reset
    await query.edit_message_text(
        text="⚠️ *Xác nhận reset tất cả bàn*\n\n"
             "Hành động này sẽ đặt tất cả các bàn về trạng thái trống.\n"
             "Bạn có chắc chắn muốn tiếp tục không?",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Xác nhận reset tất cả", callback_data='confirm_reset_tables')],
            [InlineKeyboardButton("❌ Hủy", callback_data='manage_tables')]
        ])
    )
    
    return MANAGE_TABLES

async def confirm_reset_tables(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xác nhận và thực hiện reset tất cả các bàn"""
    if not is_admin(update.effective_user.id):
        await update.callback_query.answer("Chỉ Admin mới có quyền reset tất cả các bàn.")
        return ADMIN_MENU

    query = update.callback_query
    await query.answer()
    
    conn = get_db_connection()
    try:
        # Reset tất cả bàn về trạng thái trống
        cursor = conn.cursor()
        cursor.execute("UPDATE tables SET is_reserved = 0")
        reset_count = cursor.rowcount
        conn.commit()
        
        # Gửi thông báo đến nhóm
        user = update.effective_user
        user_name = f"{user.first_name} {user.last_name or ''}"
        
        if reset_count > 0:
            notification_message = (
                f"🔄 *THÔNG BÁO RESET BÀN*\n\n"
                f"Admin *{user_name}* vừa reset {reset_count} bàn về trạng thái trống\n"
                f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
            )
            
            # Gửi thông báo không đồng bộ để không làm chậm luồng chính
            asyncio.create_task(send_group_notification(context, notification_message))
        
        # Hiển thị thông báo thành công và quay lại quản lý bàn
        message = f"✅ *Reset bàn thành công!*\n\n"
        
        if reset_count > 0:
            message += f"Đã reset {reset_count} bàn về trạng thái trống."
        else:
            message += "Tất cả các bàn đã ở trạng thái trống."
        
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Quay lại Quản lý bàn", callback_data="manage_tables")]
            ]),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi reset bàn: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi khi reset bàn: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Quay lại", callback_data="manage_tables")]
            ])
        )
        return MANAGE_TABLES
    finally:
        if conn:
            conn.close()

async def edit_table_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị giao diện chỉnh sửa thông tin bàn"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Chỉ Admin mới có quyền chỉnh sửa thông tin bàn.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    
    # Lấy danh sách bàn từ database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, capacity, is_reserved FROM tables ORDER BY name")
        tables = cursor.fetchall()
        
        if not tables:
            await query.edit_message_text(
                text="❌ Không có bàn nào trong hệ thống.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
            )
            return MANAGE_TABLES
        
        # Hiển thị danh sách bàn để chọn
        message_text = "*CHỈNH SỬA THÔNG TIN BÀN*\n\nChọn bàn cần chỉnh sửa:\n"
        
        # Tạo các nút cho từng bàn
        keyboard = []
        for table_id, table_name, capacity, is_reserved in tables:
            status = "🔴 Đã đặt" if is_reserved else "🟢 Trống"
            keyboard.append([InlineKeyboardButton(
                f"{table_name} - {capacity} chỗ - {status}",
                callback_data=f"edit_table_{table_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')])
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bàn: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def edit_table_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị giao diện chỉnh sửa sức chứa của bàn"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Chỉ Admin mới có quyền chỉnh sửa thông tin bàn.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    
    # Lấy ID bàn từ callback data
    table_id = int(query.data.split("_")[2])
    
    # Lấy thông tin bàn
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, capacity FROM tables WHERE id = ?", (table_id,))
        table = cursor.fetchone()
        
        if not table:
            await query.edit_message_text(
                text="❌ Không tìm thấy thông tin bàn.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='edit_table_info')]])
            )
            return MANAGE_TABLES
        
        table_name, current_capacity = table
        
        # Hiển thị giao diện chỉnh sửa sức chứa
        message_text = f"*CHỈNH SỬA SỨC CHỨA*\n\n"
        message_text += f"Bàn: *{table_name}*\n"
        message_text += f"Sức chứa hiện tại: *{current_capacity}* người\n\n"
        message_text += "Chọn sức chứa mới:"
        
        # Tạo các nút cho các mức sức chứa phổ biến
        keyboard = []
        for capacity in [2, 4, 6, 8, 10, 12]:
            if capacity != current_capacity:
                keyboard.append([InlineKeyboardButton(
                    f"{capacity} người", 
                    callback_data=f"update_table_{table_id}_{capacity}"
                )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='edit_table_info')])
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi lấy thông tin bàn: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='edit_table_info')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def update_table_capacity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cập nhật sức chứa của bàn"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Chỉ Admin mới có quyền cập nhật thông tin bàn.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    
    # Lấy thông tin từ callback data
    # Format: update_table_<id>_<capacity>
    parts = query.data.split("_")
    table_id = int(parts[2])
    new_capacity = int(parts[3])
    
    # Cập nhật sức chứa trong database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM tables WHERE id = ?", (table_id,))
        table_result = cursor.fetchone()
        
        if not table_result:
            await query.edit_message_text(
                text="❌ Không tìm thấy thông tin bàn.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='edit_table_info')]])
            )
            return MANAGE_TABLES
        
        table_name = table_result[0]
        
        # Cập nhật sức chứa
        cursor.execute("UPDATE tables SET capacity = ? WHERE id = ?", (new_capacity, table_id))
        conn.commit()
        
        # Gửi thông báo đến nhóm
        user = update.effective_user
        user_name = f"{user.first_name} {user.last_name or ''}"
        
        notification_message = (
            f"✏️ *THÔNG BÁO CẬP NHẬT BÀN*\n\n"
            f"Admin *{user_name}* vừa cập nhật sức chứa của {table_name} thành {new_capacity} chỗ ngồi\n"
            f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        )
        
        # Gửi thông báo không đồng bộ để không làm chậm luồng chính
        asyncio.create_task(send_group_notification(context, notification_message))
        
        # Hiển thị thông báo thành công
        await query.edit_message_text(
            text=f"✅ *Cập nhật thành công!*\n\n"
                f"Đã thay đổi sức chứa của {table_name} thành {new_capacity} người.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Quay lại danh sách bàn", callback_data='edit_table_info')],
                [InlineKeyboardButton("⬅️ Quay lại quản lý bàn", callback_data='manage_tables')]
            ]),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật sức chứa bàn: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='edit_table_info')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def delete_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị giao diện xóa bàn"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Chỉ Admin mới có quyền xóa bàn.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    
    # Lấy danh sách bàn từ database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy tất cả các bàn cùng với thông tin đơn hàng để biết bàn nào đang có đơn
        cursor.execute("""
            SELECT t.id, t.name, t.capacity, t.is_reserved,
                   (SELECT COUNT(*) FROM orders o WHERE o.table_id = t.id AND o.status != 'completed') as order_count
            FROM tables t
            ORDER BY t.name
        """)
        tables = cursor.fetchall()
        
        if not tables:
            await query.edit_message_text(
                text="❌ Không có bàn nào trong hệ thống.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
            )
            return MANAGE_TABLES
        
        # Hiển thị danh sách bàn để chọn
        message_text = "*XÓA BÀN*\n\n"
        message_text += "⚠️ *Lưu ý:* Chỉ có thể xóa bàn trống và không có đơn hàng.\n\n"
        message_text += "Chọn bàn cần xóa:\n"
        
        # Tạo các nút cho từng bàn
        keyboard = []
        for table_id, table_name, capacity, is_reserved, order_count in tables:
            # Kiểm tra xem bàn có thể xóa không (phải trống và không có đơn hàng)
            can_delete = not is_reserved and order_count == 0
            
            if can_delete:
                status = "🟢 Có thể xóa"
                keyboard.append([InlineKeyboardButton(
                    f"{table_name} - {capacity} chỗ - {status}",
                    callback_data=f"pre_confirm_delete_table_{table_id}"
                )])
            else:
                if is_reserved:
                    status = "🔴 Đã đặt"
                elif order_count > 0:
                    status = "🔴 Có đơn hàng"
                
                # Bàn không thể xóa, nhưng vẫn hiển thị để người dùng biết
                keyboard.append([InlineKeyboardButton(
                    f"{table_name} - {capacity} chỗ - {status}",
                    callback_data=f"table_cannot_delete_{table_id}"
                )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')])
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách bàn: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def pre_confirm_delete_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị xác nhận trước khi xóa bàn"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Chỉ Admin mới có quyền xóa bàn.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    
    # Lấy ID bàn từ callback data
    table_id = int(query.data.split("_")[3])
    
    # Lấy thông tin bàn
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, capacity, is_reserved FROM tables WHERE id = ?", (table_id,))
        table = cursor.fetchone()
        
        if not table:
            await query.edit_message_text(
                text="❌ Không tìm thấy thông tin bàn.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='delete_table')]])
            )
            return MANAGE_TABLES
        
        table_name, capacity, is_reserved = table
        
        # Kiểm tra xem bàn có đơn hàng không
        cursor.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE table_id = ? AND status != 'completed'
        """, (table_id,))
        order_count = cursor.fetchone()[0]
        
        # Kiểm tra điều kiện xóa
        if is_reserved:
            await query.edit_message_text(
                text=f"❌ Không thể xóa {table_name} vì đang được đặt.\n\nHãy đổi trạng thái bàn về trống trước khi xóa.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='delete_table')]])
            )
            return MANAGE_TABLES
        
        if order_count > 0:
            await query.edit_message_text(
                text=f"❌ Không thể xóa {table_name} vì có {order_count} đơn hàng chưa hoàn tất.\n\nHãy xử lý tất cả đơn hàng trước khi xóa bàn.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='delete_table')]])
            )
            return MANAGE_TABLES
        
        # Hiển thị thông báo xác nhận
        await query.edit_message_text(
            text=f"⚠️ *Xác nhận xóa bàn*\n\n"
                f"Bạn có chắc chắn muốn xóa *{table_name}* ({capacity} chỗ ngồi) khỏi hệ thống không?\n\n"
                f"Hành động này không thể khôi phục!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Xác nhận xóa", callback_data=f"confirm_delete_table_{table_id}")],
                [InlineKeyboardButton("❌ Hủy", callback_data="delete_table")]
            ]),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi chuẩn bị xóa bàn: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='delete_table')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def confirm_delete_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xác nhận và thực hiện xóa bàn"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra quyền admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Chỉ Admin mới có quyền xóa bàn.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    
    # Lấy ID bàn từ callback data
    table_id = int(query.data.split("_")[3])
    
    # Xóa bàn từ database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy thông tin bàn trước khi xóa để thông báo
        cursor.execute("SELECT name FROM tables WHERE id = ?", (table_id,))
        table = cursor.fetchone()
        
        if not table:
            await query.edit_message_text(
                text="❌ Không tìm thấy thông tin bàn.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='delete_table')]])
            )
            return MANAGE_TABLES
        
        table_name = table[0]
        
        # Kiểm tra lần cuối xem bàn có thỏa điều kiện xóa không
        cursor.execute("SELECT is_reserved FROM tables WHERE id = ?", (table_id,))
        is_reserved = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM orders 
            WHERE table_id = ? AND status != 'completed'
        """, (table_id,))
        order_count = cursor.fetchone()[0]
        
        if is_reserved or order_count > 0:
            await query.edit_message_text(
                text=f"❌ Không thể xóa {table_name}.\n\n"
                    f"Bàn đang được đặt hoặc có đơn hàng chưa hoàn tất.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='delete_table')]])
            )
            return MANAGE_TABLES
        
        # Xóa bàn
        cursor.execute("DELETE FROM tables WHERE id = ?", (table_id,))
        conn.commit()
        
        # Gửi thông báo đến nhóm
        user = update.effective_user
        user_name = f"{user.first_name} {user.last_name or ''}"
        
        notification_message = (
            f"🗑️ *THÔNG BÁO XÓA BÀN*\n\n"
            f"Admin *{user_name}* vừa xóa {table_name} khỏi hệ thống\n"
            f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
        )
        
        # Gửi thông báo không đồng bộ để không làm chậm luồng chính
        asyncio.create_task(send_group_notification(context, notification_message))
        
        # Hiển thị thông báo thành công
        await query.edit_message_text(
            text=f"✅ *Xóa bàn thành công!*\n\n"
                f"Đã xóa {table_name} khỏi hệ thống.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Quay lại danh sách bàn", callback_data='delete_table')],
                [InlineKeyboardButton("⬅️ Quay lại quản lý bàn", callback_data='manage_tables')]
            ]),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi xóa bàn: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='delete_table')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def manage_table_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị giao diện quản lý trạng thái bàn"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra nếu người dùng là admin hoặc thu ngân
    user_id = update.effective_user.id
    if not (is_admin(user_id) or is_cashier(user_id)):
        await query.edit_message_text(
            text="⛔ Bạn không có quyền truy cập vào khu vực này.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return MAIN_MENU
    
    # Lấy danh sách bàn từ database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy tất cả các bàn cùng với thông tin đơn hàng để biết bàn nào đang có đơn
        cursor.execute("""
            SELECT t.id, t.name, t.capacity, t.is_reserved,
                   (SELECT COUNT(*) FROM orders o WHERE o.table_id = t.id AND o.status != 'completed') as order_count
            FROM tables t
            ORDER BY t.name
        """)
        tables = cursor.fetchall()
        
        if not tables:
            await query.edit_message_text(
                text="❌ Không có bàn nào trong hệ thống.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
            )
            return MANAGE_TABLES
        
        # Hiển thị danh sách bàn để quản lý trạng thái
        message_text = "*QUẢN LÝ TRẠNG THÁI BÀN*\n\n"
        
        # Phân chia bàn theo trạng thái
        reserved_tables = []
        available_tables = []
        
        for table_id, table_name, capacity, is_reserved, order_count in tables:
            table_info = {
                'id': table_id,
                'name': table_name,
                'capacity': capacity,
                'is_reserved': is_reserved,
                'order_count': order_count
            }
            
            if is_reserved:
                reserved_tables.append(table_info)
            else:
                available_tables.append(table_info)
        
        # Hiển thị bàn đã đặt
        if reserved_tables:
            message_text += "🔴 *BÀN ĐÃ ĐẶT:*\n"
            for table in reserved_tables:
                status = f"({table['order_count']} đơn hàng)" if table['order_count'] > 0 else "(Không có đơn)"
                message_text += f"• {table['name']} - {table['capacity']} chỗ {status}\n"
            message_text += "\n"
        
        # Hiển thị bàn trống
        if available_tables:
            message_text += "🟢 *BÀN TRỐNG:*\n"
            for table in available_tables:
                message_text += f"• {table['name']} - {table['capacity']} chỗ\n"
            message_text += "\n"
        
        message_text += "Chọn bàn để thay đổi trạng thái:"
        
        # Tạo nút cho từng bàn
        keyboard = []
        
        # Nút để đổi trạng thái bàn đã đặt thành trống
        if reserved_tables:
            keyboard.append([InlineKeyboardButton("🟢 BÀN ĐÃ ĐẶT → TRỐNG", callback_data='dummy_separator')])
            for table in reserved_tables:
                # Nếu bàn có đơn hàng, thêm cảnh báo
                button_text = f"{table['name']} {'⚠️ Có đơn hàng' if table['order_count'] > 0 else ''}"
                keyboard.append([InlineKeyboardButton(
                    button_text, 
                    callback_data=f"unreserve_{table['id']}"
                )])
        
        # Nút để đổi trạng thái bàn trống thành đã đặt
        if available_tables:
            keyboard.append([InlineKeyboardButton("🔴 BÀN TRỐNG → ĐÃ ĐẶT", callback_data='dummy_separator')])
            for table in available_tables:
                keyboard.append([InlineKeyboardButton(
                    f"{table['name']}", 
                    callback_data=f"reserve_{table['id']}"
                )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')])
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi quản lý trạng thái bàn: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def quick_payment_by_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị giao diện thanh toán nhanh theo bàn"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    # Chỉ cho phép Admin và Thu ngân truy cập
    if not (is_admin(user_id) or is_cashier(user_id)):
        await query.edit_message_text(
            text="⛔ Chỉ Admin và Thu ngân mới có quyền thanh toán.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return MAIN_MENU
    
    # Lấy danh sách bàn từ database
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy tất cả các bàn có đơn hàng chưa thanh toán
        cursor.execute("""
            SELECT t.id, t.name, t.capacity, t.is_reserved,
                   (SELECT COUNT(*) FROM orders o WHERE o.table_id = t.id AND o.status != 'completed') as order_count,
                   (SELECT SUM(o.quantity * p.price) FROM orders o 
                    JOIN products p ON o.product_id = p.id 
                    WHERE o.table_id = t.id AND o.status != 'completed') as total_amount
            FROM tables t
            WHERE t.is_reserved = 1
            ORDER BY t.name
        """)
        tables = cursor.fetchall()
        
        # Lọc chỉ lấy các bàn có đơn hàng chưa thanh toán
        tables_with_orders = [t for t in tables if t[4] > 0 and t[5] is not None]
        
        if not tables_with_orders:
            await query.edit_message_text(
                text="Không có bàn nào cần thanh toán.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
            )
            return MANAGE_TABLES
        
        # Hiển thị danh sách bàn để thanh toán
        message_text = "*THANH TOÁN THEO BÀN*\n\n"
        message_text += "Chọn bàn để xem chi tiết và thanh toán:\n\n"
        
        for table_id, table_name, capacity, is_reserved, order_count, total_amount in tables_with_orders:
            message_text += f"• {table_name} - {order_count} món - {total_amount:,.0f}đ\n"
        
        message_text += "\nChọn bàn để thanh toán:"
        
        # Tạo nút cho từng bàn
        keyboard = []
        for table_id, table_name, capacity, is_reserved, order_count, total_amount in tables_with_orders:
            keyboard.append([InlineKeyboardButton(
                f"{table_name} - {total_amount:,.0f}đ", 
                callback_data=f"pay_table_{table_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')])
        
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị giao diện thanh toán: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='manage_tables')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def pay_table(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý thanh toán cho một bàn cụ thể"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    # Chỉ cho phép Admin và Thu ngân truy cập
    if not (is_admin(user_id) or is_cashier(user_id)):
        await query.edit_message_text(
            text="⛔ Chỉ Admin và Thu ngân mới có quyền thanh toán.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return MAIN_MENU
    
    # Lấy ID bàn từ callback data
    table_id = int(query.data.split('_')[2])
    
    # Lấy thông tin hóa đơn
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy thông tin bàn
        cursor.execute("SELECT name FROM tables WHERE id = ?", (table_id,))
        table_result = cursor.fetchone()
        
        if not table_result:
            await query.edit_message_text(
                text=f"❌ Không tìm thấy thông tin bàn.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='quick_payment_by_table')]])
            )
            return MANAGE_TABLES
        
        table_name = table_result[0]
        
        # Lấy thông tin các món đã đặt
        cursor.execute("""
            SELECT p.name, o.quantity, p.price, (o.quantity * p.price) as item_total, o.id
            FROM orders o
            JOIN products p ON o.product_id = p.id
            WHERE o.table_id = ? AND o.status != 'completed'
            ORDER BY p.name
        """, (table_id,))
        
        items = cursor.fetchall()
        if not items:
            await query.edit_message_text(
                text=f"❌ Bàn {table_name} không có món nào cần thanh toán.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='quick_payment_by_table')]])
            )
            return MANAGE_TABLES
        
        # Tính tổng tiền
        total_amount = sum(item[3] for item in items)
        
        # Tạo hóa đơn chi tiết cho bàn
        bill_text = f"*HÓA ĐƠN BÀN {table_name}*\n\n"
        bill_text += f"🕒 Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n"
        bill_text += f"👤 Thu ngân: {update.effective_user.first_name}\n\n"
        
        # Tổng hợp tất cả các mục từ tất cả các đơn hàng
        order_items = []
        for product_name, quantity, price, item_total, order_id in items:
            order_items.append({
                'name': product_name,
                'quantity': quantity,
                'price': price,
                'total': item_total,
                'id': order_id
            })
        
        # Tính tổng số tiền và hiển thị chi tiết hóa đơn
        bill_text += "*CHI TIẾT SẢN PHẨM:*\n"
        for idx, item in enumerate(order_items, 1):
            bill_text += f"{idx}. {item['name']} - {item['quantity']} x {item['price']:,.0f}đ = {item['total']:,.0f}đ\n"
        
        bill_text += f"\n💰 *Tổng tiền: {total_amount:,.0f}đ*\n\n"
        bill_text += "Bạn có muốn xác nhận thanh toán cho bàn này không?"
        
        # Lưu thông tin bill vào context để sử dụng khi thanh toán
        context.user_data['current_bill'] = {
            'table_id': table_id,
            'table_name': table_name,
            'items': order_items,
            'total_amount': total_amount,
            'bill_text': bill_text
        }
        
        # Tạo bàn phím với nút xác nhận thanh toán
        keyboard = [
            [InlineKeyboardButton("✅ XÁC NHẬN THANH TOÁN", callback_data=f"confirm_pay_table_{table_id}")],
            [InlineKeyboardButton("❌ HỦY", callback_data="quick_payment_by_table")]
        ]
        
        await query.edit_message_text(
            text=bill_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MANAGE_TABLES
    except Exception as e:
        logger.error(f"Lỗi khi xử lý thanh toán: {str(e)}")
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='quick_payment_by_table')]])
        )
        return MANAGE_TABLES
    finally:
        conn.close()

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị menu chính cho admin"""
    query = update.callback_query
    await query.answer()
    
    # Kiểm tra nếu người dùng là admin
    if not is_admin(update.effective_user.id):
        await query.edit_message_text(
            text="⛔ Bạn không có quyền truy cập vào khu vực này.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return MAIN_MENU
    
    # Hiển thị menu admin
    keyboard = [
        [InlineKeyboardButton("🪑 Quản lý bàn", callback_data='manage_tables')],
        [InlineKeyboardButton("🍔 Quản lý món ăn", callback_data='manage_products')],
        [InlineKeyboardButton("📊 Báo cáo doanh thu", callback_data='view_reports')],
        [InlineKeyboardButton("💰 Quản lý thanh toán", callback_data='view_bills')],
        [InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="*TRANG QUẢN TRỊ*\nVui lòng chọn chức năng quản trị:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return ADMIN_MENU

async def view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hiển thị danh sách đơn hàng"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    # Chỉ Admin và Thu ngân có thể xem danh sách đơn hàng
    if not (is_admin(user_id) or is_cashier(user_id)):
        await query.edit_message_text(
            text="⛔ Bạn không có quyền xem danh sách đơn hàng.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return MAIN_MENU
    
    # Hiện thông báo tạm thời
    await query.edit_message_text(
        text="🔄 Chức năng xem danh sách đơn hàng đang được phát triển.\n\nVui lòng quay lại sau!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
    )
    
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Hủy bỏ hội thoại hiện tại và quay lại điểm ban đầu."""
    await update.message.reply_text(
        f"Đã hủy thao tác. Gõ /start để bắt đầu lại.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

async def mark_order_preparing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Đánh dấu đơn hàng đang được chuẩn bị"""
    query = update.callback_query
    await query.answer()
    
    # Lấy ID đơn hàng từ callback data
    order_id = int(query.data.split('_')[-1])
    
    # Cập nhật trạng thái đơn hàng
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Kiểm tra xem đơn hàng có tồn tại không
        cursor.execute("""
            SELECT o.id, o.product_id, o.quantity, o.table_id, o.status, p.name, t.name
            FROM orders o
            JOIN products p ON o.product_id = p.id
            JOIN tables t ON o.table_id = t.id
            WHERE o.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            await query.edit_message_text(
                text="❌ Không tìm thấy đơn hàng.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
            )
            return ORDER_PREPARATION
        
        # Lấy thông tin đơn hàng
        _, product_id, quantity, table_id, status, product_name, table_name = order
        
        # Kiểm tra trạng thái hiện tại
        if status != 'pending':
            await query.edit_message_text(
                text=f"⚠️ Đơn hàng đã ở trạng thái {status}, không thể đánh dấu là đang chuẩn bị.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
            )
            return ORDER_PREPARATION
        
        # Cập nhật trạng thái đơn hàng
        cursor.execute("""
            UPDATE orders
            SET status = 'preparing', update_time = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), order_id))
        conn.commit()
        
        # Gửi thông báo đến nhóm
        user = update.effective_user
        user_name = f"{user.first_name} {user.last_name or ''}"
        
        notification_message = (
            f"🔄 *THÔNG BÁO CHUẨN BỊ ĐƠN HÀNG*\n\n"
            f"👨‍🍳 Người thực hiện: *{user_name}*\n"
            f"🪑 Bàn: *{table_name}*\n"
            f"🍽️ Món: *{product_name}* (x{quantity})\n"
            f"⏰ Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
            f"✅ Đơn hàng đang được chuẩn bị."
        )
        
        # Gửi thông báo không đồng bộ để không làm chậm luồng chính
        asyncio.create_task(send_group_notification(context, notification_message))
        
        # Hiển thị thông báo thành công
        await query.edit_message_text(
            text=f"✅ *Đơn hàng đang được chuẩn bị*\n\n"
                f"• Bàn: {table_name}\n"
                f"• Món: {product_name} (x{quantity})\n\n"
                f"Bạn có thể đánh dấu đơn hàng này là đã sẵn sàng khi hoàn thành.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Đánh dấu đã sẵn sàng", callback_data=f"order_ready_{order_id}")],
                [InlineKeyboardButton("⬅️ Quay lại", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
        
        return ORDER_PREPARATION
    except Exception as e:
        logger.error(f"Lỗi khi đánh dấu đơn hàng đang chuẩn bị: {str(e)}")
        
        if conn:
            conn.rollback()
            
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return ORDER_PREPARATION
    finally:
        if conn:
            conn.close()

async def mark_order_ready(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Đánh dấu đơn hàng đã sẵn sàng"""
    query = update.callback_query
    await query.answer()
    
    # Lấy ID đơn hàng từ callback data
    order_id = int(query.data.split('_')[-1])
    
    # Cập nhật trạng thái đơn hàng
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Kiểm tra xem đơn hàng có tồn tại không
        cursor.execute("""
            SELECT o.id, o.product_id, o.quantity, o.table_id, o.status, p.name, t.name
            FROM orders o
            JOIN products p ON o.product_id = p.id
            JOIN tables t ON o.table_id = t.id
            WHERE o.id = ?
        """, (order_id,))
        
        order = cursor.fetchone()
        if not order:
            await query.edit_message_text(
                text="❌ Không tìm thấy đơn hàng.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
            )
            return ORDER_PREPARATION
        
        # Lấy thông tin đơn hàng
        _, product_id, quantity, table_id, status, product_name, table_name = order
        
        # Kiểm tra trạng thái hiện tại
        if status != 'preparing':
            await query.edit_message_text(
                text=f"⚠️ Đơn hàng không ở trạng thái đang chuẩn bị, không thể đánh dấu là đã sẵn sàng.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
            )
            return ORDER_PREPARATION
        
        # Cập nhật trạng thái đơn hàng
        cursor.execute("""
            UPDATE orders
            SET status = 'ready', update_time = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), order_id))
        conn.commit()
        
        # Gửi thông báo đến nhóm
        user = update.effective_user
        user_name = f"{user.first_name} {user.last_name or ''}"
        
        notification_message = (
            f"✅ *THÔNG BÁO ĐƠN HÀNG SẴN SÀNG*\n\n"
            f"👨‍🍳 Người thực hiện: *{user_name}*\n"
            f"🪑 Bàn: *{table_name}*\n"
            f"🍽️ Món: *{product_name}* (x{quantity})\n"
            f"⏰ Thời gian: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}\n\n"
            f"✅ Đơn hàng đã sẵn sàng phục vụ."
        )
        
        # Gửi thông báo không đồng bộ để không làm chậm luồng chính
        asyncio.create_task(send_group_notification(context, notification_message))
        
        # Hiển thị thông báo thành công
        await query.edit_message_text(
            text=f"✅ *Đơn hàng đã sẵn sàng*\n\n"
                f"• Bàn: {table_name}\n"
                f"• Món: {product_name} (x{quantity})\n\n"
                f"Đơn hàng đã được đánh dấu là sẵn sàng phục vụ.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Quay lại", callback_data="back_to_main")]
            ]),
            parse_mode='Markdown'
        )
        
        return ORDER_PREPARATION
    except Exception as e:
        logger.error(f"Lỗi khi đánh dấu đơn hàng đã sẵn sàng: {str(e)}")
        
        if conn:
            conn.rollback()
            
        await query.edit_message_text(
            text=f"❌ Đã xảy ra lỗi: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
        )
        return ORDER_PREPARATION
    finally:
        if conn:
            conn.close()

def main() -> None:
    """Hàm khởi động bot"""
    # Tạo application
def main() -> None:
    """Hàm khởi động bot"""
    # Tạo application
    application = Application.builder().token(TOKEN).build()

    # Thêm handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(admin_panel, pattern="^admin_panel$"),
                CallbackQueryHandler(admin_manage_tables, pattern="^manage_tables$"),
                CallbackQueryHandler(admin_manage_products, pattern="^manage_products$"),
                CallbackQueryHandler(place_order, pattern="^place_order$"),
                CallbackQueryHandler(view_orders, pattern="^view_orders$"),
                CallbackQueryHandler(view_bills, pattern="^view_bills$"),
                CallbackQueryHandler(process_payment, pattern="^process_payment$"),
                CallbackQueryHandler(request_bill, pattern="^request_bill$"),
                CallbackQueryHandler(admin_reports, pattern="^view_reports$"),
                CallbackQueryHandler(show_tables, pattern="^reserve_table$"),
                CallbackQueryHandler(start, pattern="^back_to_main$"),
                CallbackQueryHandler(add_new_table, pattern="^add_new_table$"),
                CallbackQueryHandler(create_table, pattern="^create_table_"),
                # Các handlers khác...
            ],
            ADMIN_MENU: [
                CallbackQueryHandler(admin_manage_tables, pattern="^manage_tables$"),
                CallbackQueryHandler(admin_manage_products, pattern="^manage_products$"),
                CallbackQueryHandler(view_bills, pattern="^view_bills$"),
                CallbackQueryHandler(admin_reports, pattern="^view_reports$"),
                CallbackQueryHandler(reset_all_tables, pattern="^reset_all_tables$"),
                CallbackQueryHandler(start, pattern="^back_to_main$"),
                CallbackQueryHandler(add_new_table, pattern="^add_new_table$"),
                CallbackQueryHandler(create_table, pattern="^create_table_"),
                CallbackQueryHandler(edit_table_info, pattern="^edit_table_info$"),
                CallbackQueryHandler(edit_table_capacity, pattern="^edit_table_"),
                CallbackQueryHandler(update_table_capacity, pattern="^update_table_"),
                CallbackQueryHandler(delete_table, pattern="^delete_table$"),
                CallbackQueryHandler(manage_table_status, pattern="^manage_table_status$"),
                CallbackQueryHandler(quick_payment_by_table, pattern="^quick_payment_by_table$"),
                # Các handlers khác...
            ],
            ORDER_ITEMS: [
                CallbackQueryHandler(show_category_products, pattern="^category_"),
                CallbackQueryHandler(edit_product, pattern="^product_"),
                CallbackQueryHandler(add_to_cart, pattern="^add_"),
                CallbackQueryHandler(view_cart, pattern="^view_cart$"),
                CallbackQueryHandler(start, pattern="^back_to_main$"),
                CallbackQueryHandler(show_tables, pattern="^select_table$"),
                CallbackQueryHandler(order_more, pattern="^order_more$"),
                # Các handlers khác...
            ],
            ORDER_PREPARATION: [
                CallbackQueryHandler(mark_order_preparing, pattern="^order_preparing_"),
                CallbackQueryHandler(mark_order_ready, pattern="^order_ready_"),
            ],
            # Các states khác...
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    # Add standalone handlers for order preparation callbacks (works in any context)
    application.add_handler(CallbackQueryHandler(mark_order_preparing, pattern="^order_preparing_"))
    application.add_handler(CallbackQueryHandler(mark_order_ready, pattern="^order_ready_"))
    
    # Add handlers for table deletion process
    application.add_handler(CallbackQueryHandler(pre_confirm_delete_table, pattern="^pre_confirm_delete_table_"))
    application.add_handler(CallbackQueryHandler(confirm_delete_table, pattern="^confirm_delete_table_"))
    
    # Add handlers for table payment process
    application.add_handler(CallbackQueryHandler(quick_payment_by_table, pattern="^quick_payment_by_table$"))
    application.add_handler(CallbackQueryHandler(pay_table, pattern="^pay_table_"))
    application.add_handler(CallbackQueryHandler(confirm_pay_table, pattern="^confirm_pay_table_"))
    
    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
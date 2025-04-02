import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ConversationHandler, CallbackQueryHandler, ContextTypes,
    filters
)
from dotenv import load_dotenv
from database import init_db, get_session, Product, Order, OrderItem, Table

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load biến môi trường
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    # Fallback to direct token if not in environment variables
    TOKEN = '7705072328:AAElGoUVLaXNnbwsMyBg59tWOCXNdVtHkz4'
ADMIN_ID = 6079753756

# Trạng thái hội thoại
(MAIN_MENU, ADMIN_MENU, VIEW_MENU, ORDER_ITEMS, CONFIRM_ORDER, 
 ADD_PRODUCT, EDIT_PRODUCT, VIEW_ORDERS, MANAGE_TABLES,
 EDIT_PRODUCT_NAME, EDIT_PRODUCT_PRICE, EDIT_PRODUCT_CATEGORY, EDIT_PRODUCT_DESCRIPTION, EDIT_PRODUCT_AVAILABILITY) = range(14)

# Khởi tạo database
init_db()

def is_admin(user_id):
    """Kiểm tra xem người dùng có phải là admin hay không"""
    return user_id == ADMIN_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý lệnh /start và hiển thị menu chính"""
    user = update.effective_user
    user_id = user.id
    
    context.user_data.clear()  # Xóa dữ liệu phiên hiện tại
    
    if is_admin(user_id):
        # Menu cho admin
        keyboard = [
            [InlineKeyboardButton("📋 Xem Menu", callback_data='view_menu')],
            [InlineKeyboardButton("📝 Quản lý Sản phẩm", callback_data='manage_products')],
            [InlineKeyboardButton("🛎️ Quản lý Đơn hàng", callback_data='manage_orders')],
            [InlineKeyboardButton("🪑 Quản lý Bàn", callback_data='manage_tables')],
            [InlineKeyboardButton("📊 Báo cáo", callback_data='reports')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f'Xin chào Admin {user.first_name}! Chọn một tùy chọn:',
            reply_markup=reply_markup
        )
        return ADMIN_MENU
    else:
        # Menu cho khách hàng
        keyboard = [
            [InlineKeyboardButton("📋 Xem Menu", callback_data='view_menu')],
            [InlineKeyboardButton("🛒 Đặt món", callback_data='place_order')],
            [InlineKeyboardButton("🪑 Đặt bàn", callback_data='reserve_table')],
            [InlineKeyboardButton("📱 Liên hệ", callback_data='contact')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f'Xin chào {user.first_name}! Chào mừng đến với Quán Cafe của chúng tôi!',
            reply_markup=reply_markup
        )
        return MAIN_MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Xử lý các callback từ menu chính"""
    query = update.callback_query
    await query.answer()
    choice = query.data
    
    if choice == 'view_menu':
        return await show_menu_categories(update, context)
    elif choice == 'place_order':
        return await start_order(update, context)
    elif choice == 'reserve_table':
        return await show_tables(update, context)
    elif choice.startswith('reserve_') and choice != 'reserve_table':
        # Xử lý đặt bàn khi người dùng chọn một bàn cụ thể
        return await reserve_table(update, context)
    elif choice.startswith('order_cat_'):
        # Xử lý khi người dùng chọn danh mục để đặt món
        return await show_category_products(update, context)
    elif choice.startswith('add_item_'):
        # Xử lý khi người dùng thêm sản phẩm vào giỏ hàng
        return await add_to_cart(update, context)
    elif choice == 'view_cart':
        # Xem giỏ hàng
        return await view_cart(update, context)
    elif choice == 'clear_cart':
        # Xóa giỏ hàng
        return await clear_cart(update, context)
    elif choice == 'confirm_order':
        # Xác nhận đơn hàng
        return await confirm_order(update, context)
    elif choice == 'contact':
        await query.edit_message_text(
            text="📱 *Thông tin liên hệ:*\n\n"
                 "☎️ Điện thoại: 0123456789\n"
                 "📧 Email: cafe@example.com\n"
                 "🌐 Website: www.example.com\n"
                 "🏠 Địa chỉ: 123 Đường ABC, Quận XYZ, TP.HCM",
            parse_mode='Markdown'
        )
        # Thêm nút quay lại
        keyboard = [[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        return MAIN_MENU
    elif choice == 'back_to_main':
        return await start(update, context)
    elif choice == 'manage_products' and is_admin(update.effective_user.id):
        return await admin_manage_products(update, context)
    elif choice == 'manage_orders' and is_admin(update.effective_user.id):
        return await admin_manage_orders(update, context)
    elif choice == 'manage_tables' and is_admin(update.effective_user.id):
        return await admin_manage_tables(update, context)
    elif choice == 'reports' and is_admin(update.effective_user.id):
        return await admin_reports(update, context)
    elif choice == 'add_product' and is_admin(update.effective_user.id):
        # Chuyển qua form nhập thông tin sản phẩm
        context.user_data['add_product_step'] = 'name'
        
        # Hướng dẫn chi tiết
        help_text = (
            "*Hướng dẫn thêm sản phẩm mới:*\n\n"
            "Quy trình thêm sản phẩm gồm 4 bước đơn giản:\n"
            "1️⃣ Nhập tên sản phẩm\n"
            "2️⃣ Nhập giá (chỉ nhập số, không dấu phẩy)\n"
            "3️⃣ Chọn hoặc tạo danh mục\n"
            "4️⃣ Nhập mô tả sản phẩm\n\n"
            "Sau khi hoàn thành, sản phẩm sẽ được tự động thêm vào hệ thống.\n\n"
            "*Bắt đầu bước 1:*"
        )
        
        await query.edit_message_text(
            text=f"{help_text}\n\n"
                 "*Thêm sản phẩm mới - Bước 1/4*\n\n"
                 "Vui lòng nhập *tên sản phẩm*:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại menu quản lý", callback_data='manage_products')]])
        )
        return ADD_PRODUCT
    elif choice == 'list_products' and is_admin(update.effective_user.id):
        return await list_products(update, context)
    elif choice.startswith('edit_product_') and is_admin(update.effective_user.id):
        return await edit_product(update, context)
    elif choice.startswith('edit_name_') and is_admin(update.effective_user.id):
        return await edit_product_name(update, context)
    elif choice.startswith('edit_price_') and is_admin(update.effective_user.id):
        return await edit_product_price(update, context)
    elif choice.startswith('edit_category_') and is_admin(update.effective_user.id):
        return await edit_product_category(update, context)
    elif choice.startswith('edit_description_') and is_admin(update.effective_user.id):
        return await edit_product_description(update, context)
    elif choice.startswith('toggle_availability_') and is_admin(update.effective_user.id):
        return await toggle_product_availability(update, context)
    elif choice.startswith('set_category_') and is_admin(update.effective_user.id):
        return await set_product_category(update, context)
    
    return MAIN_MENU

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
    table_info = f"🪑 Bàn đã chọn: Bàn {selected_table['number']}\n\n" if selected_table else ""
    
    session = get_session()
    try:
        # Lấy danh mục sản phẩm để hiển thị
        categories = session.query(Product.category).distinct().all()
        categories = [category[0] for category in categories]
        
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(f"{category}", callback_data=f"order_cat_{category}")])
        
        keyboard.append([InlineKeyboardButton("🛒 Xem giỏ hàng", callback_data='view_cart')])
        
        # Thêm tùy chọn đặt bàn nếu chưa đặt
        if not selected_table:
            keyboard.append([InlineKeyboardButton("🪑 Đặt bàn trước", callback_data='reserve_table')])
            
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
    """Giao diện quản lý bàn cho admin"""
    query = update.callback_query
    await query.answer()
    
    session = get_session()
    try:
        tables = session.query(Table).order_by(Table.number).all()
        
        if not tables:
            keyboard = [
                [InlineKeyboardButton("➕ Thêm bàn mới", callback_data='add_table')],
                [InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="*Quản lý Bàn*\nKhông có bàn nào. Hãy thêm bàn mới.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            text = "*Danh sách bàn:*\n\n"
            for table in tables:
                status = "🔴 Đã đặt" if table.is_reserved else "🟢 Trống"
                text += f"Bàn {table.number} - {table.capacity} chỗ - {status}\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ Thêm bàn mới", callback_data='add_table')],
                [InlineKeyboardButton("✏️ Chỉnh sửa bàn", callback_data='edit_tables')],
                [InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    finally:
        session.close()
    
    return ADMIN_MENU

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
        tables = session.query(Table).filter(Table.is_reserved == False).order_by(Table.number).all()
        
        if not tables:
            await query.edit_message_text(
                text="Hiện tại tất cả các bàn đều đã được đặt. Vui lòng quay lại sau!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data='back_to_main')]])
            )
        else:
            text = "*Các bàn còn trống:*\n\n"
            keyboard = []
            for table in tables:
                text += f"Bàn {table.number} - {table.capacity} chỗ\n"
                keyboard.append([InlineKeyboardButton(f"Đặt bàn {table.number}", callback_data=f'reserve_{table.id}')])
            
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
        
        return MAIN_MENU
    except Exception as e:
        session.rollback()
        await query.edit_message_text(
            text=f"❌ Có lỗi xảy ra khi đặt bàn: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Thử lại", callback_data='reserve_table')]])
        )
        return MAIN_MENU
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
    
    # Lấy tên danh mục từ callback data
    category = query.data.replace("order_cat_", "")
    
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
            keyboard.append([InlineKeyboardButton(f"➕ Thêm {product.name}", callback_data=f"add_item_{product.id}")])
        
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
                
                await query.answer(f"Đã thêm 1 {product.name} vào giỏ hàng!")
                # Chuyển về trang danh mục sản phẩm
                return await show_category_products(update, context)
        
        # Thêm sản phẩm mới vào giỏ hàng
        context.user_data['cart'].append({
            'product_id': product_id,
            'product_name': product.name,
            'price': product.price,
            'quantity': 1
        })
        
        await query.answer(f"Đã thêm {product.name} vào giỏ hàng!")
        # Chuyển về trang danh mục sản phẩm
        return await show_category_products(update, context)
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
    
    # Hiển thị thông tin giỏ hàng
    text = "🛒 *Giỏ hàng của bạn:*\n\n"
    total = 0
    
    for i, item in enumerate(cart):
        item_total = item['price'] * item['quantity']
        total += item_total
        text += f"{i + 1}. *{item['product_name']}*\n"
        text += f"   Số lượng: {item['quantity']} x {item['price']:,.0f} VNĐ = {item_total:,.0f} VNĐ\n\n"
    
    text += f"*Tổng cộng: {total:,.0f} VNĐ*"
    
    # Thông tin bàn đã đặt (nếu có)
    selected_table = context.user_data.get('selected_table')
    if selected_table:
        text += f"\n\n🪑 *Bàn đã chọn:* Bàn {selected_table['number']}"
    
    # Tạo các nút điều khiển
    keyboard = [
        [InlineKeyboardButton("✅ Xác nhận đặt món", callback_data='confirm_order')],
        [InlineKeyboardButton("🗑️ Xóa giỏ hàng", callback_data='clear_cart')],
        [InlineKeyboardButton("➕ Thêm món khác", callback_data='place_order')]
    ]
    
    # Nếu chưa đặt bàn, hiển thị nút đặt bàn
    if not selected_table:
        keyboard.insert(1, [InlineKeyboardButton("🪑 Đặt bàn", callback_data='reserve_table')])
    
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
    
    session = get_session()
    try:
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
        
        session.commit()
        
        # Xóa giỏ hàng sau khi đặt hàng thành công
        context.user_data['cart'] = []
        
        # Thông báo thành công
        text = "✅ *Đặt món thành công!*\n\n"
        text += f"Mã đơn hàng: *#{new_order.id}*\n"
        
        if table_number:
            text += f"Bàn: *Bàn {table_number}*\n"
        
        text += f"Tổng tiền: *{total_amount:,.0f} VNĐ*\n\n"
        text += "Đơn hàng của bạn đã được gửi đi và đang chờ xác nhận.\n"
        text += "Vui lòng đợi nhân viên phục vụ món ăn của bạn.\n\n"
        text += "Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi! 🙏"
        
        await query.edit_message_text(
            text=text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🍽️ Đặt thêm món", callback_data='place_order')],
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
from datetime import datetime, timedelta
from database import get_session, Order, OrderItem, Product
from sqlalchemy import func, and_

def format_price(price):
    """Format giá tiền theo định dạng VNĐ"""
    return f"{price:,.0f} VNĐ"

def get_today_sales():
    """Lấy doanh thu hôm nay"""
    session = get_session()
    try:
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        total = session.query(func.sum(Order.total_amount)).filter(
            Order.status == 'completed',
            Order.completed_at >= start_of_day,
            Order.completed_at <= end_of_day
        ).scalar() or 0
        
        return total
    finally:
        session.close()

def get_week_sales():
    """Lấy doanh thu tuần này"""
    session = get_session()
    try:
        today = datetime.now().date()
        start_of_week = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        end_of_week = datetime.combine(today, datetime.max.time())
        
        total = session.query(func.sum(Order.total_amount)).filter(
            Order.status == 'completed',
            Order.completed_at >= start_of_week,
            Order.completed_at <= end_of_week
        ).scalar() or 0
        
        return total
    finally:
        session.close()

def get_month_sales():
    """Lấy doanh thu tháng này"""
    session = get_session()
    try:
        today = datetime.now().date()
        start_of_month = datetime.combine(today.replace(day=1), datetime.min.time())
        end_of_month = datetime.combine(today, datetime.max.time())
        
        total = session.query(func.sum(Order.total_amount)).filter(
            Order.status == 'completed',
            Order.completed_at >= start_of_month,
            Order.completed_at <= end_of_month
        ).scalar() or 0
        
        return total
    finally:
        session.close()

def get_top_products(limit=5):
    """Lấy danh sách sản phẩm bán chạy nhất"""
    session = get_session()
    try:
        # Lấy tổng số lượng bán của mỗi sản phẩm
        result = session.query(
            Product.id,
            Product.name,
            func.sum(OrderItem.quantity).label('total_quantity')
        ).join(
            OrderItem, OrderItem.product_id == Product.id
        ).join(
            Order, and_(Order.id == OrderItem.order_id, Order.status == 'completed')
        ).group_by(
            Product.id
        ).order_by(
            func.sum(OrderItem.quantity).desc()
        ).limit(limit).all()
        
        return result
    finally:
        session.close()

def add_sample_data():
    """Thêm dữ liệu mẫu vào cơ sở dữ liệu"""
    session = get_session()
    try:
        # Kiểm tra xem đã có sản phẩm nào chưa
        product_count = session.query(func.count(Product.id)).scalar()
        if product_count > 0:
            return False  # Đã có dữ liệu, không cần thêm
        
        # Thêm sản phẩm mẫu
        products = [
            Product(name="Cà phê đen", description="Cà phê đen đậm đà truyền thống", price=25000, category="Cà phê"),
            Product(name="Cà phê sữa", description="Cà phê đen pha với sữa đặc", price=30000, category="Cà phê"),
            Product(name="Bạc xỉu", description="Cà phê sữa với nhiều sữa hơn", price=35000, category="Cà phê"),
            Product(name="Cappuccino", description="Cà phê Ý với bọt sữa", price=45000, category="Cà phê"),
            Product(name="Latte", description="Cà phê Ý với nhiều sữa", price=45000, category="Cà phê"),
            Product(name="Trà đào", description="Trà với đào tươi và syrup đào", price=40000, category="Trà"),
            Product(name="Trà vải", description="Trà với vải tươi", price=40000, category="Trà"),
            Product(name="Trà chanh", description="Trà với chanh tươi", price=35000, category="Trà"),
            Product(name="Trà sữa trân châu", description="Trà sữa với trân châu đường đen", price=45000, category="Trà sữa"),
            Product(name="Trà sữa matcha", description="Trà sữa vị matcha Nhật Bản", price=45000, category="Trà sữa"),
            Product(name="Bánh flan", description="Bánh flan mềm mịn với caramel", price=25000, category="Bánh"),
            Product(name="Bánh tiramisu", description="Bánh tiramisu phong cách Ý", price=35000, category="Bánh"),
            Product(name="Bánh brownie", description="Bánh brownie chocolate đậm đà", price=30000, category="Bánh")
        ]
        
        session.add_all(products)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Lỗi khi thêm dữ liệu mẫu: {e}")
        return False
    finally:
        session.close() 
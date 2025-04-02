from database import init_db, get_session, Product

def add_sample_products():
    """Thêm một số sản phẩm mẫu vào cơ sở dữ liệu"""
    init_db()
    session = get_session()
    
    # Kiểm tra xem đã có sản phẩm nào chưa
    product_count = session.query(Product).count()
    if product_count > 0:
        print(f"Đã có {product_count} sản phẩm trong cơ sở dữ liệu.")
        session.close()
        return
    
    # Danh sách sản phẩm mẫu
    sample_products = [
        Product(name="Cà phê đen", description="Cà phê đen đậm đà", price=20000, category="Đồ uống", is_available=True),
        Product(name="Cà phê sữa", description="Cà phê với sữa đặc", price=25000, category="Đồ uống", is_available=True),
        Product(name="Trà đào", description="Trà đào thanh mát", price=30000, category="Đồ uống", is_available=True),
        Product(name="Bánh flan", description="Bánh flan caramel", price=15000, category="Tráng miệng", is_available=True),
    ]
    
    try:
        for product in sample_products:
            session.add(product)
        session.commit()
        print(f"Đã thêm {len(sample_products)} sản phẩm mẫu vào cơ sở dữ liệu.")
    except Exception as e:
        print(f"Lỗi khi thêm sản phẩm: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    add_sample_products()
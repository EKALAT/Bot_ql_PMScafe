from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

# Tạo engine SQLite
engine = create_engine('sqlite:///cafe_management.db')
Base = declarative_base()
Session = sessionmaker(bind=engine)

# Định nghĩa các models
class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    is_available = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    username = Column(String)
    status = Column(String, default='pending')  # pending, confirmed, completed, cancelled
    created_at = Column(DateTime, default=datetime.datetime.now)
    completed_at = Column(DateTime)
    table_number = Column(Integer)
    total_amount = Column(Float, default=0.0)
    
    items = relationship("OrderItem", back_populates="order")
    
    def __repr__(self):
        return f"<Order(id={self.id}, user_id={self.user_id}, status='{self.status}')>"

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    
    order = relationship("Order", back_populates="items")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, quantity={self.quantity})>"

class Table(Base):
    __tablename__ = 'tables'
    
    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False, unique=True)
    capacity = Column(Integer, nullable=False)
    is_reserved = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Table(number={self.number}, capacity={self.capacity}, is_reserved={self.is_reserved})>"

def init_db():
    Base.metadata.create_all(engine)
    
def get_session():
    return Session() 
"""
Models for the e-commerce chatbot application.
These classes represent the data structure for products, orders, and user information.
"""

import json
from sqlalchemy import Column, String, Float, Boolean, Integer, Text, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    product_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    category = Column(String(100), nullable=False)
    image_url = Column(String(500), nullable=True)
    in_stock = Column(Boolean, default=True)
    
    # Order items relationship
    order_items = relationship("OrderItem", back_populates="product")
    
    def __init__(self, product_id, name, description, price, category, image_url=None, in_stock=True):
        self.product_id = product_id if product_id else f"p{uuid.uuid4().hex[:8]}"
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.image_url = image_url
        self.in_stock = in_stock
    
    @classmethod
    def from_dict(cls, data):
        """Create a Product instance from a dictionary."""
        return cls(
            product_id=data.get('product_id'),
            name=data.get('name'),
            description=data.get('description'),
            price=data.get('price'),
            category=data.get('category'),
            image_url=data.get('image_url'),
            in_stock=data.get('in_stock', True)
        )
    
    def to_dict(self):
        """Convert Product instance to a dictionary."""
        return {
            'product_id': self.product_id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'image_url': self.image_url,
            'in_stock': self.in_stock
        }


class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(50), ForeignKey('orders.order_id'), nullable=False)
    product_id = Column(String(50), ForeignKey('products.product_id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    
    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(50), unique=True, nullable=False)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(50), nullable=False)  # e.g., "pending", "shipped", "delivered"
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    user = relationship("User", back_populates="orders")
    
    def __init__(self, order_id, user_id, products, total_amount, status, timestamp=None):
        self.order_id = order_id if order_id else f"o{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.total_amount = total_amount
        self.status = status
        self.timestamp = timestamp or datetime.utcnow()
        self._products = products  # Used temporarily for from_dict and to_dict
    
    @classmethod
    def from_dict(cls, data):
        """Create an Order instance from a dictionary."""
        return cls(
            order_id=data.get('order_id'),
            user_id=data.get('user_id'),
            products=data.get('products', []),
            total_amount=data.get('total_amount'),
            status=data.get('status'),
            timestamp=data.get('timestamp')
        )
    
    def to_dict(self):
        """Convert Order instance to a dictionary."""
        products = []
        if hasattr(self, 'items') and self.items:
            for item in self.items:
                products.append({
                    'product_id': item.product_id,
                    'quantity': item.quantity
                })
        elif hasattr(self, '_products'):
            products = self._products
        
        return {
            'order_id': self.order_id,
            'user_id': self.user_id,
            'products': products,
            'total_amount': self.total_amount,
            'status': self.status,
            'timestamp': self.timestamp
        }


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    preferences = Column(Text, nullable=True)  # JSON string of preferences
    
    # Relationships
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    
    def __init__(self, user_id, name=None, email=None, preferences=None, order_history=None):
        self.user_id = user_id if user_id else f"u{uuid.uuid4().hex[:8]}"
        self.name = name
        self.email = email
        self.preferences = json.dumps(preferences or {})
        self._order_history = order_history or []  # Used temporarily for from_dict and to_dict
    
    @classmethod
    def from_dict(cls, data):
        """Create a User instance from a dictionary."""
        return cls(
            user_id=data.get('user_id'),
            name=data.get('name'),
            email=data.get('email'),
            preferences=data.get('preferences', {}),
            order_history=data.get('order_history', [])
        )
    
    def to_dict(self):
        """Convert User instance to a dictionary."""
        preferences = {}
        if self.preferences:
            try:
                preferences = json.loads(self.preferences)
            except:
                preferences = {}
        
        order_history = []
        if hasattr(self, 'orders') and self.orders:
            order_history = [order.order_id for order in self.orders]
        elif hasattr(self, '_order_history'):
            order_history = self._order_history
            
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'preferences': preferences,
            'order_history': order_history
        }

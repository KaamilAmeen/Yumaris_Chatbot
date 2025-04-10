"""
Models for the e-commerce chatbot application.
These classes represent the data structure for products, orders, user information,
and analytics data for the chatbot performance dashboard.
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
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
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


# Analytics Models

class ChatSession(Base):
    """
    Represents a chat session between a user and the chatbot.
    Each session contains multiple interactions.
    """
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(50), ForeignKey('users.user_id'), nullable=True)  # Nullable for anonymous users
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    platform = Column(String(50), nullable=True)  # web, mobile, etc.
    device_info = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    interactions = relationship("ChatInteraction", back_populates="session", cascade="all, delete-orphan")
    
    def __init__(self, session_id, user_id=None, platform=None, device_info=None):
        self.session_id = session_id if session_id else f"s{uuid.uuid4().hex[:8]}"
        self.user_id = user_id
        self.platform = platform
        self.device_info = device_info
        self.start_time = datetime.utcnow()
    
    def end_session(self):
        """Mark the session as ended."""
        self.end_time = datetime.utcnow()
    
    def to_dict(self):
        """Convert session to dictionary for API responses."""
        duration = None
        if self.end_time and self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
            
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'platform': self.platform,
            'device_info': self.device_info,
            'interaction_count': len(self.interactions) if hasattr(self, 'interactions') else 0,
            'duration_seconds': duration
        }


class ChatInteraction(Base):
    """
    Represents a single interaction (message and response) in a chat session.
    """
    __tablename__ = 'chat_interactions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), ForeignKey('chat_sessions.session_id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_message = Column(Text, nullable=False)
    chatbot_response = Column(Text, nullable=True)
    detected_intent = Column(String(100), nullable=True)
    confidence_score = Column(Float, nullable=True)
    has_attachment = Column(Boolean, default=False)
    attachment_type = Column(String(50), nullable=True)  # image, file, audio
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    products_shown = Column(Integer, default=0)  # Number of products shown in response
    entities = Column(Text, nullable=True)  # JSON string of detected entities
    sentiment_score = Column(Float, nullable=True)  # From -1 (negative) to 1 (positive)
    was_successful = Column(Boolean, default=True)  # Whether the interaction was successful
    error_type = Column(String(100), nullable=True)  # Type of error if unsuccessful
    
    # Relationships
    session = relationship("ChatSession", back_populates="interactions")
    
    def __init__(self, session_id, user_message, chatbot_response=None, detected_intent=None, 
                 confidence_score=None, has_attachment=False, attachment_type=None,
                 response_time_ms=None, products_shown=0, entities=None, 
                 sentiment_score=None, was_successful=True, error_type=None):
        self.session_id = session_id
        self.user_message = user_message
        self.chatbot_response = chatbot_response
        self.detected_intent = detected_intent
        self.confidence_score = confidence_score
        self.has_attachment = has_attachment
        self.attachment_type = attachment_type
        self.response_time_ms = response_time_ms
        self.products_shown = products_shown
        self.entities = json.dumps(entities) if entities else None
        self.sentiment_score = sentiment_score
        self.was_successful = was_successful
        self.error_type = error_type
        self.timestamp = datetime.utcnow()
    
    def to_dict(self):
        """Convert interaction to dictionary for API responses."""
        entities = {}
        if self.entities:
            try:
                entities = json.loads(self.entities)
            except:
                pass
                
        return {
            'id': self.id,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'user_message': self.user_message,
            'chatbot_response': self.chatbot_response,
            'detected_intent': self.detected_intent,
            'confidence_score': self.confidence_score,
            'has_attachment': self.has_attachment,
            'attachment_type': self.attachment_type,
            'response_time_ms': self.response_time_ms,
            'products_shown': self.products_shown,
            'entities': entities,
            'sentiment_score': self.sentiment_score,
            'was_successful': self.was_successful,
            'error_type': self.error_type
        }


class AnalyticsSummary(Base):
    """
    Stores aggregated analytics data for reporting.
    Summaries can be daily, weekly, or monthly.
    """
    __tablename__ = 'analytics_summaries'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    period_type = Column(String(10), nullable=False)  # daily, weekly, monthly
    total_sessions = Column(Integer, default=0)
    total_interactions = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    avg_session_duration_seconds = Column(Float, nullable=True)
    avg_response_time_ms = Column(Float, nullable=True)
    
    # Intent distribution (stored as JSON)
    intent_distribution = Column(Text, nullable=True)
    
    # Product metrics
    products_shown_count = Column(Integer, default=0)
    product_search_count = Column(Integer, default=0)
    
    # Error metrics
    error_count = Column(Integer, default=0)
    error_distribution = Column(Text, nullable=True)  # JSON of error types
    
    # Session origin metrics
    platform_distribution = Column(Text, nullable=True)  # JSON of platform counts
    
    def __init__(self, date, period_type):
        self.date = date
        self.period_type = period_type  # daily, weekly, monthly
        
    def set_intent_distribution(self, distribution):
        """Set the intent distribution as a JSON string."""
        self.intent_distribution = json.dumps(distribution)
        
    def get_intent_distribution(self):
        """Get the intent distribution as a dictionary."""
        if self.intent_distribution:
            try:
                return json.loads(self.intent_distribution)
            except:
                return {}
        return {}
        
    def set_error_distribution(self, distribution):
        """Set the error distribution as a JSON string."""
        self.error_distribution = json.dumps(distribution)
        
    def get_error_distribution(self):
        """Get the error distribution as a dictionary."""
        if self.error_distribution:
            try:
                return json.loads(self.error_distribution)
            except:
                return {}
        return {}
        
    def set_platform_distribution(self, distribution):
        """Set the platform distribution as a JSON string."""
        self.platform_distribution = json.dumps(distribution)
        
    def get_platform_distribution(self):
        """Get the platform distribution as a dictionary."""
        if self.platform_distribution:
            try:
                return json.loads(self.platform_distribution)
            except:
                return {}
        return {}

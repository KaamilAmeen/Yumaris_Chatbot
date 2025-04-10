"""
Models for the e-commerce chatbot application.
These classes represent the data structure for products, orders, and user information.
"""

class Product:
    def __init__(self, product_id, name, description, price, category, image_url=None, in_stock=True):
        self.product_id = product_id
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.image_url = image_url
        self.in_stock = in_stock
    
    @classmethod
    def from_dict(cls, data):
        """Create a Product instance from a Firebase document dictionary."""
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
        """Convert Product instance to a dictionary for Firebase storage."""
        return {
            'product_id': self.product_id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'image_url': self.image_url,
            'in_stock': self.in_stock
        }


class Order:
    def __init__(self, order_id, user_id, products, total_amount, status, timestamp=None):
        self.order_id = order_id
        self.user_id = user_id
        self.products = products  # List of product IDs and quantities
        self.total_amount = total_amount
        self.status = status  # e.g., "pending", "shipped", "delivered"
        self.timestamp = timestamp
    
    @classmethod
    def from_dict(cls, data):
        """Create an Order instance from a Firebase document dictionary."""
        return cls(
            order_id=data.get('order_id'),
            user_id=data.get('user_id'),
            products=data.get('products', []),
            total_amount=data.get('total_amount'),
            status=data.get('status'),
            timestamp=data.get('timestamp')
        )
    
    def to_dict(self):
        """Convert Order instance to a dictionary for Firebase storage."""
        return {
            'order_id': self.order_id,
            'user_id': self.user_id,
            'products': self.products,
            'total_amount': self.total_amount,
            'status': self.status,
            'timestamp': self.timestamp
        }


class User:
    def __init__(self, user_id, name=None, email=None, preferences=None, order_history=None):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.preferences = preferences or {}  # User preferences like favorite categories
        self.order_history = order_history or []  # List of order IDs
    
    @classmethod
    def from_dict(cls, data):
        """Create a User instance from a Firebase document dictionary."""
        return cls(
            user_id=data.get('user_id'),
            name=data.get('name'),
            email=data.get('email'),
            preferences=data.get('preferences', {}),
            order_history=data.get('order_history', [])
        )
    
    def to_dict(self):
        """Convert User instance to a dictionary for Firebase storage."""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'preferences': self.preferences,
            'order_history': self.order_history
        }

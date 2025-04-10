"""
Firebase service module to interact with Firebase Firestore
for product, order, and user data.
"""

import os
import logging
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from models import Product, Order, User

# Set up logging
logger = logging.getLogger(__name__)

# Reference to Firestore client
db = None

def initialize_firebase():
    """Initialize Firebase Admin SDK."""
    global db
    
    try:
        # Check if Firebase Admin SDK is already initialized
        if not firebase_admin._apps:
            # Get Firebase project credentials
            project_id = os.environ.get("FIREBASE_PROJECT_ID")
            
            # If we have a service account JSON path
            service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
            if service_account_path:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            else:
                # Use application default credentials
                firebase_admin.initialize_app()
            
            logger.info("Firebase Admin SDK initialized successfully")
        
        # Get Firestore client
        db = firestore.client()
        
        # Ensure we have sample data for testing
        ensure_sample_data()
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}", exc_info=True)
        return False

def ensure_sample_data():
    """
    Ensure sample data exists for testing the application.
    Only adds data if the collections are empty.
    """
    try:
        # Check if products collection is empty
        products_ref = db.collection('products')
        products = products_ref.limit(1).get()
        
        if not list(products):
            logger.info("Adding sample product data")
            
            sample_products = [
                Product(
                    product_id="p1",
                    name="Wireless Bluetooth Headphones",
                    description="Premium noise-cancelling headphones with 20-hour battery life and comfortable over-ear design.",
                    price=99.99,
                    category="Electronics",
                    image_url="https://via.placeholder.com/150",
                    in_stock=True
                ),
                Product(
                    product_id="p2",
                    name="Stainless Steel Water Bottle",
                    description="Vacuum insulated water bottle that keeps drinks cold for 24 hours or hot for 12 hours.",
                    price=24.99,
                    category="Home & Kitchen",
                    image_url="https://via.placeholder.com/150",
                    in_stock=True
                ),
                Product(
                    product_id="p3",
                    name="Organic Cotton T-Shirt",
                    description="Soft, breathable cotton t-shirt made with 100% organic materials and sustainable practices.",
                    price=29.99,
                    category="Clothing",
                    image_url="https://via.placeholder.com/150",
                    in_stock=True
                ),
                Product(
                    product_id="p4",
                    name="Smart LED Light Bulbs (4-pack)",
                    description="WiFi-enabled LED bulbs with adjustable brightness and color, compatible with voice assistants.",
                    price=49.99,
                    category="Smart Home",
                    image_url="https://via.placeholder.com/150",
                    in_stock=True
                ),
                Product(
                    product_id="p5",
                    name="Plant-Based Protein Powder",
                    description="Vegan protein powder with 25g of protein per serving and no artificial ingredients.",
                    price=34.99,
                    category="Health & Wellness",
                    image_url="https://via.placeholder.com/150",
                    in_stock=True
                )
            ]
            
            # Add products to Firestore
            for product in sample_products:
                products_ref.document(product.product_id).set(product.to_dict())
            
            # Add a sample order
            orders_ref = db.collection('orders')
            sample_order = Order(
                order_id="o1",
                user_id="u1",
                products=[
                    {"product_id": "p1", "quantity": 1},
                    {"product_id": "p2", "quantity": 2}
                ],
                total_amount=149.97,
                status="shipped",
                timestamp=firestore.SERVER_TIMESTAMP
            )
            orders_ref.document(sample_order.order_id).set(sample_order.to_dict())
            
            # Add a sample user
            users_ref = db.collection('users')
            sample_user = User(
                user_id="u1",
                name="Sample User",
                email="user@example.com",
                preferences={"favorite_categories": ["Electronics", "Smart Home"]},
                order_history=["o1"]
            )
            users_ref.document(sample_user.user_id).set(sample_user.to_dict())
            
            logger.info("Sample data added successfully")
    
    except Exception as e:
        logger.error(f"Failed to add sample data: {str(e)}", exc_info=True)

def get_products(limit=10):
    """Get a list of products from Firestore."""
    try:
        products = []
        products_ref = db.collection('products').limit(limit)
        
        for doc in products_ref.stream():
            product_data = doc.to_dict()
            products.append(Product.from_dict(product_data))
        
        return products
    
    except Exception as e:
        logger.error(f"Error getting products: {str(e)}", exc_info=True)
        return []

def get_product_by_id(product_id):
    """Get a product by ID from Firestore."""
    try:
        doc_ref = db.collection('products').document(product_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return Product.from_dict(doc.to_dict())
        return None
    
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {str(e)}", exc_info=True)
        return None

def get_order_by_id(order_id):
    """Get an order by ID from Firestore."""
    try:
        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return Order.from_dict(doc.to_dict())
        return None
    
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {str(e)}", exc_info=True)
        return None

def search_products(query, limit=5):
    """
    Search for products based on a query string.
    Searches in product name, description, and category.
    """
    try:
        results = []
        query = query.lower()
        
        # Get all products (in a real application, this would use proper indexing)
        products_ref = db.collection('products').limit(50)
        
        for doc in products_ref.stream():
            product_data = doc.to_dict()
            product = Product.from_dict(product_data)
            
            # Simple search logic
            if (query in product.name.lower() or 
                query in product.description.lower() or 
                query in product.category.lower()):
                results.append(product)
            
            # Limit results
            if len(results) >= limit:
                break
        
        return results
    
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}", exc_info=True)
        return []

def get_trending_products(limit=3):
    """
    Get trending or recommended products.
    In a real application, this would use more sophisticated logic.
    """
    return get_products(limit=limit)

def get_user_by_id(user_id):
    """Get a user by ID from Firestore."""
    try:
        doc_ref = db.collection('users').document(user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            return User.from_dict(doc.to_dict())
        return None
    
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}", exc_info=True)
        return None

def add_product(product):
    """Add a new product to Firestore."""
    try:
        if not product.product_id:
            product.product_id = f"p{uuid.uuid4().hex[:8]}"
        
        db.collection('products').document(product.product_id).set(product.to_dict())
        return product
    
    except Exception as e:
        logger.error(f"Error adding product: {str(e)}", exc_info=True)
        return None

def update_product(product):
    """Update a product in Firestore."""
    try:
        db.collection('products').document(product.product_id).update(product.to_dict())
        return product
    
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}", exc_info=True)
        return None

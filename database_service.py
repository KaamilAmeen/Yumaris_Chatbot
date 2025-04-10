"""
Database service module to interact with PostgreSQL database
for product, order, and user data.
"""

import os
import logging
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, Product, Order, OrderItem, User

# Set up logging
logger = logging.getLogger(__name__)

# Create database engine and session
engine = create_engine(os.environ.get("DATABASE_URL"))
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    """Initialize the database, creating tables if they don't exist."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Check if we need to add sample data
        if db_session().query(Product).count() == 0:
            add_sample_data()
        
        return True
    
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        return False

def add_sample_data():
    """Add sample data to the database for testing."""
    try:
        session = db_session()
        
        # Sample products
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
        
        session.add_all(sample_products)
        
        # Sample user
        sample_user = User(
            user_id="u1",
            name="Sample User",
            email="user@example.com",
            preferences={"favorite_categories": ["Electronics", "Smart Home"]}
        )
        
        session.add(sample_user)
        
        # Sample order
        sample_order = Order(
            order_id="o1",
            user_id="u1",
            products=[],  # Will add through OrderItems
            total_amount=149.97,
            status="shipped"
        )
        
        session.add(sample_order)
        
        # Commit to save products, user and order first
        session.commit()
        
        # Add order items
        order_items = [
            OrderItem(order_id="o1", product_id="p1", quantity=1),
            OrderItem(order_id="o1", product_id="p2", quantity=2)
        ]
        
        session.add_all(order_items)
        session.commit()
        
        logger.info("Sample data added successfully")
    
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to add sample data: {str(e)}", exc_info=True)
    
    finally:
        session.close()

def get_products(limit=10):
    """Get a list of products from the database."""
    try:
        session = db_session()
        products = session.query(Product).limit(limit).all()
        return products
    
    except Exception as e:
        logger.error(f"Error getting products: {str(e)}", exc_info=True)
        return []
    
    finally:
        session.close()

def get_product_by_id(product_id):
    """Get a product by ID from the database."""
    try:
        session = db_session()
        product = session.query(Product).filter(Product.product_id == product_id).first()
        return product
    
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {str(e)}", exc_info=True)
        return None
    
    finally:
        session.close()

def get_order_by_id(order_id):
    """Get an order by ID from the database."""
    try:
        session = db_session()
        order = session.query(Order).filter(Order.order_id == order_id).first()
        return order
    
    except Exception as e:
        logger.error(f"Error getting order {order_id}: {str(e)}", exc_info=True)
        return None
    
    finally:
        session.close()

def search_products(query, limit=5):
    """
    Search for products based on a query string.
    Searches in product name, description, and category.
    """
    try:
        session = db_session()
        
        # Search using SQLAlchemy's like operator
        query = f"%{query.lower()}%"
        products = session.query(Product).filter(
            db.or_(
                db.func.lower(Product.name).like(query),
                db.func.lower(Product.description).like(query),
                db.func.lower(Product.category).like(query)
            )
        ).limit(limit).all()
        
        return products
    
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}", exc_info=True)
        
        # Fallback to simpler search
        try:
            session = db_session()
            all_products = session.query(Product).all()
            
            results = []
            query_text = query.replace("%", "").lower()
            
            for product in all_products:
                if (query_text in product.name.lower() or 
                    query_text in product.description.lower() or 
                    query_text in product.category.lower()):
                    results.append(product)
                
                if len(results) >= limit:
                    break
            
            return results
        
        except Exception:
            return []
    
    finally:
        session.close()

def get_trending_products(limit=3):
    """
    Get trending or recommended products.
    In a real application, this would use more sophisticated logic.
    """
    return get_products(limit=limit)

def get_user_by_id(user_id):
    """Get a user by ID from the database."""
    try:
        session = db_session()
        user = session.query(User).filter(User.user_id == user_id).first()
        return user
    
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}", exc_info=True)
        return None
    
    finally:
        session.close()

def add_product(product):
    """Add a new product to the database."""
    try:
        session = db_session()
        
        # If product already exists in database, update it
        existing_product = session.query(Product).filter(
            Product.product_id == product.product_id
        ).first()
        
        if existing_product:
            return update_product(product)
        
        session.add(product)
        session.commit()
        return product
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding product: {str(e)}", exc_info=True)
        return None
    
    finally:
        session.close()

def update_product(product):
    """Update a product in the database."""
    try:
        session = db_session()
        
        existing_product = session.query(Product).filter(
            Product.product_id == product.product_id
        ).first()
        
        if existing_product:
            existing_product.name = product.name
            existing_product.description = product.description
            existing_product.price = product.price
            existing_product.category = product.category
            existing_product.image_url = product.image_url
            existing_product.in_stock = product.in_stock
            
            session.commit()
            return existing_product
        
        return None
    
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating product: {str(e)}", exc_info=True)
        return None
    
    finally:
        session.close()

# Clean up function for Flask app shutdown
def close_db_session():
    db_session.remove()
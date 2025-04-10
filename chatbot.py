"""
Chatbot module with NLP capabilities to understand user intent, 
process queries, and generate appropriate responses.
This version uses Google's Gemini API for natural language processing.
"""

import os
import json
import logging
import random
import google.generativeai as genai
from database_service import (
    get_products, get_product_by_id, get_order_by_id,
    search_products, get_trending_products
)
# Keep Firebase import for backwards compatibility
import firebase_service

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Define intent categories
INTENTS = {
    "PRODUCT_SEARCH": "search for products",
    "PRODUCT_INFO": "get information about a specific product",
    "ORDER_STATUS": "check the status of an order",
    "RECOMMENDATIONS": "get product recommendations",
    "GENERAL_QUESTION": "answer a general question about shopping",
    "GREETING": "respond to a greeting",
    "SUPPORT": "provide customer support",
    "PRICE_INQUIRY": "inquire about the price of a product",
    "COMPARISON": "compare products",
    "CHECKOUT_HELP": "help with checkout process"
}

# Chat session history stored by session ID
chat_histories = {}

def detect_intent(message):
    """
    Use Gemini to detect the intent of the user message.
    Returns the detected intent and entities.
    """
    try:
        prompt = f"""
        Analyze the following e-commerce customer message and determine the user's intent.
        Choose the most appropriate intent category from this list:
        {', '.join(INTENTS.keys())}
        
        Also extract any relevant entities like product names, categories, order IDs, etc.
        
        Customer message: "{message}"
        
        Respond in JSON format:
        {{
            "intent": "INTENT_CATEGORY",
            "confidence": 0.0-1.0,
            "entities": {{
                "product": "extracted product name or null",
                "category": "extracted category or null",
                "order_id": "extracted order ID or null",
                "price_range": "extracted price range or null"
            }}
        }}
        """
        
        generation_config = {
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40,
        }
        
        # List available models to use the correct format
        models = genai.list_models()
        logger.debug(f"Available models: {[model.name for model in models]}")
        
        # Use the first available model that supports text generation
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro", generation_config=generation_config)
        response = model.generate_content(prompt)
        
        if hasattr(response, 'text'):
            result = json.loads(response.text)
        else:
            # Handle case where response is already parsed
            parts = response.candidates[0].content.parts
            result = json.loads(parts[0].text)
        
        logger.debug(f"Intent detection result: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error detecting intent: {str(e)}", exc_info=True)
        return {
            "intent": "GENERAL_QUESTION",
            "confidence": 0.5,
            "entities": {}
        }

def generate_product_recommendations(query=None, category=None, limit=3):
    """
    Generate product recommendations based on the query and/or category.
    If no specific query/category, return trending products.
    """
    if query:
        products = search_products(query, limit=limit)
    elif category:
        products = search_products(category, limit=limit)
    else:
        products = get_trending_products(limit=limit)
    
    return products

def format_product_for_display(product):
    """Format a product object for display in the chat."""
    return {
        "id": product.product_id,
        "name": product.name,
        "description": product.description,
        "price": f"${product.price:.2f}",
        "category": product.category,
        "image_url": product.image_url,
        "in_stock": "In Stock" if product.in_stock else "Out of Stock"
    }

def get_order_status_response(order_id):
    """Generate a response about an order's status."""
    order = get_order_by_id(order_id)
    
    if not order:
        return {
            "message": f"I couldn't find order #{order_id}. Please check the order number and try again.",
            "data": None
        }
    
    return {
        "message": f"Your order #{order_id} is currently {order.status}. It contains {len(order.products)} item(s) with a total of ${order.total_amount:.2f}.",
        "data": {"order": order.to_dict()}
    }

def handle_product_search(entities):
    """Handle a product search intent."""
    product_name = entities.get("product")
    category = entities.get("category")
    
    if product_name:
        products = search_products(product_name)
        if products:
            formatted_products = [format_product_for_display(p) for p in products]
            return {
                "message": f"I found the following products matching '{product_name}':",
                "data": {"products": formatted_products}
            }
        else:
            return {
                "message": f"I couldn't find any products matching '{product_name}'. Would you like to see some recommendations instead?",
                "data": None
            }
    
    elif category:
        products = search_products(category)
        if products:
            formatted_products = [format_product_for_display(p) for p in products]
            return {
                "message": f"Here are some products in the '{category}' category:",
                "data": {"products": formatted_products}
            }
        else:
            return {
                "message": f"I couldn't find any products in the '{category}' category. Would you like to see our popular products instead?",
                "data": None
            }
    
    else:
        return {
            "message": "What kind of product are you looking for? You can specify a product name or category.",
            "data": None
        }

def handle_product_info(entities):
    """Handle a request for specific product information."""
    product_name = entities.get("product")
    
    if not product_name:
        return {
            "message": "Which product would you like information about?",
            "data": None
        }
    
    products = search_products(product_name, limit=1)
    
    if not products:
        return {
            "message": f"I couldn't find any information about '{product_name}'. Can you try with a different product name?",
            "data": None
        }
    
    product = products[0]
    formatted_product = format_product_for_display(product)
    
    return {
        "message": f"Here's information about {product.name}:\n{product.description}\nPrice: ${product.price:.2f}\nCategory: {product.category}",
        "data": {"product": formatted_product}
    }

def handle_recommendations(entities):
    """Handle a request for product recommendations."""
    category = entities.get("category")
    product_name = entities.get("product")
    
    if category:
        products = generate_product_recommendations(category=category)
    elif product_name:
        products = generate_product_recommendations(query=product_name)
    else:
        products = generate_product_recommendations()
    
    if not products:
        return {
            "message": "I don't have any recommendations at the moment. Is there a specific category you're interested in?",
            "data": None
        }
    
    formatted_products = [format_product_for_display(p) for p in products]
    
    if category:
        message = f"Based on your interest in {category}, here are some recommendations:"
    elif product_name:
        message = f"If you like {product_name}, you might also like these products:"
    else:
        message = "Here are some popular products you might be interested in:"
    
    return {
        "message": message,
        "data": {"products": formatted_products}
    }

def handle_greeting():
    """Handle a greeting intent."""
    greetings = [
        "Hello! How can I help with your shopping today?",
        "Hi there! Looking for something specific in our store?",
        "Welcome! I'm your shopping assistant. What can I help you find today?",
        "Greetings! I'm here to help you find the perfect product. What are you looking for?"
    ]
    return {
        "message": random.choice(greetings),
        "data": None
    }

def generate_general_response(message, intent_info):
    """
    Generate a general response for queries that don't fall into specific categories
    using Gemini.
    """
    try:
        prompt = f"""
        You are a helpful e-commerce assistant. 
        The customer has sent this message: "{message}"
        
        Based on the detected intent ({intent_info['intent']}), provide a helpful, friendly response.
        Keep your answer brief, friendly, and focused on helping them shop.
        Do not fabricate specific product information or prices.
        """
        
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro")
        response = model.generate_content(prompt)
        
        if hasattr(response, 'text'):
            return {
                "message": response.text,
                "data": None
            }
        else:
            return {
                "message": response.candidates[0].content.parts[0].text,
                "data": None
            }
    except Exception as e:
        logger.error(f"Error generating general response: {str(e)}", exc_info=True)
        return {
            "message": "I'm here to help with your shopping needs. Could you please provide more details about what you're looking for?",
            "data": None
        }

def process_user_message(message, session_id):
    """
    Process a user message, detect intent, and generate an appropriate response.
    """
    try:
        # Add message to chat history
        if session_id not in chat_histories:
            chat_histories[session_id] = []
        
        chat_histories[session_id].append({"role": "user", "message": message})
        
        # Detect the intent of the message
        intent_info = detect_intent(message)
        intent = intent_info.get("intent", "GENERAL_QUESTION")
        entities = intent_info.get("entities", {})
        
        # Handle different intents
        if intent == "PRODUCT_SEARCH":
            response = handle_product_search(entities)
        
        elif intent == "PRODUCT_INFO":
            response = handle_product_info(entities)
        
        elif intent == "ORDER_STATUS":
            order_id = entities.get("order_id")
            if order_id:
                response = get_order_status_response(order_id)
            else:
                response = {
                    "message": "Could you provide your order number so I can check its status?",
                    "data": None
                }
        
        elif intent == "RECOMMENDATIONS":
            response = handle_recommendations(entities)
        
        elif intent == "GREETING":
            response = handle_greeting()
        
        else:
            # For other intents, generate a general response
            response = generate_general_response(message, intent_info)
        
        # Add response to chat history
        chat_histories[session_id].append({
            "role": "assistant", 
            "message": response["message"],
            "data": response.get("data")
        })
        
        # Limit chat history size
        if len(chat_histories[session_id]) > 20:
            chat_histories[session_id] = chat_histories[session_id][-20:]
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        return {
            "message": "I'm sorry, I encountered an error while processing your message. Please try again.",
            "error": str(e)
        }

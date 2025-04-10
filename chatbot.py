"""
Chatbot module with NLP capabilities to understand user intent, 
process queries, and generate appropriate responses.
This version uses Google's Gemini API for natural language processing.
"""

import os
import json
import logging
import random
import base64
import time
import urllib.parse
import google.generativeai as genai
from database_service import (
    get_products, get_product_by_id, get_order_by_id,
    search_products, get_trending_products
)
# Keep Firebase import for backwards compatibility
import firebase_service
# Import analytics service for tracking metrics
import analytics_service

# Helper function to encode URI components
def encodeURIComponent(string):
    """
    Encode a string for inclusion in a URL query parameter.
    Similar to JavaScript's encodeURIComponent
    """
    return urllib.parse.quote(string, safe='')

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

def analyze_image(image_path):
    """
    Use Gemini's vision capabilities to analyze an image.
    Returns product information, description, and other details.
    """
    try:
        # Read the image file
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        
        # Encode image as base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create multimodal content with image
        model = genai.GenerativeModel(model_name="models/gemini-1.5-pro")
        
        # Format prompt for product analysis
        prompt = """
        Analyze this product image in detail and provide the following information in JSON format:
        - Product name/type
        - Brief description (3-4 sentences)
        - Key features (list 3-5 main features)
        - Estimated price range
        - Recommended uses
        - Product category
        
        For retail products, focus on specifications, materials, and potential uses.
        For technology products, focus on technical specifications and capabilities.
        
        Format your response as a valid JSON object with these fields:
        {
          "product_name": "Name of product",
          "description": "Detailed product description",
          "features": ["feature 1", "feature 2", "feature 3"],
          "price_range": "$XX - $XX",
          "category": "Product category",
          "recommended_uses": ["use 1", "use 2"]
        }
        
        Return ONLY the JSON, nothing else.
        """
        
        # Generate content with image
        response = model.generate_content(
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
                    ]
                }
            ]
        )
        
        # Extract JSON response
        if hasattr(response, 'text'):
            # Parse the JSON results
            try:
                result = json.loads(response.text)
                logger.debug(f"Image analysis result: {result}")
                return result
            except json.JSONDecodeError:
                # If not valid JSON, try to extract JSON from the text
                import re
                json_match = re.search(r'({[\s\S]*})', response.text)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1))
                        logger.debug(f"Extracted image analysis result: {result}")
                        return result
                    except json.JSONDecodeError:
                        logger.error("Failed to parse extracted JSON")
                        return None
                logger.error("Failed to extract JSON from response")
                return None
        else:
            # Handle case where response is already parsed
            parts = response.candidates[0].content.parts
            try:
                result = json.loads(parts[0].text)
                logger.debug(f"Image analysis result: {result}")
                return result
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON from response parts")
                return None
    
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}", exc_info=True)
        return None

def get_similar_products(product_info, limit=3):
    """
    Find similar products based on the analyzed product information.
    """
    if not product_info:
        return []
    
    # Extract relevant fields for search
    product_name = product_info.get('product_name', '')
    category = product_info.get('category', '')
    
    # Search for similar products
    if product_name and category:
        query = f"{product_name} {category}"
        products = search_products(query, limit=limit)
    elif product_name:
        products = search_products(product_name, limit=limit)
    elif category:
        products = search_products(category, limit=limit)
    else:
        # If no useful info, return trending products
        products = get_trending_products(limit=limit)
    
    return products

def process_image_message(message, image_path, session_id):
    """
    Process a user message with an attached image.
    Analyzes the image, extracts product information, and finds similar products.
    """
    try:
        # Add message to chat history
        if session_id not in chat_histories:
            chat_histories[session_id] = []
        
        # Add user message with image indicator
        chat_histories[session_id].append({"role": "user", "message": message, "has_image": True})
        
        # Analyze the image
        product_info = analyze_image(image_path)
        
        if not product_info:
            response = {
                "message": "I couldn't analyze this image properly. Could you please try a clearer image or describe what you're looking for?",
                "data": None
            }
        else:
            # Find similar products
            similar_products = get_similar_products(product_info)
            formatted_products = [format_product_for_display(p) for p in similar_products] if similar_products else []
            
            # Create detailed response about the image and similar products
            product_name = product_info.get('product_name', 'product')
            category = product_info.get('category', 'item')
            price_range = product_info.get('price_range', '')
            description = product_info.get('description', '')
            features = product_info.get('features', [])
            recommended_uses = product_info.get('recommended_uses', [])
            
            # Format features as bullet points
            features_text = "\n• " + "\n• ".join(features) if features else ""
            
            # Format uses as bullet points if available
            uses_text = ""
            if recommended_uses:
                uses_text = "\n\nRecommended uses:" 
                uses_text += "\n• " + "\n• ".join(recommended_uses)
            
            # Extract a potential price value from the price range
            price_value = None
            if price_range:
                import re
                price_match = re.search(r'\$(\d+(?:\.\d{1,2})?)', price_range)
                if price_match:
                    price_value = float(price_match.group(1))
            
            # Create a product object that can be displayed properly
            analyzed_product_display = {
                "id": "analyzed-product",
                "name": product_name,
                "description": description,
                "price": price_range,
                "category": category,
                "image_url": None,  # We don't have an image URL for the analyzed product
                "in_stock": "Not Available",
                "features": features,
                "recommended_uses": recommended_uses
            }
            
            if price_value:
                analyzed_product_display["price"] = f"${price_value:.2f}"
            
            # Prepare search link for Amazon
            search_query = encodeURIComponent(product_name)
            amazon_url = f"https://www.amazon.com/s?k={search_query}"
            
            # Construct the response
            if similar_products:
                message_text = f"## Product Analysis: {product_name}\n\n"
                message_text += f"**Category:** {category}\n"
                message_text += f"**Price Range:** {price_range}\n\n"
                message_text += f"{description}\n\n"
                message_text += f"**Key Features:**{features_text}"
                message_text += uses_text
                message_text += f"\n\n[View on Amazon]({amazon_url})\n\n"
                message_text += "I found some similar products in our catalog that might interest you:"
                
                response = {
                    "message": message_text,
                    "data": {
                        "products": formatted_products, 
                        "analyzed_product": product_info,
                        "amazon_url": amazon_url
                    }
                }
            else:
                message_text = f"## Product Analysis: {product_name}\n\n"
                message_text += f"**Category:** {category}\n"
                message_text += f"**Price Range:** {price_range}\n\n"
                message_text += f"{description}\n\n"
                message_text += f"**Key Features:**{features_text}"
                message_text += uses_text
                message_text += f"\n\n[View on Amazon]({amazon_url})\n\n"
                message_text += "I don't have any similar products in our catalog at the moment. Would you like me to help you find something else?"
                
                response = {
                    "message": message_text,
                    "data": {
                        "analyzed_product": product_info,
                        "amazon_url": amazon_url
                    }
                }
        
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
        logger.error(f"Error processing image message: {str(e)}", exc_info=True)
        return {
            "message": "I'm sorry, I encountered an error analyzing this image. Please try again or describe the product you're looking for.",
            "error": str(e)
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

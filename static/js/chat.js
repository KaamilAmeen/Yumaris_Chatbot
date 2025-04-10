/**
 * E-commerce AI Chatbot Frontend Script
 * Handles chat interface, message sending/receiving, and displaying product recommendations
 */

// Generate a unique session ID for this chat
const sessionId = 'session_' + Math.random().toString(36).substring(2, 15);

// DOM Elements
const chatContainer = document.getElementById('chat-container');
const messageForm = document.getElementById('message-form');
const userInput = document.getElementById('user-input');
const clearChatBtn = document.getElementById('clearChatBtn');
const productCarouselContainer = document.getElementById('product-carousel-container');
const productCarousel = document.getElementById('product-carousel');

// Initialize the chat
document.addEventListener('DOMContentLoaded', function() {
    // Scroll to bottom of chat
    scrollToBottom();
    
    // Focus on input field
    userInput.focus();
    
    // Set up event listeners
    messageForm.addEventListener('submit', sendMessage);
    clearChatBtn.addEventListener('click', clearChat);
});

/**
 * Send a user message to the backend
 */
function sendMessage(e) {
    e.preventDefault();
    
    const message = userInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    
    // Clear input field
    userInput.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send message to backend
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: message,
            session_id: sessionId
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Remove typing indicator
        removeTypingIndicator();
        
        // Add bot response to chat
        addMessageToChat('bot', data.message);
        
        // Handle any additional data (like product recommendations)
        if (data.data) {
            handleResponseData(data.data);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        removeTypingIndicator();
        addMessageToChat('bot', 'Sorry, I encountered an error. Please try again.');
    });
}

/**
 * Add a message to the chat container
 */
function addMessageToChat(role, message) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Process message text (handle markdown-like formatting)
    const formattedMessage = message.replace(/\n/g, '<br>');
    contentDiv.innerHTML = `<p>${formattedMessage}</p>`;
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom of chat
    scrollToBottom();
}

/**
 * Show typing indicator in the chat
 */
function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot typing';
    typingDiv.id = 'typing-indicator';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    
    typingDiv.appendChild(contentDiv);
    chatContainer.appendChild(typingDiv);
    scrollToBottom();
}

/**
 * Remove typing indicator from the chat
 */
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

/**
 * Handle additional data in the response (like product recommendations)
 */
function handleResponseData(data) {
    // Handle product recommendations
    if (data.products && data.products.length > 0) {
        displayProducts(data.products);
    } 
    // Handle single product
    else if (data.product) {
        displayProducts([data.product]);
    } 
    // Handle order data
    else if (data.order) {
        // Currently not displaying order UI, but could be added
        console.log('Order data:', data.order);
    } 
    // Hide product container if no relevant data
    else {
        productCarouselContainer.classList.add('d-none');
    }
}

/**
 * Display products in the product carousel
 */
function displayProducts(products) {
    // Clear previous products
    productCarousel.innerHTML = '';
    
    // Create product cards
    products.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'col';
        
        productCard.innerHTML = `
            <div class="card h-100 product-card">
                <div class="card-body">
                    <h5 class="card-title">${product.name}</h5>
                    <p class="card-text small">${product.description.substring(0, 100)}${product.description.length > 100 ? '...' : ''}</p>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge bg-primary">${product.price}</span>
                        <span class="badge ${product.in_stock === 'In Stock' ? 'bg-success' : 'bg-danger'}">${product.in_stock}</span>
                    </div>
                </div>
                <div class="card-footer">
                    <button class="btn btn-sm btn-outline-primary w-100 product-info-btn" 
                            data-product-id="${product.id}">
                        More Info
                    </button>
                </div>
            </div>
        `;
        
        productCarousel.appendChild(productCard);
    });
    
    // Show product carousel
    productCarouselContainer.classList.remove('d-none');
    
    // Add event listeners to product buttons
    document.querySelectorAll('.product-info-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const productId = this.getAttribute('data-product-id');
            userInput.value = `Tell me more about product ${productId}`;
            messageForm.dispatchEvent(new Event('submit'));
        });
    });
    
    // Scroll to see products
    productCarouselContainer.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Clear the chat history
 */
function clearChat() {
    // Remove all messages except the first welcome message
    const messages = chatContainer.querySelectorAll('.message');
    for (let i = 1; i < messages.length; i++) {
        messages[i].remove();
    }
    
    // Hide product carousel
    productCarouselContainer.classList.add('d-none');
    
    // Focus on input field
    userInput.focus();
}

/**
 * Scroll to the bottom of the chat container
 */
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * E-commerce AI Chatbot Frontend Script
 * Handles chat interface, message sending/receiving, displaying product recommendations,
 * voice input, and file attachments
 */

// Generate a unique session ID for this chat
const sessionId = typeof uuid === 'function' ? uuid.v4() : 'session_' + Math.random().toString(36).substring(2, 15);

// DOM Elements
const chatContainer = document.getElementById('chat-container');
const messageForm = document.getElementById('message-form');
const userInput = document.getElementById('user-input');
const clearChatBtn = document.getElementById('clearChatBtn');
const productCarouselContainer = document.getElementById('product-carousel-container');
const productCarousel = document.getElementById('product-carousel');
const voiceInputBtn = document.getElementById('voice-input-btn');
const voiceStatus = document.getElementById('voice-status');
const fileUpload = document.getElementById('file-upload');
const filePreviewContainer = document.getElementById('file-preview-container');
const imagePreview = document.getElementById('image-preview');
const removeFileBtn = document.getElementById('remove-file');

// File attachment state
let currentAttachment = null;

// Initialize the chat
document.addEventListener('DOMContentLoaded', function() {
    // Scroll to bottom of chat
    scrollToBottom();
    
    // Focus on input field
    userInput.focus();
    
    // Set up event listeners
    messageForm.addEventListener('submit', sendMessage);
    clearChatBtn.addEventListener('click', clearChat);
    
    // Voice input
    if (voiceInputBtn) {
        voiceInputBtn.addEventListener('click', toggleVoiceInput);
    }
    
    // File attachment
    if (fileUpload) {
        fileUpload.addEventListener('change', handleFileUpload);
    }
    
    // Remove file button
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', removeAttachment);
    }
});

/**
 * Send a user message to the backend
 */
function sendMessage(e) {
    e.preventDefault();
    
    const message = userInput.value.trim();
    
    // Check if we have a file attachment
    if (currentAttachment) {
        sendMessageWithAttachment();
        return;
    }
    
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
        
        // Add bot response to chat with product links
        addMessageToChat('bot', formatMessageWithLinks(data.message));
        
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
 * Format message text with Amazon links
 * This transforms product mentions into clickable Amazon links
 */
function formatMessageWithLinks(message) {
    // Pattern to match product mentions - adjust as needed
    // This example looks for product names in quotes or mentions of "Product X"
    return message.replace(/(["'])([^"']+?)(["'])/g, function(match, p1, p2, p3) {
        // Only transform if it looks like a product (contains specific keywords or patterns)
        if (p2.match(/phone|camera|laptop|headphone|speaker|watch|tablet|TV|monitor|keyboard|mouse|book/i)) {
            const searchQuery = encodeURIComponent(p2);
            return `${p1}<a href="https://www.amazon.com/s?k=${searchQuery}" target="_blank" class="product-link">${p2}</a>${p3}`;
        }
        return match;
    }).replace(/\b(the |a |an )?([\w\s]+?)( product| device| gadget| item)\b/gi, function(match, article, product, suffix) {
        if (product.length > 3) { // Avoid linking very short terms
            const searchQuery = encodeURIComponent(product.trim());
            return `${article || ''}<a href="https://www.amazon.com/s?k=${searchQuery}" target="_blank" class="product-link">${product}</a>${suffix}`;
        }
        return match;
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
        
        // Format price to include sale price and original price if available
        const priceDisplay = formatPriceDisplay(product);
        
        // Create product search query for Amazon
        const searchQuery = encodeURIComponent(product.name);
        const amazonUrl = `https://www.amazon.com/s?k=${searchQuery}`;
        
        // Handle product image with fallback
        const imageUrl = product.image_url || 'https://via.placeholder.com/150x150?text=No+Image';
        
        // Get current price from price display (removing any HTML tags and symbols)
        const currentPrice = extractCurrentPrice(product.price);
        const priceLabel = `$${currentPrice}`;
        
        // Additional product details
        const productDetails = getProductDetails(product);
        
        productCard.innerHTML = `
            <div class="card h-100 product-card shadow">
                <div class="position-relative">
                    <div class="text-center p-2 bg-light product-image-container">
                        <img src="${imageUrl}" alt="${product.name}" class="img-fluid product-img" style="height: 180px; object-fit: contain;">
                    </div>
                    <div class="position-absolute top-0 end-0 p-2">
                        <span class="badge ${product.in_stock === 'In Stock' ? 'bg-success' : 'bg-danger'} fs-6">${product.in_stock}</span>
                    </div>
                    <div class="position-absolute bottom-0 start-0 p-2">
                        <div class="bg-dark bg-opacity-75 text-white px-2 py-1 rounded price-tag">
                            <span class="fs-5 fw-bold">${priceLabel}</span>
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    <h5 class="card-title fw-bold">${product.name}</h5>
                    <p class="card-text small">${product.description.substring(0, 100)}${product.description.length > 100 ? '...' : ''}</p>
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        ${priceDisplay}
                    </div>
                    <div class="product-details small">
                        ${productDetails}
                    </div>
                </div>
                <div class="card-footer d-flex">
                    <button class="btn btn-sm btn-outline-primary flex-grow-1 me-1 product-info-btn" 
                            data-product-id="${product.id}">
                        <i class="fas fa-info-circle"></i> Details
                    </button>
                    <a href="${amazonUrl}" target="_blank" class="btn btn-sm btn-warning flex-grow-1" title="View on Amazon">
                        <i class="fas fa-shopping-cart"></i> Amazon
                    </a>
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
 * Extract numeric price from price string
 */
function extractCurrentPrice(priceString) {
    // Remove $ symbol and any other non-numeric characters except decimal point
    if (typeof priceString === 'string') {
        const numericString = priceString.replace(/[^0-9.]/g, '');
        return parseFloat(numericString).toFixed(2);
    } else if (typeof priceString === 'number') {
        return priceString.toFixed(2);
    }
    
    return "0.00";
}

/**
 * Get formatted product details
 */
function getProductDetails(product) {
    let details = '';
    
    // Add category
    if (product.category) {
        details += `<div><i class="fas fa-tag me-1 text-secondary"></i> ${product.category}</div>`;
    }
    
    // Add model/type if available
    if (product.model) {
        details += `<div><i class="fas fa-cube me-1 text-secondary"></i> ${product.model}</div>`;
    }
    
    // Add brand if available
    if (product.brand) {
        details += `<div><i class="fas fa-trademark me-1 text-secondary"></i> ${product.brand}</div>`;
    }
    
    // Add rating if available
    if (product.rating) {
        const stars = '★'.repeat(Math.floor(product.rating)) + '☆'.repeat(5 - Math.floor(product.rating));
        details += `<div><i class="fas fa-star me-1 text-warning"></i> ${stars} (${product.rating})</div>`;
    }
    
    // Add warranty if available
    if (product.warranty) {
        details += `<div><i class="fas fa-shield-alt me-1 text-secondary"></i> ${product.warranty}</div>`;
    }
    
    return details || '<div class="text-muted">No additional details available</div>';
}

/**
 * Format the price display to show sale pricing
 */
function formatPriceDisplay(product) {
    // Default pricing display
    let priceDisplay = `<span class="badge bg-primary">${product.price}</span>`;
    
    // If we have sale pricing details
    if (product.original_price && product.original_price !== product.price) {
        const originalPrice = typeof product.original_price === 'string' ? 
            product.original_price : 
            `$${parseFloat(product.original_price).toFixed(2)}`;
            
        const discount = calculateDiscount(product.price, product.original_price);
        
        priceDisplay = `
            <div class="d-flex flex-column">
                <span class="badge bg-danger">${product.price} <small class="text-white">-${discount}%</small></span>
                <small class="text-decoration-line-through text-muted">${originalPrice}</small>
            </div>
        `;
    }
    
    return priceDisplay;
}

/**
 * Calculate discount percentage between current and original price
 */
function calculateDiscount(currentPrice, originalPrice) {
    // Extract numeric values from price strings if needed
    const current = typeof currentPrice === 'string' ? 
        parseFloat(currentPrice.replace(/[^0-9.]/g, '')) : 
        parseFloat(currentPrice);
        
    const original = typeof originalPrice === 'string' ? 
        parseFloat(originalPrice.replace(/[^0-9.]/g, '')) : 
        parseFloat(originalPrice);
    
    if (original > 0 && current < original) {
        const discountPercent = Math.round((1 - (current / original)) * 100);
        return discountPercent;
    }
    
    return 0;
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

/**
 * Handle voice input for the chat
 */
function toggleVoiceInput() {
    // Check if the Web Speech API is available
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Your browser does not support speech recognition. Please try Chrome or Edge.');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    
    // Show listening status
    voiceStatus.classList.remove('d-none');
    voiceInputBtn.classList.add('btn-danger');
    voiceInputBtn.classList.remove('btn-outline-secondary');
    
    recognition.start();
    
    recognition.onresult = function(event) {
        const speechResult = event.results[0][0].transcript;
        userInput.value = speechResult;
        
        // Hide listening status
        voiceStatus.classList.add('d-none');
        voiceInputBtn.classList.remove('btn-danger');
        voiceInputBtn.classList.add('btn-outline-secondary');
        
        // Focus on input to allow editing if needed
        userInput.focus();
    };
    
    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        
        // Hide listening status
        voiceStatus.classList.add('d-none');
        voiceInputBtn.classList.remove('btn-danger');
        voiceInputBtn.classList.add('btn-outline-secondary');
    };
    
    recognition.onend = function() {
        // Hide listening status
        voiceStatus.classList.add('d-none');
        voiceInputBtn.classList.remove('btn-danger');
        voiceInputBtn.classList.add('btn-outline-secondary');
    };
}

/**
 * Handle file upload for the chat
 */
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) {
        return;
    }
    
    // For now, only support image files
    if (!file.type.startsWith('image/')) {
        alert('Only image files are supported at this time.');
        fileUpload.value = '';
        return;
    }
    
    // Store the file for sending
    currentAttachment = file;
    
    // Preview the image
    const reader = new FileReader();
    reader.onload = function(e) {
        const img = imagePreview.querySelector('img');
        img.src = e.target.result;
        imagePreview.classList.remove('d-none');
    };
    reader.readAsDataURL(file);
    
    // Show the file preview container
    filePreviewContainer.classList.remove('d-none');
    
    // Add a message in the input field
    userInput.value = `I'm sending an image of ${file.name.replace(/\.[^/.]+$/, '')}.`;
    userInput.focus();
}

/**
 * Remove the current file attachment
 */
function removeAttachment() {
    currentAttachment = null;
    fileUpload.value = '';
    filePreviewContainer.classList.add('d-none');
    imagePreview.classList.add('d-none');
    userInput.value = '';
    userInput.focus();
}

/**
 * Send a message with a file attachment
 */
function sendMessageWithAttachment() {
    if (!currentAttachment) {
        return;
    }
    
    const message = userInput.value.trim() || `I'm sending an image.`;
    
    // Add user message to chat with image preview
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    contentDiv.innerHTML = `<p>${message}</p>`;
    
    // Add image preview
    const imgContainer = document.createElement('div');
    imgContainer.className = 'image-attachment mt-2';
    
    const img = document.createElement('img');
    img.className = 'img-fluid rounded';
    img.style.maxHeight = '150px';
    
    const reader = new FileReader();
    reader.onload = function(e) {
        img.src = e.target.result;
        
        // Add to DOM
        imgContainer.appendChild(img);
        contentDiv.appendChild(imgContainer);
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        scrollToBottom();
        
        // Now send to backend with the file
        sendFileToBackend(message, currentAttachment);
    };
    reader.readAsDataURL(currentAttachment);
    
    // Clear input and file attachment
    userInput.value = '';
    removeAttachment();
}

/**
 * Send a file to the backend with a message
 */
function sendFileToBackend(message, file) {
    // Show typing indicator
    showTypingIndicator();
    
    const formData = new FormData();
    formData.append('message', message);
    formData.append('session_id', sessionId);
    formData.append('file', file);
    
    fetch('/api/chat-with-file', {
        method: 'POST',
        body: formData
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
        
        // Handle any additional data
        if (data.data) {
            handleResponseData(data.data);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        removeTypingIndicator();
        addMessageToChat('bot', 'Sorry, I encountered an error processing your file. Please try again.');
    });
}

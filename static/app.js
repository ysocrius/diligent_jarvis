/**
 * Build Your Own Jarvis - Frontend JavaScript
 * Handles chat functionality and communication with Flask backend
 */

class JarvisChat {
    constructor() {
        this.apiUrl = '/api';
        this.initializeElements();
        this.bindEvents();
        this.checkStatus();
        this.loadExampleQuestions();
        this.conversationHistory = [];
        this.isTyping = false;
    }
    
    initializeElements() {
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.sendText = document.getElementById('sendText');
        this.sendSpinner = document.getElementById('sendSpinner');
        this.chatMessages = document.getElementById('chat-messages');
        this.clearBtn = document.getElementById('clearBtn');
        this.statusDiv = document.getElementById('status');
        this.errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
        this.successToast = new bootstrap.Toast(document.getElementById('successToast'));
    }
    
    bindEvents() {
        // Send button click
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Enter key to send
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Clear conversation
        this.clearBtn.addEventListener('click', () => this.clearConversation());
        
        // Example questions
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('example-question')) {
                const question = e.target.getAttribute('data-question');
                this.messageInput.value = question;
                this.sendMessage();
            }
        });
        
        // Status refresh
        setInterval(() => this.checkStatus(), 30000); // Check every 30 seconds
    }
    
    async checkStatus() {
        try {
            const response = await fetch(`${this.apiUrl}/status`);
            const data = await response.json();
            
            if (data.status === 'running') {
                this.updateStatus('success', `Connected - ${data.pinecone_index} | ${data.openai_model}`);
            } else {
                this.updateStatus('error', 'System offline');
            }
        } catch (error) {
            this.updateStatus('error', 'Cannot connect to server');
            console.error('Status check failed:', error);
        }
    }
    
    async loadExampleQuestions() {
        try {
            const response = await fetch(`${this.apiUrl}/example-questions`);
            const data = await response.json();
            
            const containers = document.querySelectorAll('#example-questions-container');
            containers.forEach(container => {
                container.innerHTML = '';
                
                if (data.questions && data.questions.length > 0) {
                    data.questions.forEach(question => {
                        const button = document.createElement('button');
                        button.className = 'btn btn-outline-primary btn-sm example-question';
                        button.setAttribute('data-question', question);
                        button.textContent = question;
                        container.appendChild(button);
                    });
                }
            });
        } catch (error) {
            console.error('Failed to load example questions:', error);
            // Fallback to default questions
            const containers = document.querySelectorAll('#example-questions-container');
            containers.forEach(container => {
                container.innerHTML = `
                    <button class="btn btn-outline-primary btn-sm example-question" data-question="What can you help me with?">What can you help me with?</button>
                    <button class="btn btn-outline-primary btn-sm example-question" data-question="Tell me about your capabilities">Tell me about your capabilities</button>
                `;
            });
        }
    }
    
    updateStatus(status, message) {
        this.statusDiv.innerHTML = '';
        
        let statusIcon = '';
        let statusClass = '';
        
        switch (status) {
            case 'success':
                statusIcon = '<span class="me-2 text-success">✓</span>';
                statusClass = 'status-success';
                break;
            case 'error':
                statusIcon = '<span class="me-2 text-danger">✗</span>';
                statusClass = 'status-error';
                break;
            case 'loading':
            default:
                statusIcon = '<div class="spinner-border spinner-border-sm me-2" role="status"></div>';
                statusClass = 'status-loading';
                break;
        }
        
        this.statusDiv.innerHTML = `${statusIcon}<span class="${statusClass}">${message}</span>`;
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || this.isTyping) return;
        
        // Add user message to UI
        this.addMessageToUI(message, 'user');
        this.messageInput.value = '';
        this.isTyping = true;
        
        // Show typing indicator
        this.showTypingIndicator();
        this.setSendButtonState('loading');
        
        try {
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                // Add assistant response to UI
                setTimeout(() => {
                    this.hideTypingIndicator();
                    this.addMessageToUI(data.message, 'assistant', data.sources);
                    this.isTyping = false;
                    this.setSendButtonState('ready');
                    this.messageInput.focus();
                }, 800); // Small delay for better UX
            } else {
                throw new Error(data.error || 'Failed to get response');
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.showError(error.message);
            this.isTyping = false;
            this.setSendButtonState('ready');
        }
    }
    
    addMessageToUI(content, sender, sources = []) {
        // Remove welcome message if it's the first real message
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `${sender}-message`;
        
        // Format markdown-like content
        let formattedContent = content;
        
        if (sender === 'assistant') {
            // Convert **bold** to <strong>
            formattedContent = formattedContent.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            
            // Convert `code` to <code>
            formattedContent = formattedContent.replace(/`([^`]+)`/g, '<code>$1</code>');
            
            // Convert code blocks ```language\ncode\n``` to <pre><code>
            formattedContent = formattedContent.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');
            
            // Convert line breaks
            formattedContent = formattedContent.replace(/\n/g, '<br>');
            
            messageDiv.innerHTML = formattedContent;
            
            // Add source citations if available
            if (sources && sources.length > 0) {
                const sourcesDiv = document.createElement('div');
                sourcesDiv.className = 'source-citation mt-2';
                sourcesDiv.innerHTML = `<small>📄 Source: ${sources.join(', ')}</small>`;
                messageDiv.appendChild(sourcesDiv);
            }
        } else {
            messageDiv.textContent = content;
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Add to conversation history
        this.conversationHistory.push({
            sender: sender,
            content: content,
            timestamp: new Date()
        });
    }
    
    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="assistant-message" style="max-width: 40px;">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        typingDiv.id = 'typing-indicator';
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    setSendButtonState(state) {
        switch (state) {
            case 'loading':
                this.sendText.classList.add('d-none');
                this.sendSpinner.classList.remove('d-none');
                this.sendBtn.disabled = true;
                break;
            case 'ready':
            default:
                this.sendText.classList.remove('d-none');
                this.sendSpinner.classList.add('d-none');
                this.sendBtn.disabled = false;
                break;
        }
    }
    
    clearConversation() {
        this.chatMessages.innerHTML = `
            <div class="text-center text-muted py-5 welcome-message">
                <h4>Conversation cleared!</h4>
                <p>Ask Jarvis anything about your documents.</p>
                <div class="mt-4">
                    <p class="mb-3"><small>Try asking:</small></p>
                    <div id="example-questions-container" class="d-flex flex-wrap justify-content-center gap-2">
                        <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                    </div>
                </div>
            </div>
        `;
        this.conversationHistory = [];
        this.messageInput.value = '';
        this.messageInput.focus();
        
        // Reload example questions
        this.loadExampleQuestions();
        
        // Show success notification
        document.getElementById('successMessage').textContent = 'Conversation cleared successfully!';
        this.successToast.show();
    }
    
    showError(errorMessage) {
        document.getElementById('errorMessage').textContent = errorMessage;
        this.errorModal.show();
        
        // Add error message to chat
        this.addMessageToUI(`Error: ${errorMessage}`, 'system-error');
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
}

// Initialize Jarvis Chat when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.jarvisChat = new JarvisChat();
    
    // Focus on input field
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.focus();
    }
    
    // Handle page visibility change
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && messageInput) {
            messageInput.focus();
        }
    });
});
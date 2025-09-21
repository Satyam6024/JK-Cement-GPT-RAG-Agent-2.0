// CementGPT RAG Agent - Frontend JavaScript

class CementGPT {
    constructor() {
        this.isTyping = false;
        this.conversationHistory = [];
        this.systemStatus = 'checking';
        
        this.initializeEventListeners();
        this.checkSystemStatus();
        this.loadConversationHistory();
    }

    initializeEventListeners() {
        // Chat input and send button
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Header buttons
        document.getElementById('corpusBtn').addEventListener('click', () => this.showCorpusModal());
        document.getElementById('clearBtn').addEventListener('click', () => this.clearConversation());
        
        // Modal close events
        document.getElementById('corpusModal').addEventListener('click', (e) => {
            if (e.target.id === 'corpusModal') {
                this.closeCorpusModal();
            }
        });
        
        // Auto-resize input
        messageInput.addEventListener('input', this.autoResizeInput);
    }

    async checkSystemStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.rag_available && data.vertex_ai_initialized) {
                this.updateStatusIndicator('online', 'System Ready');
                this.enableChat();
            } else {
                this.updateStatusIndicator('offline', 'System Unavailable');
                this.disableChat();
                this.showToast('error', data.message || 'System is not ready');
            }
        } catch (error) {
            console.error('Status check failed:', error);
            this.updateStatusIndicator('offline', 'Connection Failed');
            this.disableChat();
            this.showToast('error', 'Failed to connect to server');
        }
    }

    updateStatusIndicator(status, message) {
        const indicator = document.getElementById('statusIndicator');
        indicator.className = `status-indicator ${status}`;
        indicator.querySelector('span').textContent = message;
    }

    enableChat() {
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        
        messageInput.disabled = false;
        sendBtn.disabled = false;
        messageInput.placeholder = "Ask me about your documents or manage your corpora...";
    }

    disableChat() {
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        
        messageInput.disabled = true;
        sendBtn.disabled = true;
        messageInput.placeholder = "System is not ready. Please check configuration.";
    }

    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message || this.isTyping) return;
        
        // Clear input
        messageInput.value = '';
        this.autoResizeInput({ target: messageInput });
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Show typing indicator
        this.isTyping = true;
        const typingId = this.addTypingIndicator();
        
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            this.removeTypingIndicator(typingId);
            
            if (data.status === 'success') {
                this.addMessage('agent', data.response);
                this.conversationHistory.push(
                    { role: 'user', message, timestamp: new Date().toISOString() },
                    { role: 'agent', message: data.response, timestamp: new Date().toISOString() }
                );
            } else {
                this.addMessage('agent', `Error: ${data.message}`, true);
                this.showToast('error', data.message);
            }
        } catch (error) {
            console.error('Chat error:', error);
            this.removeTypingIndicator(typingId);
            this.addMessage('agent', 'Sorry, I encountered an error processing your request. Please try again.', true);
            this.showToast('error', 'Failed to send message');
        } finally {
            this.isTyping = false;
        }
    }

    addMessage(role, content, isError = false) {
        const messagesContainer = document.getElementById('messagesContainer');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        const avatar = role === 'user' 
            ? '<i class="fas fa-user"></i>'
            : '<i class="fas fa-robot"></i>';
        
        const messageClass = isError ? 'message-text error-message' : 'message-text';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">
                ${avatar}
            </div>
            <div class="message-content">
                <div class="${messageClass}">
                    ${this.formatMessage(content)}
                </div>
                <div class="message-time">${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addTypingIndicator() {
        const messagesContainer = document.getElementById('messagesContainer');
        const typingDiv = document.createElement('div');
        const typingId = `typing-${Date.now()}`;
        typingDiv.id = typingId;
        typingDiv.className = 'message agent-message typing-indicator';
        
        typingDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-content">
                <div class="message-text">
                    <div class="typing-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
        
        return typingId;
    }

    removeTypingIndicator(typingId) {
        const typingElement = document.getElementById(typingId);
        if (typingElement) {
            typingElement.remove();
        }
    }

    formatMessage(content) {
        // Convert markdown-like formatting to HTML
        content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
        content = content.replace(/`(.*?)`/g, '<code>$1</code>');
        
        // Convert line breaks to HTML
        content = content.replace(/\n\n/g, '</p><p>');
        content = content.replace(/\n/g, '<br>');
        
        // Wrap in paragraph if it contains breaks
        if (content.includes('<br>') || content.includes('</p>')) {
            content = '<p>' + content + '</p>';
        }
        
        return content;
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('messagesContainer');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    autoResizeInput(e) {
        const input = e.target;
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    }

    async clearConversation() {
        if (!confirm('Are you sure you want to clear the conversation?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/clear-conversation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Clear messages except welcome message
                const messagesContainer = document.getElementById('messagesContainer');
                const messages = messagesContainer.querySelectorAll('.message');
                messages.forEach((message, index) => {
                    if (index > 0) { // Keep the welcome message (first message)
                        message.remove();
                    }
                });
                
                this.conversationHistory = [];
                this.showToast('success', 'Conversation cleared');
            }
        } catch (error) {
            console.error('Clear conversation error:', error);
            this.showToast('error', 'Failed to clear conversation');
        }
    }

    async loadConversationHistory() {
        try {
            const response = await fetch('/api/conversation-history');
            const data = await response.json();
            
            if (data.status === 'success' && data.history.length > 0) {
                this.conversationHistory = data.history;
                // Restore messages to UI
                data.history.forEach(item => {
                    this.addMessage(item.role, item.message);
                });
            }
        } catch (error) {
            console.error('Load history error:', error);
        }
    }

    // Corpus Management Methods
    showCorpusModal() {
        const modal = document.getElementById('corpusModal');
        modal.classList.add('show');
        this.refreshCorpora();
    }

    closeCorpusModal() {
        const modal = document.getElementById('corpusModal');
        modal.classList.remove('show');
    }

    async refreshCorpora() {
        const corporaList = document.getElementById('corporaList');
        corporaList.innerHTML = '<div class="loading">Loading corpora...</div>';
        
        try {
            const response = await fetch('/api/corpus/list');
            const data = await response.json();
            
            if (data.status === 'success') {
                corporaList.innerHTML = `<div class="corpora-response">${this.formatMessage(data.response)}</div>`;
            } else {
                corporaList.innerHTML = `<div class="error">Failed to load corpora: ${data.message}</div>`;
            }
        } catch (error) {
            console.error('Refresh corpora error:', error);
            corporaList.innerHTML = '<div class="error">Failed to load corpora</div>';
        }
    }

    async createCorpus() {
        const corpusNameInput = document.getElementById('newCorpusName');
        const corpusName = corpusNameInput.value.trim();
        
        if (!corpusName) {
            this.showToast('warning', 'Please enter a corpus name');
            return;
        }
        
        this.showLoadingOverlay();
        
        try {
            const response = await fetch('/api/corpus/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: corpusName })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showToast('success', `Corpus "${corpusName}" created successfully`);
                corpusNameInput.value = '';
                this.refreshCorpora();
            } else {
                this.showToast('error', data.message);
            }
        } catch (error) {
            console.error('Create corpus error:', error);
            this.showToast('error', 'Failed to create corpus');
        } finally {
            this.hideLoadingOverlay();
        }
    }

    async addDocument() {
        const corpusInput = document.getElementById('targetCorpus');
        const urlInput = document.getElementById('documentUrl');
        
        const corpusName = corpusInput.value.trim();
        const documentUrl = urlInput.value.trim();
        
        if (!corpusName || !documentUrl) {
            this.showToast('warning', 'Please enter both corpus name and document URL');
            return;
        }
        
        this.showLoadingOverlay();
        
        try {
            const response = await fetch('/api/corpus/add-document', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    corpus_name: corpusName,
                    document_url: documentUrl
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.showToast('success', 'Document added successfully');
                corpusInput.value = '';
                urlInput.value = '';
            } else {
                this.showToast('error', data.message);
            }
        } catch (error) {
            console.error('Add document error:', error);
            this.showToast('error', 'Failed to add document');
        } finally {
            this.hideLoadingOverlay();
        }
    }

    // Utility Methods
    showLoadingOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        overlay.classList.add('show');
    }

    hideLoadingOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        overlay.classList.remove('show');
    }

    showToast(type, message) {
        const toast = document.getElementById('toast');
        const icon = toast.querySelector('.toast-icon');
        const messageSpan = toast.querySelector('.toast-message');
        
        // Set icon based on type
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        icon.className = `toast-icon ${icons[type] || icons.info}`;
        messageSpan.textContent = message;
        toast.className = `toast ${type}`;
        
        // Show toast
        toast.classList.add('show');
        
        // Auto hide after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
        }, 5000);
    }
}

// Global functions for HTML onclick handlers
function closeCorpusModal() {
    app.closeCorpusModal();
}

function createCorpus() {
    app.createCorpus();
}

function addDocument() {
    app.addDocument();
}

function refreshCorpora() {
    app.refreshCorpora();
}

function sendSuggestion(message) {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = message;
    app.sendMessage();
}

// CSS for typing indicator animation
const typingCSS = `
.typing-dots {
    display: flex;
    align-items: center;
    gap: 4px;
}

.typing-dots span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--primary-color);
    animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(2) {
    animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
    animation-delay: 0.4s;
}

@keyframes typing {
    0%, 60%, 100% {
        transform: scale(0.8);
        opacity: 0.5;
    }
    30% {
        transform: scale(1);
        opacity: 1;
    }
}

.error-message {
    background: #fee2e2 !important;
    color: #dc2626 !important;
    border-left: 4px solid #dc2626;
}

.message-time {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-top: 0.5rem;
    opacity: 0.7;
}

.corpora-response {
    background: var(--surface);
    border-radius: 8px;
    padding: 1rem;
}

.corpora-response h3 {
    color: var(--primary-color);
    margin-bottom: 0.5rem;
}
`;

// Inject typing animation CSS
const style = document.createElement('style');
style.textContent = typingCSS;
document.head.appendChild(style);

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new CementGPT();
});
/**
 * Lógica do Chat e Dashboard
 */

document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname !== "/dashboard" || !Auth.isAuthenticated()) return;

    const chatInput = document.getElementById("prompt-input");
    const btnSend = document.getElementById("btn-send");
    const chatMessages = document.getElementById("chat-messages");
    const chatWelcome = document.getElementById("chat-welcome");
    const historyList = document.getElementById("history-list");
    
    // Auto-resize textarea
    chatInput.addEventListener('input', function() {
        this.style.height = '56px';
        const scrollHeight = this.scrollHeight;
        if(scrollHeight > 56 && scrollHeight < 200) {
            this.style.height = scrollHeight + 'px';
        } else if(scrollHeight >= 200) {
            this.style.height = '200px';
            this.style.overflowY = 'auto';
        }
    });

    // Enter para enviar (Shift+Enter para quebra)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if(chatInput.value.trim() !== '') {
                sendMessage();
            }
        }
    });
    btnSend.addEventListener("click", () => {
        if(chatInput.value.trim() !== '') sendMessage();
    });

    // Carregar Histórico
    loadHistory();

    // Carregar Nome do Modelo
    Utils.loadModelName();

    // Cria bolha no DOM
    function appendMessage(role, text, time) {
        if (chatWelcome) chatWelcome.classList.add('d-none');
        
        const isUser = role === 'user';
        
        const bubble = document.createElement("div");
        bubble.className = `chat-bubble ${isUser ? 'user' : 'assistant'}`;
        
        const header = document.createElement("div");
        header.className = "d-flex justify-content-between mb-1";
        
        const sender = document.createElement("span");
        sender.className = "fw-bold";
        sender.innerText = isUser ? "Você" : "Modelo (Qwen)";
        
        const timestamp = document.createElement("small");
        timestamp.className = "text-secondary time-label";
        timestamp.style.opacity = "0.7";
        timestamp.innerText = time;
        
        header.appendChild(sender);
        header.appendChild(timestamp);
        
        const content = document.createElement("div");
        content.className = "message-content markdown-body";
        
        if (isUser) {
            content.innerText = text;
        } else {
            // Usa marked.js, garantindo sanitize safe fallback
            try {
                content.innerHTML = marked.parse(text);
            } catch(e) {
                content.innerText = text; // Fallback plain text
            }
        }
        
        bubble.appendChild(header);
        bubble.appendChild(content);
        
        chatMessages.appendChild(bubble);
        scrollToBottom();
    }

    function showTypingIndicator() {
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble assistant p-3";
        bubble.id = "typing-indicator";
        bubble.innerHTML = `
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        chatMessages.appendChild(bubble);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const loader = document.getElementById("typing-indicator");
        if (loader) loader.remove();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    async function sendMessage() {
        const prompt = chatInput.value.trim();
        if (!prompt) return;

        // Reset UI
        chatInput.value = '';
        chatInput.style.height = '56px';
        btnSend.disabled = true;
        
        // Settings
        const isStreamingEnabled = localStorage.getItem('app_streaming') === 'true';

        // Current Time for optimistic UI
        const now = Utils.formatDate(new Date());

        // Append User Message Optmistic
        appendMessage('user', prompt, now);
        showTypingIndicator();

        try {
            const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/chat/ask`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${Auth.getToken()}`
                },
                body: JSON.stringify({ 
                    prompt: prompt,
                    stream: isStreamingEnabled
                })
            });

            if (!res.ok) {
                removeTypingIndicator();
                if (res.status === 401) Auth.logout();
                const err = await res.json();
                appendMessage('assistant', `⚠️ Erro: ${err.detail || 'Serviço indisponível'}`, now);
                return;
            }

            if (!isStreamingEnabled) {
                removeTypingIndicator();
                const data = await res.json();
                appendMessage('assistant', data.response, data.timestamp);
                prependToHistory(data);
            } else {
                // Lógica de Streaming (SSE)
                removeTypingIndicator();
                
                // Cria bolha vazia para o assistente
                const bubble = document.createElement("div");
                bubble.className = `chat-bubble assistant`;
                
                const header = document.createElement("div");
                header.className = "d-flex justify-content-between mb-1";
                const sender = document.createElement("span");
                sender.className = "fw-bold";
                sender.innerText = "Modelo (Qwen)";
                const timestampLabel = document.createElement("small");
                timestampLabel.className = "text-secondary time-label";
                timestampLabel.style.opacity = "0.7";
                timestampLabel.innerText = "Processando...";
                
                header.appendChild(sender);
                header.appendChild(timestampLabel);
                
                const content = document.createElement("div");
                content.className = "message-content markdown-body";
                
                bubble.appendChild(header);
                bubble.appendChild(content);
                chatMessages.appendChild(bubble);
                scrollToBottom();

                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let fullText = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split("\n");

                    for (const line of lines) {
                        if (line.startsWith("data: ")) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.error) {
                                    content.innerText = `⚠️ Erro: ${data.error}`;
                                    break;
                                }
                                
                                if (data.text) {
                                    fullText += data.text;
                                    content.innerHTML = marked.parse(fullText);
                                    scrollToBottom();
                                }

                                if (data.done) {
                                    timestampLabel.innerText = data.timestamp;
                                    prependToHistory({
                                        prompt: prompt,
                                        response: fullText,
                                        timestamp: data.timestamp
                                    });
                                }
                            } catch (e) {
                                console.error("Erro ao processar chunk SSE:", e);
                            }
                        }
                    }
                }
            }

        } catch (error) {
            removeTypingIndicator();
            console.error("Erro na requisição:", error);
            appendMessage('assistant', `⚠️ Erro de rede ao conectar com o serviço.`, now);
        } finally {
            btnSend.disabled = false;
            chatInput.focus();
        }
    }

    async function loadHistory() {
        try {
            const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/chat/conversations?limit=50`, {
                headers: { "Authorization": `Bearer ${Auth.getToken()}` }
            });
            
            if (res.ok) {
                const data = await res.json();
                historyList.innerHTML = ''; // Clear loader
                
                if(data.items.length === 0) {
                    historyList.innerHTML = '<div class="p-4 text-center text-secondary small">Nenhuma conversa anterior.</div>';
                    return;
                }

                data.items.forEach(item => {
                    const div = document.createElement("div");
                    div.className = "history-item";
                    div.innerHTML = `
                        <div class="history-title"><i class="bi bi-chat-left-text me-2 text-accent"></i>${Utils.escapeHtml(item.prompt)}</div>
                        <div class="history-date">${item.created_at}</div>
                    `;
                    div.onclick = () => loadConversationIntoView(item);
                    historyList.appendChild(div);
                });
            } else {
                if (res.status === 401) {
                    Auth.logout();
                    return;
                }
                historyList.innerHTML = '<div class="p-3 text-center text-danger small">Erro ao carregar histórico</div>';
            }
        } catch(error) {
            historyList.innerHTML = '<div class="p-3 text-center text-danger small">Erro de rede ao buscar histórico</div>';
        }
    }

    function prependToHistory(item) {
        // Remove 'no items' se existir
        if(historyList.querySelector('.text-center.text-secondary')) {
            historyList.innerHTML = '';
        }
        
        const div = document.createElement("div");
        div.className = "history-item";
        div.innerHTML = `
            <div class="history-title"><i class="bi bi-chat-left-text me-2 text-accent"></i>${Utils.escapeHtml(item.prompt)}</div>
            <div class="history-date">${item.timestamp}</div>
        `;
        div.onclick = () => loadConversationIntoView(item);
        historyList.insertBefore(div, historyList.firstChild);
    }

    function loadConversationIntoView(item) {
        // Limpa o chat atual e mostra essa conversa isolada.
        chatMessages.innerHTML = '';
        if (chatWelcome) chatWelcome.classList.add('d-none');
        appendMessage('user', item.prompt, item.created_at || item.timestamp);
        appendMessage('assistant', item.response, item.created_at || item.timestamp);
    }

    // Expose para onclick
    window.startNewChat = () => {
        chatMessages.innerHTML = '';
        if (chatWelcome) {
            chatWelcome.classList.remove('d-none');
            chatMessages.appendChild(chatWelcome);
        }
    }
});

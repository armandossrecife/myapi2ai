/**
 * Lógica da Página de Consulta RAG
 */

const RAG = {
    elements: {
        messages: document.getElementById("rag-messages"),
        input: document.getElementById("rag-prompt-input"),
        btnSend: document.getElementById("btn-rag-send"),
        iconSend: document.getElementById("rag-send-icon"),
        spinnerSend: document.getElementById("rag-send-spinner"),
        welcome: document.getElementById("rag-welcome"),
        docsList: document.getElementById("docs-list")
    },

    init: async () => {
        if (!RAG.elements.input) return;

        // Auto-resize textarea
        RAG.elements.input.addEventListener("input", function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });

        // Send on Enter (not Shift+Enter)
        RAG.elements.input.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                RAG.sendQuery();
            }
        });

        RAG.elements.btnSend.addEventListener("click", RAG.sendQuery);

        // Load documents list
        await RAG.loadDocs();
    },

    loadDocs: async () => {
        try {
            const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/rag/docs`, {
                headers: { 'Authorization': `Bearer ${Auth.getToken()}` }
            });
            const data = await res.json();
            if (res.ok && data.files.length > 0) {
                RAG.elements.docsList.innerHTML = data.files.map(f => 
                    `<li class="mb-2"><i class="bi bi-file-earmark-pdf text-danger me-2"></i>${f}</li>`
                ).join("");
            } else {
                RAG.elements.docsList.innerHTML = `<li class="text-warning small"><i class="bi bi-exclamation-triangle me-2"></i>Nenhum documento encontrado.</li>`;
            }
        } catch (e) {
            console.error("Erro ao carregar documentos:", e);
        }
    },

    sendQuery: async () => {
        const question = RAG.elements.input.value.trim();
        if (!question) return;

        // UI State
        RAG.elements.input.value = "";
        RAG.elements.input.style.height = "auto";
        RAG.elements.welcome.classList.add("d-none");
        RAG.setLoading(true); // FIX: JS boolean is lowercase

        // Add User Message
        RAG.addMessage(question, "user");

        // Add Assistant Placeholder
        const aiMsgDiv = RAG.addMessage("", "assistant", true);

        try {
            const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/rag/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${Auth.getToken()}`
                },
                body: JSON.stringify({ question })
            });

            const data = await res.json();

            if (res.ok) {
                RAG.updateAIMessage(aiMsgDiv, data.resposta, data.fontes);
            } else {
                aiMsgDiv.innerHTML = `<div class="alert alert-danger mb-0">${data.detail || "Erro ao processar consulta."}</div>`;
            }
        } catch (error) {
            aiMsgDiv.innerHTML = `<div class="alert alert-danger mb-0">Erro de conexão com o servidor.</div>`;
        } finally {
            RAG.setLoading(false);
        }
    },

    setLoading: (loading) => {
        if (loading) {
            RAG.elements.btnSend.disabled = true;
            RAG.elements.iconSend.classList.add("d-none");
            RAG.elements.spinnerSend.classList.remove("d-none");
        } else {
            RAG.elements.btnSend.disabled = false;
            RAG.elements.iconSend.classList.remove("d-none");
            RAG.elements.spinnerSend.classList.add("d-none");
        }
    },

    addMessage: (text, sender, isPlaceholder = false) => {
        const div = document.createElement("div");
        div.className = `message-wrapper ${sender}`;
        
        if (isPlaceholder) {
            div.innerHTML = `
                <div class="message-bubble assistant">
                    <div class="spinner-grow spinner-grow-sm text-primary" role="status"></div>
                    <span class="ms-2">Analisando documentos...</span>
                </div>
            `;
        } else {
            div.innerHTML = `
                <div class="message-bubble ${sender}">
                    ${sender === 'assistant' ? marked.parse(text) : text}
                </div>
            `;
        }
        
        RAG.elements.messages.appendChild(div);
        RAG.elements.messages.scrollTop = RAG.elements.messages.scrollHeight;
        return div;
    },

    updateAIMessage: (wrapperDiv, text, sources) => {
        const bubble = wrapperDiv.querySelector(".message-bubble");
        
        let sourcesHtml = "";
        if (sources && sources.length > 0) {
            sourcesHtml = `
                <div class="sources-container mt-3 pt-2 border-top border-secondary">
                    <div class="text-secondary small fw-bold mb-2"><i class="bi bi-journal-bookmark me-1"></i>FONTES CONSULTADAS:</div>
                    ${sources.map(s => `
                        <div class="source-item mb-2 p-2 rounded bg-dark border border-secondary-subtle">
                            <div class="d-flex justify-content-between small">
                                <span class="text-primary fw-bold"><i class="bi bi-file-text me-1"></i>${s.documento}</span>
                                <span class="badge text-bg-secondary">${s.categoria}</span>
                            </div>
                            <div class="source-excerpt mt-1 text-secondary" style="font-size: 0.8rem; font-style: italic;">
                                "...${s.trecho.substring(0, 200)}..."
                            </div>
                        </div>
                    `).join("")}
                </div>
            `;
        }

        bubble.innerHTML = `
            <div class="markdown-content">${marked.parse(text)}</div>
            ${sourcesHtml}
        `;
        
        RAG.elements.messages.scrollTop = RAG.elements.messages.scrollHeight;
    }
};

document.addEventListener("DOMContentLoaded", RAG.init);

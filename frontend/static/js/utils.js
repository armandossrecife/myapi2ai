/**
 * Utilitários Genéricos para o Frontend
 */

const Utils = {
    showAlert: (message, type = 'danger') => {
        const container = document.getElementById('alert-container');
        if (!container) return;
        
        // Fetch HTML alert component since jinja handles static rendering,
        // we simulate string replacement here for dynamic alerts
        const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show shadow-sm" role="alert">
            <strong>${type === 'danger' ? 'Erro!' : 'Aviso:'}</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
        `;
        
        container.innerHTML += alertHtml;
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alerts = container.querySelectorAll('.alert');
            if (alerts.length > 0) {
                const firstAlert = alerts[0];
                const bsAlert = new bootstrap.Alert(firstAlert);
                bsAlert.close();
            }
        }, 5000);
    },

    formatDate: (dateString) => {
        try {
            const date = new Date(dateString);
            return new Intl.DateTimeFormat('pt-BR', {
                day: '2-digit', month: '2-digit', year: 'numeric',
                hour: '2-digit', minute: '2-digit'
            }).format(date);
        } catch(e) {
            return dateString;
        }
    },

     escapeHtml: (unsafe) => {
        return unsafe
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    },

    loadModelName: async () => {
        try {
            const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/chat/model`);
            if (res.ok) {
                const data = await res.json();
                const modelName = data.model;
                // Deixa em maiúsculas se for curto (ex: qwen3 -> QWEN3) 
                // ou apenas capitaliza se preferir
                const displayModel = modelName.toUpperCase();
                
                const elements = document.querySelectorAll('.current-model-info');
                elements.forEach(el => {
                    el.textContent = displayModel;
                });
            }
        } catch (error) {
            console.error("Erro ao carregar nome do modelo:", error);
        }
    }
};

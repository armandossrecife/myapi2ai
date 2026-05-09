/**
 * Gerenciamento de Autenticação e Sessão
 */

const Auth = {
    getToken: () => localStorage.getItem("jwt_token"),
    setToken: (token) => localStorage.setItem("jwt_token", token),
    logout: () => {
        localStorage.removeItem("jwt_token");
        window.location.href = "/login";
    },
    isAuthenticated: () => !!localStorage.getItem("jwt_token"),
    
    updateNavbar: () => {
        const nav = document.getElementById("nav-items");
        if (!nav) return;
        
        if (Auth.isAuthenticated()) {
            nav.innerHTML = `
                <li class="nav-item"><a class="nav-link" href="/dashboard"><i class="bi bi-chat-dots me-1"></i> Dashboard</a></li>
                <li class="nav-item"><a class="nav-link" href="/rag"><i class="bi bi-file-earmark-text me-1"></i> Consultar RAG</a></li>
                <li class="nav-item"><a class="nav-link" href="#" id="btnSettings"><i class="bi bi-gear me-1"></i> Configurações</a></li>
                <li class="nav-item"><a class="nav-link text-danger" href="#" id="btnLogout"><i class="bi bi-box-arrow-right me-1"></i> Sair</a></li>
            `;
            document.getElementById("btnSettings").addEventListener("click", (e) => {
                e.preventDefault();
                const modal = new bootstrap.Modal(document.getElementById('settingsModal'));
                const currentTheme = localStorage.getItem('app_theme') || 'dark';
                const currentStreaming = localStorage.getItem('app_streaming') === 'true';
                document.getElementById('themeSelect').value = currentTheme;
                document.getElementById('streamingToggle').checked = currentStreaming;
                modal.show();
            });
            document.getElementById("btnLogout").addEventListener("click", (e) => {
                e.preventDefault();
                Auth.logout();
            });
        } else {
            nav.innerHTML = `
                <li class="nav-item"><a class="nav-link" href="/login">Login</a></li>
                <li class="nav-item"><a class="nav-link btn btn-primary px-3 rounded-pill text-white" href="/register">Registrar</a></li>
            `;
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    Auth.updateNavbar();

    // Settings logic
    const btnSaveSettings = document.getElementById('btnSaveSettings');
    if (btnSaveSettings) {
        btnSaveSettings.addEventListener('click', () => {
            const theme = document.getElementById('themeSelect').value;
            const streaming = document.getElementById('streamingToggle').checked;
            localStorage.setItem('app_theme', theme);
            localStorage.setItem('app_streaming', streaming);
            document.documentElement.setAttribute('data-theme', theme);
            
            // Close modal
            const modalElement = document.getElementById('settingsModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            modal.hide();
            
            Utils.showAlert("Configurações salvas!", "success");
        });
    }

    // Redirecionamentos Automáticos
    const path = window.location.pathname;
    if ((path === "/dashboard" || path === "/rag") && !Auth.isAuthenticated()) {
        window.location.href = "/login";
    }
    if ((path === "/login" || path === "/register") && Auth.isAuthenticated()) {
        window.location.href = "/dashboard";
    }

    // Login Form Handler
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = loginForm.querySelector('button');
            const spinner = document.getElementById("login-spinner");
            
            btn.disabled = true;
            spinner.classList.remove("d-none");
            
            const formData = new URLSearchParams();
            formData.append("username", document.getElementById("username").value);
            formData.append("password", document.getElementById("password").value);
            
            try {
                const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: formData
                });
                
                const data = await res.json();
                
                if (res.ok) {
                    Auth.setToken(data.access_token);
                    window.location.href = "/dashboard";
                } else {
                    Utils.showAlert(data.detail || "Erro ao fazer login");
                }
            } catch(error) {
                Utils.showAlert("Erro de conexão com o servidor.");
            } finally {
                btn.disabled = false;
                spinner.classList.add("d-none");
            }
        });
    }

    // Register Form Handler
    const registerForm = document.getElementById("register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = registerForm.querySelector('button');
            const spinner = document.getElementById("reg-spinner");
            
            btn.disabled = true;
            spinner.classList.remove("d-none");
            
            const payload = {
                username: document.getElementById("username").value,
                email: document.getElementById("email").value,
                password: document.getElementById("password").value
            };
            
            try {
                const res = await fetch(`${window.APP_CONFIG.API_BASE_URL}/auth/register`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                
                const data = await res.json();
                
                if (res.ok) {
                    Utils.showAlert("Conta criada com sucesso! Redirecionando...", "success");
                    setTimeout(() => window.location.href = "/login", 1500);
                } else {
                    Utils.showAlert(data.detail || "Erro ao registrar. Verifique os dados.");
                }
            } catch(error) {
                Utils.showAlert("Erro de conexão com o servidor.");
            } finally {
                btn.disabled = false;
                spinner.classList.add("d-none");
            }
        });
    }
});

import { defineStore } from 'pinia';
import api from '@/service/api';

export const useAuthStore = defineStore('auth', {
    state: () => ({
        user: null,
        // Tenta recuperar de ambos os locais ao iniciar
        token: localStorage.getItem('token') || sessionStorage.getItem('token') || null,
    }),

    getters: {
        isAuthenticated: (state) => !!state.token,

        // Superusuário tem acesso total
        isAdmin: (state) => state.user?.is_superuser,

        // Grupos (Ajustados conforme criado no Banco de Dados)
        isSecretary: (state) => {            
            return state.user?.groups?.includes('Secretaria') || state.user?.is_superuser;
        },

        isCoordinator: (state) => {
            return state.user?.groups?.includes('Coordenadores') || state.user?.groups?.includes('Coordenacao') || state.user?.is_superuser;
        },

        isTeacher: (state) => {
            return state.user?.groups?.includes('Professores') || state.user?.is_superuser;
        },
    
        isGuardian: (state) => {
            // Verifica com e sem acento para garantir compatibilidade
            return state.user?.groups?.includes('Responsáveis') || state.user?.groups?.includes('Responsaveis');
        },
        
        userRole: (state) => {
            if (state.user?.is_superuser) return 'Administrador';
            if (state.user?.groups?.includes('Secretaria')) return 'Secretaria';
            if (state.user?.groups?.includes('Coordenadores') || state.user?.groups?.includes('Coordenacao')) return 'Coordenação';
            if (state.user?.groups?.includes('Professores')) return 'Docente';
            if (state.user?.groups?.includes('Responsáveis') || state.user?.groups?.includes('Responsaveis')) return 'Responsável';
            return 'Colaborador';
        }
    },

    actions: {
        // Função chamada ao carregar a aplicação (ex: no main.js ou App.vue)
        checkAuth() {
            if (this.token) {
                api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
                this.fetchUser();
            }
        },

        async login({ username, password, remember }) {
            try {
                // 1. Faz o Post
                const response = await api.post('token/', { username, password });
                this.token = response.data.access;
                
                // 2. Define o Header imediatamente
                api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;

                // 3. Lógica do "Lembrar-me"
                if (remember) {
                    // Se marcou lembrar: Salva no Local (Persistente) e limpa Session
                    localStorage.setItem('token', this.token);
                    sessionStorage.removeItem('token');
                } else {
                    // Se NÃO marcou: Salva na Session (Temporário) e limpa Local
                    sessionStorage.setItem('token', this.token);
                    localStorage.removeItem('token');
                }
                
                // 4. Busca dados do usuário
                await this.fetchUser();
                
                return true;
            } catch (error) {
                console.error("Erro no login:", error);
                throw error;
            }
        },

        async fetchUser() {
            try {
                const response = await api.get('users/me/');
                this.user = response.data;
            } catch (error) {
                // Se falhar ao buscar usuário (token expirado/inválido), faz logout
                this.logout();
            }
        },

        logout() {
            this.token = null;
            this.user = null;
            
            // Limpa tudo
            localStorage.removeItem('token');
            sessionStorage.removeItem('token');
            delete api.defaults.headers.common['Authorization'];
            
            // Força recarregar a página para limpar estados de memória
            window.location.href = '/login';
        }
    }
});
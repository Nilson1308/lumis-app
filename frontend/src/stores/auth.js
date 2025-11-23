import { defineStore } from 'pinia';
import api from '@/service/api';

export const useAuthStore = defineStore('auth', {
    state: () => ({
        user: null, // O objeto do usuário (nome, email, is_teacher)
        token: localStorage.getItem('access_token') || null,
        isAuthenticated: false
    }),

    getters: {
        // Getters funcionam como "propriedades computadas" globais
        isCoordinator: (state) => state.user?.is_coordinator || state.user?.is_superuser,
        isTeacher: (state) => state.user?.is_teacher,
        fullName: (state) => state.user?.full_name || 'Usuário'
    },

    actions: {
        // Ação 1: Fazer Login e buscar dados do usuário
        async login(username, password) {
            try {
                // 1. Pega o Token
                const response = await api.post('token/', { username, password });
                this.token = response.data.access;
                
                // Salva no LocalStorage e atualiza o estado
                localStorage.setItem('access_token', response.data.access);
                localStorage.setItem('refresh_token', response.data.refresh);
                this.isAuthenticated = true;

                // 2. Busca os dados do usuário imediatamente (/me)
                await this.fetchUser();
                
                return true; // Sucesso
            } catch (error) {
                console.error("Erro no login:", error);
                throw error;
            }
        },

        // Ação 2: Buscar dados do usuário logado (/me)
        async fetchUser() {
            try {
                const response = await api.get('users/me/');
                this.user = response.data;
                this.isAuthenticated = true;
            } catch (error) {
                this.logout(); // Se der erro ao buscar user, o token é inválido
            }
        },

        // Ação 3: Logout
        logout() {
            this.user = null;
            this.token = null;
            this.isAuthenticated = false;
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            // O redirecionamento acontece no Router ou no componente
        }
    }
});
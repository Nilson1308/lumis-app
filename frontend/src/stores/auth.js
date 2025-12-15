import { defineStore } from 'pinia';
import api from '@/service/api';

export const useAuthStore = defineStore('auth', {
    state: () => ({
        user: null,
        token: localStorage.getItem('token') || null,
    }),

    getters: {
        isAuthenticated: (state) => !!state.token,

        isAdmin: (state) => state.user?.is_superuser,

        isCoordinator: (state) => {
            return state.user?.groups?.includes('Coordenacao');
        },

        isTeacher: (state) => {
            return state.user?.groups?.includes('Professores');
        },
    
        isGuardian: (state) => {
            return state.user?.groups?.includes('Responsaveis');
        },
        
        userRole: (state) => {
            if (state.user?.is_superuser) return 'Administrador';
            if (state.user?.groups?.includes('Coordenacao')) return 'Coordenação';
            if (state.user?.groups?.includes('Professores')) return 'Docente';
            if (state.user?.groups?.includes('Responsaveis')) return 'Responsável'; // <--- NOVO
            return 'Colaborador';
        }
    },

    actions: {
        async login(credentials) {
            try {
                const response = await api.post('token/', credentials);
                this.token = response.data.access;
                
                // 1. Salva no Storage
                localStorage.setItem('token', this.token);
                
                // 2. CORREÇÃO IMEDIATA: Seta o header na hora
                api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
                
                // 3. Agora sim busca o usuário (o header já estará lá)
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
                this.logout();
            }
        },

        logout() {
            this.token = null;
            this.user = null;
            
            localStorage.removeItem('token');
        }
    }
});
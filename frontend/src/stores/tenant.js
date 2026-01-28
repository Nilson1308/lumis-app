// frontend/src/stores/tenant.js
import { defineStore } from 'pinia';
import api from '@/service/api';
import defaultLogo from '@/assets/logo-lumis.png';
import defaultIcon from '@/assets/lumis-icon.svg';

export const useTenantStore = defineStore('tenant', {
    state: () => ({
        school: {
            name: 'Lumis',
            logo: null,
            icon: null,
            primary_color: null,
            secondary_color: null,
        },
        isCustomized: false,
        loading: false
    }),

    getters: {
        currentLogo: (state) => state.school.logo || defaultLogo,
        currentIcon: (state) => state.school.icon || defaultIcon,
        currentName: (state) => state.school.name || 'Lumis'
    },

    actions: {
        async loadSettings() {
            if (this.isCustomized) return;
            this.loading = true;
            try {
                const response = await api.get('school-config/');
                const data = response.data;

                if (data && data.name) {
                    this.school = data;
                    this.isCustomized = true;
                    this.applyTheme();
                }
            } catch (error) {
                console.log("Usando identidade padrão Lumis");
            } finally {
                this.loading = false;
            }
        },

        applyTheme() {
            const root = document.documentElement;

            if (this.school.primary_color) {
                const color = this.school.primary_color;
                
                // 1. Variáveis Base
                root.style.setProperty('--primary-color', color);
                root.style.setProperty('--p-primary-500', color);
                root.style.setProperty('--p-primary-color', color);
                
                // 2. TRUQUE DO CSS COLOR-MIX PARA GERAR O HOVER/ACTIVE
                // Isso cria uma versão 10% mais escura (misturada com preto) para o hover
                root.style.setProperty('--p-primary-600', `color-mix(in srgb, ${color}, black 10%)`);
                root.style.setProperty('--p-primary-hover-color', `color-mix(in srgb, ${color}, black 10%)`);
                
                // Cria uma versão 20% mais escura para o click (active)
                root.style.setProperty('--p-primary-700', `color-mix(in srgb, ${color}, black 20%)`);
                root.style.setProperty('--p-primary-active-color', `color-mix(in srgb, ${color}, black 20%)`);
            }

            if (this.school.secondary_color) {
                root.style.setProperty('--secondary-color', this.school.secondary_color);
            }
            
            if (this.school.logo) {
                root.style.setProperty('--app-logo', `url('${this.school.logo}')`);
            }
        }
    }
});
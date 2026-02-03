<script setup>
import { onMounted } from 'vue';
import { useTenantStore } from '@/stores/tenant';
import { useAuthStore } from '@/stores/auth'; // <--- 1. Importar o AuthStore

const tenantStore = useTenantStore();
const authStore = useAuthStore(); // <--- 2. Instanciar

onMounted(() => {
    // Carrega configurações da escola (Logo, Cores)
    tenantStore.loadSettings();

    // Tenta restaurar a sessão do usuário (Lembrar-me)
    authStore.checkAuth(); // <--- 3. O Pulo do Gato
});
</script>

<template>
    <router-view />
</template>
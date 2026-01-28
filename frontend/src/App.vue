<script setup>
import { onMounted } from 'vue';
import { useTenantStore } from '@/stores/tenant';

// Carrega as configurações assim que a aplicação monta
const tenantStore = useTenantStore();

onMounted(() => {
    tenantStore.loadSettings();
});
</script>

<template>
    <router-view />
</template>
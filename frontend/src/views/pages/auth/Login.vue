<script setup>
import { useAuthStore } from '@/stores/auth';
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/service/api'; // Nosso api.js configurado

const authStore = useAuthStore();
const router = useRouter();
const username = ref('');
const password = ref('');
const loading = ref(false);
const errorMessage = ref('');

const handleLogin = async () => {
    loading.value = true;
    errorMessage.value = '';

    try {
        await authStore.login({
            username: username.value, 
            password: password.value
        });
        
        // --- LÓGICA DE REDIRECIONAMENTO ---
        if (authStore.isGuardian) {
            // Se for Pai, vai pro Portal da Família
            router.push({ name: 'parent-dashboard' });
        } else if (authStore.isTeacher) {
            // Se for Professor, vai pro Painel de Aulas (ou mantém dashboard se preferir)
            router.push({ name: 'my-classes' }); 
        } else {
            // Admin e Coordenador vão pro Dashboard Geral
            router.push({ name: 'dashboard' });
        }
        
    } catch (error) {
        // ... erros ...
    } finally {
        loading.value = false;
    }
};
</script>

<template>
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <div class="flex flex-col items-center justify-center">
            <div class="w-full bg-surface-0 dark:bg-surface-900 p-12" style="border-radius: 20px; min-width: 450px">
                <div class="text-center mb-5">
                    <img src="@/assets/logo-lumis.png" alt="Lumis Logo" class="mb-2 mx-auto" style="height: 90px;">
                    <small class="text-muted-color font-medium">Faça login para acessar o painel</small>
                </div>

                <div class="p-fluid">
                    <div class="field mb-3">
                        <label for="username" class="block text-900 font-medium mb-2">Usuário</label>
                        <InputText id="username" v-model="username" type="text" class="w-full" />
                    </div>
                    <div class="field mb-3">
                        <label for="password" class="block text-900 font-medium mb-2">Senha</label>
                        <InputText id="password" v-model="password" type="password" class="w-full" @keyup.enter="handleLogin" />
                    </div>

                    <div v-if="errorMessage" class="mb-3 text-red-500 font-bold text-center">
                        {{ errorMessage }}
                    </div>

                    <div class="flex align-center justify-between mb-6">
                        <div class="flex align-center">
                            <Checkbox id="rememberme" :binary="true" class="mr-2"></Checkbox>
                            <label for="rememberme">Lembrar-me</label>
                        </div>
                        <a class="font-medium no-underline ml-2 text-right cursor-pointer" style="color: var(--primary-color)">Esqueceu a senha?</a>
                    </div>

                    <Button label="Entrar" icon="pi pi-user" class="w-full" :loading="loading" @click="handleLogin"></Button>

                    <div class="mt-4 text-center">
                        <span class="text-600 text-sm">Acesso restrito para colaboradores</span><br>
                        <span class="font-bold text-sm" style="color: #0F172A;">Saint Thomas' International School</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
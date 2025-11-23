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
        await authStore.login(username.value, password.value);
        router.push('/');
        
    } catch (error) {
        console.error(error);
        if (error.response && error.response.status === 401) {
            errorMessage.value = 'Usuário ou senha inválidos.';
        } else {
            errorMessage.value = 'Erro ao conectar com o servidor.';
        }
    } finally {
        loading.value = false;
    }
};
</script>

<template>
    <div class="surface-ground flex align-items-center justify-content-center min-h-screen min-w-screen overflow-hidden">
        <div class="flex flex-column align-items-center justify-content-center">
            <div style="border-radius: 56px; padding: 0.3rem; background: linear-gradient(180deg, var(--primary-color) 10%, rgba(33, 150, 243, 0) 30%)">
                <div class="w-full surface-card py-8 px-5 sm:px-8" style="border-radius: 53px">
                    <div class="text-center mb-5">
                        <div class="text-900 text-3xl font-medium mb-3">Bem-vindo ao Lumis</div>
                        <span class="text-600 font-medium">Faça login para continuar</span>
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

                        <Button label="Entrar" icon="pi pi-user" class="w-full" :loading="loading" @click="handleLogin"></Button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
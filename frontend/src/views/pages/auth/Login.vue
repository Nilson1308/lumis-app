<script setup>
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';
import { ref, onMounted } from 'vue'; // Adicionei onMounted
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const tenantStore = useTenantStore();
const router = useRouter();

const username = ref('');
const password = ref('');
const loading = ref(false);
const errorMessage = ref('');

// Tenta carregar o White Label assim que abre a tela de login
onMounted(() => {
    tenantStore.loadSettings();
});

const handleLogin = async () => {
    loading.value = true;
    errorMessage.value = '';
    try {
        await authStore.login({ username: username.value, password: password.value });
        await tenantStore.loadSettings(); // Garante reload após login
        
        if (authStore.isGuardian) router.push({ name: 'parent-dashboard' });
        else if (authStore.isTeacher) router.push({ name: 'my-classes' });
        else router.push({ name: 'dashboard' });
        
    } catch (error) {
        errorMessage.value = 'Usuário ou senha inválidos.';
    } finally {
        loading.value = false;
    }
};
</script>

<template>
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <div class="w-full flex flex-col items-center justify-center">
            <div class="w-full sm:w-[450px] bg-surface-0 dark:bg-surface-900 p-8 sm:p-12 shadow-xl" style="border-radius: 20px;">
                <div class="text-center mb-8">
                    <img :src="tenantStore.currentLogo" :alt="tenantStore.currentName" class="mb-4 mx-auto" style="height: 90px; object-fit: contain;">
                    
                    <div class="text-2xl font-bold text-surface-900 dark:text-surface-0 mb-2">{{ tenantStore.currentName }}</div>
                    <small class="text-muted-color font-medium">Faça login para acessar o painel</small>
                </div>

                <div class="flex flex-col gap-4">
                    <div>
                        <label for="username" class="block text-surface-900 dark:text-surface-0 font-medium mb-2">Usuário</label>
                        <InputText id="username" v-model="username" type="text" class="w-full" placeholder="Seu usuário ou CPF" />
                    </div>
                    <div>
                        <label for="password" class="block text-surface-900 dark:text-surface-0 font-medium mb-2">Senha</label>
                        <InputText id="password" v-model="password" type="password" class="w-full" @keyup.enter="handleLogin" />
                    </div>

                    <div v-if="errorMessage" class="text-red-500 font-semibold text-sm text-center">
                        <i class="pi pi-exclamation-circle mr-1"></i> {{ errorMessage }}
                    </div>

                    <div class="flex items-center justify-between mb-4">
                        <div class="flex items-center">
                            <Checkbox id="rememberme" :binary="true" class="mr-2"></Checkbox>
                            <label for="rememberme" class="text-sm">Lembrar-me</label>
                        </div>
                        <a class="font-medium no-underline text-sm cursor-pointer text-primary">Esqueceu a senha?</a>
                    </div>

                    <Button label="Entrar" icon="pi pi-sign-in" class="w-full" :loading="loading" @click="handleLogin"></Button>

                    <div class="mt-6 text-center border-t border-surface-200 dark:border-surface-700 pt-4">
                        <span class="text-600 text-xs uppercase tracking-wider">Acesso restrito</span><br>
                        <span class="font-bold text-sm text-surface-900 dark:text-surface-0">
                            {{ tenantStore.isCustomized ? tenantStore.currentName : 'Lumis Education System' }}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
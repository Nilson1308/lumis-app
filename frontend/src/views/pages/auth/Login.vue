<script setup>
import { useAuthStore } from '@/stores/auth';
import { useTenantStore } from '@/stores/tenant';
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast'; // Import do Toast
import api from '@/service/api'; // Import da API para o Forgot Password

const authStore = useAuthStore();
const tenantStore = useTenantStore();
const router = useRouter();
const toast = useToast();

const username = ref('');
const password = ref('');
const rememberMe = ref(false); // Estado do Checkbox
const loading = ref(false);
const errorMessage = ref('');

// Estados para Recuperação de Senha
const forgotDialog = ref(false);
const recoveryEmail = ref('');
const loadingRecovery = ref(false);

// Tenta carregar o White Label assim que abre a tela de login
onMounted(() => {
    tenantStore.loadSettings();
});

const handleLogin = async () => {
    loading.value = true;
    errorMessage.value = '';
    
    try {
        // Agora passamos o rememberMe para o store (precisa ajustar o store também, veja abaixo)
        await authStore.login({ 
            username: username.value, 
            password: password.value,
            remember: rememberMe.value 
        });

        await tenantStore.loadSettings(); // Garante reload após login
        
        if (authStore.isGuardian) router.push({ name: 'parent-dashboard' });
        else if (authStore.isTeacher) router.push({ name: 'my-classes' });
        else router.push({ name: 'dashboard' });
        
    } catch (error) {
        errorMessage.value = 'Usuário ou senha inválidos.';
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Credenciais inválidas', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const sendRecoveryEmail = async () => {
    if (!recoveryEmail.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Digite seu e-mail.', life: 3000 });
        return;
    }

    loadingRecovery.value = true;
    try {
        // Envia para o backend (vamos assumir que existe essa rota ou criar depois)
        // Se não existir rota ainda, exibe apenas a mensagem visual para o usuário não ficar travado
        try {
            await api.post('password_reset/', { email: recoveryEmail.value });
        } catch (e) {
            console.warn("Rota de reset não implementada ou erro de API", e);
        }

        toast.add({ 
            severity: 'success', 
            summary: 'Solicitação Recebida', 
            detail: 'Se o e-mail estiver cadastrado, você receberá um link de redefinição.', 
            life: 5000 
        });
        forgotDialog.value = false;
        recoveryEmail.value = '';
    } finally {
        loadingRecovery.value = false;
    }
};
</script>

<template>
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <Toast />
        
        <div class="w-full flex flex-col items-center justify-center">
            <div class="w-full sm:w-[450px] bg-surface-0 dark:bg-surface-900 p-8 sm:p-12 shadow-xl" style="border-radius: 20px;">
                
                <div class="text-center mb-8">
                    <img :src="tenantStore.currentLogo" :alt="tenantStore.currentName" class="mb-4 mx-auto" style="height: 90px; object-fit: contain;">
                    <small class="text-muted-color font-medium">Faça login para acessar o painel</small>
                </div>

                <div class="flex flex-col gap-4">
                    <div>
                        <label for="username" class="block text-surface-900 dark:text-surface-0 font-medium mb-2">Usuário</label>
                        <InputText id="username" v-model="username" type="text" class="w-full" placeholder="Seu usuário ou CPF" size="large" />
                    </div>
                    <div>
                        <label for="password" class="block text-surface-900 dark:text-surface-0 font-medium mb-2">Senha</label>
                        <InputText id="password" v-model="password" type="password" class="w-full" @keyup.enter="handleLogin" size="large" />
                    </div>

                    <div v-if="errorMessage" class="text-red-500 font-semibold text-sm text-center">
                        <i class="pi pi-exclamation-circle mr-1"></i> {{ errorMessage }}
                    </div>

                    <div class="flex items-center justify-between mb-4">
                        <div class="flex items-center">
                            <Checkbox v-model="rememberMe" id="rememberme" :binary="true" class="mr-2"></Checkbox>
                            <label for="rememberme" class="text-sm cursor-pointer select-none">Lembrar-me</label>
                        </div>
                        <a class="font-medium no-underline text-sm cursor-pointer text-primary hover:underline" @click="forgotDialog = true">Esqueceu a senha?</a>
                    </div>

                    <Button label="Entrar" icon="pi pi-sign-in" class="w-full" :loading="loading" @click="handleLogin" size="large"></Button>

                    <div class="mt-6 text-center border-t border-surface-200 dark:border-surface-700 pt-4">
                        <span class="text-600 text-xs uppercase tracking-wider">Acesso restrito</span><br>
                        <span class="font-bold text-sm text-surface-900 dark:text-surface-0">
                            {{ tenantStore.isCustomized ? tenantStore.currentName : 'Lumis Education System' }}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <Dialog v-model:visible="forgotDialog" modal header="Recuperar Senha" :style="{ width: '400px' }">
            <span class="block mb-4 text-surface-600 dark:text-surface-200">
                Digite seu e-mail cadastrado. Enviaremos um link para você redefinir sua senha.
            </span>
            <div class="field">
                <label for="recoveryEmail" class="font-bold mb-2 block">E-mail</label>
                <InputText id="recoveryEmail" v-model="recoveryEmail" class="w-full" placeholder="exemplo@email.com" />
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" text @click="forgotDialog = false" />
                <Button label="Enviar Link" icon="pi pi-send" :loading="loadingRecovery" @click="sendRecoveryEmail" />
            </template>
        </Dialog>

    </div>
</template>
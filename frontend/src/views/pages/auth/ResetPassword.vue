<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useTenantStore } from '@/stores/tenant';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const toast = useToast();
const tenantStore = useTenantStore();

const password = ref('');
const confirmPassword = ref('');
const loading = ref(false);

// Pega os tokens da URL
const uid = route.params.uid;
const token = route.params.token;

const handleReset = async () => {
    if (password.value !== confirmPassword.value) {
        toast.add({ severity: 'warn', summary: 'Erro', detail: 'As senhas não coincidem.' });
        return;
    }
    if (password.value.length < 6) {
        toast.add({ severity: 'warn', summary: 'Erro', detail: 'A senha deve ter no mínimo 6 caracteres.' });
        return;
    }

    loading.value = true;
    try {
        await api.post('password_reset_confirm/', {
            uid: uid,
            token: token,
            password: password.value
        });
        
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Senha alterada! Redirecionando...', life: 3000 });
        
        setTimeout(() => {
            router.push('/login');
        }, 2000);
        
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Link inválido ou expirado.' });
    } finally {
        loading.value = false;
    }
};
</script>

<template>
    <div class="bg-surface-50 dark:bg-surface-950 flex items-center justify-center min-h-screen min-w-[100vw] overflow-hidden">
        <Toast />
        <div class="w-full flex flex-col items-center justify-center">
            <div class="w-full sm:w-[450px] bg-surface-0 dark:bg-surface-900 p-8 sm:p-12 shadow-xl" style="border-radius: 20px;">
                
                <div class="text-center mb-8">
                    <img :src="tenantStore.currentLogo" class="mb-4 mx-auto" style="height: 60px;">
                    <div class="text-2xl font-bold text-surface-900 dark:text-surface-0 mb-2">Redefinir Senha</div>
                    <small class="text-muted-color">Digite sua nova senha abaixo</small>
                </div>

                <div class="flex flex-col gap-4">
                    <div>
                        <label class="block font-medium mb-2">Nova Senha</label>
                        <InputText v-model="password" type="password" class="w-full" toggleMask />
                    </div>
                    <div>
                        <label class="block font-medium mb-2">Confirmar Senha</label>
                        <InputText v-model="confirmPassword" type="password" class="w-full" toggleMask @keyup.enter="handleReset" />
                    </div>

                    <Button label="Salvar Nova Senha" icon="pi pi-check" class="w-full mt-2" :loading="loading" @click="handleReset" />
                    
                    <div class="text-center mt-4">
                        <router-link to="/login" class="text-primary font-bold no-underline">Voltar ao Login</router-link>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
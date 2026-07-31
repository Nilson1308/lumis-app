<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import api from '@/service/api';

const router = useRouter();
const toast = useToast();
const authStore = useAuthStore();

const newPassword = ref('');
const confirmPassword = ref('');
const loading = ref(false);

const submit = async () => {
    if (!newPassword.value || !confirmPassword.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha os dois campos.', life: 3000 });
        return;
    }
    if (newPassword.value !== confirmPassword.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'As senhas não conferem.', life: 3000 });
        return;
    }
    if (newPassword.value.length < 8) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'A senha deve ter no mínimo 8 caracteres.', life: 3000 });
        return;
    }

    loading.value = true;
    try {
        await api.post('users/change-password/', {
            new_password: newPassword.value,
            confirm_password: confirmPassword.value
        });

        await authStore.fetchUser();
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Senha atualizada com sucesso.', life: 2500 });
        router.push({ name: 'dashboard' });
    } catch (error) {
        const detail = error?.response?.data?.detail || 'Não foi possível atualizar a senha.';
        toast.add({ severity: 'error', summary: 'Erro', detail, life: 3500 });
    } finally {
        loading.value = false;
    }
};

const logout = () => authStore.logout();
</script>

<template>
    <div class="flex align-items-center justify-content-center min-h-screen surface-ground px-3">
        <Toast />
        <div class="card w-full md:w-30rem">
            <div class="text-center mb-4">
                <h2 class="m-0 mb-2 text-900">Troca obrigatória de senha</h2>
                <p class="text-600 m-0">Por segurança, altere sua senha para continuar.</p>
            </div>

            <div class="field mb-6">
                <label class="font-bold block mb-2">Nova senha</label>
                <Password v-model="newPassword" :feedback="true" toggleMask class="w-full" inputClass="w-full" />
            </div>

            <div class="field mb-6">
                <label class="font-bold block mb-2">Confirmar nova senha</label>
                <Password v-model="confirmPassword" :feedback="false" toggleMask class="w-full" inputClass="w-full" @keyup.enter="submit" />
            </div>

            <div class="flex gap-2">
                <Button label="Sair" severity="secondary" class="w-full" @click="logout" />
                <Button label="Atualizar senha" icon="pi pi-check" class="w-full" :loading="loading" @click="submit" />
            </div>
        </div>
    </div>
</template>

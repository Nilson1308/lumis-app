<script setup>
import { useRouter } from 'vue-router';
import { ref, onMounted } from 'vue';
import api from '@/service/api';

const router = useRouter();
const children = ref([]);
const loading = ref(true);

const openReportCard = (studentId) => {
    router.push({ name: 'parent-report-card', params: { id: studentId } });
};

const openAttendance = (studentId) => {
    router.push({ name: 'parent-attendance', params: { id: studentId } });
};

onMounted(async () => {
    try {
        // Precisaremos criar esse endpoint no próximo passo
        const response = await api.get('students/my-children/');
        children.value = response.data;
    } catch (e) {
        console.error("Erro ao carregar filhos", e);
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <div class="grid grid-cols-12 gap-4 mb-2">
        <div class="col-span-12 xl:col-span-12">
            <div class="card mb-0">
                <div class="flex justify-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">Bem-vindo(a)</span>
                        <div class="text-900 font-medium text-xl">Portal da Família</div>
                    </div>
                    <div class="flex items-center justify-center bg-purple-50 dark:bg-purple-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-users text-purple-500 text-xl"></i>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-span-12 xl:col-span-4" v-for="child in children" :key="child.id">
            <div class="card card-w-title cursor-pointer hover:surface-100 transition-duration-200">
                <div class="flex align-center">
                    <Avatar icon="pi pi-user" size="large" shape="circle" class="mr-3 bg-indigo-500 text-white" />
                    <div>
                        <div class="text-xl font-bold">{{ child.name }}</div>
                        <span class="text-gray-500">{{ child.classroom_name }}</span>
                    </div>
                </div>
                <div class="mt-3 flex gap-2">
                    <Button label="Boletim" icon="pi pi-file" class="p-button-sm p-button-outlined" @click="openReportCard(child.id)" />
                    <Button label="Faltas" icon="pi pi-calendar" class="p-button-sm p-button-outlined p-button-warning" @click="openAttendance(child.id)" />
                </div>
            </div>
        </div>
        
        <div v-if="!loading && children.length === 0" class="col-12">
            <div class="card">
                <p>Nenhum aluno vinculado ao seu CPF.</p>
            </div>
        </div>
    </div>
</template>
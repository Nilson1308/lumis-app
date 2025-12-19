<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const reports = ref([]);
const loading = ref(true);
const studentName = ref('');
const displayDialog = ref(false);
const selectedReport = ref({});

const loadData = async () => {
    try {
        const studentId = route.params.id;
        loading.value = true;

        // Busca Relatórios filtrados pelo aluno E dados do aluno (para o cabeçalho)
        const [repRes, childRes] = await Promise.all([
            api.get(`student-reports/?student=${studentId}`),
            api.get('students/my-children/')
        ]);

        reports.value = repRes.data.results || repRes.data;

        // Pega nome do aluno
        const currentStudent = childRes.data.find(c => c.id == studentId);
        if (currentStudent) studentName.value = currentStudent.name;

    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
};

const openReport = (item) => {
    selectedReport.value = item;
    displayDialog.value = true;
};

const goBack = () => router.push({ name: 'parent-dashboard' });

onMounted(() => {
    loadData();
});
</script>

<template>
    <div class="card">
        <div class="flex justify-between items-center mb-6">
            <div class="flex items-center gap-2">
                <Button icon="pi pi-arrow-left" class="p-button-rounded p-button-text" @click="goBack" />
                <div>
                    <span class="block text-xl font-bold">Relatórios Pedagógicos</span>
                    <span class="text-sm text-gray-500">{{ studentName }}</span>
                </div>
            </div>
        </div>

        <div v-if="!loading && reports.length === 0" class="text-center p-6 border-dashed border-1 border-gray-300 border-round">
            <i class="pi pi-file text-4xl text-gray-300 mb-3"></i>
            <p class="m-0 text-gray-500">Nenhum relatório pedagógico disponível no momento.</p>
        </div>

        <div v-else class="grid grid-cols-12 gap-4">
            <div class="col-span-12" v-for="item in reports" :key="item.id">
                <div class="surface-card p-4 border-1 border-gray-200 border-round hover:surface-50 cursor-pointer transition-colors" @click="openReport(item)">
                    <div class="flex justify-between items-start">
                        <div>
                            <span class="text-xl text-primary font-bold mb-1 block">{{ item.subject }}</span>
                            <span class="text-sm">Relatório de {{ new Date(item.date).toLocaleDateString('pt-BR') }}</span>
                            <div class="flex items-center gap-2 text-sm text-gray-500 mt-3">
                                <i class="pi pi-user"></i>
                                <span>Prof. {{ item.teacher_name }}</span>
                            </div>
                        </div>
                        <Button icon="pi pi-angle-right" class="p-button-rounded p-button-text p-button-secondary" />
                    </div>
                </div>
            </div>
        </div>

        <Dialog v-model:visible="displayDialog" :header="selectedReport.subject" :modal="true" :style="{ width: '800px' }" class="p-fluid" maximizable>
            <div class="mb-4 text-sm text-gray-500 border-bottom-1 border-gray-100 pb-2">
                Data: {{ new Date(selectedReport.date).toLocaleDateString('pt-BR') }} • 
                Professor: {{ selectedReport.teacher_name }}
            </div>
            <Divider/>
            <div class="line-height-3 text-lg" v-html="selectedReport.content" style="overflow-wrap: break-word;"></div>
            <Divider/>
            <template #footer>
                <Button label="Fechar" icon="pi pi-check" @click="displayDialog = false" autofocus />
            </template>
        </Dialog>
    </div>
</template>
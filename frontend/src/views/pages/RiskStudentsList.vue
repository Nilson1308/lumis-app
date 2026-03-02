<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/service/api';
import { useToast } from 'primevue/usetoast';

const router = useRouter();
const toast = useToast();
const students = ref([]);
const loading = ref(true);

const loadData = async () => {
    loading.value = true;
    try {
        const { data } = await api.get('dashboard/risk-students/');
        students.value = data;
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar alunos em risco.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const goBack = () => {
    router.push('/');
};

onMounted(() => {
    loadData();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                    <Button icon="pi pi-arrow-left" class="p-button-text p-button-rounded" @click="goBack" v-tooltip.left="'Voltar ao Dashboard'" />
                    <div>
                        <h2 class="font-bold text-900 m-0">Alunos em Risco (+5 Faltas)</h2>
                        <span class="text-500 text-sm">Alunos com mais de 5 faltas no período</span>
                    </div>
                </div>
                <Button icon="pi pi-refresh" class="p-button-outlined" label="Atualizar" @click="loadData" />
            </div>

            <DataTable
                :value="students"
                :loading="loading"
                responsiveLayout="scroll"
                stripedRows
            >
                <template #empty>
                    <div class="text-center py-8 text-500">
                        <i class="pi pi-check-circle text-4xl text-green-500 mb-2"></i>
                        <p class="m-0">Nenhum aluno em risco no momento.</p>
                    </div>
                </template>
                <Column field="registration_number" header="Matrícula" />
                <Column field="name" header="Aluno">
                    <template #body="slotProps">
                        <span class="font-medium">{{ slotProps.data.name }}</span>
                    </template>
                </Column>
                <Column field="classroom_name" header="Turma" />
                <Column field="absences" header="Faltas">
                    <template #body="slotProps">
                        <Tag severity="danger">{{ slotProps.data.absences }}</Tag>
                    </template>
                </Column>
                <Column header="Ações">
                    <template #body="slotProps">
                        <Button
                            v-if="slotProps.data.classroom_id"
                            icon="pi pi-external-link"
                            class="p-button-sm p-button-outlined"
                            label="Ver Turma"
                            @click="router.push({ name: 'classroom-detail', params: { id: slotProps.data.classroom_id } })"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const toast = useToast();

const studentId = ref(null);
const studentName = ref('');
const studentClass = ref('');
const loading = ref(true);
const diary = ref([]);
const periods = ref([]);
const subjects = ref([]);
const selectedPeriod = ref(null);
const selectedSubject = ref(null);

const toPlainText = (value) => {
    if (!value) return '';
    const parser = new DOMParser();
    const doc = parser.parseFromString(value, 'text/html');
    return (doc.documentElement.textContent || '')
        .replace(/\u00A0/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
};

const buildQuery = () => {
    const query = {};
    if (selectedPeriod.value !== null && selectedPeriod.value !== undefined) {
        query.academic_period = Number(selectedPeriod.value);
    }
    if (selectedSubject.value !== null && selectedSubject.value !== undefined) {
        query.subject = Number(selectedSubject.value);
    }
    return query;
};

const loadPeriods = async () => {
    try {
        const response = await api.get('periods/?page_size=100');
        const rows = response.data.results || response.data;
        periods.value = rows.map((period) => ({
            id: period.id,
            name: period.name
        }));
    } catch (error) {
        periods.value = [];
    }
};

const loadData = async () => {
    loading.value = true;
    try {
        const parsedStudentId = parseInt(route.params.id, 10);
        studentId.value = parsedStudentId;

        const [diaryResponse, childrenResponse] = await Promise.all([
            api.get(`students/${parsedStudentId}/class-diary/`, { params: buildQuery() }),
            api.get('students/my-children/')
        ]);

        diary.value = diaryResponse.data || [];
        if (subjects.value.length === 0) {
            const subjectMap = new Map();
            diary.value.forEach((entry) => {
                if (!subjectMap.has(entry.subject_id)) {
                    subjectMap.set(entry.subject_id, {
                        id: entry.subject_id,
                        name: entry.subject_name
                    });
                }
            });
            subjects.value = Array.from(subjectMap.values()).sort((a, b) => a.name.localeCompare(b.name));
        }

        const currentStudent = childrenResponse.data.find((child) => child.id === parsedStudentId);
        if (currentStudent) {
            studentName.value = currentStudent.name;
            studentClass.value = currentStudent.classroom_name || 'Sem Turma';
        }
    } catch (error) {
        console.error(error);
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: 'Não foi possível carregar o diário de classe.',
            life: 3000
        });
    } finally {
        loading.value = false;
    }
};

const goBack = () => router.push({ name: 'parent-dashboard' });
const applyFilters = () => loadData();
const clearFilters = () => {
    selectedPeriod.value = null;
    selectedSubject.value = null;
    loadData();
};

onMounted(() => {
    loadPeriods();
    loadData();
});
</script>

<template>
    <div class="card">
        <Toast />

        <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
            <div class="flex items-center gap-2 self-start md:self-auto">
                <Button icon="pi pi-arrow-left" class="p-button-rounded p-button-text" @click="goBack" />
                <div>
                    <span class="block text-xl font-bold">Diário de Classe</span>
                    <span class="text-sm text-gray-500 hidden md:inline">Conteúdo ministrado e tarefas</span>
                </div>
            </div>

            <div class="flex items-center gap-3 w-full md:w-auto">
                <div class="text-right flex-grow-1 md:flex-grow-0">
                    <div class="text-900 font-bold text-lg">{{ studentName }}</div>
                    <div class="text-600">{{ studentClass }}</div>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-12 gap-4 mb-4">
            <div class="col-span-12 xl:col-span-4">
                <label class="block font-bold mb-2">Período</label>
                <Dropdown
                    v-model="selectedPeriod"
                    :options="periods"
                    optionLabel="name"
                    optionValue="id"
                    placeholder="Todos os períodos"
                    class="w-full"
                    showClear
                />
            </div>
            <div class="col-span-12 xl:col-span-4">
                <label class="block font-bold mb-2">Disciplina</label>
                <Dropdown
                    v-model="selectedSubject"
                    :options="subjects"
                    optionLabel="name"
                    optionValue="id"
                    placeholder="Todas as disciplinas"
                    class="w-full"
                    showClear
                />
            </div>
            <div class="col-span-12 xl:col-span-4 flex items-end gap-2">
                <Button label="Aplicar" icon="pi pi-filter" @click="applyFilters" />
                <Button label="Limpar" icon="pi pi-times" class="p-button-outlined" @click="clearFilters" />
            </div>
        </div>

        <DataTable :value="diary" :loading="loading" :paginator="true" :rows="10" responsiveLayout="scroll" stripedRows>
            <template #empty>Nenhum conteúdo disponível para este aluno.</template>

            <Column field="date" header="Data" sortable style="width: 130px">
                <template #body="slotProps">
                    {{ new Date(slotProps.data.date + 'T00:00:00').toLocaleDateString('pt-BR') }}
                </template>
            </Column>

            <Column field="subject_name" header="Disciplina" sortable style="width: 220px" />

            <Column header="Conteúdo Ministrado">
                <template #body="slotProps">
                    <div class="line-height-3 white-space-pre-line">{{ toPlainText(slotProps.data.content) }}</div>
                </template>
            </Column>

            <Column header="Lição de Casa / Tarefa" style="width: 260px">
                <template #body="slotProps">
                    <span>{{ slotProps.data.homework ? toPlainText(slotProps.data.homework) : '-' }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

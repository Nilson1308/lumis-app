<script setup>
import { ref, onMounted, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import api from '@/service/api';

const toast = useToast();
const authStore = useAuthStore();

const periods = ref([]);
const classrooms = ref([]);
const selectedPeriod = ref(null);
const selectedClassroom = ref(null);
const loading = ref(true);
const loadingPdf = ref(false);

const isCoordinator = computed(() => authStore.isCoordinator || authStore.isAdmin);

const loadDependencies = async () => {
    loading.value = true;
    try {
        const [periodsRes, classroomsRes] = await Promise.all([
            api.get('periods/'),
            isCoordinator.value 
                ? api.get('classrooms/?page_size=1000')
                : api.get('assignments/my_classes/')
        ]);

        periods.value = periodsRes.data.results || periodsRes.data;
        const activePeriod = periods.value.find(p => p.is_active);
        if (activePeriod) selectedPeriod.value = activePeriod.id;
        else if (periods.value.length > 0) selectedPeriod.value = periods.value[0].id;

        if (isCoordinator.value) {
            classrooms.value = (classroomsRes.data.results || classroomsRes.data).map(c => ({
                id: c.id,
                name: c.name
            }));
        } else {
            const seen = new Map();
            (classroomsRes.data || []).forEach(a => {
                if (a.classroom && !seen.has(a.classroom)) {
                    seen.set(a.classroom, { id: a.classroom, name: a.classroom_name });
                }
            });
            classrooms.value = Array.from(seen.values()).sort((a, b) => a.name.localeCompare(b.name));
        }

        if (classrooms.value.length === 1) selectedClassroom.value = classrooms.value[0].id;
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const downloadPdf = async (type) => {
    if (!selectedPeriod.value || !selectedClassroom.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Selecione período e turma.', life: 3000 });
        return;
    }

    loadingPdf.value = true;
    try {
        const endpoint = type === 'diary' ? 'reports/diary-pdf/' : 'reports/attendance-pdf/';
        const params = { classroom: selectedClassroom.value, period: selectedPeriod.value };
        const { data } = await api.get(endpoint, {
            params,
            responseType: 'blob'
        });
        const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
        window.open(url, '_blank');
        setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
        const msg = (e.response?.data && !(e.response.data instanceof Blob) && e.response.data.detail) 
            ? e.response.data.detail 
            : 'Falha ao gerar PDF.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 3000 });
    } finally {
        loadingPdf.value = false;
    }
};

onMounted(() => {
    loadDependencies();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <h2 class="font-bold text-900 mb-4">Relatórios em PDF</h2>
            <p class="text-500 mb-4">Gere o Diário de Classe ou o Relatório de Frequências por período e turma.</p>

            <div v-if="loading" class="flex align-items-center gap-2">
                <i class="pi pi-spin pi-spinner"></i>
                <span>Carregando...</span>
            </div>

            <div v-else class="grid grid-cols-12 gap-4">
                <div class="col-span-12 md:col-span-4">
                    <label class="block font-bold mb-2">Período</label>
                    <Dropdown
                        v-model="selectedPeriod"
                        :options="periods"
                        optionLabel="name"
                        optionValue="id"
                        placeholder="Selecione o período"
                        class="w-full"
                    />
                </div>
                <div class="col-span-12 md:col-span-4">
                    <label class="block font-bold mb-2">Turma</label>
                    <Dropdown
                        v-model="selectedClassroom"
                        :options="classrooms"
                        optionLabel="name"
                        optionValue="id"
                        placeholder="Selecione a turma"
                        class="w-full"
                    />
                </div>
            </div>

            <div class="flex flex-wrap gap-3 mt-4">
                <Button
                    label="Gerar Diário de Classe (PDF)"
                    icon="pi pi-file-pdf"
                    :loading="loadingPdf"
                    :disabled="!selectedPeriod || !selectedClassroom"
                    @click="downloadPdf('diary')"
                />
                <Button
                    label="Gerar Frequências (PDF)"
                    icon="pi pi-file-pdf"
                    severity="secondary"
                    :loading="loadingPdf"
                    :disabled="!selectedPeriod || !selectedClassroom"
                    @click="downloadPdf('attendance')"
                />
            </div>
        </div>
    </div>
</template>

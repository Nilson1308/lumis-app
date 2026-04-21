<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import api from '@/service/api';

const router = useRouter();
const toast = useToast();
const authStore = useAuthStore();

const loading = ref(true);
const classrooms = ref([]);
const filterText = ref('');

const filteredRows = computed(() => {
    const q = filterText.value.trim().toLowerCase();
    if (!q) return classrooms.value;
    return classrooms.value.filter((c) => {
        const name = (c.name || '').toLowerCase();
        const seg = (c.segment_name || c.segment || '').toLowerCase();
        const year = String(c.year || '');
        return name.includes(q) || seg.includes(q) || year.includes(q);
    });
});

const loadClassrooms = async () => {
    loading.value = true;
    try {
        const { data } = await api.get('classrooms/', { params: { page_size: 500 } });
        const rows = data.results || data || [];
        classrooms.value = Array.isArray(rows) ? rows : [];
    } catch {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Não foi possível carregar as turmas.', life: 4000 });
        classrooms.value = [];
    } finally {
        loading.value = false;
    }
};

const openSchedule = (row) => {
    router.push({
        name: 'classroom-detail',
        params: { id: row.id },
        query: { tab: 'schedule' }
    });
};

onMounted(() => {
    if (!authStore.canEditClassSchedule) {
        toast.add({ severity: 'warn', summary: 'Acesso', detail: 'Sem permissão para gestão de grades.', life: 4000 });
        router.replace({ name: 'dashboard' });
        return;
    }
    loadClassrooms();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <div class="flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                <div>
                    <h2 class="text-900 font-semibold m-0 mb-1">Grades horárias por turma</h2>
                    <p class="text-600 m-0 text-sm">
                        Escolha uma turma para abrir o detalhe já no separador da grade (criar, editar ou remover
                        horários).
                    </p>
                </div>
                <Button
                    label="Atualizar lista"
                    icon="pi pi-refresh"
                    class="p-button-outlined"
                    :loading="loading"
                    @click="loadClassrooms"
                />
            </div>

            <IconField class="mb-3" style="max-width: 24rem">
                <InputIcon>
                    <i class="pi pi-search" />
                </InputIcon>
                <InputText v-model="filterText" placeholder="Filtrar por nome, segmento ou ano…" fluid />
            </IconField>

            <DataTable
                :value="filteredRows"
                :loading="loading"
                dataKey="id"
                stripedRows
                responsiveLayout="scroll"
                :paginator="filteredRows.length > 15"
                :rows="15"
                sortField="name"
                :sortOrder="1"
            >
                <template #empty>
                    <span v-if="!loading">Nenhuma turma encontrada.</span>
                </template>
                <Column field="name" header="Turma" sortable />
                <Column field="segment_name" header="Segmento" sortable>
                    <template #body="{ data }">
                        {{ data.segment_name || data.segment || '—' }}
                    </template>
                </Column>
                <Column field="year" header="Ano" sortable style="width: 6rem" />
                <Column header="" style="width: 11rem">
                    <template #body="{ data }">
                        <Button
                            label="Abrir grade"
                            icon="pi pi-calendar"
                            class="p-button-sm"
                            @click="openSchedule(data)"
                        />
                    </template>
                </Column>
            </DataTable>
        </div>
    </div>
</template>

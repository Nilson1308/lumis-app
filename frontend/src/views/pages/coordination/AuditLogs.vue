<script setup>
import { ref, onMounted } from 'vue';
import api from '@/service/api';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const loading = ref(false);
const logs = ref([]);
const totalRecords = ref(0);
const lazyParams = ref({ first: 0, rows: 20, page: 0 });
const filters = ref({
    action: '',
    resource_type: '',
    username: '',
    date_from: '',
    date_to: ''
});

const formatDateForApi = (value) => {
    if (!value) return '';
    if (typeof value === 'string') return value;
    const d = new Date(value);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const loadLogs = async () => {
    loading.value = true;
    try {
        const params = {
            page: (lazyParams.value.page || 0) + 1,
            page_size: lazyParams.value.rows || 20,
            ...Object.fromEntries(
                Object.entries({
                    ...filters.value,
                    date_from: formatDateForApi(filters.value.date_from),
                    date_to: formatDateForApi(filters.value.date_to),
                }).filter(([, v]) => v)
            )
        };
        const res = await api.get('access-audits/', { params });
        logs.value = res.data?.results || [];
        totalRecords.value = res.data?.count || 0;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao carregar logs de auditoria.', life: 4000 });
    } finally {
        loading.value = false;
    }
};

const getQueryParams = () => ({
    ...Object.fromEntries(
        Object.entries({
            ...filters.value,
            date_from: formatDateForApi(filters.value.date_from),
            date_to: formatDateForApi(filters.value.date_to),
        }).filter(([, v]) => v)
    )
});

const exportCsv = async () => {
    try {
        const res = await api.get('access-audits/export-csv/', {
            params: getQueryParams(),
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv;charset=utf-8;' }));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'auditoria-lumis.csv');
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao exportar CSV.', life: 4000 });
    }
};

const severityTag = (severity) => {
    if (severity === 'HIGH') return 'danger';
    if (severity === 'MEDIUM') return 'warning';
    return 'info';
};

const onPage = (event) => {
    lazyParams.value = event;
    loadLogs();
};

const clearFilters = () => {
    filters.value = { action: '', resource_type: '', username: '', date_from: '', date_to: '' };
    lazyParams.value = { ...lazyParams.value, first: 0, page: 0 };
    loadLogs();
};

onMounted(loadLogs);
</script>

<template>
    <div class="card">
        <Toast />
        <h4 class="mb-3">Auditoria de Ações Sensíveis</h4>
        <div class="flex justify-end mb-2">
            <Button label="Exportar CSV" icon="pi pi-download" class="p-button-outlined p-button-success" @click="exportCsv" />
        </div>

        <div class="grid grid-cols-12 gap-3 mb-3">
            <div class="col-span-12 md:col-span-2">
                <InputText v-model="filters.action" placeholder="Ação" class="w-full" />
            </div>
            <div class="col-span-12 md:col-span-2">
                <InputText v-model="filters.resource_type" placeholder="Recurso" class="w-full" />
            </div>
            <div class="col-span-12 md:col-span-2">
                <InputText v-model="filters.username" placeholder="Usuário" class="w-full" />
            </div>
            <div class="col-span-12 md:col-span-2">
                <DatePicker v-model="filters.date_from" dateFormat="yy-mm-dd" placeholder="Data inicial" showIcon fluid />
            </div>
            <div class="col-span-12 md:col-span-2">
                <DatePicker v-model="filters.date_to" dateFormat="yy-mm-dd" placeholder="Data final" showIcon fluid />
            </div>
            <div class="col-span-12 md:col-span-2 flex gap-2">
                <Button label="Filtrar" icon="pi pi-search" class="w-full" @click="loadLogs" />
                <Button icon="pi pi-times" class="p-button-outlined" @click="clearFilters" />
            </div>
        </div>

        <DataTable
            :value="logs"
            :loading="loading"
            :lazy="true"
            :paginator="true"
            :rows="lazyParams.rows"
            :first="lazyParams.first"
            :totalRecords="totalRecords"
            @page="onPage"
            responsiveLayout="scroll"
            stripedRows
        >
            <template #empty>Nenhum log encontrado para os filtros aplicados.</template>
            <Column field="created_at" header="Data/Hora">
                <template #body="slotProps">
                    {{ new Date(slotProps.data.created_at).toLocaleString('pt-BR') }}
                </template>
            </Column>
            <Column field="username" header="Usuário" />
            <Column field="action" header="Ação" />
            <Column field="severity" header="Severidade">
                <template #body="slotProps">
                    <Tag :value="slotProps.data.severity" :severity="severityTag(slotProps.data.severity)" />
                </template>
            </Column>
            <Column field="resource_type" header="Recurso" />
            <Column field="resource_id" header="ID Recurso" />
            <Column header="Detalhes">
                <template #body="slotProps">
                    <span class="text-sm">{{ JSON.stringify(slotProps.data.details || {}) }}</span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

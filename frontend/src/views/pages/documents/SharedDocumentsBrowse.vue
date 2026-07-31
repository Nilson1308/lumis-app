<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const route = useRoute();

const documents = ref([]);
const loading = ref(true);
const search = ref('');
const filterCategory = ref(null);
const unreadOnly = ref(false);

const totalRecords = ref(0);
const lazyParams = ref({ first: 0, rows: 10, page: 0 });

const categoryOptions = [
    { label: 'Geral', value: 'GENERAL' },
    { label: 'Pedagógico', value: 'PEDAGOGICAL' },
    { label: 'Administrativo', value: 'ADMINISTRATIVE' },
    { label: 'Financeiro', value: 'FINANCIAL' },
    { label: 'Eventos', value: 'EVENTS' },
];

let searchTimeout = null;

const loadDocuments = async () => {
    loading.value = true;
    try {
        const params = {
            page: (lazyParams.value.page ?? 0) + 1,
            page_size: lazyParams.value.rows ?? 10,
        };
        if (search.value.trim()) params.search = search.value.trim();
        if (filterCategory.value) params.category = filterCategory.value;
        if (unreadOnly.value) params.unread_only = 'true';

        const res = await api.get('shared-documents/', { params });
        documents.value = res.data.results || res.data;
        totalRecords.value = res.data.count ?? documents.value.length;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao carregar documentos', life: 3000 });
        documents.value = [];
        totalRecords.value = 0;
    } finally {
        loading.value = false;
    }
};

const onPage = (event) => {
    lazyParams.value = { first: event.first, rows: event.rows, page: event.page };
    loadDocuments();
};

const onSearch = () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        lazyParams.value = { ...lazyParams.value, first: 0, page: 0 };
        loadDocuments();
    }, 400);
};

const onFilterChange = () => {
    lazyParams.value = { ...lazyParams.value, first: 0, page: 0 };
    loadDocuments();
};

const markAsRead = async (item) => {
    if (item.is_read) return item;
    try {
        await api.post(`shared-documents/${item.id}/mark-read/`);
        item.is_read = true;
    } catch (e) {
        console.error(e);
    }
    return item;
};

const openDocument = async (item) => {
    await markAsRead(item);
    const url = item.file_url || item.external_link;
    if (url) window.open(url, '_blank', 'noopener');
};

const markReadOnly = async (item) => {
    await markAsRead(item);
    toast.add({ severity: 'success', summary: 'Marcado como lido', life: 2000 });
};

const audienceSeverity = (value) => {
    if (value === 'TEACHERS') return 'info';
    if (value === 'GUARDIANS') return 'warn';
    if (value === 'CLASSROOM') return 'secondary';
    if (value === 'SEGMENT') return 'contrast';
    return 'success';
};

const highlightDocId = () => {
    const raw = route.query.doc;
    const docId = raw ? parseInt(String(raw), 10) : null;
    if (!docId) return;
    const found = documents.value.find((d) => d.id === docId);
    if (found && !found.is_read) {
        markAsRead(found);
    }
};

onMounted(async () => {
    await loadDocuments();
    highlightDocId();
});
</script>

<template>
    <div class="card">
        <Toast />

        <DataTable
            :value="documents"
            :loading="loading"
            lazy
            paginator
            :rows="lazyParams.rows"
            :totalRecords="totalRecords"
            :first="lazyParams.first"
            @page="onPage"
            dataKey="id"
            responsiveLayout="scroll"
        >
            <template #header>
                <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                        <span class="text-xl font-semibold block">Documentos da escola</span>
                        <span class="text-sm text-muted-color">Arquivos compartilhados com você pela coordenação e secretaria.</span>
                    </div>
                    <div class="flex flex-col sm:flex-row sm:items-center gap-2 w-full md:w-auto">
                        <IconField iconPosition="left" class="w-full sm:min-w-[14rem]">
                            <InputIcon class="pi pi-search" />
                            <InputText v-model="search" placeholder="Buscar..." @input="onSearch" fluid />
                        </IconField>
                        <Select
                            v-model="filterCategory"
                            :options="categoryOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder="Categoria"
                            showClear
                            class="w-full sm:w-auto sm:min-w-[10rem]"
                            @change="onFilterChange"
                        />
                        <div class="flex items-center gap-2 px-1">
                            <ToggleSwitch v-model="unreadOnly" @change="onFilterChange" />
                            <label class="text-sm whitespace-nowrap">Somente não lidos</label>
                        </div>
                    </div>
                </div>
            </template>

            <template #empty>
                <div class="text-center py-8 text-muted-color">
                    <i class="pi pi-folder-open text-4xl mb-3 block"></i>
                    Nenhum documento disponível no momento.
                </div>
            </template>

            <Column field="title" header="Documento" style="min-width: 16rem">
                <template #body="{ data }">
                    <div class="flex items-center gap-2">
                        <span class="font-medium">{{ data.title }}</span>
                        <Tag v-if="data.is_read === false" value="Novo" severity="danger" />
                    </div>
                    <div v-if="data.description" class="text-sm text-muted-color">{{ data.description }}</div>
                </template>
            </Column>
            <Column field="category_label" header="Categoria" style="min-width: 8rem" />
            <Column header="Destinado a" style="min-width: 10rem">
                <template #body="{ data }">
                    <Tag :value="data.target_audience_label" :severity="audienceSeverity(data.target_audience)" />
                    <div v-if="data.classroom_name" class="text-xs mt-1">{{ data.classroom_name }}</div>
                    <div v-if="data.segment_name" class="text-xs mt-1">{{ data.segment_name }}</div>
                </template>
            </Column>
            <Column field="created_at" header="Publicado em" style="min-width: 8rem">
                <template #body="{ data }">
                    {{ new Date(data.created_at).toLocaleDateString('pt-BR') }}
                </template>
            </Column>
            <Column header="Acesso" style="min-width: 10rem">
                <template #body="{ data }">
                    <div class="flex flex-wrap gap-1">
                        <Button
                            label="Abrir"
                            icon="pi pi-external-link"
                            size="small"
                            outlined
                            :disabled="!data.file_url && !data.external_link"
                            @click="openDocument(data)"
                        />
                        <Button
                            v-if="!data.is_read"
                            label="Marcar lido"
                            icon="pi pi-check"
                            size="small"
                            text
                            @click="markReadOnly(data)"
                        />
                    </div>
                </template>
            </Column>
        </DataTable>
    </div>
</template>

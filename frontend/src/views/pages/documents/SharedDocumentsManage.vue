<script setup>
import { ref, onMounted, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();

const documents = ref([]);
const classrooms = ref([]);
const segments = ref([]);
const loading = ref(true);
const documentDialog = ref(false);
const deleteDialog = ref(false);
const readReportDialog = ref(false);
const readReportLoading = ref(false);
const readReportRows = ref([]);
const readReportTitle = ref('');
const submitted = ref(false);
const saving = ref(false);

const doc = ref({});
const selectedFile = ref(null);

const totalRecords = ref(0);
const lazyParams = ref({ first: 0, rows: 10, page: 0 });
const search = ref('');
const filterCategory = ref(null);
const filterAudience = ref(null);
const filterActive = ref(null);
const filterSegment = ref(null);

const categoryOptions = [
    { label: 'Geral', value: 'GENERAL' },
    { label: 'Pedagógico', value: 'PEDAGOGICAL' },
    { label: 'Administrativo', value: 'ADMINISTRATIVE' },
    { label: 'Financeiro', value: 'FINANCIAL' },
    { label: 'Eventos', value: 'EVENTS' },
];

const audienceOptions = [
    { label: 'Todos (professores e responsáveis)', value: 'ALL' },
    { label: 'Professores', value: 'TEACHERS' },
    { label: 'Responsáveis / Pais', value: 'GUARDIANS' },
    { label: 'Turma específica', value: 'CLASSROOM' },
    { label: 'Segmento / série', value: 'SEGMENT' },
];

const activeOptions = [
    { label: 'Ativos', value: 'true' },
    { label: 'Inativos', value: 'false' },
];

const showClassroomField = computed(() => doc.value.target_audience === 'CLASSROOM');
const showSegmentField = computed(() => doc.value.target_audience === 'SEGMENT');
const isEditing = computed(() => !!doc.value.id);

let searchTimeout = null;

const loadClassrooms = async () => {
    try {
        const res = await api.get('classrooms/', { params: { page_size: 500 } });
        classrooms.value = (res.data.results || res.data).map((c) => ({
            label: `${c.name} (${c.year})`,
            value: c.id,
        }));
    } catch (e) {
        console.error(e);
    }
};

const loadSegments = async () => {
    try {
        const res = await api.get('segments/', { params: { page_size: 500 } });
        segments.value = (res.data.results || res.data).map((s) => ({
            label: s.name,
            value: s.id,
        }));
    } catch (e) {
        console.error(e);
    }
};

const loadDocuments = async () => {
    loading.value = true;
    try {
        const params = {
            page: (lazyParams.value.page ?? 0) + 1,
            page_size: lazyParams.value.rows ?? 10,
        };
        if (search.value.trim()) params.search = search.value.trim();
        if (filterCategory.value) params.category = filterCategory.value;
        if (filterAudience.value) params.target_audience = filterAudience.value;
        if (filterActive.value) params.is_active = filterActive.value;
        if (filterSegment.value) params.segment = filterSegment.value;

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

const openNew = () => {
    doc.value = {
        title: '',
        description: '',
        category: 'GENERAL',
        target_audience: 'ALL',
        classroom: null,
        segment: null,
        external_link: '',
        is_active: true,
        has_file: false,
    };
    selectedFile.value = null;
    submitted.value = false;
    documentDialog.value = true;
};

const editDocument = (item) => {
    doc.value = {
        ...item,
        classroom: item.classroom || null,
        segment: item.segment || null,
        external_link: item.external_link || '',
    };
    selectedFile.value = null;
    submitted.value = false;
    documentDialog.value = true;
};

const confirmDelete = (item) => {
    doc.value = { ...item };
    deleteDialog.value = true;
};

const hideDialog = () => {
    documentDialog.value = false;
    submitted.value = false;
    selectedFile.value = null;
};

const onFileSelect = (event) => {
    const file = event.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
        toast.add({ severity: 'warn', summary: 'Arquivo grande', detail: 'O limite é 10 MB.', life: 4000 });
        return;
    }
    selectedFile.value = file;
    doc.value.external_link = '';
};

const clearSelectedFile = () => {
    selectedFile.value = null;
};

const buildFormData = () => {
    const formData = new FormData();
    formData.append('title', doc.value.title.trim());
    formData.append('description', doc.value.description || '');
    formData.append('category', doc.value.category);
    formData.append('target_audience', doc.value.target_audience);
    formData.append('is_active', doc.value.is_active ? 'true' : 'false');
    if (doc.value.target_audience === 'CLASSROOM' && doc.value.classroom) {
        formData.append('classroom', doc.value.classroom);
    }
    if (doc.value.target_audience === 'SEGMENT' && doc.value.segment) {
        formData.append('segment', doc.value.segment);
    }
    if (selectedFile.value) {
        formData.append('file', selectedFile.value);
    } else if (doc.value.external_link?.trim()) {
        formData.append('external_link', doc.value.external_link.trim());
    }
    return formData;
};

const saveDocument = async () => {
    submitted.value = true;

    if (!doc.value.title?.trim()) return;
    if (doc.value.target_audience === 'CLASSROOM' && !doc.value.classroom) return;
    if (doc.value.target_audience === 'SEGMENT' && !doc.value.segment) return;
    if (!selectedFile.value && !doc.value.external_link?.trim() && !doc.value.has_file) return;

    saving.value = true;
    try {
        const formData = buildFormData();
        if (isEditing.value) {
            await api.patch(`shared-documents/${doc.value.id}/`, formData);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Documento salvo com sucesso.', life: 3000 });
        } else {
            await api.post('shared-documents/', formData);
            toast.add({ severity: 'success', summary: 'Publicado', detail: 'Documento criado com sucesso.', life: 3000 });
        }
        hideDialog();
        loadDocuments();
    } catch (e) {
        const detail = e.response?.data?.error
            || Object.values(e.response?.data || {}).flat?.()?.[0]
            || 'Não foi possível salvar o documento.';
        toast.add({ severity: 'error', summary: 'Erro', detail, life: 5000 });
    } finally {
        saving.value = false;
    }
};

const deleteDocument = async () => {
    try {
        await api.delete(`shared-documents/${doc.value.id}/`);
        deleteDialog.value = false;
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Documento excluído.', life: 3000 });
        loadDocuments();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Não foi possível excluir.', life: 3000 });
    }
};

const audienceSeverity = (value) => {
    if (value === 'TEACHERS') return 'info';
    if (value === 'GUARDIANS') return 'warn';
    if (value === 'CLASSROOM') return 'secondary';
    if (value === 'SEGMENT') return 'contrast';
    return 'success';
};

const openReadReport = async (item) => {
    readReportTitle.value = item.title;
    readReportRows.value = [];
    readReportDialog.value = true;
    readReportLoading.value = true;
    try {
        const res = await api.get(`shared-documents/${item.id}/read-report/`);
        readReportRows.value = res.data || [];
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao carregar leituras.', life: 3000 });
        readReportDialog.value = false;
    } finally {
        readReportLoading.value = false;
    }
};

const openDocument = (item) => {
    const url = item.file_url || item.external_link;
    if (url) window.open(url, '_blank', 'noopener');
};

onMounted(async () => {
    await Promise.all([loadClassrooms(), loadSegments()]);
    await loadDocuments();
});
</script>

<template>
    <div class="card">
        <Toast />

        <Toolbar class="mb-4">
            <template #start>
                <Button label="Novo documento" icon="pi pi-plus" @click="openNew" />
            </template>
        </Toolbar>

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
                    <span class="text-xl font-semibold">Documentos compartilhados</span>
                    <div class="flex flex-col sm:flex-row flex-wrap gap-2 w-full md:w-auto">
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
                        <Select
                            v-model="filterAudience"
                            :options="audienceOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder="Público"
                            showClear
                            class="w-full sm:w-auto sm:min-w-[10rem]"
                            @change="onFilterChange"
                        />
                        <Select
                            v-model="filterActive"
                            :options="activeOptions"
                            optionLabel="label"
                            optionValue="value"
                            placeholder="Status"
                            showClear
                            class="w-full sm:w-auto sm:min-w-[9rem]"
                            @change="onFilterChange"
                        />
                        <Select
                            v-model="filterSegment"
                            :options="segments"
                            optionLabel="label"
                            optionValue="value"
                            placeholder="Segmento"
                            showClear
                            class="w-full sm:w-auto sm:min-w-[10rem]"
                            @change="onFilterChange"
                        />
                    </div>
                </div>
            </template>

            <Column field="title" header="Título" style="min-width: 14rem">
                <template #body="{ data }">
                    <div class="font-medium">{{ data.title }}</div>
                    <div v-if="data.description" class="text-sm text-muted-color line-clamp-2">{{ data.description }}</div>
                </template>
            </Column>
            <Column field="category_label" header="Categoria" style="min-width: 8rem" />
            <Column header="Público" style="min-width: 10rem">
                <template #body="{ data }">
                    <Tag :value="data.target_audience_label" :severity="audienceSeverity(data.target_audience)" />
                    <div v-if="data.classroom_name" class="text-xs mt-1">{{ data.classroom_name }}</div>
                    <div v-if="data.segment_name" class="text-xs mt-1">{{ data.segment_name }}</div>
                </template>
            </Column>
            <Column header="Leituras" style="min-width: 8rem">
                <template #body="{ data }">
                    <div v-if="data.read_stats" class="text-sm">
                        <span class="font-medium">{{ data.read_stats.read }}/{{ data.read_stats.total }}</span>
                        <span class="text-muted-color"> lidos</span>
                    </div>
                    <span v-else class="text-muted-color">—</span>
                </template>
            </Column>
            <Column header="Arquivo" style="min-width: 6rem">
                <template #body="{ data }">
                    <Button
                        v-if="data.file_url || data.external_link"
                        icon="pi pi-download"
                        text
                        rounded
                        v-tooltip.top="'Abrir documento'"
                        @click="openDocument(data)"
                    />
                    <span v-else class="text-muted-color">—</span>
                </template>
            </Column>
            <Column field="uploaded_by_name" header="Enviado por" style="min-width: 8rem" />
            <Column header="Status" style="min-width: 6rem">
                <template #body="{ data }">
                    <Tag :value="data.is_active ? 'Ativo' : 'Inativo'" :severity="data.is_active ? 'success' : 'danger'" />
                </template>
            </Column>
            <Column field="created_at" header="Data" style="min-width: 8rem">
                <template #body="{ data }">
                    {{ new Date(data.created_at).toLocaleDateString('pt-BR') }}
                </template>
            </Column>
            <Column header="Ações" style="min-width: 10rem">
                <template #body="{ data }">
                    <Button
                        icon="pi pi-eye"
                        text
                        rounded
                        class="mr-1"
                        v-tooltip.top="'Relatório de leitura'"
                        @click="openReadReport(data)"
                    />
                    <Button icon="pi pi-pencil" text rounded class="mr-1" @click="editDocument(data)" />
                    <Button icon="pi pi-trash" text rounded severity="danger" @click="confirmDelete(data)" />
                </template>
            </Column>
        </DataTable>

        <Dialog
            v-model:visible="documentDialog"
            :header="isEditing ? 'Editar documento' : 'Novo documento'"
            modal
            :style="{ width: '640px', maxWidth: '95vw' }"
            class="p-fluid shared-document-dialog"
            @hide="hideDialog"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label for="doc-title" class="block font-bold mb-2">Título *</label>
                    <InputText
                        id="doc-title"
                        v-model="doc.title"
                        :invalid="submitted && !doc.title?.trim()"
                        fluid
                    />
                    <small v-if="submitted && !doc.title?.trim()" class="p-error">Título é obrigatório.</small>
                </div>

                <div>
                    <label for="doc-description" class="block font-bold mb-2">Descrição</label>
                    <Textarea id="doc-description" v-model="doc.description" rows="4" autoResize fluid />
                </div>

                <div class="grid grid-cols-12 gap-4">
                    <div class="col-span-12 md:col-span-6">
                        <label for="doc-category" class="block font-bold mb-2">Categoria</label>
                        <Select
                            id="doc-category"
                            v-model="doc.category"
                            :options="categoryOptions"
                            optionLabel="label"
                            optionValue="value"
                            fluid
                        />
                    </div>
                    <div class="col-span-12 md:col-span-6">
                        <label for="doc-audience" class="block font-bold mb-2">Público-alvo *</label>
                        <Select
                            id="doc-audience"
                            v-model="doc.target_audience"
                            :options="audienceOptions"
                            optionLabel="label"
                            optionValue="value"
                            fluid
                        />
                    </div>
                </div>

                <div v-if="showClassroomField">
                    <label for="doc-classroom" class="block font-bold mb-2">Turma *</label>
                    <Select
                        id="doc-classroom"
                        v-model="doc.classroom"
                        :options="classrooms"
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Selecione a turma"
                        :invalid="submitted && !doc.classroom"
                        fluid
                    />
                    <small v-if="submitted && !doc.classroom" class="p-error">Selecione a turma.</small>
                </div>

                <div v-if="showSegmentField">
                    <label for="doc-segment" class="block font-bold mb-2">Segmento / série *</label>
                    <Select
                        id="doc-segment"
                        v-model="doc.segment"
                        :options="segments"
                        optionLabel="label"
                        optionValue="value"
                        placeholder="Selecione o segmento"
                        :invalid="submitted && !doc.segment"
                        fluid
                    />
                    <small v-if="submitted && !doc.segment" class="p-error">Selecione o segmento.</small>
                </div>

                <div class="rounded-lg border border-surface-200 dark:border-surface-700 p-4 flex flex-col gap-4">
                    <div>
                        <label for="doc-link" class="block font-bold mb-2">Link externo</label>
                        <InputText
                            id="doc-link"
                            v-model="doc.external_link"
                            placeholder="Google Drive, OneDrive, etc."
                            :disabled="!!selectedFile || (isEditing && doc.has_file && !selectedFile)"
                            fluid
                        />
                        <small class="text-muted-color block mt-2">
                            Informe um link externo ou selecione um arquivo abaixo (não use os dois).
                        </small>
                    </div>

                    <div class="flex items-center gap-3 text-muted-color text-sm">
                        <span class="flex-1 h-px bg-surface-200 dark:bg-surface-700"></span>
                        <span>ou</span>
                        <span class="flex-1 h-px bg-surface-200 dark:bg-surface-700"></span>
                    </div>

                    <div>
                        <label class="block font-bold mb-2">Arquivo</label>
                        <FileUpload
                            mode="basic"
                            chooseLabel="Selecionar arquivo"
                            accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.jpg,.jpeg,.png,.zip"
                            :maxFileSize="10485760"
                            customUpload
                            auto
                            class="w-full"
                            @select="onFileSelect"
                        />
                        <small class="text-muted-color block mt-2">PDF, Office, imagens ou ZIP — máximo 10 MB.</small>

                        <div
                            v-if="selectedFile"
                            class="mt-3 flex items-center gap-2 rounded-md border border-surface-200 dark:border-surface-700 px-3 py-2"
                        >
                            <i class="pi pi-file text-primary"></i>
                            <span class="flex-1 truncate">{{ selectedFile.name }}</span>
                            <Button icon="pi pi-times" text rounded size="small" @click="clearSelectedFile" />
                        </div>
                        <div v-else-if="isEditing && doc.has_file" class="mt-3 text-sm text-muted-color">
                            Já existe um arquivo anexado. Selecione outro para substituir.
                        </div>
                        <small
                            v-if="submitted && !selectedFile && !doc.external_link?.trim() && !doc.has_file"
                            class="p-error block mt-2"
                        >
                            Informe um arquivo ou um link externo.
                        </small>
                    </div>
                </div>

                <div class="flex items-start gap-3 rounded-lg bg-surface-50 dark:bg-surface-900 px-4 py-3">
                    <ToggleSwitch v-model="doc.is_active" />
                    <div class="flex flex-col gap-1">
                        <label class="font-bold leading-none">Documento ativo</label>
                        <span class="text-sm text-muted-color">Visível para o público-alvo selecionado.</span>
                    </div>
                </div>
            </div>

            <template #footer>
                <div class="flex justify-end gap-2 w-full">
                    <Button label="Cancelar" icon="pi pi-times" text @click="hideDialog" />
                    <Button label="Salvar" icon="pi pi-check" :loading="saving" @click="saveDocument" />
                </div>
            </template>
        </Dialog>

        <Dialog v-model:visible="readReportDialog" :header="`Leituras — ${readReportTitle}`" modal :style="{ width: '520px', maxWidth: '95vw' }">
            <div v-if="readReportLoading" class="py-6 text-center text-muted-color">Carregando...</div>
            <DataTable v-else :value="readReportRows" responsiveLayout="scroll" size="small">
                <template #empty>
                    <div class="py-4 text-center text-muted-color">Nenhum destinatário registrado ainda.</div>
                </template>
                <Column field="name" header="Usuário" />
                <Column header="Status" style="width: 8rem">
                    <template #body="{ data }">
                        <Tag :value="data.read ? 'Lido' : 'Não lido'" :severity="data.read ? 'success' : 'warn'" />
                    </template>
                </Column>
                <Column header="Em" style="width: 10rem">
                    <template #body="{ data }">
                        {{ data.read_at ? new Date(data.read_at).toLocaleString('pt-BR') : '—' }}
                    </template>
                </Column>
            </DataTable>
        </Dialog>

        <Dialog v-model:visible="deleteDialog" header="Confirmar exclusão" modal :style="{ width: '28rem' }">
            <p>Tem certeza que deseja excluir <strong>{{ doc.title }}</strong>?</p>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" text @click="deleteDialog = false" />
                <Button label="Excluir" icon="pi pi-trash" severity="danger" @click="deleteDocument" />
            </template>
        </Dialog>
    </div>
</template>

<style scoped>
.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

:deep(.shared-document-dialog .p-fileupload-basic) {
    width: 100%;
}

:deep(.shared-document-dialog .p-fileupload-basic .p-button) {
    width: 100%;
    justify-content: center;
}
</style>

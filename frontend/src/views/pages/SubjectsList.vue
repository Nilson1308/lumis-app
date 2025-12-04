<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const dt = ref();

// --- ESTADOS ---
const subjects = ref([]);
const subject = ref({});
const loading = ref(true);
const subjectDialog = ref(false);
const deleteDialog = ref(false);
const submitted = ref(false);

// --- PAGINAÇÃO ---
const totalRecords = ref(0);
const lazyParams = ref({
    first: 0,
    rows: 10,
    page: 1,
    filters: {}
});
const globalFilter = ref('');

// --- API: LISTAR ---
const fetchSubjects = async () => {
    loading.value = true;
    try {
        const pageNumber = (lazyParams.value.first / lazyParams.value.rows) + 1;
        const params = {
            page: pageNumber,
            page_size: lazyParams.value.rows,
            search: globalFilter.value
        };

        // Note: endpoint é 'subjects' (conforme definimos no urls.py do backend)
        const response = await api.get('subjects/', { params });
        
        // Verifica se veio paginado (results) ou lista direta (caso mude config no futuro)
        if (response.data.results) {
            subjects.value = response.data.results;
            totalRecords.value = response.data.count;
        } else {
            subjects.value = response.data;
            totalRecords.value = response.data.length;
        }

    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar matérias', life: 3000 });
    } finally {
        loading.value = false;
    }
};

const onPage = (event) => {
    lazyParams.value = event;
    fetchSubjects();
};

let timeout = null;
const onSearch = () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
        lazyParams.value.first = 0;
        fetchSubjects();
    }, 500);
};

// --- AÇÕES ---
const openNew = () => {
    subject.value = {};
    submitted.value = false;
    subjectDialog.value = true;
};

const hideDialog = () => {
    subjectDialog.value = false;
    submitted.value = false;
};

const editSubject = (item) => {
    subject.value = { ...item };
    subjectDialog.value = true;
};

const confirmDeleteSubject = (item) => {
    subject.value = item;
    deleteDialog.value = true;
};

// --- SALVAR ---
const saveSubject = async () => {
    submitted.value = true;

    if (subject.value.name && subject.value.name.trim()) {
        try {
            if (subject.value.id) {
                await api.put(`subjects/${subject.value.id}/`, subject.value);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Matéria atualizada', life: 3000 });
            } else {
                await api.post('subjects/', subject.value);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Matéria criada', life: 3000 });
            }
            subjectDialog.value = false;
            subject.value = {};
            fetchSubjects();
        } catch (error) {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar.', life: 3000 });
        }
    }
};

const deleteSubject = async () => {
    try {
        await api.delete(`subjects/${subject.value.id}/`);
        deleteDialog.value = false;
        subject.value = {};
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Matéria excluída', life: 3000 });
        fetchSubjects();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir', life: 3000 });
    }
};

onMounted(() => {
    fetchSubjects();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Nova Matéria" icon="pi pi-plus" class="mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable 
                ref="dt" 
                :value="subjects" 
                :lazy="true" 
                :paginator="true" 
                :rows="10" 
                :totalRecords="totalRecords" 
                :loading="loading" 
                @page="onPage" 
                responsiveLayout="scroll"
            >
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Gerenciar Matérias</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="globalFilter" placeholder="Buscar..." @input="onSearch" />
                        </IconField>
                    </div>
                </template>

                <Column field="id" header="ID" style="width: 10%"></Column>
                <Column field="name" header="Nome da Matéria" style="width: 70%"></Column>
                
                <Column header="Ações" style="width: 20%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editSubject(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDeleteSubject(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="subjectDialog" :style="{ width: '450px' }" header="Detalhes da Matéria" :modal="true">
                <div class="flex flex-col gap-6">
                    <div>
                        <label for="name" class="block font-bold mb-3">Nome da Matéria</label>
                        <InputText id="name" v-model.trim="subject.name" required="true" autofocus :class="{ 'p-invalid': submitted && !subject.name }" fluid />
                        <small class="p-error" v-if="submitted && !subject.name">Nome é obrigatório.</small>
                    </div>
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="hideDialog" />
                    <Button label="Salvar" icon="pi pi-check" class="p-button-text" @click="saveSubject" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-center justify-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span v-if="subject">Tem certeza que deseja excluir <b>{{ subject.name }}</b>?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteSubject" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
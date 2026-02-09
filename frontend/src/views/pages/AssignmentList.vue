<script setup>
import { ref, onMounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const assignments = ref([]);
const assignmentDialog = ref(false);
const deleteAssignmentDialog = ref(false);
const assignment = ref({});
const submitted = ref(false);
const loading = ref(false);

// Listas para os Dropdowns
const teachers = ref([]);
const classrooms = ref([]);
const subjects = ref([]);

// --- PAGINAÇÃO E FILTROS ---
const totalRecords = ref(0);
const lazyParams = ref({ first: 0, rows: 10, page: 0 });
const globalFilter = ref('');

// Variáveis de Filtro
const filterClassroom = ref(null);
const filterSubject = ref(null);
const filterTeacher = ref(null);

// --- 1. CARREGAR DEPENDÊNCIAS (Listas para os Dropdowns) ---
const loadDependencies = async () => {
    try {
        const [resClass, resSubj, resUsers] = await Promise.all([
            api.get('classrooms/?page_size=1000'),
            api.get('subjects/?page_size=1000'),
            api.get('users/?role=teacher&page_size=1000') 
        ]);

        classrooms.value = resClass.data.results;
        subjects.value = resSubj.data.results;
        
        teachers.value = resUsers.data.results.map(u => ({
            ...u,
            full_name: (u.first_name || u.last_name) ? `${u.first_name} ${u.last_name}` : u.username
        }));
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar listas.' });
    }
};

// --- 2. BUSCAR DADOS DA TABELA (Server-Side) ---
const fetchAssignments = async () => {
    loading.value = true;
    try {
        const page = lazyParams.value.page + 1; // Django inicia em 1
        const rows = lazyParams.value.rows;

        // Monta os parâmetros
        const params = {
            page: page,
            page_size: rows,
            search: globalFilter.value,
            classroom: filterClassroom.value,
            subject: filterSubject.value,
            teacher: filterTeacher.value
        };

        const res = await api.get('assignments/', { params });
        assignments.value = res.data.results;
        totalRecords.value = res.data.count;

    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar atribuições.' });
    } finally {
        loading.value = false;
    }
};

// --- WATCHERS (Recarregar ao filtrar) ---
watch([filterClassroom, filterSubject, filterTeacher], () => {
    lazyParams.value.first = 0; // Volta para página 1
    lazyParams.value.page = 0;
    fetchAssignments();
});

const onPage = (event) => {
    lazyParams.value = event;
    fetchAssignments();
};

let timeout = null;
const onSearch = () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
        lazyParams.value.first = 0;
        lazyParams.value.page = 0;
        fetchAssignments();
    }, 500);
};

const clearFilters = () => {
    filterClassroom.value = null;
    filterSubject.value = null;
    filterTeacher.value = null;
    globalFilter.value = '';
    onSearch();
};

// --- AÇÕES CRUD ---
const openNew = () => {
    assignment.value = {};
    submitted.value = false;
    assignmentDialog.value = true;
};

const editAssignment = (item) => {
    // Clona o item
    const data = { ...item };
    
    // CORREÇÃO IMPORTANTE:
    // Se o backend enviar objetos aninhados (ex: { id: 1, name: 'Matemática' }),
    // precisamos extrair apenas o ID para o Dropdown funcionar.
    if (typeof data.classroom === 'object') data.classroom = data.classroom.id;
    if (typeof data.subject === 'object') data.subject = data.subject.id;
    if (typeof data.teacher === 'object') data.teacher = data.teacher.id;

    assignment.value = data;
    assignmentDialog.value = true;
};

const confirmDeleteAssignment = (item) => {
    assignment.value = item;
    deleteAssignmentDialog.value = true;
};

const saveAssignment = async () => {
    submitted.value = true;
    if (!assignment.value.teacher || !assignment.value.classroom || !assignment.value.subject) return;

    try {
        if (assignment.value.id) {
            await api.put(`assignments/${assignment.value.id}/`, assignment.value);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atualizado com sucesso' });
        } else {
            await api.post('assignments/', assignment.value);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Criado com sucesso' });
        }
        assignmentDialog.value = false;
        fetchAssignments(); // Recarrega a lista
    } catch (e) {
        const msg = e.response?.data?.non_field_errors?.[0] || 'Erro ao salvar.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg });
    }
};

const deleteAssignment = async () => {
    try {
        await api.delete(`assignments/${assignment.value.id}/`);
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Removido com sucesso' });
        deleteAssignmentDialog.value = false;
        fetchAssignments(); // Recarrega a lista
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir' });
    }
};

onMounted(() => {
    loadDependencies(); // Carrega listas uma vez
    fetchAssignments(); // Carrega dados da tabela
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <Toolbar class="mb-4">
                <template #start>
                    <div class="my-2">
                        <Button label="Nova Atribuição" icon="pi pi-plus" class="mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable 
                :value="assignments" 
                :lazy="true" 
                :paginator="true" 
                :rows="10" 
                :totalRecords="totalRecords"
                :loading="loading" 
                @page="onPage" 
                :first="lazyParams.first"
                responsiveLayout="scroll"
            >
                <template #header>
                    <div class="flex flex-col gap-3">
                        <div class="flex flex-wrap gap-2 items-center justify-between">
                            <h4 class="m-0">Grade de Aulas</h4>
                            <IconField>
                                <InputIcon>
                                    <i class="pi pi-search" />
                                </InputIcon>
                                <InputText v-model="globalFilter" placeholder="Buscar..." @input="onSearch" />
                            </IconField>
                        </div>

                        <div class="grid grid-cols-12 gap-2">
                            <div class="col-span-12 md:col-span-3">
                                <Dropdown v-model="filterClassroom" :options="classrooms" optionLabel="name" optionValue="id" placeholder="Filtrar Turma" showClear class="w-full" />
                            </div>
                            <div class="col-span-12 md:col-span-3">
                                <Dropdown v-model="filterSubject" :options="subjects" optionLabel="name" optionValue="id" placeholder="Filtrar Matéria" showClear class="w-full" />
                            </div>
                            <div class="col-span-12 md:col-span-3">
                                <Dropdown v-model="filterTeacher" :options="teachers" optionLabel="full_name" optionValue="id" placeholder="Filtrar Professor" showClear class="w-full" />
                            </div>
                            <div class="col-span-12 md:col-span-3">
                                <Button icon="pi pi-filter-slash" label="Limpar" class="p-button-outlined w-full" @click="clearFilters" />
                            </div>
                        </div>
                    </div>
                </template>

                <template #empty>Nenhum registro encontrado.</template>

                <Column field="classroom_name" header="Turma" sortable></Column>
                <Column field="subject_name" header="Matéria" sortable></Column>
                <Column field="teacher_name" header="Professor" sortable>
                    <template #body="slotProps">
                        <span class="font-bold">{{ slotProps.data.teacher_name }}</span>
                    </template>
                </Column>
                
                <Column header="Ações">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editAssignment(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDeleteAssignment(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="assignmentDialog" :style="{ width: '450px' }" :header="assignment.id ? 'Editar Atribuição' : 'Nova Atribuição'" :modal="true" class="p-fluid">
                
                <div class="mb-3">
                    <label class="block font-bold mb-2">Turma</label>
                    <Dropdown v-model="assignment.classroom" :options="classrooms" optionLabel="name" optionValue="id" placeholder="Selecione..." filter fluid />
                    <small class="p-error" v-if="submitted && !assignment.classroom">Obrigatório.</small>
                </div>

                <div class="mb-3">
                    <label class="block font-bold mb-2">Matéria</label>
                    <Dropdown v-model="assignment.subject" :options="subjects" optionLabel="name" optionValue="id" placeholder="Selecione..." filter fluid />
                    <small class="p-error" v-if="submitted && !assignment.subject">Obrigatório.</small>
                </div>

                <div class="mb-3">
                    <label class="block font-bold mb-2">Professor</label>
                    <Dropdown v-model="assignment.teacher" :options="teachers" optionLabel="full_name" optionValue="id" placeholder="Selecione..." filter fluid />
                    <small class="p-error" v-if="submitted && !assignment.teacher">Obrigatório.</small>
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="assignmentDialog = false" />
                    <Button label="Salvar" icon="pi pi-check" @click="saveAssignment" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteAssignmentDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex items-center justify-center">
                    <i class="pi pi-exclamation-triangle mr-3 text-yellow-500" style="font-size: 2rem" />
                    <span>Confirmar a exclusão?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteAssignmentDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-danger" @click="deleteAssignment" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
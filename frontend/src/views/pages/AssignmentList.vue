<script setup>
import { ref, onMounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const dt = ref();

// --- ESTADOS ---
const assignments = ref([]);
const assignment = ref({});
const loading = ref(true);
const assignmentDialog = ref(false);
const deleteDialog = ref(false);
const submitted = ref(false);

// --- LISTAS PARA DROPDOWNS ---
const teachers = ref([]);
const subjects = ref([]);
const classrooms = ref([]);

// --- FILTROS E PAGINAÇÃO ---
const totalRecords = ref(0);
const lazyParams = ref({
    first: 0,
    rows: 10,
    page: 1,
});
const globalFilter = ref('');

// Filtros específicos (Dropdowns do Header)
const filterTeacher = ref(null);
const filterSubject = ref(null);
const filterClassroom = ref(null);

// --- CARREGAR DEPENDÊNCIAS ---
const loadDependencies = async () => {
    try {
        const [resTeachers, resSubjects, resClasses] = await Promise.all([
            api.get('users/?page_size=1000'), // Traz usuários para filtrar front (MVP)
            api.get('subjects/?page_size=1000'),
            api.get('classrooms/?page_size=1000')
        ]);
        
        // Filtra apenas quem é professor
        teachers.value = resTeachers.data.results.filter(u => u.is_teacher);
        subjects.value = resSubjects.data.results;
        classrooms.value = resClasses.data.results;
    } catch (e) {
        console.error("Erro ao carregar dependências");
    }
};

// --- LISTAR ATRIBUIÇÕES (Com Filtros e Paginação) ---
const fetchAssignments = async () => {
    loading.value = true;
    try {
        const pageNumber = (lazyParams.value.first / lazyParams.value.rows) + 1;
        
        // Monta os parâmetros da URL
        const params = {
            page: pageNumber,
            page_size: lazyParams.value.rows,
            search: globalFilter.value,
            // Adiciona filtros se estiverem selecionados
            teacher: filterTeacher.value,
            subject: filterSubject.value,
            classroom: filterClassroom.value
        };

        const response = await api.get('assignments/', { params });
        assignments.value = response.data.results;
        totalRecords.value = response.data.count;
        
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar atribuições', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// Observadores para recarregar a tabela ao mudar filtros
watch([filterTeacher, filterSubject, filterClassroom], () => {
    lazyParams.value.first = 0; // Volta pra pag 1
    fetchAssignments();
});

const clearFilters = () => {
    filterTeacher.value = null;
    filterSubject.value = null;
    filterClassroom.value = null;
    globalFilter.value = ''; // Opcional: limpa também a busca textual
    // Como temos 'watch' nessas variáveis, a tabela recarregará sozinha
};

const onPage = (event) => {
    lazyParams.value = event;
    fetchAssignments();
};

let timeout = null;
const onSearch = () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
        lazyParams.value.first = 0;
        fetchAssignments();
    }, 500);
};

// --- AÇÕES ---
const openNew = () => {
    assignment.value = {};
    submitted.value = false;
    assignmentDialog.value = true;
};

const hideDialog = () => {
    assignmentDialog.value = false;
    submitted.value = false;
};

// --- EDIÇÃO ---
const editAssignment = (item) => {
    // Clona o objeto para não alterar a tabela diretamente
    assignment.value = { ...item };
    assignmentDialog.value = true;
};

const confirmDelete = (item) => {
    assignment.value = item;
    deleteDialog.value = true;
};

// --- SALVAR (CRIAR OU EDITAR) ---
const saveAssignment = async () => {
    submitted.value = true;

    if (assignment.value.teacher && assignment.value.subject && assignment.value.classroom) {
        try {
            if (assignment.value.id) {
                // UPDATE (PUT)
                await api.put(`assignments/${assignment.value.id}/`, assignment.value);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atribuição atualizada!', life: 3000 });
            } else {
                // CREATE (POST)
                await api.post('assignments/', assignment.value);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aula atribuída!', life: 3000 });
            }
            
            assignmentDialog.value = false;
            fetchAssignments();
        } catch (error) {
            // Verifica duplicidade ou erros gerais
            const msg = error.response?.data?.non_field_errors?.[0] || 'Erro ao salvar. Verifique conflitos.';
            toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 3000 });
        }
    }
};

const deleteAssignment = async () => {
    try {
        await api.delete(`assignments/${assignment.value.id}/`);
        deleteDialog.value = false;
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Atribuição removida', life: 3000 });
        fetchAssignments();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover', life: 3000 });
    }
};

onMounted(() => {
    loadDependencies();
    fetchAssignments();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Nova Atribuição" icon="pi pi-plus" class="mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable 
                ref="dt"
                :value="assignments" 
                :lazy="true" 
                :paginator="true" 
                :rows="10" 
                :totalRecords="totalRecords"
                :loading="loading"
                @page="onPage"
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
                                <InputText v-model="globalFilter" placeholder="Buscar geral..." @input="onSearch" />
                            </IconField>
                        </div>
                        
                        <div class="flex flex-col md:flex-row gap-3">
                            <Dropdown 
                                v-model="filterTeacher" 
                                :options="teachers" 
                                optionLabel="username" 
                                optionValue="id" 
                                placeholder="Filtrar por Professor" 
                                showClear
                                class="w-full"
                            >
                                <template #option="slotProps">
                                    {{ slotProps.option.first_name ? slotProps.option.first_name : slotProps.option.username }}
                                </template>
                                <template #value="slotProps">
                                    <span v-if="slotProps.value">
                                        {{ teachers.find(t => t.id === slotProps.value)?.first_name || 'Professor' }}
                                    </span>
                                    <span v-else>{{ slotProps.placeholder }}</span>
                                </template>
                            </Dropdown>

                            <Dropdown 
                                v-model="filterSubject" 
                                :options="subjects" 
                                optionLabel="name" 
                                optionValue="id" 
                                placeholder="Filtrar por Matéria" 
                                showClear
                                class="w-full"
                            />

                            <Dropdown 
                                v-model="filterClassroom" 
                                :options="classrooms" 
                                optionLabel="name" 
                                optionValue="id" 
                                placeholder="Filtrar por Turma" 
                                showClear
                                class="w-full"
                            />

                            <Button 
                                type="button" 
                                icon="pi pi-filter-slash" 
                                label=" " 
                                class="p-button w-full md:w-auto" 
                                @click="clearFilters" 
                                v-tooltip.top="'Limpar todos os filtros'"
                            />
                        </div>
                    </div>
                </template>
                
                <template #empty>Nenhuma aula encontrada.</template>

                <Column field="teacher_name" header="Professor" sortable></Column>
                <Column field="subject_name" header="Matéria" sortable></Column>
                <Column field="classroom_name" header="Turma" sortable></Column>
                <Column field="classroom_year" header="Ano"></Column>
                
                <Column header="Ações" style="width: 15%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editAssignment(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="assignmentDialog" :header="assignment.id ? 'Editar Atribuição' : 'Nova Atribuição'" :modal="true" :style="{ width: '450px' }" class="p-fluid">
                
                <div class="mb-2">
                    <label class="mb-2 block font-bold">Professor</label>
                    <Dropdown 
                        v-model="assignment.teacher" 
                        :options="teachers" 
                        optionLabel="username" 
                        optionValue="id" 
                        placeholder="Selecione o Professor" 
                        filter
                        :class="{ 'p-invalid': submitted && !assignment.teacher }"
                        fluid
                    >
                        <template #option="slotProps">
                            {{ slotProps.option.first_name ? slotProps.option.first_name + ' ' + slotProps.option.last_name : slotProps.option.username }}
                        </template>
                        <template #value="slotProps">
                            <span v-if="slotProps.value">
                                {{ teachers.find(t => t.id === slotProps.value)?.first_name || teachers.find(t => t.id === slotProps.value)?.username || 'Selecionado' }}
                            </span>
                            <span v-else>{{ slotProps.placeholder }}</span>
                        </template>
                    </Dropdown>
                    <small class="p-error" v-if="submitted && !assignment.teacher">Professor é obrigatório.</small>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Matéria</label>
                    <Dropdown 
                        v-model="assignment.subject" 
                        :options="subjects" 
                        optionLabel="name" 
                        optionValue="id" 
                        placeholder="Selecione a Matéria" 
                        filter
                        :class="{ 'p-invalid': submitted && !assignment.subject }"
                        fluid
                    />
                    <small class="p-error" v-if="submitted && !assignment.subject">Matéria é obrigatória.</small>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Turma</label>
                    <Dropdown 
                        v-model="assignment.classroom" 
                        :options="classrooms" 
                        optionLabel="name" 
                        optionValue="id" 
                        placeholder="Selecione a Turma" 
                        filter
                        :class="{ 'p-invalid': submitted && !assignment.classroom }"
                        fluid
                    />
                    <small class="p-error" v-if="submitted && !assignment.classroom">Turma é obrigatória.</small>
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="hideDialog" />
                    <Button label="Salvar" icon="pi pi-check" @click="saveAssignment" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" header="Remover Atribuição" :modal="true" :style="{ width: '450px' }">
                <div class="flex align-center justify-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span>Tem certeza que deseja remover esta aula?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteAssignment" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
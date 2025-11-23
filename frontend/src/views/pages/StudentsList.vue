<script setup>
import { ref, onMounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const dt = ref(); // Referência para a DataTable

// --- ESTADOS ---
const students = ref([]);
const student = ref({});
const loading = ref(true);
const studentDialog = ref(false);
const deleteDialog = ref(false);
const submitted = ref(false);

// --- ESTADOS DA PAGINAÇÃO E FILTRO ---
const totalRecords = ref(0); // Total que vem do backend (count)
const lazyParams = ref({
    first: 0,
    rows: 10,
    page: 1,
    sortField: null,
    sortOrder: null,
    filters: {}
});
const globalFilter = ref(''); // Campo de busca

// --- API: LISTAR (COM PAGINAÇÃO E BUSCA) ---
const fetchStudents = async () => {
    loading.value = true;
    try {
        // Calcula a página atual: (0 / 10) + 1 = Pag 1; (10 / 10) + 1 = Pag 2
        const pageNumber = (lazyParams.value.first / lazyParams.value.rows) + 1;
        
        // Monta a URL com parâmetros
        const params = {
            page: pageNumber,
            page_size: lazyParams.value.rows,
            search: globalFilter.value // O Django já espera ?search=
        };

        const response = await api.get('students/', { params });
        
        // DRF retorna: { count: 50, next: "...", previous: "...", results: [...] }
        students.value = response.data.results;
        totalRecords.value = response.data.count; // Atualiza o totalizador do rodapé
        
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados', life: 3000 });
        console.error(error);
    } finally {
        loading.value = false;
    }
};

// Evento disparado ao mudar de página ou ordenar
const onPage = (event) => {
    lazyParams.value = event;
    fetchStudents();
};

// Evento de Busca (com delay para não chamar API a cada letra)
let timeout = null;
const onSearch = () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
        lazyParams.value.first = 0; // Volta para primeira página
        fetchStudents();
    }, 500); // Espera 500ms após parar de digitar
};

// --- API: EXPORTAR CSV (TODOS OS DADOS) ---
const exportCSV = async () => {
    try {
        loading.value = true;
        // Pede uma lista gigante para exportação (limitado a 1000 por segurança ou criar endpoint específico)
        const response = await api.get('students/', { params: { page_size: 1000, search: globalFilter.value } });
        
        // Usa a função nativa do PrimeVue para exportar, mas injetando os dados carregados
        // Precisamos formatar os dados para ficarem bonitos no Excel
        const dataToExport = response.data.results.map(s => ({
            ...s,
            created_at: new Date(s.created_at).toLocaleDateString('pt-BR')
        }));

        dt.value.exportCSV(null, dataToExport);
        
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao exportar', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES DE INTERFACE ---
const openNew = () => {
    student.value = {};
    submitted.value = false;
    studentDialog.value = true;
};

const hideDialog = () => {
    studentDialog.value = false;
    submitted.value = false;
};

const editStudent = (prod) => {
    // Clona o objeto e ajusta a data para o Calendar entender (objeto Date JS)
    student.value = { ...prod };
    if (student.value.birth_date) {
        // Converte string '2025-01-01' para Date Object, corrigindo fuso horário
        const [year, month, day] = student.value.birth_date.split('-');
        student.value.birth_date = new Date(year, month - 1, day);
    }
    studentDialog.value = true;
};

const confirmDeleteStudent = (prod) => {
    student.value = prod;
    deleteDialog.value = true;
};

// --- UTILITÁRIO: FORMATAR DATA PARA DJANGO (YYYY-MM-DD) ---
const formatDateToAPI = (dateObj) => {
    if (!dateObj) return null;
    const offset = dateObj.getTimezoneOffset();
    const date = new Date(dateObj.getTime() - (offset*60*1000));
    return date.toISOString().split('T')[0];
};

// --- API: SALVAR ---
const saveStudent = async () => {
    submitted.value = true;

    if (student.value.name && student.value.name.trim() && student.value.registration_number) {
        // Prepara objeto para envio (formata data)
        const payload = { ...student.value };
        if (payload.birth_date instanceof Date) {
            payload.birth_date = formatDateToAPI(payload.birth_date);
        }

        try {
            if (student.value.id) {
                await api.put(`students/${student.value.id}/`, payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aluno atualizado', life: 3000 });
            } else {
                await api.post('students/', payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aluno criado', life: 3000 });
            }
            studentDialog.value = false;
            student.value = {};
            fetchStudents(); 
        } catch (error) {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Verifique os dados.', life: 3000 });
        }
    }
};

const deleteStudent = async () => {
    try {
        await api.delete(`students/${student.value.id}/`);
        deleteDialog.value = false;
        student.value = {};
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aluno excluído', life: 3000 });
        fetchStudents();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir', life: 3000 });
    }
};

onMounted(() => {
    fetchStudents();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Novo Aluno" icon="pi pi-plus" class="p-button-success mr-2" @click="openNew" />
                    </div>
                </template>
                <template v-slot:end>
                    <Button label="Exportar CSV" icon="pi pi-upload" class="p-button-help" @click="exportCSV" />
                </template>
            </Toolbar>

            <DataTable 
                ref="dt" 
                :value="students" 
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
                        <h4 class="m-0">Gerenciar Alunos</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="globalFilter" placeholder="Buscar..." @input="onSearch" />
                        </IconField>
                    </div>
                </template>

                <Column field="registration_number" header="Matrícula" style="width: 15%"></Column>
                <Column field="name" header="Nome" style="width: 40%"></Column>
                <Column field="birth_date" header="Nascimento" style="width: 15%">
                        <template #body="slotProps">
                        {{ slotProps.data.birth_date ? new Date(slotProps.data.birth_date + 'T12:00:00').toLocaleDateString('pt-BR') : '-' }}
                    </template>
                </Column>
                <Column field="created_at" header="Cadastro" style="width: 15%">
                    <template #body="slotProps">
                        {{ new Date(slotProps.data.created_at).toLocaleDateString('pt-BR') }}
                    </template>
                </Column>
                
                <Column header="Ações" style="width: 15%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded p-button-success mr-2" @click="editStudent(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded p-button-warning" @click="confirmDeleteStudent(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="studentDialog" :style="{ width: '450px' }" header="Product Details" :modal="true">
                <div class="flex flex-col gap-6">
                    <div>
                        <label for="name" class="block font-bold mb-3">Nome Completo</label>
                        <InputText id="name" v-model.trim="student.name" required="true" autofocus :class="{ 'p-invalid': submitted && !student.name }"  fluid />
                        <small class="p-error" v-if="submitted && !student.name">Nome é obrigatório.</small>
                    </div>
                    <div>
                        <label for="reg" class="block font-bold mb-3">Matrícula</label>
                        <InputText id="reg" v-model.trim="student.registration_number" required="true" :class="{ 'p-invalid': submitted && !student.registration_number }"  fluid />
                        <small class="p-error" v-if="submitted && !student.registration_number">Matrícula é obrigatória.</small>
                    </div>
                    <div>
                        <label for="birth" class="block font-bold mb-3">Data de Nascimento</label>
                        <Calendar id="birth" v-model="student.birth_date" dateFormat="dd/mm/yy" :showIcon="true"  fluid />
                    </div>
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="hideDialog" />
                    <Button label="Salvar" icon="pi pi-check" class="p-button-text" @click="saveStudent" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-items-center justify-content-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span v-if="student">Tem certeza que deseja excluir <b>{{ student.name }}</b>?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteStudent" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
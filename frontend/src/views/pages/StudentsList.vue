<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import { FilterMatchMode } from '@primevue/core/api'; 
import api from '@/service/api';

// IMPORTAÇÃO DO COMPONENTE LIMPO
import StudentFormDialog from '@/components/StudentFormDialog.vue';

const toast = useToast();
const students = ref([]);
const loading = ref(true);

// Estado do Dialog (Controlado pelo Pai)
const studentDialogVisible = ref(false);
const selectedStudentId = ref(null);

const deleteStudentDialog = ref(false);
const studentToDelete = ref({});

// Paginação
const totalRecords = ref(0);
const lazyParams = ref({
    page: 1,
    rows: 10
});

// Filtro
const filters = ref({
    global: { value: '', matchMode: FilterMatchMode.CONTAINS }
});

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        const page = lazyParams.value.page; // PrimeVue agora usa page direto (1, 2, 3...)
        const rows = lazyParams.value.rows;
        
        let query = `students/?page=${page}&page_size=${rows}`;
        
        const searchValue = filters.value.global.value;
        if (searchValue && searchValue.trim() !== '') {
            query += `&search=${searchValue}`;
        }

        const res = await api.get(query);
        students.value = res.data.results; 
        totalRecords.value = res.data.count;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar dados' });
    } finally {
        loading.value = false;
    }
};

const onPage = (event) => {
    // PrimeVue Lazy Page Event: { page: 0, rows: 10, ... }
    // Backend Django espera page=1, page=2...
    lazyParams.value.page = event.page + 1;
    lazyParams.value.rows = event.rows;
    loadData();
};

const onSearch = () => {
    lazyParams.value.page = 1; // Volta pra primeira página
    loadData();
}

// --- AÇÕES DO DIALOG (ABRIR/FECHAR) ---
const openNew = () => {
    selectedStudentId.value = null; // Modo Criação
    studentDialogVisible.value = true;
};

const editStudent = (student) => {
    selectedStudentId.value = student.id; // Modo Edição
    studentDialogVisible.value = true;
};

// Callback chamado quando o componente filho salva com sucesso
const onStudentSaved = () => {
    loadData(); // Recarrega a tabela
};

// --- DELETE ---
const confirmDeleteStudent = (student) => {
    studentToDelete.value = student;
    deleteStudentDialog.value = true;
};

const deleteStudent = async () => {
    try {
        await api.delete(`students/${studentToDelete.value.id}/`);
        deleteStudentDialog.value = false;
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Removido!', life: 3000 });
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao remover.', life: 3000 });
    }
};

onMounted(() => {
    loadData();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Novo Aluno" icon="pi pi-plus" class="mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable 
                :value="students" 
                :loading="loading" 
                responsiveLayout="scroll" 
                :paginator="true" 
                :rows="10"
                :totalRecords="totalRecords"
                :lazy="true"
                @page="onPage"
                :filters="filters"
            >
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Listagem de Alunos</h4>
                        <div class="flex gap-2">
                            <IconField>
                                <InputIcon>
                                    <i class="pi pi-search" />
                                </InputIcon>
                                <InputText 
                                    v-model="filters.global.value" 
                                    placeholder="Buscar por Nome, Matrícula ou CPF..." 
                                    @keydown.enter="onSearch"
                                    style="width: 300px" 
                                />
                            </IconField>
                            <Button icon="pi pi-search" class="p-button-rounded p-button-text ml-2" @click="onSearch" v-tooltip="'Pesquisar'" />
                            <Button icon="pi pi-refresh" class="p-button-rounded p-button-text" @click="loadData" v-tooltip="'Recarregar Tabela'" />
                        </div>
                    </div>
                </template>
                
                <Column field="registration_number" header="Matrícula"></Column>
                <Column field="name" header="Nome">
                    <template #body="slotProps">
                        <div class="flex items-center gap-2">
                            <Avatar 
                                :image="slotProps.data.photo || null" 
                                :icon="!slotProps.data.photo ? 'pi pi-user' : null" 
                                shape="circle" 
                                size="normal"
                                class="surface-200"
                                style="object-fit: cover"
                            />
                            <span>{{ slotProps.data.name }}</span>
                        </div>
                    </template>
                </Column>
                
                <Column field="period" header="Período">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.period === 'MORNING' ? 'Manhã' : 'Tarde'" 
                             :severity="slotProps.data.period === 'MORNING' ? 'info' : 'warning'" />
                    </template>
                </Column>
                <Column field="is_full_time" header="Integral">
                    <template #body="slotProps">
                        <i class="pi" :class="{'pi-check-circle text-green-500': slotProps.data.is_full_time, 'pi-times-circle text-gray-400': !slotProps.data.is_full_time}"></i>
                    </template>
                </Column>

                <Column field="birth_date" header="Nascimento">
                    <template #body="slotProps">
                        <span v-if="slotProps.data.birth_date">
                            {{ new Date(slotProps.data.birth_date + 'T00:00:00').toLocaleDateString('pt-BR') }}
                        </span>
                    </template>
                </Column>
                
                <Column header="Ações">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editStudent(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDeleteStudent(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <StudentFormDialog 
                v-model:visible="studentDialogVisible" 
                :studentId="selectedStudentId"
                @saved="onStudentSaved"
            />

            <Dialog v-model:visible="deleteStudentDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-items-center justify-content-center">
                    <i class="pi pi-exclamation-triangle mr-3 text-yellow-500" style="font-size: 2rem" />
                    <span>Deseja remover <b>{{ studentToDelete.name }}</b>?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteStudentDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text p-button-danger" @click="deleteStudent" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
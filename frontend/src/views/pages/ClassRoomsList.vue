<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const dt = ref();

// --- ESTADOS ---
const router = useRouter();
const classRooms = ref([]);
const segments = ref([]); // Lista para o Dropdown
const classRoom = ref({});
const loading = ref(true);
const classRoomDialog = ref(false);
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

const openClassroom = (classroom) => {
    router.push(`/classrooms/${classroom.id}`);
};

// --- API: LISTAR TURMAS ---
const fetchClassRooms = async () => {
    loading.value = true;
    try {
        const pageNumber = (lazyParams.value.first / lazyParams.value.rows) + 1;
        const params = {
            page: pageNumber,
            page_size: lazyParams.value.rows,
            search: globalFilter.value
        };

        const response = await api.get('classrooms/', { params });
        classRooms.value = response.data.results;
        totalRecords.value = response.data.count;
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar turmas', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- API: LISTAR SEGMENTOS (Para o Dropdown) ---
// Trazemos todos de uma vez (geralmente são poucos, ex: 4 ou 5)
const fetchSegments = async () => {
    try {
        const response = await api.get('segments/');
        // Se a API de segmentos tiver paginação, pegamos o .results, senão o .data direto
        segments.value = response.data.results || response.data;
    } catch (error) {
        console.error("Erro ao carregar segmentos");
    }
};

const onPage = (event) => {
    lazyParams.value = event;
    fetchClassRooms();
};

let timeout = null;
const onSearch = () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
        lazyParams.value.first = 0;
        fetchClassRooms();
    }, 500);
};

// --- AÇÕES ---
const openNew = () => {
    classRoom.value = { year: 2025 }; // Valor padrão
    submitted.value = false;
    classRoomDialog.value = true;
};

const hideDialog = () => {
    classRoomDialog.value = false;
    submitted.value = false;
};

const editClassRoom = (item) => {
    classRoom.value = { ...item };
    classRoomDialog.value = true;
};

const confirmDeleteClassRoom = (item) => {
    classRoom.value = item;
    deleteDialog.value = true;
};

// --- SALVAR ---
const saveClassRoom = async () => {
    submitted.value = true;

    if (classRoom.value.name && classRoom.value.segment) {
        try {
            if (classRoom.value.id) {
                await api.put(`classrooms/${classRoom.value.id}/`, classRoom.value);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Turma atualizada', life: 3000 });
            } else {
                await api.post('classrooms/', classRoom.value);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Turma criada', life: 3000 });
            }
            classRoomDialog.value = false;
            classRoom.value = {};
            fetchClassRooms();
        } catch (error) {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar.', life: 3000 });
        }
    }
};

const deleteClassRoom = async () => {
    try {
        await api.delete(`classrooms/${classRoom.value.id}/`);
        deleteDialog.value = false;
        classRoom.value = {};
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Turma excluída', life: 3000 });
        fetchClassRooms();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir', life: 3000 });
    }
};

onMounted(() => {
    fetchClassRooms();
    fetchSegments(); // Carrega o dropdown
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Nova Turma" icon="pi pi-plus" class="mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable 
                ref="dt" 
                :value="classRooms" 
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
                        <h4 class="m-0">Gerenciar Turmas</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="globalFilter" placeholder="Buscar..." @input="onSearch" />
                        </IconField>
                    </div>
                </template>

                <Column field="name" header="Nome da Turma" style="width: 40%"></Column>
                <Column field="year" header="Ano Letivo" style="width: 20%"></Column>
                
                <Column field="segment_name" header="Segmento" style="width: 25%">
                        <template #body="slotProps">
                        <Tag :value="slotProps.data.segment_name" severity="info" />
                    </template>
                </Column>
                
                <Column header="Ações" style="width: 15%">
                    <template #body="slotProps">
                        <Button icon="pi pi-eye" class="p-button-rounded mr-2" @click="openClassroom(slotProps.data)" v-tooltip.top="'Dashboard da Turma'" />
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editClassRoom(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDeleteClassRoom(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="classRoomDialog" :style="{ width: '450px' }" header="Detalhes da Turma" :modal="true">
                <div class="flex flex-col gap-6">
                    <div>
                        <label for="name" class="block font-bold mb-3">Nome da Turma</label>
                        <InputText id="name" v-model.trim="classRoom.name" required="true" autofocus :class="{ 'p-invalid': submitted && !classRoom.name }" fluid />
                        <small class="p-error" v-if="submitted && !classRoom.name">Nome é obrigatório.</small>
                    </div>

                    <div>
                        <label for="year" class="block font-bold mb-3">Ano Letivo</label>
                        <InputNumber id="year" v-model="classRoom.year" :useGrouping="false" fluid />
                    </div>

                    <div>
                        <label for="segment" class="block font-bold mb-3">Segmento</label>
                        <Dropdown 
                            id="segment" 
                            v-model="classRoom.segment" 
                            :options="segments" 
                            optionLabel="name" 
                            optionValue="id" 
                            placeholder="Selecione um Segmento" 
                            fluid
                            :class="{ 'p-invalid': submitted && !classRoom.segment }"
                        />
                        <small class="p-error" v-if="submitted && !classRoom.segment">Segmento é obrigatório.</small>
                    </div>
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="hideDialog" />
                    <Button label="Salvar" icon="pi pi-check" class="p-button-text" @click="saveClassRoom" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-center justify-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span v-if="classRoom">Tem certeza que deseja excluir <b>{{ classRoom.name }}</b>?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteClassRoom" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
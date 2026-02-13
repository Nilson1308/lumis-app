<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { FilterMatchMode } from '@primevue/core/api';
import api from '@/service/api';

const toast = useToast();
const route = useRoute();
const router = useRouter();

// ID da atribuição (Turma/Matéria) vindo da URL
const assignmentId = route.params.id;

// Estados
const contents = ref([]);
const content = ref({});
const assignmentInfo = ref(null); 
const contentDialog = ref(false);
const deleteDialog = ref(false);
const loading = ref(true);
const submitted = ref(false);

// Filtros da Tabela
const filters = ref({ 
    global: { value: null, matchMode: FilterMatchMode.CONTAINS } 
});

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        // CORREÇÃO AQUI: Adicionamos page_size=1000 para pegar tudo de uma vez
        // e tratamos o formato de resposta do Django (.results)
        const response = await api.get(`taught-contents/?assignment=${assignmentId}&page_size=1000`);
        
        // Verifica se veio paginado (com .results) ou direto (lista)
        if (response.data.results) {
            contents.value = response.data.results;
        } else {
            contents.value = response.data;
        }

        // Tenta pegar info da turma para o título
        if (contents.value.length > 0) {
            assignmentInfo.value = `${contents.value[0].subject_name} - ${contents.value[0].classroom_name}`;
        } else if (!assignmentInfo.value) {
            // Fallback: Busca info da atribuição se a lista estiver vazia
            try {
                const resAssign = await api.get(`/assignments/${assignmentId}/`);
                assignmentInfo.value = `${resAssign.data.subject.name} - ${resAssign.data.classroom.name}`;
            } catch (e) {
                assignmentInfo.value = "Diário de Classe";
            }
        }
    } catch (e) {
        console.error("Erro ao carregar:", e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao carregar dados', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES ---
const openNew = () => {
    content.value = {
        date: new Date(),
        content: '', 
        homework: ''
    };
    submitted.value = false;
    contentDialog.value = true;
};

const editContent = (item) => {
    content.value = { ...item };
    
    // Tratamento de Data
    if (content.value.date && typeof content.value.date === 'string') {
        const parts = content.value.date.split('-');
        // Cria a data no fuso local corretamente (YYYY, MM-1, DD)
        content.value.date = new Date(parts[0], parts[1] - 1, parts[2]);
    }
    contentDialog.value = true;
};

const saveContent = async () => {
    submitted.value = true;

    if (!content.value.content || !content.value.date) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha a Data e o Conteúdo.', life: 3000 });
        return;
    }

    const payload = {
        assignment: assignmentId,
        date: content.value.date instanceof Date ? content.value.date.toISOString().split('T')[0] : content.value.date,
        content: content.value.content,
        homework: content.value.homework
    };

    try {
        if (content.value.id) {
            await api.patch(`taught-contents/${content.value.id}/`, payload);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Registro atualizado', life: 3000 });
        } else {
            await api.post('taught-contents/', payload);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Aula registrada', life: 3000 });
        }
        contentDialog.value = false;
        loadData();
    } catch (error) {
        console.error(error);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Não foi possível salvar.', life: 3000 });
    }
};

const confirmDelete = (item) => {
    content.value = item;
    deleteDialog.value = true;
};

const deleteContent = async () => {
    try {
        await api.delete(`taught-contents/${content.value.id}/`);
        deleteDialog.value = false;
        content.value = {};
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Registro removido', life: 3000 });
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover', life: 3000 });
    }
};

const goBack = () => {
    router.go(-1);
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
                    <div class="my-2 flex flex-col items-center md:flex-row">
                        <Button icon="pi pi-arrow-left" class="p-button-text mr-2" @click="goBack" />
                        <div class="text-xl font-bold text-900" v-if="assignmentInfo">{{ assignmentInfo }}</div>
                    </div>
                </template>
                <template v-slot:end>
                    <Button label="Registrar Aula" icon="pi pi-plus" class="mr-2" @click="openNew" />
                </template>
            </Toolbar>

            <DataTable :value="contents" :filters="filters" :loading="loading" responsiveLayout="scroll" :paginator="true" :rows="10" rowHover>
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Diário de Classe</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="filters['global'].value" placeholder="Buscar..." />
                        </IconField>
                    </div>
                </template>
                <template #empty>Nenhum registro encontrado.</template>

                <Column field="date" header="Data" sortable style="width: 15%">
                    <template #body="slotProps">
                        {{ new Date(slotProps.data.date + 'T00:00:00').toLocaleDateString('pt-BR') }}
                    </template>
                </Column>

                <Column field="content" header="Conteúdo Ministrado" sortable style="width: 45%">
                    <template #body="slotProps">
                        <div v-html="slotProps.data.content" class="line-clamp-3 text-sm text-700"></div>
                    </template>
                </Column>

                <Column field="homework" header="Tarefa / Obs" style="width: 25%">
                    <template #body="slotProps">
                        <span class="text-sm text-gray-500">{{ slotProps.data.homework || '-' }}</span>
                    </template>
                </Column>

                <Column header="Ações" style="width: 15%; min-width: 8rem" bodyClass="text-center">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editContent(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded p-button-warning" @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="contentDialog" :style="{ width: '800px' }" header="Registro de Aula" :modal="true" class="p-fluid" maximizable>
                <div class="grid grid-cols-12 gap-4 mb-2">
                    
                    <div class="col-span-12 xl:col-span-4">
                        <label class="block font-bold mb-3">Data da Aula</label>
                        <DatePicker v-model="content.date" dateFormat="dd/mm/yy" showIcon fluid :class="{ 'p-invalid': submitted && !content.date }" />
                        <small class="p-error" v-if="submitted && !content.date">Data é obrigatória.</small>
                    </div>

                    <div class="col-span-12 xl:col-span-12">
                        <label class="block font-bold mb-3 text-primary">Conteúdo Trabalhado</label>
                        <Editor v-model="content.content" editorStyle="height: 320px" placeholder="Descreva o conteúdo..." />
                        <small class="p-error" v-if="submitted && !content.content">Conteúdo é obrigatório.</small>
                    </div>

                    <div class="col-span-12 xl:col-span-12">
                        <label class="block font-bold mb-3">Lição de Casa / Tarefa (Opcional)</label>
                        <Textarea v-model="content.homework" rows="2" autoResize placeholder="Páginas do livro, exercícios para casa..." fluid />
                    </div>
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="contentDialog = false" />
                    <Button label="Salvar Registro" icon="pi pi-check" class="p-button-primary" @click="saveContent" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar Exclusão" :modal="true">
                <div class="flex align-items-center justify-content-center">
                    <i class="pi pi-exclamation-triangle mr-3 text-warning" style="font-size: 2rem" />
                    <span v-if="content">Tem certeza que deseja remover o registro do dia <b>{{ new Date(content.date + 'T00:00:00').toLocaleDateString('pt-BR') }}</b>?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text p-button-danger" @click="deleteContent" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
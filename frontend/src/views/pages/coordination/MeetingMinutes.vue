<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();

// --- ESTADOS ---
const minutes = ref([]);
const minute = ref({});
const loading = ref(true);
const minuteDialog = ref(false);
const deleteDialog = ref(false);
const submitted = ref(false);

// --- CARREGAR DADOS ---
const fetchMinutes = async () => {
    loading.value = true;
    try {
        const response = await api.get('meeting-minutes/');
        minutes.value = response.data.results;
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar atas', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- AÇÕES ---
const openNew = () => {
    minute.value = {
        date: new Date() // Padrão: Hoje
    };
    submitted.value = false;
    minuteDialog.value = true;
};

const editMinute = (item) => {
    minute.value = { ...item };
    // Corrige data string para objeto Date
    if (minute.value.date) {
        minute.value.date = new Date(minute.value.date);
    }
    minuteDialog.value = true;
};

const confirmDelete = (item) => {
    minute.value = item;
    deleteDialog.value = true;
};

// --- SALVAR ---
const saveMinute = async () => {
    submitted.value = true;

    if (minute.value.title && minute.value.date && minute.value.content) {
        // Formata data YYYY-MM-DD
        const payload = { ...minute.value };
        if (payload.date instanceof Date) {
            const offset = payload.date.getTimezoneOffset();
            payload.date = new Date(payload.date.getTime() - (offset*60*1000)).toISOString().split('T')[0];
        }

        try {
            if (minute.value.id) {
                await api.put(`meeting-minutes/${minute.value.id}/`, payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Ata atualizada', life: 3000 });
            } else {
                await api.post('meeting-minutes/', payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Ata registrada', life: 3000 });
            }
            minuteDialog.value = false;
            fetchMinutes();
        } catch (error) {
            toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar.', life: 3000 });
        }
    }
};

const deleteMinute = async () => {
    try {
        await api.delete(`meeting-minutes/${minute.value.id}/`);
        deleteDialog.value = false;
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Ata removida', life: 3000 });
        fetchMinutes();
    } catch (error) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover', life: 3000 });
    }
};

onMounted(() => {
    fetchMinutes();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            <Toolbar class="mb-4">
                <template v-slot:start>
                    <div class="my-2">
                        <Button label="Nova Ata" icon="pi pi-plus" class="p-button-success mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable :value="minutes" :loading="loading" responsiveLayout="scroll" :paginator="true" :rows="10">
                <template #header>Atas de Reunião</template>
                <template #empty>Nenhuma ata registrada.</template>

                <Column field="date" header="Data" sortable style="width: 15%">
                    <template #body="slotProps">
                        {{ new Date(slotProps.data.date).toLocaleDateString('pt-BR') }}
                    </template>
                </Column>
                <Column field="title" header="Pauta / Título" sortable style="width: 40%"></Column>
                <Column field="created_by_name" header="Registrado por" style="width: 25%"></Column>
                
                <Column header="Ações" style="width: 20%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded p-button-success mr-2" @click="editMinute(slotProps.data)" v-tooltip.top="'Editar/Ver Detalhes'" />
                        <Button icon="pi pi-trash" class="p-button-rounded p-button-warning" @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="minuteDialog" :style="{ width: '700px' }" header="Registro de Reunião" :modal="true" class="p-fluid">
                
                <div class="formgrid grid">
                    <div class="field col-8">
                        <label class="font-bold">Título / Pauta Principal</label>
                        <InputText v-model="minute.title" required="true" autofocus :class="{ 'p-invalid': submitted && !minute.title }" />
                        <small class="p-error" v-if="submitted && !minute.title">Título obrigatório.</small>
                    </div>
                    <div class="field col-4">
                        <label class="font-bold">Data</label>
                        <Calendar v-model="minute.date" dateFormat="dd/mm/yy" showIcon />
                    </div>
                </div>

                <div class="field">
                    <label class="font-bold">Participantes</label>
                    <InputText v-model="minute.participants" placeholder="Ex: Livia, Nilson, Coordenadores..." />
                    <small class="text-500">Liste os nomes separados por vírgula.</small>
                </div>

                <div class="field">
                    <label class="font-bold">Conteúdo / Decisões</label>
                    <Textarea v-model="minute.content" rows="10" autoResize placeholder="Descreva o que foi discutido e decidido..." :class="{ 'p-invalid': submitted && !minute.content }" />
                    <small class="p-error" v-if="submitted && !minute.content">Conteúdo obrigatório.</small>
                </div>

                <div class="field">
                    <label class="font-bold">Próximos Passos / Tarefas</label>
                    <Textarea v-model="minute.next_steps" rows="3" autoResize placeholder="O que ficou para fazer? Quem fará?" />
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="minuteDialog = false" />
                    <Button label="Salvar Ata" icon="pi pi-check" @click="saveMinute" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-items-center justify-content-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span>Deseja excluir este registro permanentemente?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteMinute" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
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
const participantsOptions = ref([]);

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

const loadParticipants = async () => {
    try {
        // Carrega usuários de diferentes grupos
        // Busca coordenadores com variações de nome do grupo
        const [teachersRes, coordinatorsRes1, coordinatorsRes2, secretariesRes] = await Promise.all([
            api.get('users/?role=teacher&page_size=1000'),
            api.get('users/?group=Coordenadores&page_size=1000'),
            api.get('users/?group=Coordenacao&page_size=1000'), // Variação sem acento
            api.get('users/?group=Secretaria&page_size=1000')
        ]);

        const teachers = (teachersRes.data.results || teachersRes.data).map(u => ({
            id: u.id,
            name: u.full_name || u.first_name || u.username,
            group: 'Professores'
        }));

        // Combina coordenadores de ambas as variações
        const coordinators1 = (coordinatorsRes1.data.results || coordinatorsRes1.data).map(u => ({
            id: u.id,
            name: u.full_name || u.first_name || u.username,
            group: 'Coordenadores'
        }));

        const coordinators2 = (coordinatorsRes2.data.results || coordinatorsRes2.data).map(u => ({
            id: u.id,
            name: u.full_name || u.first_name || u.username,
            group: 'Coordenadores'
        }));

        const coordinators = [...coordinators1, ...coordinators2];

        const secretaries = (secretariesRes.data.results || secretariesRes.data).map(u => ({
            id: u.id,
            name: u.full_name || u.first_name || u.username,
            group: 'Secretaria'
        }));

        // Combina todos e remove duplicados por ID
        const allUsers = [...teachers, ...coordinators, ...secretaries];
        const uniqueUsers = Array.from(new Map(allUsers.map(u => [u.id, u])).values());
        
        participantsOptions.value = uniqueUsers.sort((a, b) => a.name.localeCompare(b.name));
        
        // Debug: mostra quantos de cada tipo foram carregados
        console.log(`Participantes carregados: ${teachers.length} professores, ${coordinators.length} coordenadores, ${secretaries.length} secretários`);
    } catch (error) {
        console.error('Erro ao carregar participantes:', error);
        toast.add({ severity: 'warn', summary: 'Aviso', detail: 'Erro ao carregar lista de participantes', life: 3000 });
    }
};

// --- AÇÕES ---
const openNew = async () => {
    minute.value = {
        date: new Date(), // Padrão: Hoje
        participants: [],
        guests: ''
    };
    submitted.value = false;
    if (participantsOptions.value.length === 0) {
        await loadParticipants();
    }
    minuteDialog.value = true;
};

const editMinute = async (item) => {
    minute.value = { ...item };
    // Corrige data string para objeto Date
    if (minute.value.date) {
        minute.value.date = new Date(minute.value.date);
    }
    // Converte string de participantes para array de IDs
    if (minute.value.participants && typeof minute.value.participants === 'string') {
        // Tenta encontrar os IDs correspondentes aos nomes na string
        const participantNames = minute.value.participants.split(',').map(n => n.trim());
        const foundIds = participantsOptions.value
            .filter(p => participantNames.some(name => p.name.toLowerCase().includes(name.toLowerCase()) || name.toLowerCase().includes(p.name.toLowerCase())))
            .map(p => p.id);
        minute.value.participants = foundIds.length > 0 ? foundIds : [];
    } else if (!Array.isArray(minute.value.participants)) {
        minute.value.participants = [];
    }
    // Garante que guests existe
    if (!minute.value.guests) {
        minute.value.guests = '';
    }
    if (participantsOptions.value.length === 0) {
        await loadParticipants();
        // Recarrega após carregar participantes para fazer a conversão correta
        if (minute.value.participants && typeof minute.value.participants === 'string') {
            const participantNames = minute.value.participants.split(',').map(n => n.trim());
            const foundIds = participantsOptions.value
                .filter(p => participantNames.some(name => p.name.toLowerCase().includes(name.toLowerCase()) || name.toLowerCase().includes(p.name.toLowerCase())))
                .map(p => p.id);
            minute.value.participants = foundIds.length > 0 ? foundIds : [];
        }
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
        
        // Converte array de IDs de participantes para string com nomes separados por vírgula
        if (Array.isArray(payload.participants) && payload.participants.length > 0) {
            const selectedParticipants = participantsOptions.value.filter(p => payload.participants.includes(p.id));
            payload.participants = selectedParticipants.map(p => p.name).join(', ');
        } else {
            payload.participants = '';
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
                        <Button label="Nova Ata" icon="pi pi-plus" class="mr-2" @click="openNew" />
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
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editMinute(slotProps.data)" v-tooltip.top="'Editar/Ver Detalhes'" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDelete(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="minuteDialog" :style="{ width: '800px' }" header="Registro de Reunião" :modal="true" class="p-fluid" maximizable>
                
                <div class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-8">
                        <label class="mb-2 block font-bold">Título / Pauta Principal</label>
                        <InputText v-model="minute.title" required="true" autofocus :class="{ 'p-invalid': submitted && !minute.title }" fluid />
                        <small class="p-error" v-if="submitted && !minute.title">Título obrigatório.</small>
                    </div>
                    <div class="col-span-12 xl:col-span-4">
                        <label class="mb-2 block font-bold">Data</label>
                        <DatePicker v-model="minute.date" dateFormat="dd/mm/yy" showIcon fluid />
                    </div>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Participantes</label>
                    <MultiSelect 
                        v-model="minute.participants" 
                        :options="participantsOptions" 
                        optionLabel="name" 
                        optionValue="id"
                        placeholder="Selecione os participantes"
                        :maxSelectedLabels="3"
                        selectedItemsLabel="{0} participantes selecionados"
                        display="chip"
                        filter
                        class="w-full"
                    />
                    <small class="text-500">Selecione professores, coordenadores ou secretaria.</small>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Convidados</label>
                    <InputText 
                        v-model="minute.guests" 
                        placeholder="Ex: Pais, representantes, visitantes..." 
                        fluid 
                    />
                    <small class="text-500">Liste os convidados externos separados por vírgula.</small>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Conteúdo / Decisões</label>
                    <Editor v-model="minute.content" rows="10" autoResize placeholder="Descreva o que foi discutido e decidido..." :class="{ 'p-invalid': submitted && !minute.content }" fluid editorStyle="height: 320px" />
                    <small class="p-error" v-if="submitted && !minute.content">Conteúdo obrigatório.</small>
                </div>

                <div class="mb-2">
                    <label class="mb-2 block font-bold">Próximos Passos / Tarefas</label>
                    <Editor v-model="minute.next_steps" rows="3" autoResize placeholder="O que ficou para fazer? Quem fará?" fluid editorStyle="height: 320px" />
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="minuteDialog = false" />
                    <Button label="Salvar Ata" icon="pi pi-check" @click="saveMinute" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-center justify-center">
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
<script setup>
import { ref, onMounted, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import { FilterMatchMode } from '@primevue/core/api';
import api from '@/service/api';

const toast = useToast();
const currentUser = ref(null); // Para saber se é coord ou prof

// --- DADOS ---
const inboxMessages = ref([]);
const sentMessages = ref([]);
const usersList = ref([]); // Lista de destinatários possíveis

// --- CONTROLES VISUAIS ---
const activeTab = ref(0);
const loading = ref(true);
const viewDialog = ref(false);     // Ler mensagem
const createDialog = ref(false);   // Criar mensagem
const reportDialog = ref(false);   // Ver quem leu
const deleteDialog = ref(false);

// --- OBJETOS DE EDIÇÃO ---
const selectedMessage = ref({});
const newMessage = ref({
    title: '',
    message: '',
    priority: 'NORMAL',
    recipient_ids: []
});
const readReport = ref([]); // Lista de quem leu

// --- FILTROS ---
const filters = ref({ global: { value: null, matchMode: FilterMatchMode.CONTAINS } });

const isCoordinator = computed(() => {
    const user = currentUser.value;
    if (!user) return false;

    // Se for superusuário, libera tudo
    if (user.is_superuser) return true;

    // Verifica se a lista de grupos (strings) contém 'Coordenacao'
    // O serializer retorna algo como: ["Coordenacao", "Professores"]
    const groups = user.groups || [];
    return groups.includes('Coordenacao');
});

// --- CARGA INICIAL ---
onMounted(async () => {
    await loadCurrentUser();
    loadMessages();
    if (isCoordinator.value) {
        loadUsers(); // Carrega lista de professores para o select
    }
});

const loadCurrentUser = async () => {
    // Simulação ou pegar do store. 
    // Idealmente: const user = useAuthStore().user;
    // Aqui vou bater num endpoint de profile ou assumir pelo grupo
    try {
        const { data } = await api.get('users/me/'); 
        currentUser.value = data;
    } catch (e) {
        console.error("Erro ao carregar usuário");
    }
};

// --- CARREGAR MENSAGENS ---
const loadMessages = async () => {
    loading.value = true;
    try {
        const { data } = await api.get('announcements/');
        const allMessages = data.results || data;
        
        // Garante que temos o ID do usuário logado
        if (!currentUser.value) await loadCurrentUser();
        const myId = currentUser.value.id;

        // SEPARAÇÃO:
        
        // 1. Inbox: Mensagens onde eu NÃO sou o remetente
        inboxMessages.value = allMessages.filter(msg => msg.sender_id !== myId);

        // 2. Enviados: Mensagens onde eu SOU o remetente
        // (Só preenche se tiver permissão de coordenador, senão fica vazio)
        if (isCoordinator.value) {
            sentMessages.value = allMessages.filter(msg => msg.sender_id === myId);
        }

    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar.' });
    } finally {
        loading.value = false;
    }
};

const loadUsers = async () => {
    try {
        // Carrega todos os usuários (estamos assumindo que o endpoint retorna o campo 'groups')
        const { data } = await api.get('users/?page_size=1000');
        
        // --- FILTRO DE SEGURANÇA ---
        const staffOnly = data.results.filter(u => {
            const groups = u.groups || [];
            return groups.includes('Professores') || groups.includes('Coordenacao') || groups.includes('Direcao') || u.is_superuser;
        });

        // Mapeia para o formato do Dropdown
        usersList.value = staffOnly.map(u => ({
            id: u.id,
            label: `${u.first_name || ''} ${u.last_name || ''} (${u.username})`.trim()
        }));

    } catch (e) {
        console.error("Erro ao carregar lista de usuários", e);
    }
};

// --- AÇÕES DO RECEPTOR (LER) ---
const openMessage = async (msg) => {
    selectedMessage.value = msg;
    viewDialog.value = true;

    // Se não leu ainda, marca como lido
    if (!msg.is_read && !isCoordinator.value) {
        try {
            await api.post(`announcements/${msg.id}/mark_as_read/`);
            msg.is_read = true; // Atualiza visualmente na hora
            // Opcional: emitir evento para atualizar contador no header
        } catch (e) {
            console.error("Erro ao marcar como lido");
        }
    }
};

// --- AÇÕES DO EMISSOR (CRIAR) ---
const openCreate = () => {
    newMessage.value = { 
        id: null, // Importante para saber que é criação
        title: '', 
        message: '', 
        priority: 'NORMAL', 
        recipient_ids: [] 
    };
    createDialog.value = true;
};

// 2. Abrir para Editar (Carrega dados)
const openEdit = (msg) => {
    // Clona o objeto para não alterar a tabela diretamente antes de salvar
    newMessage.value = { 
        id: msg.id,
        title: msg.title,
        message: msg.message,
        priority: msg.priority,
        // O backend agora retorna os IDs no campo recipient_ids (graças ao serializer)
        recipient_ids: msg.recipient_ids || [] 
    };
    createDialog.value = true;
};

// 3. Salvar (Inteligente: Cria ou Atualiza)
const sendMessage = async () => {
    if (!newMessage.value.title || !newMessage.value.message || newMessage.value.recipient_ids.length === 0) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha todos os campos.' });
        return;
    }

    try {
        if (newMessage.value.id) {
            // EDIÇÃO (PUT/PATCH)
            await api.patch(`announcements/${newMessage.value.id}/`, newMessage.value);
            toast.add({ severity: 'success', summary: 'Atualizado', detail: 'Comunicado corrigido com sucesso!' });
        } else {
            // CRIAÇÃO (POST)
            await api.post('announcements/', newMessage.value);
            toast.add({ severity: 'success', summary: 'Enviado', detail: 'Comunicado criado com sucesso!' });
        }
        
        createDialog.value = false;
        loadMessages(); // Recarrega a lista
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao salvar.' });
    }
};

// --- AÇÕES DE EXCLUSÃO ---

const confirmDelete = (msg) => {
    selectedMessage.value = msg;
    deleteDialog.value = true;
};

const deleteMessage = async () => {
    try {
        await api.delete(`announcements/${selectedMessage.value.id}/`);
        toast.add({ severity: 'success', summary: 'Removido', detail: 'Comunicado excluído.' });
        deleteDialog.value = false;
        loadMessages();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao excluir.' });
    }
};

// --- AÇÕES DO EMISSOR (RELATÓRIO) ---
const openReport = async (msg) => {
    selectedMessage.value = msg;
    reportDialog.value = true;
    readReport.value = []; // Limpa anterior
    
    try {
        const { data } = await api.get(`announcements/${msg.id}/report/`);
        readReport.value = data;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao carregar relatório.' });
    }
};

// --- HELPERS ---
const getPrioritySeverity = (p) => {
    return p === 'HIGH' ? 'danger' : 'info';
};
const getPriorityLabel = (p) => {
    return p === 'HIGH' ? 'Alta / Urgente' : 'Normal';
};
</script>

<template>
    <div class="card">
        <div class="flex justify-between items-center mb-4">
            <h4 class="m-0">Mural de Comunicados</h4>
            <Button 
                v-if="isCoordinator" 
                label="Novo Comunicado" 
                icon="pi pi-plus" 
                @click="openCreate" 
            />
        </div>

        <TabView v-model:activeIndex="activeTab">
            
            <TabPanel header="Caixa de Entrada">
                <DataTable :value="inboxMessages" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
                    <template #empty>Nenhum comunicado recebido.</template>
                    
                    <Column field="is_read" header="" style="width: 3rem">
                        <template #body="slotProps">
                            <i v-if="slotProps.data.is_read" class="pi pi-envelope-open text-gray-400" v-tooltip="'Lido'"></i>
                            <i v-else class="pi pi-envelope text-primary font-bold" v-tooltip="'Não Lido'"></i>
                        </template>
                    </Column>

                    <Column field="title" header="Assunto" sortable>
                        <template #body="slotProps">
                            <span :class="{'font-bold': !slotProps.data.is_read, 'cursor-pointer hover:underline': true}" @click="openMessage(slotProps.data)">
                                {{ slotProps.data.title }}
                            </span>
                        </template>
                    </Column>
                    
                    <Column field="sender_name" header="De" sortable></Column>
                    
                    <Column field="priority" header="Prioridade" sortable>
                        <template #body="slotProps">
                            <Tag :value="getPriorityLabel(slotProps.data.priority)" :severity="getPrioritySeverity(slotProps.data.priority)" />
                        </template>
                    </Column>

                    <Column field="created_at" header="Data" sortable>
                        <template #body="slotProps">
                            {{ new Date(slotProps.data.created_at).toLocaleDateString() }}
                        </template>
                    </Column>

                    <Column header="Ação">
                        <template #body="slotProps">
                            <Button icon="pi pi-eye" class="p-button-rounded p-button-text" @click="openMessage(slotProps.data)" />
                        </template>
                    </Column>
                </DataTable>
            </TabPanel>

            <TabPanel header="Itens Enviados" v-if="isCoordinator">
                <DataTable :value="sentMessages" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
                    <template #empty>Nenhum comunicado enviado.</template>

                    <Column field="title" header="Assunto" sortable></Column>
                    <Column field="created_at" header="Data Envio" sortable>
                        <template #body="slotProps">
                            {{ new Date(slotProps.data.created_at).toLocaleDateString() }} {{ new Date(slotProps.data.created_at).toLocaleTimeString().slice(0,5) }}
                        </template>
                    </Column>
                    
                    <Column field="priority" header="Prioridade">
                         <template #body="slotProps">
                            <Tag :value="getPriorityLabel(slotProps.data.priority)" :severity="getPrioritySeverity(slotProps.data.priority)" />
                        </template>
                    </Column>

                    <Column header="Ações" style="min-width: 150px">
                        <template #body="slotProps">
                             <div class="flex gap-2">
                                <Button 
                                    :label="slotProps.data.read_stats || 'Ver'" 
                                    icon="pi pi-chart-pie" 
                                    class="p-button-outlined p-button-sm" 
                                    @click="openReport(slotProps.data)" 
                                    v-tooltip="'Clique para ver quem leu'"
                                />
                                
                                <Button icon="pi pi-pencil" class="p-button-rounded p-button p-button-sm" 
                                    @click="openEdit(slotProps.data)" v-tooltip="'Corrigir Erro'" />
                                
                                <Button icon="pi pi-trash" class="p-button-rounded p-button p-button-sm" 
                                    @click="confirmDelete(slotProps.data)" v-tooltip="'Apagar Comunicado'" />
                             </div>
                        </template>
                    </Column>
                </DataTable>
            </TabPanel>
        </TabView>

        <Dialog v-model:visible="viewDialog" :header="selectedMessage.title" :modal="true" :style="{width: '600px'}">
            <div class="flex flex-col gap-3">
                <div class="flex justify-between text-sm text-gray-500 border-b pb-2">
                    <span><b>De:</b> {{ selectedMessage.sender_name }}</span>
                    <span>{{ new Date(selectedMessage.created_at).toLocaleString() }}</span>
                </div>
                
                <div class="p-3 surface-100 border-round text-lg line-height-3">
                    {{ selectedMessage.message }}
                </div>
            </div>
            <template #footer>
                <Button label="Fechar" icon="pi pi-times" @click="viewDialog = false" autofocus />
            </template>
        </Dialog>

        <Dialog v-model:visible="createDialog" header="Novo Comunicado" :modal="true" :style="{width: '600px'}">
            <div class="flex flex-col gap-4">
                <div class="flex flex-col gap-2">
                    <label class="font-bold">Assunto</label>
                    <InputText v-model="newMessage.title" placeholder="Ex: Reunião de Pais" />
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div class="flex flex-col gap-2">
                        <label class="font-bold">Prioridade</label>
                        <Dropdown 
                            v-model="newMessage.priority" 
                            :options="[{label: 'Normal', value: 'NORMAL'}, {label: 'Alta / Urgente', value: 'HIGH'}]" 
                            optionLabel="label" 
                            optionValue="value" 
                        />
                    </div>
                    <div class="flex flex-col gap-2">
                        <label class="font-bold">Destinatários</label>
                        <MultiSelect 
                            v-model="newMessage.recipient_ids" 
                            :options="usersList" 
                            optionLabel="label" 
                            optionValue="id" 
                            placeholder="Selecione..." 
                            filter
                            :maxSelectedLabels="3"
                            class="w-full"
                        />
                    </div>
                </div>

                <div class="flex flex-col gap-2">
                    <label class="font-bold">Mensagem</label>
                    <Textarea v-model="newMessage.message" rows="6" placeholder="Digite o conteúdo..." />
                </div>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="createDialog = false" />
                <Button label="Enviar" icon="pi pi-send" @click="sendMessage" />
            </template>
        </Dialog>

        <Dialog v-model:visible="reportDialog" header="Relatório de Leitura" :modal="true" :style="{width: '800px'}">
            <DataTable :value="readReport" responsiveLayout="scroll" size="small" stripedRows paginator :rows="5">
                <Column field="name" header="Destinatário" sortable></Column>
                <Column field="read" header="Status" sortable>
                    <template #body="slotProps">
                        <Tag v-if="slotProps.data.read" severity="success" value="Lido" icon="pi pi-check" />
                        <Tag v-else severity="warning" value="Pendente" icon="pi pi-clock" />
                    </template>
                </Column>
                <Column field="read_at" header="Data Leitura">
                    <template #body="slotProps">
                        <span v-if="slotProps.data.read_at" class="text-sm">
                            {{ new Date(slotProps.data.read_at).toLocaleString() }}
                        </span>
                        <span v-else>-</span>
                    </template>
                </Column>
            </DataTable>
        </Dialog>

        <Dialog v-model:visible="deleteDialog" :style="{ width: '450px' }" header="Excluir Comunicado" :modal="true">
            <div class="flex items-center gap-4">
                <i class="pi pi-exclamation-triangle text-red-500 text-4xl" />
                <span class="line-height-3">
                    Tem certeza que deseja apagar este comunicado?
                    <br>
                    <small class="text-gray-500">Ele sumirá da caixa de entrada de todos os professores.</small>
                </span>
            </div>
            <template #footer>
                <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false" />
                <Button label="Sim, Apagar" icon="pi pi-trash" class="p-button" @click="deleteMessage" autofocus />
            </template>
        </Dialog>
    </div>
</template>
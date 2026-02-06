<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const FilterMatchMode = {
    CONTAINS: 'contains'
};

const toast = useToast();

const guardians = ref([]);
const guardian = ref({});
const guardianDialog = ref(false);
const deleteGuardianDialog = ref(false);
const loading = ref(true);
const submitted = ref(false);
const totalRecords = ref(0);
const lazyParams = ref({ page: 0, rows: 10 });

const filters = ref({
    global: { value: null, matchMode: FilterMatchMode.CONTAINS },
});

// --- CARREGAR DADOS ---
const loadData = async () => {
    loading.value = true;
    try {
        const page = lazyParams.value.page + 1;
        const limit = lazyParams.value.rows;
        
        // --- CORREÇÃO AQUI ---
        // Pega o valor digitado na busca global
        const searchTerm = filters.value.global.value;
        
        // Monta a URL com o parâmetro de busca se existir
        let url = `guardians/?page=${page}&page_size=${limit}`;
        if (searchTerm) {
            url += `&search=${encodeURIComponent(searchTerm)}`;
        }

        const response = await api.get(url);
        
        guardians.value = response.data.results;
        totalRecords.value = response.data.count; 
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar responsáveis' });
    } finally {
        loading.value = false;
    }
};

const onFilter = (event) => {
    // Atualiza os filtros com o que veio do evento
    filters.value = event.filters;
    // Reseta para a primeira página quando filtra
    lazyParams.value.page = 0; 
    loadData();
};

const onPage = (event) => {
    lazyParams.value = event;
    loadData();
};

// --- AÇÕES ---
const openNew = () => {
    guardian.value = {};
    submitted.value = false;
    guardianDialog.value = true;
};

const editGuardian = (item) => {
    // Garante que campos opcionais tenham string vazia se vierem null do backend
    guardian.value = { 
        ...item,
        secondary_phone: item.secondary_phone || '',
        email: item.email || '',
        profession: item.profession || ''
    };
    guardianDialog.value = true;
};

const confirmDeleteGuardian = (item) => {
    guardian.value = item;
    deleteGuardianDialog.value = true;
};

// --- SALVAR ---
const saveGuardian = async () => {
    submitted.value = true;

    // Validação básica frontend
    if (guardian.value.name && guardian.value.cpf && guardian.value.phone) {
        
        // Clona o objeto para limpar dados antes de enviar (se necessário)
        const payload = { ...guardian.value };

        // TRUQUE: Se o telefone secundário estiver vazio, envie null ou string vazia
        // para evitar erro de validação no backend
        if (!payload.secondary_phone) payload.secondary_phone = '';
        if (!payload.email) payload.email = '';

        try {
            if (guardian.value.id) {
                // --- MUDANÇA PRINCIPAL: PUT -> PATCH ---
                // PATCH é mais seguro para edições parciais
                await api.patch(`guardians/${guardian.value.id}/`, payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Responsável atualizado', life: 3000 });
            } else {
                await api.post('guardians/', payload);
                toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Responsável cadastrado', life: 3000 });
            }
            
            guardianDialog.value = false;
            loadData(); // Recarrega a lista
            
        } catch (error) {
            console.error("Erro detalhado:", error);
            
            // --- TRATAMENTO DE ERRO MELHORADO ---
            // Se o backend mandou detalhes (ex: CPF duplicado, Campo obrigatório), mostramos aqui.
            if (error.response && error.response.data) {
                const errors = error.response.data;
                // Pega a primeira mensagem de erro que encontrar
                const firstError = Object.values(errors)[0]; 
                const msg = Array.isArray(firstError) ? firstError[0] : firstError;
                
                toast.add({ severity: 'error', summary: 'Erro de Validação', detail: msg || 'Verifique os dados.', life: 5000 });
            } else {
                toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha na comunicação com o servidor.', life: 3000 });
            }
        }
    } else {
         toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Preencha Nome, CPF e Celular.', life: 3000 });
    }
};

const deleteGuardian = async () => {
    try {
        await api.delete(`guardians/${guardian.value.id}/`);
        deleteGuardianDialog.value = false;
        guardian.value = {};
        toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Removido com sucesso', life: 3000 });
        loadData();
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao remover. Verifique se não há alunos vinculados.', life: 3000 });
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
                        <Button label="Novo Responsável" icon="pi pi-plus" class="mr-2" @click="openNew" />
                    </div>
                </template>
            </Toolbar>

            <DataTable 
                :value="guardians" 
                :lazy="true" 
                :filters="filters" 
                :loading="loading" 
                responsiveLayout="scroll" 
                :paginator="true" 
                :rows="10" 
                :totalRecords="totalRecords" 
                @page="onPage"
                @filter="onFilter"  >
                <template #header>
                    <div class="flex flex-wrap gap-2 items-center justify-between">
                        <h4 class="m-0">Cadastro de Pais e Responsáveis</h4>
                        <IconField>
                            <InputIcon>
                                <i class="pi pi-search" />
                            </InputIcon>
                            <InputText v-model="filters['global'].value" placeholder="Buscar..." @input="loadData" />
                        </IconField>
                    </div>
                </template>
                
                <Column field="name" header="Nome" sortable></Column>
                <Column field="cpf" header="CPF"></Column>
                <Column field="phone" header="Celular"></Column>
                <Column field="email" header="Email"></Column>
                
                <Column header="Ações">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded mr-2" @click="editGuardian(slotProps.data)" />
                        <Button icon="pi pi-trash" class="p-button-rounded" @click="confirmDeleteGuardian(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <Dialog v-model:visible="guardianDialog" :style="{ width: '500px' }" header="Dados do Responsável" :modal="true" class="p-fluid">
                
                <div class="mb-2">
                    <label for="name" class="block font-bold mb-3">Nome Completo</label>
                    <InputText id="name" v-model.trim="guardian.name" required="true" autofocus :class="{ 'p-invalid': submitted && !guardian.name }" fluid />
                    <small class="p-error" v-if="submitted && !guardian.name">Nome é obrigatório.</small>
                </div>

                <div class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-3">CPF</label>
                        <InputMask v-model="guardian.cpf" mask="999.999.999-99" placeholder="000.000.000-00" :class="{ 'p-invalid': submitted && !guardian.cpf }" fluid />
                        <small class="p-error" v-if="submitted && !guardian.cpf">CPF obrigatório.</small>
                    </div>
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-3">RG</label>
                        <InputText v-model="guardian.rg" fluid />
                    </div>
                </div>

                <div class="grid grid-cols-12 gap-4 mb-2">
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-3">Celular / WhatsApp</label>
                        <InputMask v-model="guardian.phone" mask="(99) 99999-9999" placeholder="(11) 99999-9999" :class="{ 'p-invalid': submitted && !guardian.phone }" fluid />
                        <small class="p-error" v-if="submitted && !guardian.phone">Telefone obrigatório.</small>
                    </div>
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block font-bold mb-3">Telefone Secundário</label>
                        <InputMask v-model="guardian.secondary_phone" mask="(99) 99999-9999" placeholder="Opcional" fluid />
                    </div>
                </div>

                <div class="mb-2">
                    <label class="block font-bold mb-3">Email (Login)</label>
                    <InputText v-model="guardian.email" placeholder="exemplo@email.com" fluid />
                </div>

                <div class="mb-2">
                    <label class="block font-bold mb-3">Profissão</label>
                    <InputText v-model="guardian.profession" fluid />
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="guardianDialog = false" />
                    <Button label="Salvar" icon="pi pi-check" @click="saveGuardian" />
                </template>
            </Dialog>

            <Dialog v-model:visible="deleteGuardianDialog" :style="{ width: '450px' }" header="Confirmar" :modal="true">
                <div class="flex align-items-center justify-content-center">
                    <i class="pi pi-exclamation-triangle mr-3" style="font-size: 2rem" />
                    <span>Deseja remover este responsável?</span>
                </div>
                <template #footer>
                    <Button label="Não" icon="pi pi-times" class="p-button-text" @click="deleteGuardianDialog = false" />
                    <Button label="Sim" icon="pi pi-check" class="p-button-text" @click="deleteGuardian" />
                </template>
            </Dialog>
        </div>
    </div>
</template>
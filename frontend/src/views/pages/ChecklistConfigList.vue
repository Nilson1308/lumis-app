<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const configs = ref([]);
const configDialog = ref(false);
const config = ref({});
const submitted = ref(false);
const loading = ref(false);

// Lista de segmentos
const segments = ref([]);

// --- CARREGAR DEPENDÊNCIAS ---
const loadDependencies = async () => {
    try {
        const resSegments = await api.get('segments/?page_size=1000');
        segments.value = resSegments.data.results || resSegments.data;
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar segmentos.', life: 3000 });
    }
};

// --- BUSCAR CONFIGURAÇÕES ---
const fetchConfigs = async () => {
    loading.value = true;
    try {
        const res = await api.get('checklist-configs/?page_size=1000');
        configs.value = res.data.results || res.data;
        
        // Cria configurações vazias para segmentos que não têm
        const existingSegmentIds = configs.value.map(c => c.segment);
        segments.value.forEach(segment => {
            if (!existingSegmentIds.includes(segment.id)) {
                configs.value.push({
                    id: null,
                    segment: segment.id,
                    segment_name: segment.name,
                    requires_checklist: false,
                    requires_lunch: false,
                    requires_snack: false,
                    requires_checkin: false,
                    requires_checkout: false
                });
            }
        });
    } catch (e) {
        console.error(e);
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar configurações.', life: 3000 });
    } finally {
        loading.value = false;
    }
};

// --- ABRIR DIALOG ---
const openConfig = (cfg) => {
    config.value = { ...cfg };
    configDialog.value = true;
};

// --- SALVAR ---
const saveConfig = async () => {
    submitted.value = true;

    if (!config.value.segment) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Selecione um segmento.', life: 3000 });
        return;
    }

    if (!config.value.requires_checklist) {
        // Se não requer checklist, desmarca todos os campos
        config.value.requires_lunch = false;
        config.value.requires_snack = false;
        config.value.requires_checkin = false;
        config.value.requires_checkout = false;
    }

    try {
        if (config.value.id) {
            await api.put(`checklist-configs/${config.value.id}/`, config.value);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Configuração atualizada', life: 3000 });
        } else {
            await api.post('checklist-configs/', config.value);
            toast.add({ severity: 'success', summary: 'Sucesso', detail: 'Configuração criada', life: 3000 });
        }
        configDialog.value = false;
        config.value = {};
        await fetchConfigs();
    } catch (error) {
        console.error(error);
        const msg = error.response?.data?.error || error.response?.data?.detail || 'Erro ao salvar.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 3000 });
    }
};

onMounted(async () => {
    await loadDependencies();
    await fetchConfigs();
});
</script>

<template>
    <div class="col-12">
        <div class="card">
            <Toast />
            
            <div class="flex justify-content-between align-items-center mb-4">
                <h3>Configuração de Checklist por Segmento</h3>
            </div>

            <DataTable :value="configs" :loading="loading" responsiveLayout="scroll" stripedRows>
                <template #empty>Nenhuma configuração cadastrada.</template>

                <Column field="segment_name" header="Segmento" sortable></Column>
                <Column field="requires_checklist" header="Requer Checklist" style="width: 15%">
                    <template #body="slotProps">
                        <Tag :value="slotProps.data.requires_checklist ? 'Sim' : 'Não'" 
                             :severity="slotProps.data.requires_checklist ? 'success' : 'danger'" />
                    </template>
                </Column>
                <Column header="Campos" style="width: 40%">
                    <template #body="slotProps">
                        <div class="flex flex-wrap gap-1" v-if="slotProps.data.requires_checklist">
                            <Tag v-if="slotProps.data.requires_lunch" value="Almoço" severity="info" />
                            <Tag v-if="slotProps.data.requires_snack" value="Lanche" severity="info" />
                            <Tag v-if="slotProps.data.requires_checkin" value="Entrada" severity="info" />
                            <Tag v-if="slotProps.data.requires_checkout" value="Saída" severity="info" />
                            <span v-if="!slotProps.data.requires_lunch && !slotProps.data.requires_snack && !slotProps.data.requires_checkin && !slotProps.data.requires_checkout" class="text-600 text-sm">Nenhum campo configurado</span>
                        </div>
                        <span v-else class="text-600 text-sm">-</span>
                    </template>
                </Column>
                <Column header="Ações" style="width: 10%">
                    <template #body="slotProps">
                        <Button icon="pi pi-pencil" class="p-button-rounded" 
                                @click="openConfig(slotProps.data)" />
                    </template>
                </Column>
            </DataTable>

            <!-- Dialog de Edição/Criação -->
            <Dialog v-model:visible="configDialog" :style="{ width: '500px' }" header="Configuração de Checklist" :modal="true" class="p-fluid">
                <div class="field mb-4">
                    <label class="block font-bold mb-3" for="segment">Segmento *</label>
                    <Dropdown 
                        id="segment"
                        v-model="config.segment" 
                        :options="segments" 
                        optionLabel="name" 
                        optionValue="id"
                        placeholder="Selecione o segmento"
                        class="w-full"
                        :disabled="!!config.id"
                    />
                </div>

                <div class="field mb-4">
                    <label class="block font-bold mb-3" for="requires_checklist">Requer Checklist Diário?</label>
                    <InputSwitch id="requires_checklist" v-model="config.requires_checklist" />
                </div>

                <div v-if="config.requires_checklist" class="grid grid-cols-12 gap-4 mt-3">
                    <div class="col-span-12 xl:col-span-6">
                        <label class="block mb-3" for="requires_lunch">Requer Almoço?</label>
                        <InputSwitch id="requires_lunch" v-model="config.requires_lunch" />
                    </div>

                    <div class="col-span-12 xl:col-span-6">
                        <label class="block mb-3" for="requires_snack">Requer Lanche?</label>
                        <InputSwitch id="requires_snack" v-model="config.requires_snack" />
                    </div>

                    <div class="col-span-12 xl:col-span-6">
                        <label class="block mb-3" for="requires_checkin">Requer Check-in (Entrada)?</label>
                        <InputSwitch id="requires_checkin" v-model="config.requires_checkin" />
                    </div>

                    <div class="col-span-12 xl:col-span-6">
                        <label class="block mb-3" for="requires_checkout">Requer Check-out (Saída)?</label>
                        <InputSwitch id="requires_checkout" v-model="config.requires_checkout" />
                    </div>
                </div>

                <template #footer>
                    <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="configDialog = false" />
                    <Button label="Salvar" icon="pi pi-check" @click="saveConfig" />
                </template>
            </Dialog>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';
import api from '@/service/api';

const toast = useToast();
const loading = ref(false);
const releasingId = ref(null);
const blocking = ref(false);
const data = ref({ enabled: false, count: 0, items: [] });
const activeTab = ref('active');
const search = ref('');
const teachers = ref([]);
const blockForm = ref({ teacher_id: null, reason: '' });

const loadBlocks = async () => {
    loading.value = true;
    try {
        const res = await api.get('lesson-plans/blocked-teachers/', {
            params: {
                active: activeTab.value === 'active' ? 'true' : 'false',
                q: search.value || undefined
            }
        });
        data.value = res.data || { enabled: false, count: 0, items: [] };
    } catch (error) {
        toast.add({
            severity: 'error',
            summary: 'Erro',
            detail: 'Falha ao carregar bloqueios de planejamento.',
            life: 4000
        });
    } finally {
        loading.value = false;
    }
};

const loadTeachers = async () => {
    try {
        const res = await api.get('users/', { params: { role: 'teacher', page_size: 1000 } });
        const rows = res.data?.results || res.data || [];
        teachers.value = rows.map((u) => ({
            id: u.id,
            label: u.first_name ? `${u.first_name} (${u.username})` : u.username
        }));
    } catch (e) {
        teachers.value = [];
    }
};

const releaseTeacher = async (row) => {
    releasingId.value = row.teacher_id;
    try {
        await api.post('lesson-plans/release-submission-guard/', { teacher_id: row.teacher_id });
        toast.add({
            severity: 'success',
            summary: 'Fluxo liberado',
            detail: `${row.teacher_name} foi liberado para enviar planejamentos.`,
            life: 3500
        });
        await loadBlocks();
    } catch (error) {
        const msg = error.response?.data?.error || 'Não foi possível liberar o professor.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 4500 });
    } finally {
        releasingId.value = null;
    }
};

const blockTeacher = async () => {
    if (!blockForm.value.teacher_id) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Selecione um professor.', life: 3000 });
        return;
    }
    blocking.value = true;
    try {
        await api.post('lesson-plans/block-submission-guard/', blockForm.value);
        toast.add({ severity: 'success', summary: 'Professor bloqueado', detail: 'Bloqueio manual aplicado.', life: 3500 });
        blockForm.value = { teacher_id: null, reason: '' };
        await loadBlocks();
    } catch (error) {
        const msg = error.response?.data?.error || 'Não foi possível bloquear.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 4500 });
    } finally {
        blocking.value = false;
    }
};

const releaseAll = async () => {
    try {
        const res = await api.post('lesson-plans/release-all-submission-guard/');
        toast.add({ severity: 'success', summary: 'Concluído', detail: res.data?.message || 'Bloqueios liberados.', life: 4000 });
        await loadBlocks();
    } catch (error) {
        const msg = error.response?.data?.error || 'Falha ao liberar todos.';
        toast.add({ severity: 'error', summary: 'Erro', detail: msg, life: 4000 });
    }
};

const switchTab = async (tab) => {
    activeTab.value = tab;
    await loadBlocks();
};

onMounted(async () => {
    await Promise.all([loadBlocks(), loadTeachers()]);
});
</script>

<template>
    <div class="card">
        <Toast />
        <div class="flex justify-between items-center mb-4">
            <div>
                <h4 class="m-0">Bloqueio de Envio de Planejamento</h4>
                <small class="text-600">Gestão de bloqueios por atraso para professores.</small>
            </div>
            <div class="flex gap-2">
                <Button icon="pi pi-unlock" label="Liberar Todos" class="p-button-outlined p-button-success" @click="releaseAll" :disabled="activeTab !== 'active' || data.count === 0" />
                <Button icon="pi pi-refresh" label="Atualizar" class="p-button-outlined" @click="loadBlocks" :loading="loading" />
            </div>
        </div>

        <Message v-if="!data.enabled" severity="info" :closable="false" class="mb-4">
            A política de bloqueio por atraso está desativada em Configuração da Escola.
        </Message>

        <Message v-else severity="warn" :closable="false" class="mb-4">
            Política ativa: professores em atraso ficam bloqueados até liberação manual.
        </Message>

        <div class="grid grid-cols-12 gap-3 mb-4">
            <div class="col-span-12 md:col-span-4">
                <Dropdown v-model="blockForm.teacher_id" :options="teachers" optionLabel="label" optionValue="id" placeholder="Selecionar professor para bloqueio manual" fluid filter />
            </div>
            <div class="col-span-12 md:col-span-6">
                <InputText v-model="blockForm.reason" placeholder="Motivo do bloqueio manual (opcional)" class="w-full" />
            </div>
            <div class="col-span-12 md:col-span-2">
                <Button label="Bloquear" icon="pi pi-lock" class="w-full p-button-warning" @click="blockTeacher" :loading="blocking" />
            </div>
        </div>

        <div class="flex gap-2 mb-3">
            <Button :class="activeTab === 'active' ? '' : 'p-button-outlined'" label="Ativos" icon="pi pi-lock" @click="switchTab('active')" />
            <Button :class="activeTab === 'history' ? '' : 'p-button-outlined'" label="Histórico" icon="pi pi-history" @click="switchTab('history')" />
            <IconField class="ml-auto">
                <InputIcon><i class="pi pi-search" /></InputIcon>
                <InputText v-model="search" placeholder="Buscar professor" @keyup.enter="loadBlocks" />
            </IconField>
        </div>

        <DataTable :value="data.items" :loading="loading" responsiveLayout="scroll" stripedRows>
            <template #empty>Nenhum professor bloqueado no momento.</template>
            <Column field="teacher_name" header="Professor" />
            <Column field="blocked_at_br" header="Bloqueado em" />
            <Column v-if="activeTab === 'history'" field="released_at_br" header="Liberado em" />
            <Column field="blocked_by" header="Origem do bloqueio" />
            <Column header="Motivo">
                <template #body="slotProps">
                    <span>{{ slotProps.data.reason || 'Sem motivo detalhado.' }}</span>
                </template>
            </Column>
            <Column header="Pendência mais antiga">
                <template #body="slotProps">
                    <span v-if="slotProps.data.overdue_items?.length">
                        {{ slotProps.data.overdue_items[0].subject_name }} - {{ slotProps.data.overdue_items[0].classroom_name }}
                        ({{ slotProps.data.overdue_items[0].week_start }} a {{ slotProps.data.overdue_items[0].week_end }})
                    </span>
                    <span v-else class="text-600">Sem pendências detalhadas.</span>
                </template>
            </Column>
            <Column header="Ação" style="width: 10rem">
                <template #body="slotProps">
                    <Button
                        v-if="activeTab === 'active'"
                        label="Liberar"
                        icon="pi pi-unlock"
                        class="p-button-sm p-button-success"
                        :loading="releasingId === slotProps.data.teacher_id"
                        @click="releaseTeacher(slotProps.data)"
                    />
                    <Tag v-else value="Liberado" severity="success" />
                </template>
            </Column>
        </DataTable>
    </div>
</template>

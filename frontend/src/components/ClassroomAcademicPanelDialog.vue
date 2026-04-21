<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({
    visible: { type: Boolean, default: false },
    periods: { type: Array, default: () => [] },
    assignments: { type: Array, default: () => [] },
    selectedPeriod: { type: [Number, String, null], default: null },
    selectedAssignmentIds: { type: Array, default: () => [] }
});

const emit = defineEmits([
    'update:visible',
    'update:selectedPeriod',
    'update:selectedAssignmentIds',
    'open-gradebooks'
]);

const selectionMode = ref('all');

const hasAssignments = computed(() => props.assignments.length > 0);
const selectedCount = computed(() => props.selectedAssignmentIds.length);
const subjectFilter = ref('');

const filteredAssignments = computed(() => {
    const query = subjectFilter.value.trim().toLowerCase();
    if (!query) return props.assignments;
    return props.assignments.filter((item) => item.label.toLowerCase().includes(query));
});

watch(
    () => props.visible,
    (isVisible) => {
        if (isVisible) {
            selectionMode.value = props.selectedAssignmentIds.length > 0 ? 'custom' : 'all';
        }
    },
    { immediate: true }
);

watch(selectionMode, (mode) => {
    if (mode === 'all') {
        emit('update:selectedAssignmentIds', []);
    }
});

const modeOptions = [
    { label: 'Todas as matérias', value: 'all' },
    { label: 'Selecionar matérias', value: 'custom' }
];

const submitOpen = () => {
    const assignmentIds = selectionMode.value === 'all'
        ? props.assignments.map((item) => item.id)
        : props.selectedAssignmentIds;

    emit('open-gradebooks', assignmentIds);
};

const toggleAssignment = (assignmentId) => {
    const current = props.selectedAssignmentIds;
    const exists = current.includes(assignmentId);
    const next = exists
        ? current.filter((id) => id !== assignmentId)
        : [...current, assignmentId];
    emit('update:selectedAssignmentIds', next);
};

const selectAllFiltered = () => {
    const ids = filteredAssignments.value.map((item) => item.id);
    emit('update:selectedAssignmentIds', ids);
};

const clearSelection = () => {
    emit('update:selectedAssignmentIds', []);
};
</script>

<template>
    <Dialog
        :visible="visible"
        header="Painel de Notas por Período"
        :modal="true"
        :style="{ width: '680px', maxWidth: '95vw' }"
        @update:visible="emit('update:visible', $event)"
    >
        <div class="grid grid-cols-12 gap-3">
            <div class="col-span-12 md:col-span-5">
                <label class="font-bold block mb-2">Período</label>
                <Dropdown
                    :modelValue="selectedPeriod"
                    :options="periods"
                    optionLabel="name"
                    optionValue="id"
                    placeholder="Selecione o período"
                    class="w-full"
                    autofocus
                    @update:modelValue="emit('update:selectedPeriod', $event)"
                />
            </div>

            <div class="col-span-12 md:col-span-7">
                <label class="font-bold block mb-2">Modo de abertura</label>
                <SelectButton
                    v-model="selectionMode"
                    :options="modeOptions"
                    optionLabel="label"
                    optionValue="value"
                    class="w-full"
                />
            </div>

            <div v-if="selectionMode === 'custom'" class="col-span-12">
                <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <label class="font-bold">Matérias</label>
                    <div class="flex gap-2">
                        <Button label="Selecionar tudo" icon="pi pi-check-square" size="small" text @click="selectAllFiltered" />
                        <Button label="Limpar" icon="pi pi-times" size="small" text severity="secondary" @click="clearSelection" />
                    </div>
                </div>

                <IconField class="w-full mb-2">
                    <InputIcon>
                        <i class="pi pi-search" />
                    </InputIcon>
                    <InputText
                        v-model="subjectFilter"
                        class="w-full"
                        placeholder="Filtrar matérias/professores"
                    />
                </IconField>

                <div class="surface-0 border-1 border-200 border-round p-2 max-h-16rem overflow-y-auto">
                    <div
                        v-for="assignment in filteredAssignments"
                        :key="assignment.id"
                        class="flex items-center justify-between px-2 py-2 border-round hover:surface-100 cursor-pointer"
                        @click="toggleAssignment(assignment.id)"
                    >
                        <span class="text-900">{{ assignment.label }}</span>
                        <Checkbox
                            :binary="true"
                            :modelValue="selectedAssignmentIds.includes(assignment.id)"
                            @update:modelValue="toggleAssignment(assignment.id)"
                            @click.stop
                        />
                    </div>

                    <div v-if="filteredAssignments.length === 0" class="text-sm text-500 px-2 py-3">
                        Nenhuma matéria encontrada para o filtro informado.
                    </div>
                </div>
            </div>

            <div class="col-span-12">
                <div class="surface-50 border-1 border-round border-200 p-3 text-sm text-700">
                    <template v-if="!hasAssignments">
                        Nenhuma atribuição de matéria/professor encontrada para esta turma.
                    </template>
                    <template v-else-if="selectionMode === 'all'">
                        Serão abertas <strong>{{ assignments.length }}</strong> matérias desta turma.
                    </template>
                    <template v-else>
                        Você selecionou <strong>{{ selectedCount }}</strong> matéria(s).
                    </template>
                </div>
            </div>
        </div>

        <template #footer>
            <Button label="Fechar" icon="pi pi-times" class="p-button-text" @click="emit('update:visible', false)" />
            <Button
                label="Abrir diários"
                icon="pi pi-external-link"
                :disabled="!hasAssignments || (selectionMode === 'custom' && selectedCount === 0)"
                @click="submitOpen"
            />
        </template>
    </Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import api from '@/service/api';
import { useToast } from 'primevue/usetoast';

const props = defineProps({
    visible: { type: Boolean, default: false },
    classroomId: { type: [String, Number], required: true },
    periods: { type: Array, default: () => [] },
    assignments: { type: Array, default: () => [] },
    enrollments: { type: Array, default: () => [] },
    selectedPeriod: { type: [Number, String, null], default: null }
});

const emit = defineEmits(['update:visible', 'update:selectedPeriod']);

const toast = useToast();
const loading = ref(false);
const selectionMode = ref('all');
const selectedSubjectIds = ref([]);
const studentFilter = ref('');
const rawGrades = ref([]);
let gradesRequestSeq = 0;
const debugEnabled = true;

const dedupeById = (items = []) => {
    const map = new Map();
    items.forEach((item) => {
        if (item?.id != null && !map.has(item.id)) {
            map.set(item.id, item);
        }
    });
    return Array.from(map.values());
};

const subjectOptions = computed(() => {
    const map = new Map();
    props.assignments.forEach((item) => {
        if (!item.subjectId) return;
        if (!map.has(item.subjectId)) {
            map.set(item.subjectId, {
                id: item.subjectId,
                label: item.subjectName || item.label
            });
        }
    });
    return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label));
});

const totalAssessments = computed(() => rawGrades.value.length);
const filteredStudentsCount = computed(() => studentRows.value.length);
const currentPeriodLabel = computed(() => {
    const current = props.periods.find((p) => p.id === props.selectedPeriod);
    return current?.name || '-';
});

const displayedSubjects = computed(() => {
    if (selectionMode.value === 'all') return subjectOptions.value;
    const selected = new Set(selectedSubjectIds.value);
    return subjectOptions.value.filter((s) => selected.has(s.id));
});

const gradesByEnrollmentAndSubject = computed(() => {
    const gradeMap = new Map();
    rawGrades.value.forEach((grade) => {
        const key = `${grade.enrollment}-${grade.subject}`;
        if (!gradeMap.has(key)) {
            gradeMap.set(key, { weightedSum: 0, totalWeight: 0, count: 0 });
        }
        const bucket = gradeMap.get(key);
        const value = Number(grade.value);
        const weight = Number(grade.weight ?? 1);
        if (!Number.isNaN(value) && !Number.isNaN(weight)) {
            bucket.weightedSum += value * weight;
            bucket.totalWeight += weight;
            bucket.count += 1;
        }
    });
    return gradeMap;
});

const subjectAverageMap = computed(() => {
    const map = new Map();
    displayedSubjects.value.forEach((subject) => {
        let total = 0;
        let count = 0;
        props.enrollments.forEach((enrollment) => {
            const key = `${enrollment.id}-${subject.id}`;
            const bucket = gradesByEnrollmentAndSubject.value.get(key);
            if (bucket && bucket.totalWeight > 0) {
                total += bucket.weightedSum / bucket.totalWeight;
                count += 1;
            }
        });
        map.set(subject.id, count > 0 ? total / count : null);
    });
    return map;
});

const studentRows = computed(() => {
    const query = studentFilter.value.trim().toLowerCase();
    return props.enrollments
        .filter((e) => !query || e.label.toLowerCase().includes(query))
        .map((enrollment) => {
            let total = 0;
            let count = 0;
            const subjectGrades = {};

            displayedSubjects.value.forEach((subject) => {
                const key = `${enrollment.id}-${subject.id}`;
                const bucket = gradesByEnrollmentAndSubject.value.get(key);
                let average = null;
                if (bucket && bucket.totalWeight > 0) {
                    average = bucket.weightedSum / bucket.totalWeight;
                    total += average;
                    count += 1;
                }
                subjectGrades[subject.id] = {
                    average,
                    assessments: bucket?.count ?? 0
                };
            });

            return {
                enrollmentId: enrollment.id,
                studentName: enrollment.label,
                subjectGrades,
                generalAverage: count > 0 ? total / count : null
            };
        });
});

const gradeTagSeverity = (gradeValue) => {
    if (gradeValue === null || gradeValue === undefined) return 'contrast';
    if (gradeValue >= 7) return 'success';
    if (gradeValue >= 6) return 'warning';
    return 'danger';
};

const formatGrade = (value) => (value === null || value === undefined ? '-' : value.toFixed(1));

/** Lista bruta de notas por par matrícula + matéria (para o dialog de detalhes) */
const gradesListByEnrollmentSubject = computed(() => {
    const map = new Map();
    rawGrades.value.forEach((g) => {
        const key = `${g.enrollment}-${g.subject}`;
        if (!map.has(key)) map.set(key, []);
        map.get(key).push(g);
    });
    map.forEach((list) => {
        list.sort((a, b) => {
            const da = a.date ? new Date(a.date).getTime() : 0;
            const db = b.date ? new Date(b.date).getTime() : 0;
            return da - db;
        });
    });
    return map;
});

const detailsVisible = ref(false);
const detailsTitle = ref('');
const detailRows = ref([]);

const openGradeDetails = (enrollmentId, subjectId, studentName, subjectLabel, assessmentCount) => {
    if (!assessmentCount) return;
    const key = `${enrollmentId}-${subjectId}`;
    detailRows.value = gradesListByEnrollmentSubject.value.get(key) || [];
    detailsTitle.value = `${studentName} · ${subjectLabel}`;
    detailsVisible.value = true;
};

const exportDetailRowsCsv = () => {
    if (!detailRows.value.length) return;

    const headers = ['Avaliacao', 'Peso', 'Nota', 'Data'];
    const lines = detailRows.value.map((row) => {
        const date = row.date ? new Date(row.date).toLocaleDateString('pt-BR') : '';
        const safeName = String(row.name ?? '').replaceAll('"', '""');
        return [`"${safeName}"`, row.weight ?? 1, row.value ?? '', `"${date}"`].join(',');
    });
    const csvContent = [headers.join(','), ...lines].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `avaliacoes-${detailsTitle.value.replaceAll(' ', '_').toLowerCase()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
};

const getPaginatedItems = async (endpoint, params = {}) => {
    const items = [];
    let page = 1;

    while (true) {
        const response = await api.get(endpoint, {
            params: {
                ...params,
                page_size: params.page_size || 1000,
                page
            }
        });
        const data = response.data;
        if (Array.isArray(data)) return data;
        const chunk = Array.isArray(data?.results) ? data.results : [];
        items.push(...chunk);
        if (!data?.next || chunk.length === 0) break;
        page += 1;
    }
    return items;
};

const loadGrades = async () => {
    if (!props.visible || !props.selectedPeriod || !props.classroomId) return;
    const requestSeq = ++gradesRequestSeq;
    loading.value = true;
    try {
        const grades = await getPaginatedItems('grades/', {
            enrollment__classroom: props.classroomId,
            period: props.selectedPeriod,
            page_size: 1000
        });

        // Evita sobrescrever estado com resposta antiga (troca rápida de período)
        if (requestSeq !== gradesRequestSeq) return;

        const enrollmentIds = new Set(props.enrollments.map((e) => e.id));
        const subjectIds = new Set(subjectOptions.value.map((s) => s.id));

        const deduped = dedupeById(grades);
        const filtered = deduped.filter((grade) =>
            enrollmentIds.has(grade.enrollment) && subjectIds.has(grade.subject)
        );
        rawGrades.value = filtered;

        if (debugEnabled) {
            const duplicateCount = grades.length - deduped.length;
            const outOfScopeCount = deduped.length - filtered.length;
            console.info('[ClassroomGradesOverviewDialog] grades debug', {
                classroomId: props.classroomId,
                periodId: props.selectedPeriod,
                fetched: grades.length,
                deduped: deduped.length,
                duplicatesRemoved: duplicateCount,
                removedOutOfScope: outOfScopeCount,
                finalInScope: filtered.length
            });
        }
    } catch (e) {
        if (requestSeq !== gradesRequestSeq) return;
        rawGrades.value = [];
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Não foi possível carregar as notas da turma.', life: 3000 });
    } finally {
        if (requestSeq === gradesRequestSeq) {
            loading.value = false;
        }
    }
};

watch(
    () => props.visible,
    (isVisible) => {
        if (isVisible) {
            selectionMode.value = 'all';
            selectedSubjectIds.value = [];
            studentFilter.value = '';
            detailsVisible.value = false;
            detailRows.value = [];
            loadGrades();
        }
    }
);

watch(
    () => props.selectedPeriod,
    () => {
        detailsVisible.value = false;
        detailRows.value = [];
        if (props.visible) loadGrades();
    }
);
</script>

<template>
    <Dialog
        :visible="visible"
        header="Painel Analítico de Notas da Turma"
        :modal="true"
        maximizable
        class="grades-overview-dialog"
        :style="{ width: '95vw' }"
        @update:visible="emit('update:visible', $event)"
    >
        <div class="grid grid-cols-12 gap-3 mb-3">
            <div class="col-span-12 md:col-span-3">
                <label class="font-bold block mb-2">Período</label>
                <Dropdown
                    :modelValue="selectedPeriod"
                    :options="periods"
                    optionLabel="name"
                    optionValue="id"
                    class="w-full"
                    placeholder="Selecione o período"
                    autofocus
                    @update:modelValue="emit('update:selectedPeriod', $event)"
                />
            </div>
            <div class="col-span-12 md:col-span-5">
                <label class="font-bold block mb-2">Matérias</label>
                <SelectButton
                    v-model="selectionMode"
                    :options="[{ label: 'Todas', value: 'all' }, { label: 'Escolher', value: 'custom' }]"
                    optionLabel="label"
                    optionValue="value"
                    class="w-full"
                />
            </div>
            <div class="col-span-12 md:col-span-4">
                <label class="font-bold block mb-2">Buscar aluno</label>
                <IconField class="w-full">
                    <InputIcon><i class="pi pi-search" /></InputIcon>
                    <InputText v-model="studentFilter" class="w-full" placeholder="Digite o nome do aluno" />
                </IconField>
            </div>
        </div>

        <div v-if="selectionMode === 'custom'" class="mb-3">
            <MultiSelect
                v-model="selectedSubjectIds"
                :options="subjectOptions"
                optionLabel="label"
                optionValue="id"
                display="chip"
                filter
                class="w-full"
                placeholder="Escolha uma ou mais matérias"
            />
        </div>

        <div class="surface-50 border-1 border-200 border-round p-3 mb-3 text-sm text-700 flex flex-wrap gap-3">
            <span><strong>Período:</strong> {{ currentPeriodLabel }}</span>
            <span><strong>Alunos exibidos:</strong> {{ filteredStudentsCount }}</span>
            <span><strong>Matérias exibidas:</strong> {{ displayedSubjects.length }}</span>
            <span><strong>Notas carregadas:</strong> {{ totalAssessments }}</span>
        </div>

        <!-- Cards de média por matéria: flex + min-width evita colunas estreitas que quebram o texto (grid dentro do dialog) -->
        <div class="mb-4">
            <div class="font-semibold text-900 mb-3">Médias da turma por matéria</div>
            <div class="flex flex-wrap gap-3">
                <div
                    v-for="subject in displayedSubjects"
                    :key="subject.id"
                    class="card mb-0 grades-overview-stat-card"
                >
                    <div class="flex justify-between gap-3 align-items-start">
                        <div class="min-w-0 flex-1">
                            <span class="block text-500 font-medium mb-2 text-sm" :title="subject.label">{{ subject.label }}</span>
                            <div class="text-900 font-semibold text-2xl leading-none">
                                {{ formatGrade(subjectAverageMap.get(subject.id)) }}
                            </div>
                        </div>
                        <div
                            class="flex items-center justify-center bg-primary-100 dark:bg-primary-400/10 rounded-border shrink-0"
                            style="width: 2.5rem; height: 2.5rem"
                        >
                            <i class="pi pi-chart-bar text-primary-500 text-xl" />
                        </div>
                    </div>
                    <span class="block text-500 text-xs mt-3">Média da turma no período</span>
                </div>
            </div>
        </div>

        <DataTable :value="studentRows" :loading="loading" responsiveLayout="scroll" stripedRows size="small">
            <template #empty>Nenhuma nota encontrada para os filtros selecionados.</template>

            <Column field="studentName" header="Aluno" frozen style="min-width: 220px">
                <template #body="slotProps">
                    <div class="font-medium">{{ slotProps.data.studentName }}</div>
                </template>
            </Column>

            <Column
                v-for="subject in displayedSubjects"
                :key="subject.id"
                :header="subject.label"
                style="min-width: 140px; text-align: center"
            >
                <template #body="slotProps">
                    <div class="inline-flex flex-column align-items-center gap-1">
                        <Tag
                            :value="formatGrade(slotProps.data.subjectGrades[subject.id].average)"
                            :severity="gradeTagSeverity(slotProps.data.subjectGrades[subject.id].average)"
                        />
                        <button
                            v-if="slotProps.data.subjectGrades[subject.id].assessments > 0"
                            type="button"
                            class="block text-center border-none bg-transparent p-0 cursor-pointer text-primary underline text-sm m-0 font-inherit"
                            v-tooltip.top="'Ver nome, peso e nota de cada avaliação'"
                            @click="
                                openGradeDetails(
                                    slotProps.data.enrollmentId,
                                    subject.id,
                                    slotProps.data.studentName,
                                    subject.label,
                                    slotProps.data.subjectGrades[subject.id].assessments
                                )
                            "
                        >
                            {{ slotProps.data.subjectGrades[subject.id].assessments }} avaliação(ões)
                        </button>
                        <small v-else class="block text-500 text-center">
                            {{ slotProps.data.subjectGrades[subject.id].assessments }} avaliação(ões)
                        </small>
                    </div>
                </template>
            </Column>

            <Column header="Média Geral" style="min-width: 120px; text-align: center">
                <template #body="slotProps">
                    <strong>{{ formatGrade(slotProps.data.generalAverage) }}</strong>
                </template>
            </Column>
        </DataTable>

        <template #footer>
            <Button label="Fechar" icon="pi pi-times" class="p-button-text" @click="emit('update:visible', false)" />
        </template>
    </Dialog>

    <Dialog
        v-model:visible="detailsVisible"
        :header="detailsTitle"
        :modal="true"
        maximizable
        appendTo="body"
        :style="{ width: '520px', maxWidth: '95vw' }"
    >
        <p class="text-500 text-sm mb-3 m-0">Avaliações lançadas neste período para a matéria selecionada.</p>
        <DataTable :value="detailRows" responsiveLayout="scroll" stripedRows size="small">
            <template #empty>Nenhuma avaliação encontrada.</template>
            <Column field="name" header="Avaliação" sortable style="min-width: 160px" />
            <Column field="weight" header="Peso" style="width: 90px; text-align: center">
                <template #body="slotProps">
                    {{ slotProps.data.weight ?? 1 }}
                </template>
            </Column>
            <Column field="value" header="Nota" style="width: 100px; text-align: center">
                <template #body="slotProps">
                    <Tag
                        :value="String(slotProps.data.value)"
                        :severity="gradeTagSeverity(Number(slotProps.data.value))"
                    />
                </template>
            </Column>
            <Column field="date" header="Data" style="width: 120px">
                <template #body="slotProps">
                    {{ slotProps.data.date ? new Date(slotProps.data.date).toLocaleDateString('pt-BR') : '—' }}
                </template>
            </Column>
        </DataTable>
        <template #footer>
            <Button
                label="Exportar CSV"
                icon="pi pi-download"
                class="p-button-text"
                :disabled="!detailRows.length"
                @click="exportDetailRowsCsv"
            />
            <Button label="Fechar" icon="pi pi-times" class="p-button-text" @click="detailsVisible = false" />
        </template>
    </Dialog>
</template>

<style scoped>
.grades-overview-stat-card {
    flex: 1 1 12rem;
    min-width: 12rem;
    max-width: 100%;
}
</style>

<style>
/* Conteúdo rolável quando o painel principal está maximizado */
.grades-overview-dialog .p-dialog-content {
    overflow: auto;
}
</style>

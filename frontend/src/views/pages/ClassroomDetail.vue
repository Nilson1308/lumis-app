<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/service/api';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import StudentViewDialog from '@/components/StudentViewDialog.vue';
import ClassroomSchedule from '@/components/ClassroomSchedule.vue';
import ClassroomGradesOverviewDialog from '@/components/ClassroomGradesOverviewDialog.vue';

const authStore = useAuthStore();

// Import necessário para navegar para o aluno futuramente
const route = useRoute();
const router = useRouter();
const toast = useToast();
const activeTab = ref(0);
/** Índice do separador «Grade Horária» no TabView (0=Alunos, 1=Corpo docente, 2=Grade). */
const SCHEDULE_TAB_INDEX = 2;

const showClassroomSchedule = computed(
    () => Boolean(data.value.classroom?.id) && Number(activeTab.value) === SCHEDULE_TAB_INDEX
);

const loading = ref(true);
const classroomId = route.params.id;
const data = ref({
    classroom: {},
    stats: { total_students: 0, total_subjects: 0 }, // Valores padrão para não quebrar
    students: [],
    faculty: []
});

const showStudentDialog = ref(false);
const selectedStudentId = ref(null);
const periods = ref([]);
const assignments = ref([]);
const classroomEnrollments = ref([]);
const selectedPeriod = ref(null);
const selectedEnrollmentId = ref(null);
const loadingPdf = ref(false);
const academicDialogVisible = ref(false);
const reportsDialogVisible = ref(false);
const periodStorageKey = computed(() => `classroom-detail:${classroomId}:selected-period`);

const isCoordinatorAccess = computed(() => authStore.isCoordinator || authStore.isAdmin || authStore.isSecretary);

/** Grade horária: só gestão escolar edita; professores e responsáveis só veem. */
const scheduleReadOnly = computed(() => !authStore.canEditClassSchedule);

const loadDashboard = async () => {
    loading.value = true;
    try {
        const response = await api.get(`classrooms/${classroomId}/dashboard/`);
        data.value = response.data;
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Erro ao carregar turma.', life: 3000 });
        router.push('classrooms');
    } finally {
        loading.value = false;
    }
};

const loadAcademicDependencies = async () => {
    if (!isCoordinatorAccess.value) return;
    try {
        const [periodsRes, assignmentsRes, enrollmentsRes] = await Promise.all([
            api.get('periods/'),
            api.get(`assignments/?classroom=${classroomId}&page_size=1000`),
            api.get(`enrollments/?classroom=${classroomId}&page_size=1000`)
        ]);

        periods.value = periodsRes.data.results || periodsRes.data || [];
        assignments.value = (assignmentsRes.data.results || assignmentsRes.data || []).map((a) => ({
            id: a.id,
            label: `${a.subject_name} - ${a.teacher_name || 'Sem professor'}`,
            subjectId: a.subject,
            subjectName: a.subject_name,
            teacherName: a.teacher_name || 'Sem professor'
        }));
        classroomEnrollments.value = (enrollmentsRes.data.results || enrollmentsRes.data || []).map((e) => ({
            id: e.id,
            label: e.student_name
        }));

        const savedPeriod = Number(localStorage.getItem(periodStorageKey.value));
        const hasSaved = periods.value.some((p) => p.id === savedPeriod);
        const activePeriod = periods.value.find((p) => p.is_active);
        selectedPeriod.value = hasSaved ? savedPeriod : (activePeriod?.id || periods.value[0]?.id || null);
    } catch (e) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Não foi possível carregar ações pedagógicas.', life: 3000 });
    }
};

const goBack = () => {
    // Se for professor, volta para minhas turmas, senão para lista de turmas
    if (authStore.isTeacher && !authStore.isCoordinator && !authStore.isAdmin) {
        router.push('/teacher/classes');
    } else {
        router.push('/classrooms');
    }
};

const openStudent = (studentId) => {
    selectedStudentId.value = studentId;
    showStudentDialog.value = true;
};

const openAcademicDialog = () => {
    academicDialogVisible.value = true;
};

const openReportsDialog = () => {
    reportsDialogVisible.value = true;
};

const openReportPdf = async (type) => {
    if (!selectedPeriod.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Selecione o período.', life: 3000 });
        return;
    }
    loadingPdf.value = true;
    try {
        const endpoint = type === 'diary' ? 'reports/diary-pdf/' : 'reports/attendance-pdf/';
        const { data: blob } = await api.get(endpoint, {
            params: { classroom: classroomId, period: selectedPeriod.value },
            responseType: 'blob'
        });
        const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
        window.open(url, '_blank');
        reportsDialogVisible.value = false;
        setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao gerar relatório PDF.', life: 3000 });
    } finally {
        loadingPdf.value = false;
    }
};

const openStudentReportCardPdf = async () => {
    if (!selectedEnrollmentId.value) {
        toast.add({ severity: 'warn', summary: 'Atenção', detail: 'Selecione um aluno para o boletim.', life: 3000 });
        return;
    }
    loadingPdf.value = true;
    try {
        let endpoint = `reports/student_card/${selectedEnrollmentId.value}/`;
        if (selectedPeriod.value) {
            endpoint += `?period=${selectedPeriod.value}`;
        }
        const { data: blob } = await api.get(endpoint, { responseType: 'blob' });
        const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
        window.open(url, '_blank');
        reportsDialogVisible.value = false;
        setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
        toast.add({ severity: 'error', summary: 'Erro', detail: 'Falha ao gerar boletim PDF.', life: 3000 });
    } finally {
        loadingPdf.value = false;
    }
};

watch(selectedPeriod, (newValue) => {
    if (newValue && isCoordinatorAccess.value) {
        localStorage.setItem(periodStorageKey.value, String(newValue));
    }
});

function applyTabFromRouteQuery() {
    if (route.query.tab === 'schedule') {
        activeTab.value = SCHEDULE_TAB_INDEX;
    }
}

watch(
    () => [route.params.id, route.query.tab],
    () => {
        applyTabFromRouteQuery();
    },
    { immediate: true }
);

onMounted(() => {
    loadDashboard();
    loadAcademicDependencies();
});
</script>

<template>
    <div class="col-12">
        <div v-if="!loading">
            
            <div class="flex items-center mb-4">
                <Button icon="pi pi-arrow-left" class="p-button-text p-button-rounded mr-2" @click="goBack" />
                <div>
                    <h2 class="font-bold text-900" style="margin-bottom: 0 !important">{{ data.classroom.name }}</h2>
                    <span class="text-500">{{ data.classroom.segment }} • {{ data.classroom.year }}</span>
                </div>
            </div>

            <div v-if="isCoordinatorAccess" class="card mb-4">
                <div class="flex flex-wrap items-center justify-between gap-3">
                    <div class="flex items-center gap-2 text-primary-700 font-semibold">
                        <i class="pi pi-briefcase"></i>
                        <span>Ações da Coordenação</span>
                    </div>
                    <div class="flex flex-wrap items-center gap-2">
                    <Button label="Painel de Notas" icon="pi pi-chart-line" @click="openAcademicDialog" />
                    <Button label="Relatórios PDF" icon="pi pi-file-pdf" severity="secondary" @click="openReportsDialog" />
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-12 gap-8">
                <div class="col-span-12 lg:col-span-6 xl:col-span-3">
                    <div class="card mb-0">
                        <div class="flex justify-between mb-3">
                            <div>
                                <span class="block text-500 font-medium mb-3">Total Alunos</span>
                                <div class="text-900 font-medium text-xl">{{ data.stats.total_students }}</div>
                            </div>
                            <div class="flex items-center justify-center bg-blue-100 rounded-border" style="width: 2.5rem; height: 2.5rem">
                                <i class="pi pi-users text-blue-500 text-xl"></i>
                            </div>
                        </div>
                        <span class="text-green-500 font-medium">100% </span>
                        <span class="text-500">matriculados</span>
                    </div>
                </div>

                <div class="col-span-12 lg:col-span-6 xl:col-span-3">
                    <div class="card mb-0">
                        <div class="flex justify-between mb-3">
                            <div>
                                <span class="block text-500 font-medium mb-3">Matérias/Profs</span>
                                <div class="text-900 font-medium text-xl">{{ data.stats.total_subjects }}</div>
                            </div>
                            <div class="flex items-center justify-center bg-orange-100 rounded-border" style="width: 2.5rem; height: 2.5rem">
                                <i class="pi pi-book text-orange-500 text-xl"></i>
                            </div>
                        </div>
                        <span class="text-500">Grade curricular</span>
                    </div>
                </div>

                <div class="col-span-12 lg:col-span-6 xl:col-span-3">
                    <div class="card mb-0">
                        <div class="flex justify-between mb-3">
                            <div>
                                <span class="block text-500 font-medium mb-3">Presença Média</span>
                                <div class="text-900 font-medium text-xl">{{ data.stats.average_attendance }}%</div>
                            </div>
                            <div class="flex items-center justify-center bg-cyan-100 rounded-border" style="width: 2.5rem; height: 2.5rem">
                                <i class="pi pi-check-circle text-cyan-500 text-xl"></i>
                            </div>
                        </div>
                        <span :class="data.stats.average_attendance > 75 ? 'text-green-500' : 'text-red-500'" class="font-medium">
                            {{ data.stats.average_attendance > 75 ? 'Regular' : 'Atenção' }}
                        </span>
                    </div>
                </div>

                <div class="col-span-12 lg:col-span-6 xl:col-span-3">
                    <div class="card mb-0">
                        <div class="flex justify-between mb-3">
                            <div>
                                <span class="block text-500 font-medium mb-3">Ocorrências</span>
                                <div class="text-900 font-medium text-xl">{{ data.stats.occurrences }}</div>
                            </div>
                            <div class="flex items-center justify-center bg-purple-100 rounded-border" style="width: 2.5rem; height: 2.5rem">
                                <i class="pi pi-exclamation-circle text-purple-500 text-xl"></i>
                            </div>
                        </div>
                        <span class="text-500">registros disciplinares</span>
                    </div>
                </div>
            </div>

            <div class="card mt-4">
                <TabView v-model:activeIndex="activeTab">
                    <TabPanel header="Alunos">
                        <DataTable :value="data.students" responsiveLayout="scroll" :rows="50" :paginator="true">
                            <template #empty>Nenhum aluno matriculado.</template>
                            <Column field="name" header="Nome" sortable>
                                <template #body="slotProps">
                                    <div class="flex items-center gap-2">
                                        <Avatar 
                                            :image="slotProps.data.photo" 
                                            :icon="!slotProps.data.photo ? 'pi pi-user' : null" 
                                            shape="circle" 
                                            size="large"
                                            class="surface-200 text-600"
                                            style="object-fit: cover" 
                                        />
                                        <span class="font-medium">{{ slotProps.data.name }}</span>
                                    </div>
                                </template>
                            </Column>
                            <Column field="status" header="Status">
                                <template #body="slotProps">
                                    <Tag :value="slotProps.data.status" severity="success" />
                                </template>
                            </Column>
                            <Column header="Ações" style="width: 100px">
                                <template #body="slotProps">
                                    <Button icon="pi pi-eye" class="p-button-text p-button-info" @click="openStudent(slotProps.data.id)" v-tooltip.top="'Ver Ficha do Aluno'" />
                                </template>
                            </Column>
                        </DataTable>
                    </TabPanel>

                    <TabPanel header="Corpo Docente">
                        <DataTable :value="data.faculty" responsiveLayout="scroll">
                            <template #empty>Nenhuma atribuição feita.</template>
                            <Column field="subject" header="Matéria" sortable class="font-bold text-primary"></Column>
                            <Column field="teacher" header="Professor" sortable></Column>
                            <Column field="teacher_email" header="Contato"></Column>
                        </DataTable>
                    </TabPanel>

                    <TabPanel header="Grade Horária">
                        <ClassroomSchedule
                            v-if="showClassroomSchedule"
                            :key="data.classroom.id"
                            :classroom-id="data.classroom.id"
                            :read-only="scheduleReadOnly"
                        />
                    </TabPanel>
                </TabView>
            </div>
            <StudentViewDialog 
                v-model:visible="showStudentDialog" 
                :studentId="selectedStudentId" 
            />

            <ClassroomGradesOverviewDialog
                v-model:visible="academicDialogVisible"
                v-model:selectedPeriod="selectedPeriod"
                :classroomId="classroomId"
                :periods="periods"
                :assignments="assignments"
                :enrollments="classroomEnrollments"
            />

            <Dialog v-model:visible="reportsDialogVisible" header="Relatórios PDF" :modal="true" :style="{ width: '560px' }">
                <div class="grid grid-cols-12 gap-3">
                    <div class="col-span-12">
                        <label class="font-bold block mb-2">Período</label>
                        <Dropdown
                            v-model="selectedPeriod"
                            :options="periods"
                            optionLabel="name"
                            optionValue="id"
                            placeholder="Selecione o período"
                            class="w-full"
                            autofocus
                        />
                    </div>
                    <div class="col-span-12 flex flex-wrap gap-2">
                        <Button label="Diário da Turma (PDF)" icon="pi pi-file-pdf" :loading="loadingPdf" :disabled="!selectedPeriod" @click="openReportPdf('diary')" />
                        <Button label="Frequências (PDF)" icon="pi pi-file-pdf" severity="secondary" :loading="loadingPdf" :disabled="!selectedPeriod" @click="openReportPdf('attendance')" />
                    </div>
                    <div class="col-span-12 mt-2">
                        <Divider />
                        <span class="block text-600 mb-2">Boletim individual</span>
                        <Dropdown
                            v-model="selectedEnrollmentId"
                            :options="classroomEnrollments"
                            optionLabel="label"
                            optionValue="id"
                            placeholder="Selecione o aluno"
                            class="w-full"
                            filter
                        />
                    </div>
                </div>
                <template #footer>
                    <Button label="Fechar" icon="pi pi-times" class="p-button-text" @click="reportsDialogVisible = false" />
                    <Button label="Gerar Boletim (PDF)" icon="pi pi-download" :loading="loadingPdf" :disabled="!selectedEnrollmentId" @click="openStudentReportCardPdf" />
                </template>
            </Dialog>
        </div>

        <div v-else class="col-12 flex justify-center items-center" style="height: 50vh">
            <ProgressSpinner />
        </div>
    </div>
</template>
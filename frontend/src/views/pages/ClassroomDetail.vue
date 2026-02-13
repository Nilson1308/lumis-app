<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/service/api';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import StudentViewDialog from '@/components/StudentViewDialog.vue';
import ClassroomSchedule from '@/components/ClassroomSchedule.vue';

const authStore = useAuthStore();

// Import necessário para navegar para o aluno futuramente
const route = useRoute();
const router = useRouter();
const toast = useToast();
const activeTab = ref(0);

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

onMounted(() => {
    loadDashboard();
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
                            :classroomId="data.classroom.id" 
                            :readOnly="authStore.isTeacher && !authStore.isCoordinator && !authStore.isAdmin"
                            v-if="activeTab === 2 && data.classroom.id" 
                        />
                    </TabPanel>
                </TabView>
            </div>
            <StudentViewDialog 
                v-model:visible="showStudentDialog" 
                :studentId="selectedStudentId" 
            />
        </div>

        <div v-else class="col-12 flex justify-center items-center" style="height: 50vh">
            <ProgressSpinner />
        </div>
    </div>
</template>
<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/service/api';

const router = useRouter();
const myClasses = ref([]);
const myContraturnos = ref([]);
const loading = ref(true);

const fetchMyClasses = async () => {
    loading.value = true;
    try {
        const [classesRes, contraturnosRes] = await Promise.all([
            api.get('assignments/my_classes/'),
            api.get('contraturno-classrooms/my_contraturnos/').catch(() => ({ data: [] })) // Ignora erro se não houver contraturnos
        ]);
        myClasses.value = classesRes.data;
        myContraturnos.value = contraturnosRes.data || [];
    } catch (error) {
        console.error("Erro ao carregar turmas", error);
    } finally {
        loading.value = false;
    }
};

const openClassroom = (assignment) => {
    router.push({ 
        name: 'class-gradebook', 
        params: { id: assignment.id } 
    });
};

const openAttendance = (assignment) => {
    router.push({ 
        name: 'class-attendance', 
        params: { id: assignment.id } 
    });
};

const openPlanning = (assignment) => {
    router.push({ 
        name: 'lesson-plans', 
        query: { assignment: assignment.id } 
    });
};

// --- NOVO MÉTODO ---
const openDiary = (assignment) => {
    router.push({
        name: 'class-diary',
        params: { id: assignment.id }
    });
};

const openObservations = (assignment) => {
    router.push({ 
        name: 'teacher-observations', 
        query: { assignment: assignment.id }
    });
};

const openContraturnoAttendance = (contraturno) => {
    router.push({ 
        name: 'contraturno-attendance', 
        params: { id: contraturno.id }
    });
};

const openChecklist = (assignment) => {
    router.push({ 
        name: 'student-checklist', 
        params: { id: assignment.id }
    });
};

const openClassroomDetail = (assignment) => {
    router.push({ 
        name: 'classroom-detail', 
        params: { id: assignment.classroom }
    });
};

onMounted(() => {
    fetchMyClasses();
});
</script>

<template>
    <div class="mb-4">
        <div class="card mb-0">
            <span class="block text-500 font-medium mb-3">Portal do Professor</span>
            <div class="text-900 font-medium text-xl">Minhas Turmas & Diários</div>
        </div>
    </div>

    <div v-if="loading" class="mb-4">
        <div class="card">Carregando suas turmas...</div>
    </div>

    <div v-else-if="myClasses.length === 0" class="mb-4">
        <div class="card text-center">
            <h3>Você não possui turmas atribuídas.</h3>
            <p>Entre em contato com a coordenação.</p>
        </div>
    </div>

    <div v-else>
        <!-- Turmas Regulares -->
        <div v-if="myClasses.length > 0" class="mb-4">
            <h3 class="mb-3">Minhas Turmas</h3>
            <div class="grid grid-cols-12 gap-6">
                <div class="col-span-12 lg:col-span-3 xl:col-span-3" v-for="item in myClasses" :key="item.id">
                    <div class="card h-full flex flex-col">
                        <div class="flex justify-between mb-3">
                            <div class="flex-1">
                                <span class="block text-500 font-medium mb-3">{{ item.subject_name }}</span>
                                <div class="text-900 font-medium text-xl">{{ item.classroom_name }}</div>
                            </div>
                            <div class="flex items-center gap-2">
                                <Button 
                                    icon="pi pi-info-circle" 
                                    class="p-button-text p-button-rounded p-button-sm p-button-secondary"
                                    v-tooltip.top="'Ver detalhes da turma'"
                                    @click="openClassroomDetail(item)"
                                />
                                <div class="flex items-center justify-center bg-purple-50 dark:bg-purple-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                                    <i class="pi pi-book text-purple-500 text-xl"></i>
                                </div>
                            </div>
                        </div>
                        
                        <Divider/>
                        
                        <div class="mt-auto grid grid-cols-2 gap-2">
                            <div class="col-span-2 relative">
                                <Button 
                                    label="Feedbacks / Obs" 
                                    icon="pi pi-envelope" 
                                    class="p-button-outlined w-full p-button-secondary p-button-sm" 
                                    @click="openObservations(item)"
                                />
                                <span v-if="item.unread_count > 0" 
                                      class="absolute -top-2 -right-2 bg-red-500 text-white text-xs font-bold px-2 py-1 border-round-2xl shadow-1">
                                    {{ item.unread_count }}
                                </span>
                            </div>

                            <Button 
                                label="Notas" 
                                icon="pi pi-pencil" 
                                class="p-button-outlined p-button-sm" 
                                @click="openClassroom(item)" 
                            />
                            
                            <Button 
                                label="Chamada" 
                                icon="pi pi-calendar-plus" 
                                class="p-button-outlined p-button-sm" 
                                @click="openAttendance(item)" 
                            />
                            
                            <div class="col-span-2 relative">
                                <Button
                                    label="Diário de Classe"
                                    icon="pi pi-bookmark"
                                    class="p-button-outlined p-button-sm"
                                    @click="openDiary(item)"
                                    fluid
                                />
                            </div>
                            <div class="col-span-2 relative">
                                <Button
                                    label="Planejamento Semanal" 
                                    icon="pi pi-list" 
                                    class="p-button-outlined p-button-sm" 
                                    @click="openPlanning(item)"
                                    fluid
                                />
                            </div>
                            <div class="col-span-2 relative">
                                <Button
                                    label="Checklist Diário" 
                                    icon="pi pi-check-square" 
                                    class="p-button-outlined p-button-sm p-button-help" 
                                    @click="openChecklist(item)"
                                    fluid
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Contraturnos -->
        <div v-if="myContraturnos.length > 0" class="mb-4">
            <h3 class="mb-3">Meus Contraturnos</h3>
            <div class="grid grid-cols-12 gap-6">
                <div class="col-span-12 lg:col-span-3 xl:col-span-3" v-for="item in myContraturnos" :key="item.id">
                    <div class="card h-full flex flex-col">
                        <div class="flex justify-between mb-3">
                            <div>
                                <span class="block text-500 font-medium mb-3">Contraturno</span>
                                <div class="text-900 font-medium text-xl">{{ item.classroom_name }}</div>
                                <div class="text-600 text-sm mt-1">{{ item.contraturno_period_display }}</div>
                            </div>
                            <div class="flex items-center justify-center bg-blue-50 dark:bg-blue-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                                <i class="pi pi-clock text-blue-500 text-xl"></i>
                            </div>
                        </div>
                        
                        <Divider/>
                        
                        <div class="mt-auto">
                            <Button 
                                label="Chamada do Contraturno" 
                                icon="pi pi-calendar-plus" 
                                class="p-button-outlined w-full p-button-sm p-button-info" 
                                @click="openContraturnoAttendance(item)"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
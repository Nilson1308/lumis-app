<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router'; // Para navegar ao clicar no card
import api from '@/service/api';

const router = useRouter();
const myClasses = ref([]);
const loading = ref(true);

const fetchMyClasses = async () => {
    loading.value = true;
    try {
        // Chama a rota personalizada que criamos agora
        const response = await api.get('assignments/my_classes/');
        myClasses.value = response.data;
    } catch (error) {
        console.error("Erro ao carregar turmas", error);
    } finally {
        loading.value = false;
    }
};

const openClassroom = (assignment) => {
    // Agora navega para a rota real usando o ID da atribuição
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

onMounted(() => {
    fetchMyClasses();
});
</script>

<template>
    <div class="mb-4">
        <div class="card mb-0">
            <div class="flex justify-content-between mb-3">
                <span class="block text-500 font-medium mb-3">Portal do Professor</span>
            </div>
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

    <div v-else class="grid grid-cols-12 gap-6">
        <div class="col-span-12 lg:col-span-4 xl:col-span-4" v-for="item in myClasses" :key="item.id">
            <div class="card" @click="openClassroom(item)">
                <div class="flex justify-between mb-3">
                    <div>
                        <span class="block text-500 font-medium mb-3">{{ item.subject_name }}</span>
                        <div class="text-900 font-medium text-xl">{{ item.classroom_name }}</div>
                    </div>
                    <div class="flex items-center justify-center bg-purple-50 dark:bg-purple-400/10 rounded-border" style="width: 2.5rem; height: 2.5rem">
                        <i class="pi pi-book text-purple-500 text-xl"></i>
                    </div>
                </div>
                <Divider/>
                <div class="mt-auto flex gap-2">
                    <Button 
                        label="Notas" 
                        icon="pi pi-pencil" 
                        class="p-button-outlined flex-1" 
                        @click="openClassroom(item)" 
                    />
                    <Button 
                        label="Chamada" 
                        icon="pi pi-calendar-plus" 
                        class="p-button-outlined flex-1" 
                        @click="openAttendance(item)" 
                    />
                </div>
            </div>
        </div>
    </div>
</template>
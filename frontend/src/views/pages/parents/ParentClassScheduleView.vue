<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/service/api';
import ClassroomSchedule from '@/components/ClassroomSchedule.vue';

const route = useRoute();
const studentId = computed(() => Number(route.params.id));
const classroomId = ref(null);
const studentName = ref('');
const loading = ref(true);
const errorMsg = ref('');

onMounted(async () => {
    try {
        const { data } = await api.get('students/my-children/');
        const child = data.find((c) => Number(c.id) === studentId.value);
        if (!child) {
            errorMsg.value = 'Aluno não encontrado ou sem vínculo com a sua conta.';
            return;
        }
        studentName.value = child.name || '';
        if (!child.classroom_id) {
            errorMsg.value = 'Este aluno ainda não tem turma atribuída.';
            return;
        }
        classroomId.value = child.classroom_id;
    } catch {
        errorMsg.value = 'Não foi possível carregar os dados.';
    } finally {
        loading.value = false;
    }
});
</script>

<template>
    <div class="p-4">
        <div class="mb-4">
            <span class="text-500 text-sm block mb-1">Portal da família</span>
            <h1 class="text-2xl font-semibold text-900 m-0">Grade horária</h1>
            <p v-if="studentName" class="text-600 mt-2 mb-0">{{ studentName }}</p>
        </div>

        <div v-if="loading" class="card p-4 text-600">A carregar…</div>
        <div v-else-if="errorMsg" class="card p-4 text-orange-700">{{ errorMsg }}</div>
        <ClassroomSchedule v-else :classroom-id="classroomId" :read-only="true" />
    </div>
</template>

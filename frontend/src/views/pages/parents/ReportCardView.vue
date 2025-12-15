<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/service/api';

const route = useRoute();
const router = useRouter();
const grades = ref([]);
const loading = ref(true);
const studentName = ref('');

onMounted(async () => {
    try {
        const studentId = route.params.id;
        // Pega as notas
        const response = await api.get(`students/${studentId}/report-card/`);
        grades.value = response.data;
        
        // Opcional: Pegar nome do aluno de algum lugar ou cache, 
        // ou fazer um request simples get(`students/${studentId}/`) se quiser exibir no título
    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
});

const goBack = () => router.push({ name: 'parent-dashboard' });
</script>

<template>
    <div class="card">
        <div class="flex justify-content-between align-items-center mb-4">
            <h5 class="m-0">Boletim Escolar</h5>
            <Button label="Voltar" icon="pi pi-arrow-left" class="p-button-text" @click="goBack" />
        </div>

        <DataTable :value="grades" :loading="loading" responsiveLayout="scroll" stripedRows>
            <Column field="subject" header="Disciplina" sortable></Column>
            <Column field="1" header="1º Bimestre" class="text-center font-bold text-blue-600"></Column>
            <Column field="2" header="2º Bimestre" class="text-center font-bold text-blue-600"></Column>
            <Column field="3" header="3º Bimestre" class="text-center font-bold text-blue-600"></Column>
            <Column field="4" header="4º Bimestre" class="text-center font-bold text-blue-600"></Column>
            <Column field="final" header="Média Final" class="text-center">
                <template #body="slotProps">
                    <span :class="{'text-red-500 font-bold': slotProps.data.final < 6 && slotProps.data.final !== '-', 'text-green-500 font-bold': slotProps.data.final >= 6}">
                        {{ slotProps.data.final }}
                    </span>
                </template>
            </Column>
        </DataTable>
    </div>
</template>
<script setup>
import { ref, watch } from 'vue';
import api from '@/service/api';

const props = defineProps({
    visible: Boolean,
    studentId: Number
});

const emit = defineEmits(['update:visible']);
const localVisible = ref(false);
const loading = ref(true);
const student = ref({});

// Monitora a abertura do dialog para carregar os dados
watch(() => props.visible, async (newVal) => {
    localVisible.value = newVal;
    if (newVal && props.studentId) {
        await loadStudentDetails();
    }
});

const loadStudentDetails = async () => {
    loading.value = true;
    try {
        const res = await api.get(`students/${props.studentId}/`);
        student.value = res.data;
    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
};

const close = () => {
    emit('update:visible', false);
};
</script>

<template>
    <Dialog 
        v-model:visible="localVisible" 
        header="Ficha do Aluno" 
        :modal="true" 
        :style="{ width: '700px' }" 
        @hide="close"
        class="p-fluid"
    >
        <div v-if="!loading">
            <div class="flex flex-col items-center mb-5 surface-50 p-4 border-round">
                <Avatar 
                    :image="student.photo || null" 
                    :icon="!student.photo ? 'pi pi-user' : null"
                    size="xlarge" 
                    shape="circle" 
                    class="w-6rem h-6rem mb-3 surface-200"
                    style="object-fit: cover"
                />
                <h2 class="m-0 text-900">{{ student.name }}</h2>
                <span class="text-500">Matrícula: {{ student.registration_number }}</span>
                <Tag :value="student.is_full_time ? 'Integral' : 'Parcial'" class="mt-2" />
            </div>

            <div class="grid grid-cols-12 gap-8">
                <div class="col-span-12 lg:col-span-6">
                    <p class="font-bold mb-2 border-bottom-1 surface-border pb-1">Dados Pessoais</p>
                    <div class="flex justify-between mb-2">
                        <span class="text-500">Nascimento:</span>
                        <span>{{ student.birth_date ? new Date(student.birth_date).toLocaleDateString('pt-BR') : 'N/A' }}</span>
                    </div>
                    <div class="flex justify-between mb-2">
                        <span class="text-500">CPF:</span>
                        <span>{{ student.cpf || 'Não inf.' }}</span>
                    </div>
                    <div class="flex justify-between mb-2">
                        <span class="text-500">Turma/Período:</span>
                        <span>{{ student.period === 'MORNING' ? 'Manhã' : 'Tarde' }}</span>
                    </div>
                </div>

                <div class="col-span-12 lg:col-span-6">
                    <p class="font-bold mb-2 border-bottom-1 surface-border pb-1">Saúde & Segurança</p>
                    <div class="mb-2">
                        <span class="text-500 block">Contato Emergência:</span>
                        <span class="font-medium text-900">{{ student.emergency_contact || 'Não informado' }}</span>
                    </div>
                    <div v-if="student.allergies" class="mb-2">
                        <span class="text-red-500 font-bold block">Alergias:</span>
                        <span>{{ student.allergies }}</span>
                    </div>
                    <div v-if="student.medications" class="mb-2">
                        <span class="text-blue-500 font-bold block">Medicamentos:</span>
                        <span>{{ student.medications }}</span>
                    </div>
                </div>

                <div class="col-span-12 mt-3" v-if="student.guardians_details && student.guardians_details.length">
                     <p class="font-bold mb-2 border-bottom-1 surface-border pb-1">Responsáveis</p>
                     <ul class="list-none p-0 m-0">
                        <li v-for="g in student.guardians_details" :key="g.id" class="mb-3 p-2 surface-50 border-round">
                            <div class="flex items-center gap-2 mb-1">
                                <i class="pi pi-user text-primary"></i>
                                <span class="font-bold text-900">{{ g.name }}</span>
                            </div>
                            
                            <div class="flex flex-column ml-4 text-sm text-600 gap-1">
                                <span v-if="g.phone">
                                    <i class="pi pi-whatsapp text-green-500 mr-1 text-xs"></i> 
                                    {{ g.phone }}
                                </span>
                                <span v-if="g.email">
                                    <i class="pi pi-envelope text-500 mr-1 text-xs"></i> 
                                    {{ g.email }}
                                </span>
                            </div>
                        </li>
                     </ul>
                </div>
                
                <div class="col-span-12 mt-3" v-else-if="student.guardians && student.guardians.length">
                    <p class="text-sm text-500">Responsáveis vinculados (IDs: {{ student.guardians.join(', ') }}). Detalhes indisponíveis.</p>
                </div>
            </div>
        </div>
        
        <div v-else class="flex justify-center p-4">
            <ProgressSpinner />
        </div>

        <template #footer>
            <Button label="Fechar" icon="pi pi-times" class="p-button-text" @click="close" />
        </template>
    </Dialog>
</template>

<style scoped>
.p-avatar-xl{
    width: 8rem !important;
    height: 8rem !important;
}
</style>
<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
    attendanceDates: {
        type: Array,
        default: () => []
    },
    currentDate: {
        type: Date,
        required: true
    }
});

const emit = defineEmits(['update:currentDate']);

const displayedDate = ref(new Date(props.currentDate));

const formatDate = (date) => {
    if (!date) return '';
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const getWeekDays = computed(() => {
    const current = new Date(displayedDate.value);
    const day = current.getDay();
    const diff = current.getDate() - day + (day === 0 ? -6 : 1); // Segunda-feira
    const monday = new Date(current.setDate(diff));
    
    const week = [];
    for (let i = 0; i < 7; i++) {
        const date = new Date(monday);
        date.setDate(monday.getDate() + i);
        week.push(date);
    }
    return week;
});

const getWeekRange = computed(() => {
    const week = getWeekDays.value;
    if (week.length === 0) return '';
    const first = week[0];
    const last = week[6];
    return `${first.getDate()}/${first.getMonth() + 1} - ${last.getDate()}/${last.getMonth() + 1}`;
});

const previousWeek = () => {
    const newDate = new Date(displayedDate.value);
    newDate.setDate(newDate.getDate() - 7);
    displayedDate.value = newDate;
    emit('update:currentDate', newDate);
};

const nextWeek = () => {
    const newDate = new Date(displayedDate.value);
    newDate.setDate(newDate.getDate() + 7);
    displayedDate.value = newDate;
    emit('update:currentDate', newDate);
};

const goToCurrentWeek = () => {
    displayedDate.value = new Date();
    emit('update:currentDate', displayedDate.value);
};

// Atualiza quando a prop currentDate mudar externamente
watch(() => props.currentDate, (newDate) => {
    displayedDate.value = new Date(newDate);
});

const selectDate = (date) => {
    displayedDate.value = date;
    emit('update:currentDate', date);
};

const isDateRecorded = (date) => {
    const dateStr = formatDate(date);
    // Compara strings de data (YYYY-MM-DD)
    return props.attendanceDates.some(d => {
        const dStr = typeof d === 'string' ? d : formatDate(d);
        return dStr === dateStr;
    });
};

const isToday = (date) => {
    const today = new Date();
    return formatDate(date) === formatDate(today);
};

const getDayLabel = (date) => {
    const days = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
    return days[date.getDay()];
};
</script>

<template>
    <div class="weekly-calendar">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-2 gap-2">
            <div class="flex items-center gap-1 md:gap-2 flex-wrap">
                <Button 
                    icon="pi pi-chevron-left" 
                    class="p-button-text p-button-sm p-button-rounded"
                    @click="previousWeek"
                    v-tooltip.top="'Semana anterior'"
                />
                <span class="text-xs md:text-sm font-semibold whitespace-nowrap">Chamadas da Semana</span>
                <span class="text-xs text-600 hidden md:inline">({{ getWeekRange }})</span>
                <Button 
                    icon="pi pi-chevron-right" 
                    class="p-button-text p-button-sm p-button-rounded"
                    @click="nextWeek"
                    v-tooltip.top="'Próxima semana'"
                />
                <Button 
                    icon="pi pi-calendar" 
                    class="p-button-text p-button-sm p-button-rounded"
                    @click="goToCurrentWeek"
                    v-tooltip.top="'Ir para semana atual'"
                />
            </div>
            <div class="flex gap-2 text-xs flex-wrap">
                <div class="flex items-center gap-1">
                    <div class="w-2 h-2 md:w-3 md:h-3 rounded-circle bg-green-500"></div>
                    <span class="hidden sm:inline">Realizada</span>
                </div>
                <div class="flex items-center gap-1">
                    <div class="w-2 h-2 md:w-3 md:h-3 rounded-circle bg-gray-400"></div>
                    <span class="hidden sm:inline">Não realizada</span>
                </div>
            </div>
        </div>
        <div class="flex gap-1 overflow-x-auto pb-2">
            <div 
                v-for="(day, index) in getWeekDays" 
                :key="index"
                class="flex-1 min-w-[3rem] text-center p-1 md:p-2 border-round cursor-pointer transition-colors"
                :class="{
                    'bg-green-100 dark:bg-green-900': isDateRecorded(day),
                    'bg-gray-100 dark:bg-gray-800': !isDateRecorded(day),
                    'border-2 border-primary': isToday(day)
                }"
                @click="selectDate(day)"
            >
                <div class="text-xs font-semibold">{{ getDayLabel(day) }}</div>
                <div class="text-xs mt-1">{{ day.getDate() }}/{{ day.getMonth() + 1 }}</div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.weekly-calendar {
    padding: 0.5rem;
}

/* Mobile optimizations */
@media (max-width: 640px) {
    .weekly-calendar {
        padding: 0.25rem;
    }
}

/* Scrollbar styling for mobile */
.weekly-calendar .flex.overflow-x-auto {
    scrollbar-width: thin;
    scrollbar-color: #cbd5e1 transparent;
}

.weekly-calendar .flex.overflow-x-auto::-webkit-scrollbar {
    height: 4px;
}

.weekly-calendar .flex.overflow-x-auto::-webkit-scrollbar-track {
    background: transparent;
}

.weekly-calendar .flex.overflow-x-auto::-webkit-scrollbar-thumb {
    background-color: #cbd5e1;
    border-radius: 2px;
}
</style>

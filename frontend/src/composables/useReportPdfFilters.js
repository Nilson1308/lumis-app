import { ref, computed, watch } from 'vue';
import { useToast } from 'primevue/usetoast';

const MAX_RANGE_DAYS = 366;

const formatDateForApi = (date) => {
    if (!date) return '';
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const parseApiDate = (value) => {
    if (!value) return null;
    const [year, month, day] = String(value).split('-').map(Number);
    return new Date(year, month - 1, day);
};

const daysBetweenInclusive = (start, end) => {
    const ms = end.getTime() - start.getTime();
    return Math.floor(ms / (1000 * 60 * 60 * 24)) + 1;
};

/**
 * Filtros compartilhados para relatórios PDF (período letivo + intervalo de datas).
 */
export function buildReportParamsFromFilters({ classroomId, periodId, dateRange }) {
    const params = {
        classroom: classroomId,
        period: periodId,
    };
    if (dateRange?.[0] && dateRange?.[1]) {
        params.start_date = formatDateForApi(dateRange[0]);
        params.end_date = formatDateForApi(dateRange[1]);
    }
    return params;
}

export const extractPdfError = (error) => {
    const data = error.response?.data;
    if (data instanceof Blob) {
        return 'Falha ao gerar PDF.';
    }
    return data?.detail || data?.error || data?.message || 'Falha ao gerar PDF.';
};

export function validateReportFiltersState({
    toast,
    classroomId,
    periodId,
    dateRange,
    requireClassroom = true,
}) {
    if (requireClassroom && !classroomId) {
        toast.add({
            severity: 'warn',
            summary: 'Atenção',
            detail: 'Selecione a turma.',
            life: 3000,
        });
        return false;
    }
    if (!periodId) {
        toast.add({
            severity: 'warn',
            summary: 'Atenção',
            detail: 'Selecione o período letivo.',
            life: 3000,
        });
        return false;
    }
    if (!dateRange?.[0] || !dateRange?.[1]) {
        toast.add({
            severity: 'warn',
            summary: 'Atenção',
            detail: 'Selecione o intervalo de datas (de/até).',
            life: 3000,
        });
        return false;
    }
    const start = new Date(dateRange[0]);
    const end = new Date(dateRange[1]);
    if (end < start) {
        toast.add({
            severity: 'warn',
            summary: 'Atenção',
            detail: 'A data final deve ser igual ou posterior à inicial.',
            life: 3000,
        });
        return false;
    }
    if (daysBetweenInclusive(start, end) > MAX_RANGE_DAYS) {
        toast.add({
            severity: 'warn',
            summary: 'Atenção',
            detail: `O intervalo máximo é de ${MAX_RANGE_DAYS} dias.`,
            life: 4000,
        });
        return false;
    }
    return true;
}

export function useReportPdfFilters(periodsRef) {
    const toast = useToast();
    const selectedPeriod = ref(null);
    const dateRange = ref(null);

    const selectedPeriodMeta = computed(() =>
        (periodsRef.value || []).find((p) => p.id === selectedPeriod.value)
    );

    const syncDateRangeFromPeriod = () => {
        const period = selectedPeriodMeta.value;
        if (period?.start_date && period?.end_date) {
            dateRange.value = [parseApiDate(period.start_date), parseApiDate(period.end_date)];
        }
    };

    watch(selectedPeriod, () => {
        syncDateRangeFromPeriod();
    });

    const validateReportFilters = ({ requireClassroom = true, classroomId = null } = {}) =>
        validateReportFiltersState({
            toast,
            classroomId,
            periodId: selectedPeriod.value,
            dateRange: dateRange.value,
            requireClassroom,
        });

    const buildReportParams = (classroomId) =>
        buildReportParamsFromFilters({
            classroomId,
            periodId: selectedPeriod.value,
            dateRange: dateRange.value,
        });

    return {
        selectedPeriod,
        dateRange,
        selectedPeriodMeta,
        syncDateRangeFromPeriod,
        validateReportFilters,
        buildReportParams,
        extractPdfError,
        formatDateForApi,
    };
}

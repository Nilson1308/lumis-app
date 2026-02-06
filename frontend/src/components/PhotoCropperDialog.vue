<script setup>
import { ref, watch } from 'vue';
import { Cropper } from 'vue-advanced-cropper';
import 'vue-advanced-cropper/dist/style.css';

const props = defineProps({
    visible: Boolean,
    imageSrc: String, // A imagem temporária carregada do computador
});

const emit = defineEmits(['update:visible', 'save']);

const localVisible = ref(false);
const cropperRef = ref(null);

watch(() => props.visible, (val) => {
    localVisible.value = val;
});

const close = () => {
    emit('update:visible', false);
};

const saveCrop = () => {
    const { canvas } = cropperRef.value.getResult();
    if (canvas) {
        // Converte o canvas para Blob (arquivo)
        canvas.toBlob((blob) => {
            // Emite o arquivo pronto para quem chamou
            emit('save', blob);
            close();
        }, 'image/jpeg', 0.8); // 80% de qualidade JPG
    }
};
</script>

<template>
    <Dialog 
        v-model:visible="localVisible" 
        header="Ajustar Foto" 
        :modal="true" 
        :style="{ width: '500px' }"
        @hide="close"
    >
        <div class="flex flex-column align-items-center">
            <div class="cropper-wrapper w-full" style="height: 400px; background-color: #f0f0f0;">
                <Cropper
                    ref="cropperRef"
                    class="cropper"
                    :src="imageSrc"
                    :stencil-props="{ aspectRatio: 1/1 }" 
                    :resize-image="{ adjustStencil: false }"
                />
                </div>
            
            <div class="mt-3 text-sm text-500">
                Arraste e zoom para ajustar o rosto no centro.
            </div>
        </div>

        <template #footer>
            <Button label="Cancelar" icon="pi pi-times" class="p-button-text" @click="close" />
            <Button label="Confirmar Foto" icon="pi pi-check" @click="saveCrop" autofocus />
        </template>
    </Dialog>
</template>

<style scoped>
.cropper {
    height: 100%;
    width: 100%;
}
</style>
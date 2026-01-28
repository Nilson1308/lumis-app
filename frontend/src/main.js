import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

import Aura from '@primeuix/themes/aura';
import PrimeVue from 'primevue/config';
import { definePreset } from '@primeuix/themes';
import ConfirmationService from 'primevue/confirmationservice';
import ToastService from 'primevue/toastservice';

import { updatePreset } from '@primeuix/themes';
import '@/assets/tailwind.css';
import '@/assets/styles.scss';
import 'quill/dist/quill.snow.css';

const app = createApp(App);
app.use(createPinia());
app.use(router);

const LumisPreset = definePreset(Aura, {
    semantic: {
        primary: {
            50: '#faf5ff',
            100: '#f3e8ff',
            200: '#e9d5ff',
            300: '#d8b4fe',
            400: '#c084fc',
            500: '#a855f7',
            600: '#9333ea',
            700: '#7e22ce',
            800: '#6b21a8',
            900: '#581c87',
            950: '#3b0764'
        }
    }
});

app.use(PrimeVue, {
    theme: {
        preset: LumisPreset,
        options: {
            darkModeSelector: '.app-dark'
        }
    }
});

app.use(ToastService);
app.use(ConfirmationService);
app.mount('#app');
import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api/',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    }
});

// INTERCEPTOR DE REQUISIÇÃO (O porteiro de saída)
// Antes de qualquer requisição sair do Vue, esse código roda.
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            // O Django espera: "Bearer <token>"
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// INTERCEPTOR DE RESPOSTA (O porteiro de entrada)
// Se o Backend responder "401 Unauthorized" (Token inválido/vencido), limpamos tudo.
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            // Se der erro de auth, desloga o usuário forçado
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            // Opcional: Redirecionar para login via window.location ou router
            // window.location.href = '/login'; 
        }
        return Promise.reject(error);
    }
);

export default api;
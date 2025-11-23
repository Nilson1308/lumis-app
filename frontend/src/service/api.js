import axios from 'axios';

const api = axios.create({
    baseURL: 'http://127.0.0.1:8000/api/',
    timeout: 5000,
    headers: {
        'Content-Type': 'application/json',
    }
});

// INTERCEPTOR DE REQUISIÇÃO (O porteiro de saída)
// Antes de qualquer requisição sair do Vue, esse código roda.
api.interceptors.request.use(
    (config) => {
        // Tenta pegar o token salvo no LocalStorage
        const token = localStorage.getItem('access_token');
        
        // Se tiver token, injeta no cabeçalho
        if (token) {
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
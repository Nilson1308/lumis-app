# frontend/Dockerfile

# --- Stage 1: Build do Vue ---
FROM node:20-slim as build-stage

WORKDIR /app

# 1. Copia apenas os arquivos de dependência primeiro
COPY package*.json ./

# 2. Instala as dependências (Cache layer)
RUN npm install

# 3. Copia todo o resto do projeto
COPY . .

# --- CORREÇÃO BLINDADA ---
# O comando COPY . . acima pode ter trazido a pasta 'node_modules' do Windows,
# que corrompe o build no Linux. Aqui nós forçamos a remoção dela e reinstalamos
# tudo limpo para garantir binários compatíveis com Linux.
RUN rm -rf node_modules && npm install

# 4. Agora roda o build com certeza de que o ambiente está limpo
RUN npm run build

# --- Stage 2: Produção com Nginx ---
FROM nginx:stable-alpine as production-stage

# Copiar os arquivos compilados do Stage 1
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Remover config padrão
RUN rm /etc/nginx/conf.d/default.conf

# Copiar nossa config customizada
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
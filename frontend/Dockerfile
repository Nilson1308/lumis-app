# --- Stage 1: Build do Vue ---
    FROM node:20-slim as build-stage

    WORKDIR /app
    
    # 1. Manifestos com lockfile versionado (build reproduzível)
    COPY package.json package-lock.json ./
    
    # 2. Instala dependências de forma determinística
    RUN npm ci
    
    # 3. Copia o código fonte (O .dockerignore impede que node_modules do host venha junto)
    COPY . .
    
    # 4. Roda o build
    RUN npm run build
    
    # --- Stage 2: Produção com Nginx ---
    FROM nginx:stable-alpine as production-stage
    
    COPY --from=build-stage /app/dist /usr/share/nginx/html
    RUN rm /etc/nginx/conf.d/default.conf
    COPY nginx/default.conf /etc/nginx/conf.d/default.conf
    
    EXPOSE 80
    CMD ["nginx", "-g", "daemon off;"]
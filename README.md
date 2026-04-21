# Lumis App

Plataforma de gestão escolar com backend em Django/DRF e frontend em Vue 3.

## Visão Geral

- **Arquitetura:** monorepo com `backend` (API), `frontend` (SPA) e `docker-compose.prod.yml` para produção.
- **Objetivo do domínio:** gestão acadêmica completa (notas, frequência, diário, coordenação pedagógica, comunicação e portal da família).
- **Execução em produção:** containers Docker para banco, backend (Gunicorn) e frontend (Nginx).

## Stack Técnica

- **Backend:** Python 3.11, Django 5.1.4, Django REST Framework, JWT (`simplejwt`), PostgreSQL, CORS, WeasyPrint (PDF).
- **Frontend:** Vue 3, Vite, Vue Router, Pinia, Axios, PrimeVue, Tailwind CSS.
- **Infra:** Docker Compose, volumes para `static` e `media`, SSL via Let's Encrypt montado no frontend.

## Estrutura Principal

- `backend/` — API Django + apps de domínio (`academic`, `core`, `coordination`, `communication`)
- `frontend/` — aplicação web Vue
- `docker-compose.prod.yml` — orquestração de produção
- `COMMANDS.md` — manual operacional (deploy, migração, logs, SSL, rotinas)
- `AUTHORIZATION.md` — matriz de autorização da API (por endpoint e método HTTP)

## Pontos de Atenção (Prioridade)

- **Segurança/configuração**
  - produção: `.env` na raiz com `SECRET_KEY` forte, `ALLOWED_HOSTS` explícitos e `DEBUG=False` (ver `COMMANDS.md` secção 8 e `docker-compose.prod.yml`);
  - sensíveis só em variáveis de ambiente, não no Git.
- **Qualidade e testes**
  - cobertura de testes ainda pode crescer (backend e frontend); existe pipeline mínima em `.github/workflows/ci.yml`.
- **Build reprodutível**
  - frontend em produção usa `npm ci` e `package-lock.json` (ver `frontend/Dockerfile`).
- **Autorização**
  - garantir regras no backend (não depender apenas de visibilidade no frontend por perfil).

## Arquivos-Chave para Onboarding

- `backend/setup/settings.py`
- `backend/setup/urls.py`
- `backend/apps/academic/models.py`
- `backend/apps/academic/views.py`
- `backend/apps/core/views.py`
- `backend/apps/coordination/models.py`
- `frontend/src/main.js`
- `frontend/src/router/index.js`
- `frontend/src/stores/auth.js`
- `frontend/src/service/api.js`
- `frontend/package.json`
- `docker-compose.prod.yml`

## Operação

Para comandos de deploy, banco, logs, shell, SSL e rotinas:

- `COMMANDS.md`

Para regras de acesso por perfil na API:

- `AUTHORIZATION.md`

## Evolução Técnica

Roadmap de melhorias por prioridade (segurança, performance e manutenibilidade):

- `ROADMAP.md`

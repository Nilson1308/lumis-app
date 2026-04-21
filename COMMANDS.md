# Manual de Operações - Lumis (Produção)

Este guia reúne os comandos essenciais para operar o projeto em produção usando Docker Compose.

> Todos os comandos abaixo partem da raiz do projeto (onde está `docker-compose.prod.yml`).
> Use `docker compose` (sem hífen). Se seu servidor ainda usa versão antiga, troque por `docker-compose`.

---

## 1) Deploy / Atualização de Código

Quando houver atualização no repositório:

```bash
git pull origin main
docker compose -f docker-compose.prod.yml up --build -d
```

O comando acima:
- reconstrói imagens de backend e frontend,
- aplica o build do frontend durante a imagem,
- sobe/reinicia os containers em background.

---

## 2) Banco de Dados (Django)

### Criar migrações

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py makemigrations
```

### Aplicar migrações

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Criar superusuário

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

---

## 3) Arquivos estáticos

Se necessário (principalmente admin Django sem CSS):

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

---

## 4) Tarefas operacionais (rotinas)

### Notificar planejamentos em atraso

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py notify_late_plans
```

> Observação: esse comando depende de existir no código da versão em produção.
> Se retornar `Unknown command`, revise se a management command está presente no backend.

### Reconciliar bloqueios de envio de planejamento (forçar checagem)

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py reconcile_lesson_plan_guards
```

Esse comando roda a lógica de atraso semanal e cria bloqueios automaticamente para professores em pendência (quando a política estiver ativa em `SchoolAccount`).

Modo simulação (não grava no banco):

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py reconcile_lesson_plan_guards --dry-run
```

Analisar semana específica:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py reconcile_lesson_plan_guards --week-start 2026-04-20
```

### Notificar atraso de relatório semanal (sem bloqueio)

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py notify_late_weekly_reports
```

Esse comando verifica quem não enviou relatório semanal no período anterior e gera notificações para professor e coordenação/admin.

Modo simulação (não grava no banco):

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py notify_late_weekly_reports --dry-run
```

Analisar semana específica:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py notify_late_weekly_reports --week-start 2026-04-20
```

---

## 5) Logs e monitoramento

### Logs de todos os serviços

```bash
docker compose -f docker-compose.prod.yml logs -f
```

### Logs por serviço

```bash
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
docker compose -f docker-compose.prod.yml logs -f db
```

### Status dos containers

```bash
docker compose -f docker-compose.prod.yml ps
```

---

## 6) Acesso shell nos containers

### Backend (Django)

```bash
docker compose -f docker-compose.prod.yml exec backend /bin/bash
```

### Banco (PostgreSQL container)

```bash
docker compose -f docker-compose.prod.yml exec db sh
```

---

## 7) Comandos rápidos de rotina

### Alteração só de código (sem mudança de schema)

```bash
git pull origin main
docker compose -f docker-compose.prod.yml up --build -d
```

### Atualizar apenas o frontend

```bash
git pull origin main
docker compose -f docker-compose.prod.yml up --build -d frontend
```

### Atualizar apenas o backend

```bash
git pull origin main
docker compose -f docker-compose.prod.yml up --build -d backend
```

### Alteração com mudança de banco

```bash
git pull origin main
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Agendar automação semanal (sexta-feira) via crontab

> Executar no host de produção (fora do container), com usuário que tem acesso ao Docker.

```bash
(crontab -l 2>/dev/null; echo "0 7 * * 5 cd /root/lumis-app && /usr/bin/docker compose -f docker-compose.prod.yml exec -T backend python manage.py reconcile_lesson_plan_guards >> /var/log/lumis_plan_guard.log 2>&1") | crontab -
```

Para executar também a verificação de relatório semanal:

```bash
(crontab -l 2>/dev/null; echo "10 7 * * 5 cd /root/lumis-app && /usr/bin/docker compose -f docker-compose.prod.yml exec -T backend python manage.py notify_late_weekly_reports >> /var/log/lumis_weekly_report_guard.log 2>&1") | crontab -
```

Validação:

```bash
crontab -l | grep reconcile_lesson_plan_guards
```

---

## 8) Checklist de deploy seguro (roadmap)

Antes do primeiro deploy ou após alterar segredos:

1. **Arquivo `.env` na raiz** (mesmo diretório que `docker-compose.prod.yml`, não versionado), com pelo menos:
   - `SECRET_KEY` — ver secção *Gerar e aplicar SECRET_KEY* abaixo.
   - `ALLOWED_HOSTS` — domínios reais, separados por vírgula (sem `*` em produção).
   - `DB_PASSWORD` — senha forte; o `docker-compose.prod.yml` usa a mesma variável para o Postgres e para o backend.
   - `DEBUG=False` em produção.
2. **Variáveis injetadas no backend:** o `docker-compose.prod.yml` passa explicitamente `SECRET_KEY`, `DEBUG` e `ALLOWED_HOSTS` a partir do `.env` da raiz (interpolação do Compose). Garanta que editou **esse** ficheiro no servidor.
3. **Após alterar o `.env`**, recrie o backend para carregar variáveis novas:

```bash
docker compose -f docker-compose.prod.yml up -d --force-recreate backend
```

4. **Validação Django** (no container):

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py check
docker compose -f docker-compose.prod.yml exec backend python manage.py check --deploy
```

5. **Rotação de segredos:** ao trocar `SECRET_KEY`, `DB_PASSWORD` ou credenciais de e-mail, atualize o `.env`, execute o passo 3 e, se necessário, invalide sessões/tokens conforme a política da escola.

### Gerar e aplicar `SECRET_KEY`

Gere uma chave longa (não a guarde em repositório nem em tickets públicos):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

No `.env` da raiz, **uma única linha**, sem aspas, por exemplo:

`SECRET_KEY=<cole aqui a saída completa do comando>`

**Não** deixe em produção o texto de exemplo do `.env.example` (frases curtas tipo “troque-por-…”). O Django (`check --deploy`, aviso **W009**) exige chave longa e aleatória (tipicamente 50+ caracteres).

### Interpretação do `python manage.py check --deploy`

| Aviso | Significado habitual | Ação |
|--------|------------------------|------|
| **W009** (`SECRET_KEY` fraca/curta/`django-insecure-`) | Chave inválida ou placeholder | Corrigir o `.env` e recriar o backend (passo 3). |
| **W018** (`DEBUG=True`) | Modo desenvolvimento em produção | `DEBUG=False` no `.env` e recriar o backend. |
| **W008** (`SECURE_SSL_REDIRECT`) | Django não redireciona HTTP→HTTPS | Comum quando o **Nginx** (ou outro proxy) já força HTTPS. Pode ficar **documentado como aceite** se o tráfego público for sempre TLS. |
| **W004** (`SECURE_HSTS_SECONDS`) | HSTS não ativado no Django | Idem: muitas vezes tratado no proxy. **Só** ative HSTS no Django ou no proxy depois de confirmar que **nunca** servirá HTTP em produção (erro bloqueia clientes). |

Critério prático de “pronto”: **sem W009 nem W018**; W004/W008 conforme política da escola e arquitetura (proxy vs Django).

### Problemas comuns: `SECRET_KEY` não muda no container

- **Variável no shell:** se existir `export SECRET_KEY=...` na sessão, o Docker Compose pode usar **esse** valor na interpolação em vez do `.env`. No servidor: `unset SECRET_KEY` e volte a subir o backend.
- **Ficheiro errado:** confirme que editou `~/lumis-app/.env` (raiz do projeto no servidor), não só uma cópia local.
- **Confirmar comprimento** (sem imprimir a chave inteira):

```bash
docker compose -f docker-compose.prod.yml exec backend python -c "import os; k=os.environ.get('SECRET_KEY',''); print('len=', len(k))"
```

Com `secrets.token_urlsafe(50)` o comprimento costuma ser **66–68**.

### Registo interno (roadmap)

Após cada release relevante, registe data, commit e resultado do `check --deploy` (e quais avisos, se houver, foram aceites por decisão documentada).

---

## 9) SSL / Certificado (Let's Encrypt)

Referência do servidor:
- Certificado: `/etc/letsencrypt/live/app.sthomasmogi.com.br/fullchain.pem`
- Chave: `/etc/letsencrypt/live/app.sthomasmogi.com.br/privkey.pem`

Verificar validade:

```bash
sudo certbot certificates
```

Testar renovação (sem efetivar):

```bash
sudo certbot renew --dry-run
```

Como o `docker-compose.prod.yml` monta `/etc/letsencrypt` no serviço `frontend`, após renovação pode ser necessário recarregar o Nginx:

```bash
docker compose -f docker-compose.prod.yml restart frontend
```

---

## 10) Matriz de autorização (API) - ciclo atual

Matriz detalhada (por endpoint e método HTTP) disponível em:

- `AUTHORIZATION.md`

Checklist mínimo de regressão (pré-release):

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py test \
  apps.core.tests.UserViewSetAuthorizationTests \
  apps.academic.tests.AuthorizationHardeningTests \
  apps.academic.tests.AttendanceScheduleRulesTests \
  apps.academic.tests.ParentPortalSecurityTests
```


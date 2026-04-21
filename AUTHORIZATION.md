# Matriz de Autorização da API - Lumis

Documento de referência para regras de acesso por perfil nos endpoints críticos.

## Perfis considerados

- `Coordenação/Admin`: superuser, staff e grupos de gestão (`Coordenadores`, `Coordenação`, `Coordenacao`, `Direção`, `Direcao`, `Diretoria`, `Secretaria`).
- `Professor`: usuário no grupo `Professores`.
- `Responsável`: usuário com `guardian_profile` vinculado.
- `Usuário comum`: autenticado sem perfil de gestão/professor/responsável.

## Regras por domínio

## Core

| Endpoint | Método | Professor | Responsável | Coordenação/Admin | Regra aplicada |
|---|---|---:|---:|---:|---|
| `/api/users/` | `GET/POST` | ❌ | ❌ | ✅ | Gestão de usuários apenas para perfis de poder |
| `/api/users/{id}/` | `PATCH/DELETE` | ❌ | ❌ | ✅ | Gestão de usuários apenas para perfis de poder |
| `/api/users/me/` | `GET` | ✅ | ✅ | ✅ | Usuário autenticado vê próprio perfil |
| `/api/access-audits/` | `GET` | ❌ | ❌ | ✅ | Logs só para perfis de poder |
| `/api/notifications/` | `GET` | ✅ (próprias) | ✅ (próprias) | ✅ (próprias) | Escopo por `recipient=request.user` |

## Responsáveis / Alunos

| Endpoint | Método | Professor | Responsável | Coordenação/Admin | Regra aplicada |
|---|---|---:|---:|---:|---|
| `/api/guardians/` | `GET` | ❌ | ✅ (somente próprio perfil) | ✅ | Queryset restrito para responsável |
| `/api/guardians/{id}/` | `PATCH` | ❌ | ✅ (somente próprio perfil) | ✅ | `IsGuardianOwner` + queryset |
| `/api/students/{id}/report-card-pdf/` | `GET` | ❌ | ✅ (somente aluno vinculado) | ✅ | Bloqueio de IDOR no portal família |
| `/api/students/{id}/attendance-report/` | `GET` | ❌ | ✅ (somente aluno vinculado) | ✅ | Bloqueio de IDOR no portal família |
| `/api/students/{id}/class-diary/` | `GET` | ❌ | ✅ (somente aluno vinculado) | ✅ | Bloqueio de IDOR no portal família |

## Frequência (Attendance)

| Endpoint | Método | Professor | Responsável | Coordenação/Admin | Regra aplicada |
|---|---|---:|---:|---:|---|
| `/api/attendance/bulk_save/` | `POST` | ✅ (apenas atribuição própria) | ❌ | ✅ | Validação por `TeacherAssignment` + grade/feriado |
| `/api/attendance/pending-by-assignment/` | `GET` | ✅ (apenas atribuição própria) | ❌ | ✅ | Validação explícita por atribuição |
| `/api/attendance/pending-overview/` | `GET` | ✅ (próprio escopo) | ❌ | ✅ | Professor só vê suas atribuições |
| `/api/attendance/daily-log/` | `GET` | ✅ (somente turma/matéria vinculada) | ❌ | ✅ | Escopo validado por turma/matéria |
| `/api/attendance/weekly_dates/` | `GET` | ✅ (somente turma/matéria vinculada) | ❌ | ✅ | Escopo validado por turma/matéria |
| `/api/attendance/stats/` | `GET` | ✅ (somente escopo vinculado) | ❌ | ✅ | Escopo validado por matrícula/turma/matéria |

## Justificativas de falta

| Endpoint | Método | Professor | Responsável | Coordenação/Admin | Regra aplicada |
|---|---|---:|---:|---:|---|
| `/api/justifications/` | `POST` | ❌ | ✅ (somente aluno vinculado) | ✅ | `perform_create` valida vínculo do responsável |
| `/api/justifications/{id}/` | `PATCH` (`status`) | ❌ | ❌ | ✅ | Responsável não pode alterar status |
| `/api/justifications/` | `GET` | ❌ | ✅ (somente seus filhos) | ✅ | Queryset restrito para responsável |

## Calendário escolar

| Endpoint | Método | Professor | Responsável | Coordenação/Admin | Regra aplicada |
|---|---|---:|---:|---:|---|
| `/api/calendar/` | `GET` | ✅ (escopo de audiência) | ✅ (escopo de audiência/vínculo) | ✅ | Filtro por público-alvo |
| `/api/calendar/` | `POST` | ✅ | ❌ | ✅ | Criação bloqueada para responsável/comum |
| `/api/calendar/{id}/` | `PATCH/DELETE` | ✅ (somente conforme `can_edit`) | ❌ | ✅ | Regra centralizada em `can_edit` |

## Grade horária

| Endpoint | Método | Professor | Responsável | Coordenação/Admin | Regra aplicada |
|---|---|---:|---:|---:|---|
| `/api/schedules/` | `GET` | ✅ (turmas vinculadas) | ✅ (turmas dos filhos) | ✅ | Queryset por perfil |
| `/api/schedules/` | `POST/PATCH/DELETE` | ❌ | ❌ | ✅ | Apenas perfis de gestão editam grade |

## Como validar antes de release

Executar suíte mínima de autorização:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py test \
  apps.core.tests.UserViewSetAuthorizationTests \
  apps.academic.tests.AuthorizationHardeningTests \
  apps.academic.tests.AttendanceScheduleRulesTests \
  apps.academic.tests.ParentPortalSecurityTests
```

## Observações de governança

- Toda nova endpoint crítica deve entrar nesta matriz junto com teste negativo.
- Alterações de permissão exigem atualização simultânea em:
  - `AUTHORIZATION.md`
  - testes de autorização
  - menu/guardas de rota no frontend (quando aplicável)

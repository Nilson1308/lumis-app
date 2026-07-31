# Roadmap de Produto — Lumis

Backlog funcional por módulo, derivado da lista de melhorias acordada.  
Complementa o [roadmap técnico](./ROADMAP.md) (segurança, CI, performance).

**Última atualização:** 16/05/2026  
**Legenda de status:** `backlog` · `em definição` · `em desenvolvimento` · `concluído`

### Decisões de negócio (fechadas)

| ID | Decisão |
|---|---|
| F1 | Dia inicial = **próximo dia letivo na grade**; se houver chamadas pendentes, priorizar o **dia pendente mais antigo**. |
| F3 | **Reset do dia inteiro** (todos os registros daquela data na chamada). |
| F4 | Sábado e domingo **sempre** desabilitados (sem exceção por grade). |
| N1 | Autocomplete com biblioteca de nomes de **toda a escola**. |
| R1 | Filtros **bimestre/período letivo** e **intervalo de datas**; aplicar a **todos os relatórios**. |
| C1 | Módulo de **suporte**: formulário simples para usuários + tela de respostas; gestão administrativa só no **Django Admin** (sem painel admin no frontend). |
| CAL1 | **Sem** integração externa (Google/Outlook); escopo = revisão/evolução do calendário atual + visibilidade por equipe (detalhar com a escola). |
| P1 | Retenção de anexos: **30 dias** (valor inicial fixo). |

| Prioridade | Significado |
|---|---|
| P0 | Bloqueia uso diário ou gera dado incorreto |
| P1 | Melhoria relevante para professores/coordenação |
| P2 | Novo módulo ou evolução estratégica |

---

## Visão geral

| Módulo | Itens | Prioridade sugerida | Base no código |
|---|---|---:|---|
| Frequência | 4 | ✅ concluído | `AttendanceClass.vue`, `WeeklyCalendar.vue` |
| Notas | 1 | ✅ N1 concluído | `GradeBook.vue` |
| Planejamento semanal | 1 (+ alinhamento) | P1 | `LessonPlanList.vue` |
| Chamado (ocorrências) | 1 | ✅ C1 concluído | `apps.support`, `SupportTickets.vue` |
| Relatórios | 1 | ✅ R1 concluído | `ReportsPage.vue`, `reports.py` |
| Calendário | 1 | P2 | `CalendarView.vue`, `SchoolEvent` |

**Ordem sugerida de entrega:** Frequência → Notas → Relatórios → Chamado → Planejamento → Calendário (equipe).

---

## Módulo — Frequência

Tela principal: chamada por atribuição (`/teacher/classes/:id/attendance`).  
Já existe restrição parcial por grade (`classSchedules`, `scheduledWeekdays`) e calendário semanal (`WeeklyCalendar`).

### F1 — Calendário alinhado ao dia de referência da grade do professor

| Campo | Valor |
|---|---|
| **Status** | concluído |
| **Prioridade** | P0 |
| **Descrição** | Ao abrir a chamada, selecionar automaticamente o dia correto para lançar frequência. |
| **Regra de negócio** | **(1)** Se existir chamada pendente, ir para o **dia pendente mais antigo**. **(2)** Caso contrário, ir para o **próximo dia letivo** conforme a grade (disciplina + turma). |
| **Contexto atual** | `attendanceDate` inicia em `new Date()`; `isSelectedDateAllowed` valida dia, mas a navegação inicial pode cair em dia sem aula. |
| **Critérios de aceite** | (1) Com pendências, abre no dia pendente mais antigo; (2) sem pendências, abre no próximo dia com aula na grade; (3) trocar semana mantém coerência com dias da grade; (4) dias sem aula continuam indisponíveis para lançamento. |
| **Backend** | Reutilizar `pending-overview` / pendências já usadas em `AttendanceClass.vue`, grade (`schedules`) e datas não letivas. |
| **Estimativa** | 2–3 dias |

### F2 — Borda do dia selecionado no calendário semanal

| Campo | Valor |
|---|---|
| **Status** | concluído |
| **Prioridade** | P1 |
| **Descrição** | Destacar visualmente o **dia selecionado** (borda/anel), distinto de “hoje” e de “chamada realizada”. |
| **Contexto atual** | `WeeklyCalendar.vue` aplica `border-primary` só em `isToday(day)`; seleção não altera estilo. |
| **Critérios de aceite** | (1) Dia clicado recebe estilo de seleção persistente; (2) “Hoje” e “selecionado” podem coexistir com hierarquia visual clara; (3) acessível em tema claro/escuro. |
| **Estimativa** | 0,5–1 dia |

### F3 — Opção “Reset” na chamada

| Campo | Valor |
|---|---|
| **Status** | concluído |
| **Prioridade** | P1 |
| **Descrição** | Reverter **a chamada inteira do dia** (todos os alunos daquela data/disciplina), com confirmação. |
| **Regra de negócio** | Reset = **dia todo**: remove ou zera todos os registros de `Attendance` daquela data para a atribuição (estado inicial, ex. todos presentes ou sem lançamento — alinhar ao comportamento atual da tela). |
| **Critérios de aceite** | (1) Botão “Reset” visível na tela de chamada; (2) confirmação explícita; (3) após confirmar, backend reflete reset do dia; (4) UI recarrega estado consistente. |
| **Estimativa** | 1–2 dias |

### F4 — Desativar finais de semana

| Campo | Valor |
|---|---|
| **Status** | concluído |
| **Prioridade** | P1 |
| **Descrição** | Sábado e domingo **sempre** indisponíveis para chamada. |
| **Regra de negócio** | Bloqueio **incondicional** de sáb/dom (sem exceção por grade ou turma). |
| **Contexto atual** | `disabledWeekdays` depende da grade; fins de semana podem aparecer na semana sem bloqueio explícito. |
| **Critérios de aceite** | (1) Sáb/dom desabilitados na UI e no date picker; (2) API rejeita lançamento nesses dias. |
| **Estimativa** | 1 dia |

---

## Módulo — Notas

Tela: diário de notas por atribuição (`GradeBook.vue`).

### N1 — Autocomplete no “Nome da Avaliação”

| Campo | Valor |
|---|---|
| **Status** | concluído |
| **Prioridade** | P1 |
| **Descrição** | Campo de nome da avaliação com sugestões a partir da **biblioteca de nomes já usados em toda a escola**. |
| **Critérios de aceite** | (1) Digitar filtra sugestões globais da escola; (2) permitir nome novo; (3) performance aceitável (cache ou paginação na busca); (4) deduplicação de nomes (case-insensitive). |
| **Implementação** | `GET /api/grades/assessment-names/` + `AutoComplete` em `GradeBook.vue` (cache local ao abrir o diálogo). |
| **Estimativa** | 2 dias |

---

## Módulo — Planejamento semanal

Tela: `LessonPlanList.vue` (anexos: máx. 5 arquivos, 5 MB total hoje).

### P1 — Regras de arquivos anexados e retenção (30 dias)

| Campo | Valor |
|---|---|
| **Status** | backlog |
| **Prioridade** | P1 |
| **Descrição** | Manter regras atuais de upload (5 arquivos, 5 MB) e implementar **descarte automático de anexos após 30 dias**. |
| **Regra de negócio** | Retenção fixa em **30 dias** na primeira versão (sem parâmetro configurável por enquanto). Link externo (`attachment_link`) **não** é removido pelo job. |
| **Ações complementares** | [ ] Validar com Lívia tipos/tamanho já vigentes · [ ] LGPD se anexo tiver dado pessoal |
| **Critérios de aceite** | (1) Regras exibidas na UI ao anexar; (2) comando/cron remove arquivos com idade > 30 dias e registra log; (3) link externo preservado. |
| **Estimativa** | 3–4 dias |

---

## Módulo — Chamado (ocorrências)

**Módulo novo** — não existe entidade “chamado” no código hoje.

### C1 — Chamado de suporte (ocorrências)

| Campo | Valor |
|---|---|
| **Status** | concluído |
| **Prioridade** | P1 |
| **Descrição** | Módulo de **suporte técnico/operacional** para usuários do sistema abrirem chamados e acompanharem respostas. |
| **Parâmetros** | `data`, `hora`, `solicitante`, `descrição`, `anexo`, `status` |
| **Escopo de UI** | **Usuários:** formulário simples para abrir chamado + área para ver chamados e **respostas**. **Admin (você):** gestão completa no **Django Admin** — sem painel gerencial dedicado no frontend. |
| **Critérios de aceite** | (1) Usuário autenticado abre chamado com os campos acima; (2) lista “meus chamados” com status; (3) thread ou lista de respostas visível ao solicitante; (4) staff responde via Admin (e/ou API interna); (5) anexo opcional com limites alinhados ao planejamento; (6) status: aberto → em atendimento → resolvido (mínimo). |
| **Implementação** | App `apps.support`; API `support-tickets/`; Admin com respostas; tela `/suporte` (`SupportTickets.vue`). |
| **Estimativa** | 1–1,5 sprint |

#### Modelo sugerido

| Entidade | Campos principais |
|---|---|
| `SupportTicket` | data, hora, solicitante (FK User), descrição, anexo, status, created_at |
| `SupportTicketReply` | ticket (FK), autor (FK User), mensagem, created_at, interno (bool, só Admin) |

---

## Módulo — Relatórios

Tela: `ReportsPage.vue` — hoje filtra por **período letivo** + **turma** para PDFs de diário e frequência.

### R1 — Filtro por período

| Campo | Valor |
|---|---|
| **Status** | concluído |
| **Prioridade** | P1 |
| **Descrição** | Oferecer **dois filtros complementares** em todos os relatórios: período letivo (bimestre/cadastro) **e** intervalo de datas (de/até). |
| **Regra de negócio** | Interseção entre bimestre e intervalo; sem datas informadas, usa o período letivo inteiro. |
| **Critérios de aceite** | (1) UI com seletor de período letivo + calendário de/até; (2) cada relatório/PDF respeita os filtros; (3) limite máximo de intervalo (ex.: 1 ano) para evitar PDF excessivo; (4) mensagem clara se combinação não retornar dados. |
| **Implementação** | `report_filters.py`; PDFs diário/frequência/boletim; `ReportsPage.vue`, `ClassroomDetail.vue`, composable `useReportPdfFilters.js`. |
| **Estimativa** | 3–5 dias (inventário de todos os relatórios) |

---

## Módulo — Calendário

Tela: `CalendarView.vue` + API `calendar` (`SchoolEvent`).

### CAL1 — Calendário e visibilidade por equipe

| Campo | Valor |
|---|---|
| **Status** | em definição (escola) |
| **Prioridade** | P2 |
| **Descrição** | **Revisar e evoluir** o calendário já existente (`CalendarView` / `SchoolEvent`) para melhor atender a equipe escolar — **sem integração** com Google, Outlook ou ferramentas externas. |
| **Fora de escopo** | Sync com calendários externos; APIs de terceiros. |
| **Responsabilidade escola** | Detalhar o que significa “integração com a equipe” (quem vê o quê, quem cria eventos, categorias por setor/turma). |
| **Critérios de aceite (após alinhamento)** | (1) Regras de visibilidade por perfil/equipe documentadas; (2) ajustes de UI/UX no calendário atual; (3) família continua com visão restrita já garantida no backend. |
| **Estimativa** | A definir após especificação da escola |

---

## Riscos e dependências transversais

| Item | Impacto |
|---|---|
| CAL1 — definição “equipe” | Escopo técnico depende da especificação da escola |
| R1 — relatórios fora da área PDF | Boletim via matrícula/portal família já usa `period`; demais relatórios operacionais fora do escopo R1 |
| Chamado (C1) | Concluído — respostas internas só no Admin |
| P1 — retenção 30 dias | Job em produção + backup antes de purge; validar LGPD com Lívia |
| F4 — sáb/dom sempre | Se no futuro houver contraturno sábado, será necessária exceção explícita |

---

## Checklist de entrega por item

Use em PRs/issues:

- [ ] Critérios de aceite atendidos  
- [ ] Permissões validadas no backend (não só no frontend)  
- [ ] Teste manual documentado em `COMMANDS.md` ou issue  
- [ ] Sem regressão em portal família / professor  
- [ ] Atualizar status neste arquivo ao concluir  

---

## Histórico

| Data | Alteração |
|---|---|
| 16/05/2026 | Criação do roadmap a partir da lista de módulos (Frequência, Notas, Planejamento, Chamado, Relatórios, Calendário). |
| 16/05/2026 | Decisões de negócio registradas: F1 (pendente mais antigo → próximo dia), F3 (reset dia todo), F4 (fds sempre), N1 (escola), R1 (ambos filtros, todos relatórios), C1 (suporte + Admin), CAL1 (sem integração externa), P1 (30 dias). |
| 16/05/2026 | F1–F4 (Frequência) concluídos: correção weekday grade/API, dia inicial, borda seleção, reset do dia, bloqueio fim de semana, alertas de pendência. |
| 16/05/2026 | N1 concluído: autocomplete de nomes de avaliação (biblioteca escola) em `GradeBook.vue`. |
| 16/05/2026 | R1 concluído: filtros período letivo + intervalo de datas nos PDFs (diário, frequência, boletim) e telas de relatórios. |
| 16/05/2026 | C1 concluído: módulo de chamados de suporte (`SupportTicket` / respostas, API, Admin, tela Meus Chamados). |

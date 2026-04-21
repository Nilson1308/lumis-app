# Roadmap Técnico - Lumis

Plano geral para evoluir segurança, performance e manutenibilidade com execução em etapas.

## Objetivos

- Reduzir riscos de segurança e configuração em produção.
- Aumentar previsibilidade de deploy e qualidade de release.
- Melhorar performance percebida e eficiência operacional.
- Fortalecer governança de autorização e testes.

---

## Diagnóstico Consolidado

> Última revisão técnica: 21/04/2026.

### 1) Segurança (crítico)

- Matriz de autorização ainda heterogênea entre viewsets (risco de divergência entre frontend e backend).
- Ainda há pontos com RBAC a consolidar e cobrir com testes negativos por perfil.
- URLs de domínio/base ainda aparecem hardcoded em alguns pontos (Nginx/reset de senha).

### 2) Qualidade e entrega (crítico)

- CI já implantada em `.github/workflows/ci.yml` (backend + frontend).
- Cobertura ainda parcial para frontend e para cenários negativos de segurança/autorização.

### 3) Reprodutibilidade de build (alto)

- Build frontend já determinístico com `package-lock.json` e `npm ci`.
- Falta padronizar rollback operacional com versão/tag de imagem no runbook.

### 4) Performance e observabilidade (médio/alto)

- Sem baseline de métricas de API e frontend.
- Sem check automatizado de orçamento de bundle e tempos de resposta.
- Logs existem via Docker, mas sem trilha de SLO/alerta.

### 5) Manutenibilidade e governança (médio)

- Regras de acesso distribuídas e heterogêneas em vários viewsets.
- Pouca padronização de testes por camada (unitário, integração, e2e).

---

## Roadmap por Fases

## Status Executivo (ciclo atual)

| Fase | Situação | Progresso estimado | Observação |
|---|---|---:|---|
| Fase 0 - Blindagem imediata | Quase concluída | 90% | Base de segurança operacional estabilizada; manter validação recorrente em deploy |
| Fase 1 - Qualidade mínima | Em andamento | 70% | CI ativa e testes críticos avançaram; falta ampliar cobertura frontend/lint |
| Fase 2 - Build/deploy confiável | Em andamento | 65% | Build determinístico concluído; falta formalizar rollback e smoke pós-deploy |
| Fase 3 - Autorização/observabilidade | Em andamento | 60% | Hardening e matriz de autorização entregues; faltam KPIs e observabilidade |
| Fase 4 - Escala de qualidade | Não iniciada formalmente | 10% | Backlog definido, execução ainda não planejada por sprint |

## Próximos 5 itens objetivos

1. Formalizar playbook de rollback/smoke em `COMMANDS.md` (critério de go/no-go).
2. Completar testes negativos de autorização para todos os endpoints sensíveis remanescentes.
3. Expandir lint/test frontend para além do escopo mínimo atual no CI.
4. Definir baseline de performance (p95 APIs críticas, PDF e bundle frontend).
5. Implantar monitoramento inicial de erros/latência (logs estruturados + painel básico).

## Fase 0 (Semana 1) - Blindagem imediata

**Prioridade:** P0  
**Meta:** remover riscos de exposição acidental e estabilizar operação.

- Mover `SECRET_KEY` para variável de ambiente obrigatória (sem fallback inseguro).
- Trocar `ALLOWED_HOSTS` default para vazio e configurar explicitamente por ambiente.
- Remover senhas do compose e usar `.env` seguro no servidor (fora do Git).
- Executar `python manage.py check --deploy` em produção e corrigir alertas.
- Documentar rotação de segredos (DB, e-mail, JWT key se aplicável).

**Critério de pronto**
- Nenhum segredo hardcoded no código.
- `ALLOWED_HOSTS` restrito a domínios válidos.
- Checklist de deploy seguro validado em `COMMANDS.md`.

---

## Fase 1 (Semanas 2-3) - Qualidade mínima de release

**Prioridade:** P0  
**Meta:** impedir regressões básicas antes de deploy.

- Criar suíte mínima backend (pytest ou Django TestCase) para:
  - autenticação JWT,
  - permissões por perfil em endpoints críticos,
  - geração de relatórios PDF (status + contrato de resposta).
- Criar suíte mínima frontend (Vitest) para stores/auth e guards de rota.
- Adicionar lint/format e execução em CI.
- Criar pipeline CI (GitHub Actions) com:
  - backend: install + tests + lint,
  - frontend: install + lint + test + build.

**Critério de pronto**
- CI obrigatória no branch principal.
- Cobertura inicial >= 25% backend crítico e smoke frontend.
- Build verde como condição de merge.

**Status atual**
- CI backend/frontend implementada e ativa.
- Etapa segue aberta para ampliar cobertura de segurança e padronização de lint completo.

---

## Fase 2 (Semanas 4-5) - Build reproduzível e deploy confiável

**Prioridade:** P1  
**Meta:** tornar releases previsíveis e rastreáveis.

- Reintroduzir lockfile do frontend (`package-lock.json`) e usar `npm ci` no Dockerfile.
- Ajustar `.dockerignore` para permitir lockfile.
- Publicar convenção de versionamento de imagem/tag.
- Adicionar validação de migrações no pipeline (fail se houver drift).
- Criar check de smoke pós-deploy (health endpoint + rota principal frontend).

**Critério de pronto**
- Build determinístico com lockfile versionado.
- Mesmo commit gera artefatos consistentes.
- Playbook de rollback documentado.

**Status atual**
- Lockfile + `npm ci` aplicados no Dockerfile e no CI.
- Etapa segue aberta por falta de playbook formal de rollback/smoke pós-deploy.

---

## Fase 3 (Semanas 6-8) - Autorização robusta e observabilidade

**Prioridade:** P1  
**Meta:** garantir segurança de acesso no backend e visibilidade operacional.

- Inventariar endpoints críticos e mapear política de acesso por perfil.
- Padronizar autorização no backend (permission classes por domínio).
- Criar testes de autorização negativos (usuário sem permissão deve falhar).
- Definir baseline de performance:
  - p95 de APIs críticas,
  - tempo de geração de PDF,
  - tamanho de bundle frontend.
- Introduzir logs estruturados e painéis básicos (erros 5xx, latência, throughput).

**Critério de pronto**
- Matriz de autorização publicada e validada por testes.
- KPIs com acompanhamento semanal.

---

## Fase 4 (Semanas 9-12) - Escala de qualidade

**Prioridade:** P2  
**Meta:** evolução contínua com menor custo de manutenção.

- Expandir cobertura para fluxos acadêmicos centrais (notas, frequência, matrícula).
- Adicionar e2e para jornadas críticas (coordenação e professor).
- Criar ADRs leves para decisões arquiteturais importantes.
- Instituir rotina de atualização de dependências e scanner de vulnerabilidades.

**Critério de pronto**
- Regressões críticas detectadas automaticamente.
- Lead time de mudança reduzido e menor taxa de incidentes.

---

## Backlog da Análise Profunda (priorizado)

## Segurança
- Endurecer cookies e cabeçalhos de segurança (`SecurityMiddleware` completo por ambiente).
- Revisar CORS/CSRF trusted origins por ambiente (dev/staging/prod).
- Validar política de retenção e acesso de arquivos em `media`.

## Performance
- Paginação e filtros padronizados em listagens grandes.
- Cache seletivo para endpoints de leitura pesada (dashboard/relatórios quando aplicável).
- Budget de bundle frontend e lazy loading adicional em rotas menos usadas.

## Manutenibilidade
- Camada de serviços/repositório para regras críticas hoje espalhadas em views.
- Guia de contribuição (padrões de código, testes obrigatórios, revisão).
- Templates de PR com checklist técnico.

---

## KPIs sugeridos (acompanhamento mensal)

- **Segurança:** 0 segredos hardcoded; 100% env vars sensíveis mapeadas.
- **Qualidade:** taxa de sucesso CI > 95%; cobertura backend crítico >= 50% em 90 dias.
- **Entrega:** tempo médio de deploy < 15 min; rollback documentado e testado.
- **Performance:** p95 APIs críticas < 500ms (sem PDF); geração de PDF p95 < 5s.
- **Confiabilidade:** redução de erros 5xx e incidentes por release.

---

## Ordem recomendada de execução

1. Fase 0 (segurança base)  
2. Fase 1 (testes + CI)  
3. Fase 2 (build reproduzível)  
4. Fase 3 (autorização + observabilidade)  
5. Fase 4 (escala e maturidade)


# Banco de Dados

## Entidades

### Core (existentes)
- tenants, users, profiles
- photoshoots, photos, analyses, reports, evaluations

### Vision Core v0.1 (novos)
- digital_twin_assets - Assets do gêmeo digital
- castings - Oportunidades de casting
- casting_matches - Matches casting-perfil
- content_items - Conteúdo social
- content_approvals - Aprovações
- ai_tasks - Tarefas de IA
- audit_logs - Logs de auditoria
- voice_commands - Comandos de voz
- workflows - Workflows configuráveis
- workflow_runs - Execuções de workflow
- notifications - Notificações

## Convenções
- UUID como PK em todas as tabelas
- created_at e updated_at
- tenant_id para multi-tenancy
- status para controle de workflow
- metadata JSONB para flexibilidade

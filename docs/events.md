# Eventos do Vision Ecosystem

## Visão Geral
Sistema orientado a eventos via EventBus singleton.

## Tipos de Eventos

### Usuário
- USER_CREATED, USER_UPDATED, PROFILE_UPDATED

### Gêmeo Digital
- DIGITAL_TWIN_UPDATED, DIGITAL_TWIN_ASSET_ADDED

### Casting
- CASTING_CREATED, CASTING_ANALYZED, CASTING_MATCH_FOUND

### Conteúdo
- CONTENT_CREATED, CONTENT_APPROVAL_REQUESTED
- CONTENT_APPROVED, CONTENT_REJECTED, CONTENT_PUBLISHED

### Tarefas IA
- AI_TASK_CREATED, AI_TASK_STARTED
- AI_TASK_COMPLETED, AI_TASK_FAILED

### Aprovação
- APPROVAL_APPROVED, APPROVAL_REJECTED, APPROVAL_REVISION_REQUESTED

## Uso
```python
from app.core.event_bus import emit_event, VisionEventType

await emit_event(
    event_type=VisionEventType.CONTENT_CREATED,
    payload={"content_id": "123"},
)
```

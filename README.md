# Vision AI Casting + Vision Core v0.1

Plataforma de inteligência artificial voltada para atores, modelos, casting, figuração, agências e profissionais de imagem.

## Arquitetura

O sistema segue o conceito de **"cérebro grande"** (Vision Core) conectado a vários **"mini cérebros"** especializados (agentes).

```
Vision Core (Orquestrador)
├── Agent Router
├── Intent Recognizer
├── Context Builder
└── Event Bus

Mini Cérebros (10 Agentes)
├── IdentityAgent
├── VisagismAgent
├── DigitalTwinAgent
├── CastingAgent
├── PortfolioAgent
├── SocialAgent
├── OpportunityAgent
├── ApprovalAgent
├── AnalyticsAgent
└── AutomationAgent

Infraestrutura
├── PostgreSQL (dados)
├── Redis (cache/fila)
├── Event Bus (eventos)
└── Audit Log (auditoria)
```

## Stack Tecnológica

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async)
- **Banco de Dados**: PostgreSQL + asyncpg
- **Cache/Fila**: Redis (preparado)
- **AI/ML**: OpenAI GPT-4o, AWS Rekognition, DeepFace, MediaPipe
- **Storage**: S3-compatível
- **Auth**: JWT

## Estrutura do Projeto

```
backend/app/
├── agents/              # 10 mini-cérebros especializados
├── ai/                  # Módulos de IA (visagismo, casting, etc.)
├── audit/               # Logs de auditoria
├── connectors/          # Integrações externas (mock)
├── core/                # Event Bus, Celery, WebSocket
├── engines/             # Interfaces de motores
├── memory/              # Camada de memória
├── models/              # Modelos SQLAlchemy (20+ entidades)
├── modules/             # Serviços de domínio
│   ├── approval/
│   ├── casting/
│   ├── content/
│   └── digital_twin/
├── providers/           # Abstrações LLM
├── routers/             # API REST
├── schemas/             # Schemas Pydantic
├── services/            # Serviços existentes
├── tasks/               # Gerenciador de tarefas IA
├── tests/               # Testes unitários
├── utils/               # Utilitários
└── vision_core/         # Orquestrador central
```

## Endpoints da API

### Vision Core
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/commands` | Processar comando |
| GET | `/api/v1/commands/history` | Histórico |
| GET | `/api/v1/commands/health` | Saúde do sistema |

### Aprovações
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/approvals` | Listar |
| POST | `/api/v1/approvals/{id}/approve` | Aprovar |
| POST | `/api/v1/approvals/{id}/reject` | Rejeitar |
| POST | `/api/v1/approvals/{id}/revision` | Solicitar revisão |

### Módulos Existentes
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/ai/analyze` | Análise completa |
| GET | `/api/v1/profiles` | Perfis |
| POST | `/api/v1/photoshoots` | Photoshoots |
| GET | `/api/v1/reports` | Relatórios |

## Executar

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env

# Iniciar banco de dados
docker-compose up -d postgres redis

# Executar migrações
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
```

## Testes

```bash
pytest app/tests/ -v
```

## Documentação

- `docs/architecture.md` - Arquitetura completa
- `docs/agents.md` - Documentação dos agentes
- `docs/events.md` - Sistema de eventos
- `docs/database.md` - Modelo de dados
- `docs/security.md` - Segurança
- `docs/roadmap.md` - Roadmap

## Roadmap

### v0.1 ✅ Vision Core (Atual)
- Arquitetura modular, 10 agentes, Event Bus, Approval Workflow

### v0.2 Digital Twin
- Assets multi-ângulo, embeddings, simulação

### v0.3 Casting Intelligence
- Matching automático, candidatura automatizada

### v0.4 Social Brain
- Geração de conteúdo, agendamento, métricas

### v0.5 WhatsApp Approval
- Integração real WhatsApp Business API

### v0.6 Voice Command
- STT/TTS, comandos naturais

### v0.7 Analytics Brain
- Dashboard, recomendações

### v0.8 Agency Portal
- Portal para agências

### v1.0 Autonomous Career Agent
- Agente autônomo completo

<!-- CI validation: analyzers 4-9 -->

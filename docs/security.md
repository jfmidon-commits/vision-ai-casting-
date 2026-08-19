# Segurança

## Princípios
1. Nunca armazenar senhas de redes sociais
2. Usar OAuth e APIs oficiais
3. Tokens criptografados
4. Separação de dados por tenant
5. Aprovação humana para ações importantes
6. Logs de auditoria

## Autenticação
- JWT para API REST
- Clerk para autenticação (preparado)

## Autorização
- Multi-tenancy com tenant_id
- Roles: admin, manager, user

## Redes Sociais
- OAuth 2.0
- Tokens armazenados criptografados
- Refresh automático

## Dados Sensíveis
- Variáveis de ambiente para secrets
- Nunca no código

# API Aura

Django 5.2 LTS + Django REST Framework + MySQL. Veja o [guia completo](../README.md) para instalação, deploy, MySQL, Docker, HTTPS e CI.

Execute os comandos Django **neste diretório** para descoberta automática dos testes:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
python manage.py test --verbosity=2
```

## Convenções

- JSON em `/api/`, sempre com `/` final.
- Sessões Django. Não há JWT nem tokens em localStorage.
- Data: `AAAA-MM-DD`; hora: `HH:MM[:SS]`, no fuso `America/Sao_Paulo`.
- Valores monetários são strings decimais, por exemplo `"85.00"`.
- Listagens retornam arrays JSON. Disponibilidade retorna `{ "date": "AAAA-MM-DD", "slots": [{ "start_time": "09:00", "end_time": "10:00" }] }`.
- `400` para validação; `403` para acesso proibido, sessão ausente ou CSRF; `404` para registro ausente/não pertencente à cliente; `429` para excesso de tentativas.
- Erros DRF: `{ "campo": ["mensagem"] }`, `{ "detail": "mensagem" }` ou lista de mensagens. O front-end normaliza esses formatos.

## Autenticação

| Método | Endpoint | Acesso / uso |
|---|---|---|
| GET | `/api/auth/csrf/` | Público; obtém `csrfToken` e cookie CSRF |
| POST | `/api/auth/register/` | Público + CSRF; nome, e-mail, telefone, senha, confirmação e aceite |
| POST | `/api/auth/login/` | Público + CSRF; `email`, `password` |
| POST | `/api/auth/logout/` | Autenticado + CSRF |
| GET | `/api/auth/me/` | Usuário, papel e perfil atuais |
| PATCH | `/api/auth/me/` | Edita o próprio perfil da cliente |
| POST | `/api/auth/password-reset/` | Público + CSRF; `email`; sempre resposta genérica |
| POST | `/api/auth/password-reset-confirm/` | Público + CSRF; `uid`, `token`, `password`, `password_confirmation` |

Cadastro:

```json
{
  "full_name": "Cliente de exemplo",
  "email": "cliente@example.com",
  "phone": "11999990000",
  "password": "SUBSTITUA_PELA_SENHA_ESCOLHIDA",
  "password_confirmation": "SUBSTITUA_PELA_SENHA_ESCOLHIDA",
  "terms": true,
  "cpf": "",
  "birth_date": null,
  "address": "",
  "notes": ""
}
```

Senha é validada pelos validadores Django. E-mail é normalizado; telefone é normalizado para dígitos e único. CPF opcional é validado pelos dígitos verificadores. Nunca retorne hashes nem senhas. O aceite registra data/hora no perfil; complemente com versionamento da política de privacidade conforme as necessidades legais do negócio.

## Recursos

| Recurso | Métodos | Permissões |
|---|---|---|
| `/api/clients/` | GET, POST | Profissional |
| `/api/clients/{id}/` | GET, PUT, PATCH, DELETE | Profissional; DELETE desativa acesso, mantém histórico |
| `/api/clients/{id}/history/` | GET | Profissional |
| `/api/services/` | GET, POST | GET público (somente ativos); POST profissional |
| `/api/services/{id}/` | GET, PUT, PATCH, DELETE | Leitura pública de ativos; escrita profissional |
| `/api/business-hours/` | GET, POST | Leitura pública; escrita profissional |
| `/api/business-hours/{id}/` | GET, PUT, PATCH, DELETE | Leitura pública; escrita profissional |
| `/api/blocked-slots/` | GET, POST | Profissional |
| `/api/blocked-slots/{id}/` | GET, PUT, PATCH, DELETE | Profissional |
| `/api/settings/` | GET, PATCH | Leitura pública das regras; escrita profissional |
| `/api/available-slots/?date=AAAA-MM-DD&service_id=1` | GET | Público; consulta até 366 dias à frente |
| `/api/appointments/` | GET, POST | Autenticado; cliente vê/cria somente os próprios |
| `/api/appointments/{id}/` | GET, PUT, PATCH, DELETE | Autenticado; cliente restrita aos próprios |
| `/api/appointments/{id}/cancel/` | POST | Cliente proprietária dentro do prazo ou profissional |
| `/api/appointments/{id}/confirm/` | POST | Profissional; pendente → confirmado |
| `/api/appointments/{id}/reject/` | POST | Profissional; pendente → recusado |
| `/api/appointments/{id}/complete/` | POST | Profissional; confirmado → concluído após o término |
| `/api/notifications/` | GET | Notificações do usuário autenticado |
| `/api/notifications/{id}/` | GET | Notificação própria |
| `/api/notifications/read_all/` | POST | Marca todas as próprias como lidas |

`PUT` requer os campos obrigatórios; prefira `PATCH` para edições parciais. Todas as escritas exigem CSRF. Horários usam `day_of_week`: **0 segunda-feira … 6 domingo**. Campos de intervalo `break_start`/`break_end` devem ser ambos nulos ou um intervalo válido dentro do expediente.

Criar uma reserva:

```json
{
  "service": 1,
  "appointment_date": "2030-10-21",
  "start_time": "09:00",
  "client_notes": "Observação opcional"
}
```

A profissional informa também `client`. Para a cliente esse campo é ignorado; sua identidade vem da sessão. `end_time`, `price` e `status` não são aceitos do navegador. `admin_notes` é visível/editável apenas pela profissional via API. Filtre a listagem por `appointment_date`, `status` ou `client`.

Status internos: `pending`, `confirmed`, `completed`, `cancelled`, `rejected`. O front-end os traduz. DELETE de agendamento tem semântica de cancelamento e retorna o registro preservado com status atualizado.

## Transações e concorrência

O lock global da agenda é uma linha `ScheduleSettings(pk=1)`, criada em migration. Ela é bloqueada **antes da consulta de conflitos e da escrita**, dentro da mesma transação. Assim, mesmo se não existir nenhum agendamento no dia, duas reservas simultâneas são serializadas. Apenas bloquear linhas de agendamentos já existentes não resolveria a corrida em uma agenda vazia.

O teste `MySQLConcurrencyTests` usa duas conexões/requisições concorrentes e espera exatamente uma criação. SQLite não fornece a mesma garantia e não é configuração de produção. Escritas diretas por SQL/bulk scripts precisam obedecer à mesma regra; o seed é uma ferramenta de desenvolvimento, não um importador de produção.

A disponibilidade é consultiva: o horário pode ser ocupado entre GET e POST. A API revalida e retorna `400`; a cliente deve escolher outro horário.

## Operação

- Django Admin: usuários/perfis/notificações; agenda e serviços somente leitura para não contornar a API.
- E-mails: console em desenvolvimento, SMTP em produção; tokens de recuperação expiram segundo o padrão Django e são invalidados após alteração de senha.
- Logs não devem conter passwords, tokens ou perfis completos.
- O throttle usa cache local por padrão; configure Redis/cache compartilhado e limitação no proxy em produção.
- As listagens não estão paginadas nesta versão, adequada ao escopo de uma profissional. Para históricos muito extensos, adicione paginação e consultas agregadas antes de crescer o volume.
- Não armazene dados reais na base da demonstração. Mantenha retenção, exportação/exclusão de dados, backups e obrigações LGPD sob controle do negócio.

## Diagnóstico de CSRF

Rejeições CSRF, tanto nas telas de autenticação quanto na autenticação de sessão do DRF, retornam `403` com `code: "csrf_failed"` e `csrfReason` (`cookie_missing`, `token_invalid`, `origin_rejected` ou `referer_rejected`). A resposta não expõe tokens nem os diagnósticos internos do middleware. Outros erros de permissão continuam distintos e não disparam tentativas automáticas.

O endpoint de CSRF, autenticação e perfil usa `Cache-Control: no-store`. Em desenvolvimento, `PREVIEW_ORIGIN` adiciona uma **origem HTTPS exata** à lista confiável; no Arena ela pode ser obtida do identificador do sandbox. Essa inclusão automática só existe com `DEBUG=True`. Em produção, configure `CSRF_TRUSTED_ORIGINS` explicitamente. Nunca use `csrf_exempt` como correção para cookies bloqueados.

O proxy Node ajusta atributos dos cookies apenas na origem HTTPS de prévia. Não substitui nem inventa o cookie/token recebido e não altera a política de produção do Django. Consulte o README do front-end para o teste de regressão em iframe e o fallback de abrir em nova aba.

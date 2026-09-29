# Usando o SQL `Sistema-Agendamento` no site

A branch `B` contém o script `Sistema-Agendamento (3).sql` (banco
`sistema_agendamento`, 7 tabelas, 2 triggers e dados fictícios). Este documento
explica **o que falta adicionar** para o site funcionar, como aproveitar os
dados do script e o que melhorar.

## Ponto principal

O site **não lê as tabelas `sistema_agendamento` diretamente**. O banco do site
é criado pelo Django (`python manage.py migrate`) com outros nomes de
tabela/coluna e tabelas internas (`auth`, `sessions`, `django_migrations`).
Aplicar o `.sql` sozinho não faz o site funcionar nem permite login.

Caminho recomendado:

1. Criar o banco MySQL e o `.env` (veja `backend/.env.example`).
2. `python manage.py migrate` — cria o schema oficial do site.
3. `python manage.py createsuperuser` — conta administrativa **real** (o hash do
   script `$2b$12$hash_exemplo_123` é apenas um exemplo e **não funciona**; o
   Django usa outro formato e nunca deve haver senha padrão).
4. `python manage.py import_sistema_agendamento "Sistema-Agendamento (3).sql"` —
   converte os dados do script para os modelos do site (opcional; sem credenciais).
5. Completar as informações abaixo pelo Django Admin (`/admin/`).

## Informações que precisam ser adicionadas

| Onde | Informação | Observação |
|---|---|---|
| `.env` | `SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Credenciais nunca no Git. |
| Conta admin | e-mail + senha fortes | `createsuperuser`; para usuários importados, `manage.py changepassword <email>`. |
| Configurações (`ScheduleSettings`) | nome do estúdio/salão, nome do profissional, intervalo entre horários, antecedência mínima de cancelamento, passo da grade | Painel Django Admin. |
| Horários (`BusinessHour`) | abertura/fechamento por dia, pausa (almoço), dias indisponíveis | O site permite **um intervalo por dia**; feriados use `BlockedSlot`. |
| Serviços (`Service`) | nome, categoria, descrição, **duração**, **preço**, imagem (URL, opcional), ativo/inativo | Obrigatórios para a agenda. |
| Clientes (`ClientProfile`) | nome completo, **telefone único**, e-mail (login), CPF/nascimento/endereço opcionais, aceite dos termos | Clientes também podem se cadastrar pelo site. |
| Cancelamentos | motivo e observações | O admin registra em `admin_notes`. |
| Produção | `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, SSL, e-mail de recuperação de senha | Ver `backend/README.md`. |

Sem esses dados o site **roda**, mas a agenda fica vazia e o login administrativo
não existe.

## Mapeamento do SQL para o site

| Tabela do script | Modelo do site | Conversão |
|---|---|---|
| `profissional` | `ScheduleSettings` (admin) | `nome` → `professional_name`. O site é **monoprofissional**; com vários profissionais no arquivo, importe `--profissional <id>` (padrão: primeiro). |
| `categoria_servico` | `Service.category` | Texto da categoria em cada serviço. |
| `usuario` | `users.User` (`is_staff`) | `senha_hash` **sempre ignorado**; senha fica inutilizável até `changepassword`. |
| `cliente` | `users.User` + `ClientProfile` | `email` vira login (obrigatório); `telefone` deve ser único. |
| `servico` | `services.Service` | `ativo` → `status`; `preco`/`duracao_minutos` iguais. |
| `horario_disponivel` | `appointments.BusinessHour` | `Segunda`=0 … `Domingo`; várias linhas no mesmo dia são combinadas em uma. |
| `agendamento` | `appointments.Appointment` | `CONFIRMADO`→`confirmed`, `CANCELADO`→`cancelled`, `CONCLUIDO`→`completed`, `PENDENTE`→`pending`; `observacao` → `client_notes`; preço é copiado do serviço no momento da importação. |
| triggers de conflito | validação em transação do backend | O importador aplica a mesma regra: conflito é pulado com aviso. Linhas `CANCELADO` podem coexistir (melhoria sobre o trigger, que bloqueia até canceladas). |

Regras de segurança do importador: nada é atualizado ou apagado; dados já
existentes são preservados; a importação roda em **uma transação única** (erro
reverte tudo); IDs auto-incremento ausentes são numerados como em um banco novo.

## Executando

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py import_sistema_agendamento "../Sistema-Agendamento (3).sql"
python manage.py changepassword admin@mariana.com   # para usuários importados
```

## Sugestões de melhoria para o SQL da branch `B`

1. **Senhas**: remover `senha_hash` dos INSERTs de exemplo — o valor
   `$2b$12$hash_exemplo_123` não é um hash válido nem compatível com Django.
   Criar contas sempre pela aplicação.
2. **Gramática do trigger**: `Esta profissional já possui` → `Este profissional
   já possui` (ou `A profissional...`).
3. **Trigger de UPDATE**: considerar também o novo status (não bloquear quando
   `NEW.status = 'CANCELADO'`) e validar se o horário está dentro de
   `horario_disponivel` (hoje só verifica conflito entre agendamentos).
4. **CHECKs**: `hora_fim > hora_inicio` em `horario_disponivel` e
   `agendamento` (MySQL 8.0.16+ suporta `CHECK`); `preco >= 0`;
   `duracao_minutos > 0`.
5. **Preço histórico**: em `agendamento`, guardar `preco` no momento do
   agendamento (hoje o preço muda se o serviço for editado — o site do Aura já
   faz o snapshot).
6. **ENUM de dias**: padronizar acentuação (`Terca`/`Terça`) ou usar
   `TINYINT` (0–6) como o site.
7. **Unicidade**: impedir dois `horario_disponivel` duplicados
   (`UNIQUE (id_profissional, dia_semana, hora_inicio)`) e `cliente.email`
   único quando usado como login.
8. **Índices**: `cliente(telefone)` para busca; `agendamento(status)`.
9. **LGPD**: não versionar dados pessoais reais em `INSERT`s; dados de teste
   devem ser claramente fictícios (os atuais são — mantenha assim).
10. **`DROP DATABASE`**: separar o script em `schema.sql` (estrutura) e
    `seed.sql` (dados de teste) para não apagar acidentalmente um banco real.

## Segurança

- Nunca commitar `.env`, senhas ou hashes reais.
- O ZIP/backup de dados contém credenciais — proteja a cópia.
- Importação não cria senha padrão; qualquer acesso administrativo exige
  definição interativa de senha.

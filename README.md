# Aura — gestão leve, beleza livre

Sistema de gerenciamento e agendamento para uma profissional autônoma de beleza. Interface responsiva em português, JavaScript sem framework, API Django REST Framework, sessões do Django e MySQL.

**GitHub Pages serve somente o front-end. Python, sessões e banco de dados precisam de um servidor separado.** Nenhuma senha, credencial de banco ou dado real de cliente está incluído no repositório.

## Instalação no Windows

Há dois pacotes online preparados para Windows 10/11 x64: **Essencial** (Python/MySQL já preparados) e **Completo** (preparação dos pré-requisitos via winget). Ambos incluem LEIAME, configurador, atalhos e backup. A instalação abre o Aura localmente, sem depender da prévia do Arena; não publica um site na internet.

- [Guia de uso dos instaladores — LEIAME](installer/windows/LEIAME.txt)
- [Conteúdo dos pacotes](installer/windows/CONTEUDO.txt)
- [Build, testes e publicação dos instaladores](installer/README.md)
- [Releases do projeto](https://github.com/Random01-01/Teste-BD/releases)

## O que está implementado

- **Profissional:** painel com métricas calculadas, agenda diária/semanal, busca, clientes e seus históricos, serviços (ativação/desativação), expediente semanal, intervalos, bloqueios, prazo de cancelamento, confirmação/recusa/conclusão de atendimentos.
- **Cliente:** cadastro com aceite dos termos, login/logout, recuperação e redefinição de senha por e-mail, perfil, catálogo e detalhes de serviços, horários disponíveis, reservas, reagendamento, cancelamento e histórico.
- **Segurança:** senhas com hash Django, CSRF inclusive no login/cadastro, sessões HTTP-only, permissões por objeto, isolamento entre clientes, limitação de requisições e configurações HTTPS de produção.
- **Integridade:** validação de horários no servidor, duração calculada, preço preservado na reserva, transações e mutex `SELECT ... FOR UPDATE` no MySQL/InnoDB. Intervalos, pausas, bloqueios e status são considerados.
- **Notificações:** caixa de notificações dentro do sistema; recuperação de senha por e-mail. Não há integração com WhatsApp/SMS nem pagamentos.
- **Entrega:** migrations, dados fictícios opcionais, Django Admin, Docker opcional, testes de API e navegador, CI com MySQL 8.4 e workflow de publicação do front-end.

## Arquitetura

```text
GitHub                               Servidor compatível com Django
├─ Código + GitHub Actions           └─ Gunicorn + proxy HTTPS
└─ GitHub Pages (frontend/)  ─Fetch─►    └─ Django REST API + sessões
                                            └─ MySQL 8 / InnoDB
```

```text
frontend/                HTML, CSS, JavaScript e assets estáticos
backend/
  config/                settings, URLs, WSGI
  users/                 usuário com e-mail único e autenticação
  clients/               perfis, validação e serialização
  services/              serviços e preços
  appointments/          agenda, expediente, bloqueios, notificações, API e testes
scripts/                 servidor de desenvolvimento com proxy e build estático
tests/                   testes Playwright
.github/workflows/       validação, testes MySQL e GitHub Pages
compose.yml              MySQL + API (opcional)
```

## 1. Pré-requisitos e clone

- Python **3.11 ou superior** (recomendado 3.12), Node.js **22+**, npm e Git.
- MySQL **8.0.11+**, recomendado **8.4**, tabelas **InnoDB** e `utf8mb4`.
- Linux/macOS: instalar Python pelo gerenciador do sistema ou [python.org](https://www.python.org/downloads/). Windows: instalador oficial, marcando **Add Python to PATH**.

```bash
git clone https://github.com/Random01-01/Teste-BD.git
cd Teste-BD
python3 -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
```

No Ubuntu/Debian, instale os pré-requisitos do driver `mysqlclient`:

```bash
sudo apt update
sudo apt install python3-dev python3-venv build-essential pkg-config default-libmysqlclient-dev
# Ubuntu: sudo apt install mysql-server
# macOS: brew install mysql pkg-config
```

Em Windows, utilize MySQL Community Server e o wheel de `mysqlclient` compatível com sua versão do Python. WSL2 é uma alternativa.

```bash
pip install -r backend/requirements.txt
npm ci
```

## 2. Banco MySQL

Inicie o serviço MySQL (`sudo systemctl start mysql` no Ubuntu ou `brew services start mysql` no macOS), entre no cliente administrativo e execute:

```sql
CREATE DATABASE aura CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'aura'@'localhost' IDENTIFIED BY 'SUBSTITUA_POR_UMA_SENHA_FORTE';
GRANT ALL PRIVILEGES ON aura.* TO 'aura'@'localhost';
```

O usuário de aplicação **não deve ser root**. Em um banco externo, use o host e o usuário fornecidos pelo provedor, restrinja o acesso de rede ao back-end e configure TLS conforme as exigências do serviço (opção `ssl` do `mysqlclient`, usando certificados montados no servidor). Não exponha a porta 3306 publicamente. Faça backups criptografados e teste a restauração.

## 3. Configuração do back-end

```bash
cp backend/.env.example backend/.env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Coloque a chave gerada em `SECRET_KEY`, sem publicá-la. Edite `backend/.env` para desenvolvimento:

```dotenv
DEBUG=True
SECRET_KEY=SUBSTITUA_PELA_CHAVE_GERADA
DB_ENGINE=mysql
DB_NAME=aura
DB_USER=aura
DB_PASSWORD=SUBSTITUA_PELA_SENHA_DO_BANCO
DB_HOST=localhost
DB_PORT=3306
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
FRONTEND_URL=http://localhost:5173/
COOKIE_SAMESITE=Lax
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Os valores em maiúsculas acima são placeholders, não credenciais utilizáveis. O `.env` é ignorado pelo Git e pelo Docker build.

```bash
cd backend
python manage.py migrate
python manage.py createsuperuser   # Informe e-mail e senha no terminal
python manage.py runserver 0.0.0.0:8000
```

O superusuário acessa tanto o painel Aura quanto `http://localhost:8000/admin/`. Usuários `is_staff=True` são profissionais; contas de clientes criadas pela API não podem atribuir privilégios a si mesmas. No Django Admin, os objetos de agenda são somente leitura: use o painel/API para manter as validações e os locks transacionais.

## 4. Front-end local

Em outro terminal, na **raiz** do repositório:

```bash
npm run dev
```

Acesse `http://localhost:5173`. O Node serve arquivos estáticos e encaminha `/api/` para o Django em `127.0.0.1:8000`. **O navegador sempre usa URLs relativas**, inclusive em prévias remotas; não precisa acessar o localhost do servidor. Se mudar a porta do Django, defina `BACKEND_URL` no ambiente do servidor Node.

1. Entre com o usuário criado por `createsuperuser`.
2. Configure os horários de atendimento (inicialmente não há dias abertos).
3. Cadastre serviços e clientes, ou crie uma conta de cliente pela tela de cadastro.
4. Crie e gerencie agendamentos.

## 5. Demonstração opcional (somente desenvolvimento)

O sistema não cria credenciais padrão. Para dados fictícios, com `DEBUG=True`:

```bash
# Execute a partir de backend/, com o ambiente virtual ativo.
export DEMO_EMAIL=demo@example.com
export DEMO_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
python manage.py seed_demo
```

O comando cria serviços, 12 clientes fictícias com e-mails `example.com`, histórico e agenda em datas próximas. Não aceita execução com `DEBUG=False`. Para abrir automaticamente o painel fictício na prévia, passe os mesmos `DEMO_EMAIL`/`DEMO_PASSWORD`, `DEBUG=True` e `DEV_DEMO=true` ao `npm run dev`. Também é possível colocá-los no `.env` **local e ignorado**. A rota temporária `/api/demo-login/` existe apenas no proxy de desenvolvimento; não existe na API Django nem no build do Pages. Nunca ative esse modo com dados reais.

**Alternativa sem MySQL para experimentar a interface:** `DB_ENGINE=sqlite`, `DEBUG=True`. Isso utiliza `backend/db.sqlite3`, ignorado pelo Git. SQLite **não implementa o mutex de linhas do MySQL** e não é autorizado para produção. A prévia desta implementação usa esse modo; valide MySQL antes de receber clientes reais.

## 6. Testes

```bash
# Na raiz:
npm test                      # Verificação sintática e testes unitários JS
npm run build                 # Gera dist/ estático, sem modo demo

# Em backend/, com um banco de TESTE configurado:
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --verbosity=2
```

O Django cria e remove um banco `test_<DB_NAME>`. Para executar testes MySQL fora do CI, conceda ao usuário de testes as permissões de criação/remoção desse banco; não use um banco de produção. Os testes incluem CSRF, registro, hashes, recuperação de senha, propriedade dos objetos, intervalos, bloqueios, preço/duração calculados, transições de status e duas requisições simultâneas. O teste de concorrência exige MySQL; em SQLite ele é explicitamente ignorado.

Testes de navegador precisam de um **ambiente de demonstração descartável**:

```bash
npx playwright install --with-deps chromium
# Configure/rode seed_demo primeiro; exporte DEV_DEMO=true e a mesma DEMO_PASSWORD.
npm run test:e2e
```

O Playwright inicia os dois servidores se não estiverem abertos. Use `PYTHON=/caminho/para/python` se necessário. Os testes exercitam busca, agenda, reserva/confirmação/cancelamento, horários, bloqueios, configurações, cadastro/perfil/logout/recuperação e layout móvel. Criam somente dados fictícios; use banco separado. O workflow executa tudo em MySQL 8.4 descartável.

## 7. Regras da agenda

- Uma profissional, um atendimento por vez. Fuso: **America/Sao_Paulo**. Horários na interface e na API são locais nesse fuso.
- O servidor calcula término e preço, ignorando valores forjados pelo cliente.
- Reservas pendentes, confirmadas e concluídas ocupam horário; canceladas e recusadas liberam a vaga.
- Todo novo agendamento ou reagendamento valida expediente, pausa, bloqueios, duração, futuro e intervalo entre atendimentos.
- A linha singleton `ScheduleSettings(id=1)` é criada por migration. Escritas na agenda, nos bloqueios, expediente, serviços e configurações adquirem seu lock dentro de `transaction.atomic()`.
- Clientes só podem alterar/cancelar reservas próprias pendentes ou confirmadas, respeitando a antecedência configurada. A profissional pode abrir exceção ao prazo.
- Reagendar volta o status para pendente. Um atendimento só pode ser concluído se estiver confirmado e já tiver terminado.
- `DELETE` de agendamento **cancela**, preservando histórico. `DELETE` de serviço desativa; de cliente desativa o perfil e a conta. Clientes cadastradas pela profissional recebem senha inutilizável e podem definir uma usando recuperação de senha.
- Mudanças de expediente/serviços não apagam reservas já existentes. Revise a agenda e remaneje-as. Um bloqueio sobre uma reserva ativa é rejeitado.
- O preço é guardado na reserva; edição de preço não altera o histórico. A duração exibida é calculada do início/fim reservado.

## 8. Publicar somente o front-end no GitHub Pages

1. Publique primeiro o back-end Django com HTTPS e banco MySQL persistente.
2. Em **Settings → Secrets and variables → Actions → Variables**, crie a variável pública `API_URL`, por exemplo `https://api.seudominio.com/api` (sem barra final).
3. Em **Settings → Pages → Build and deployment**, selecione **GitHub Actions**.
4. Integre este trabalho à branch `main`. O workflow valida Python/JS, testa com MySQL, executa testes de navegador e gera `dist/`.
5. Somente o conteúdo de `dist/` é publicado. O deploy só roda em `main`, depois dos testes, e com `API_URL` configurada. Sem a variável, testes/build ainda rodam, mas a publicação é ignorada.

A interface utiliza caminhos relativos e rotas `#hash`; funciona tanto em `usuario.github.io/` quanto em `usuario.github.io/Teste-BD/`, sem regras especiais para recarregar rotas. O build não contém secrets, sessões ou banco.

Build manual:

```bash
API_URL=https://api.seudominio.com/api npm run build
```

Alternativa: edite `frontend/js/config.js` antes de servir os arquivos diretamente. `API_URL` é configuração **pública**, nunca coloque tokens nela. O servidor de desenvolvimento usa `/api` por padrão. Não publique `http://localhost:8000/api` em um site público.

## 9. CORS, CSRF e cookies entre domínios

Exemplo para Pages + API em hosts diferentes:

```dotenv
DEBUG=False
ALLOWED_HOSTS=api.seudominio.com
CORS_ALLOWED_ORIGINS=https://seu-usuario.github.io
CSRF_TRUSTED_ORIGINS=https://seu-usuario.github.io
FRONTEND_URL=https://seu-usuario.github.io/Teste-BD/
COOKIE_SAMESITE=None
```

Origens **não** contêm caminho (`/Teste-BD`); `FRONTEND_URL` contém o caminho do site porque compõe o link de recuperação. Configure a origem exata do domínio personalizado se houver. Não use `CORS_ALLOW_ALL_ORIGINS` com credenciais.

Na **prévia incorporada de desenvolvimento**, o proxy ajusta os cookies apenas para a origem HTTPS exata da prévia, utilizando `SameSite=None; Secure; Partitioned`. A interface renova tokens desatualizados uma vez e oferece abertura em nova aba se o navegador ainda bloquear cookies. O CSRF continua obrigatório; essa política de prévia não é publicada no Pages. Veja os detalhes no [README do front-end](frontend/README.md#prévia-incorporada-e-recuperação-automática-de-csrf).

A API fornece um token CSRF em `GET /api/auth/csrf/`. O front-end o mantém em memória e o envia em `X-CSRFToken`, sempre com `credentials: 'include'`. Após login, cadastro e logout, o token é renovado. Isso funciona sem tentar ler, pelo JavaScript do Pages, o cookie pertencente ao domínio da API.

Com `DEBUG=False`, o projeto ativa `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `CSRF_COOKIE_HTTPONLY=False`, redirecionamento HTTPS e HSTS.

**Limitação real dos navegadores:** cookies de terceiros podem ser bloqueados mesmo com `SameSite=None; Secure`. Para sessões confiáveis, prefira **domínios do mesmo site**: GitHub Pages em `agenda.seudominio.com` (domínio personalizado) e Django em `api.seudominio.com`, ambos HTTPS, com `COOKIE_SAMESITE=Lax`. Configure CORS/CSRF para `https://agenda.seudominio.com`. Se necessário, use proxy reverso para expor tudo na mesma origem. Não é possível contornar o bloqueio do navegador apenas ligando CORS.

## 10. Publicar Django e MySQL

Use um VPS/container/PaaS que execute Python e mantenha acesso a MySQL. GitHub Pages não executa WSGI nem mantém sessões.

1. Instale as dependências, configure as variáveis no gerenciador de secrets do provedor e defina `DEBUG=False`.
2. Use um banco MySQL persistente, privado e com backups.
3. Execute `python manage.py migrate`, `python manage.py collectstatic --noinput` e `python manage.py createsuperuser`.
4. Execute `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3` em `backend/`, sob um supervisor.
5. Configure um proxy HTTPS (Nginx/Caddy ou o proxy do provedor) para a API. Sirva `backend/staticfiles/` em `/static/` para o Django Admin. Não use `runserver` em produção.
6. Só defina `TRUST_PROXY=True` se o proxy remover o header `X-Forwarded-Proto` enviado externamente e defini-lo corretamente. Caso contrário, não confie nesse header.
7. Configure SMTP real com `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` e `DEFAULT_FROM_EMAIL`. Em desenvolvimento o console imprime os links; produção não deve expor esses logs.
8. Execute `python manage.py check --deploy` com configuração de produção. Avalie os avisos de HSTS conforme seus subdomínios; a inclusão de todos os subdomínios não é ativada automaticamente.
9. Configure limites de login no proxy e cache compartilhado (Redis/Memcached) se usar múltiplos workers/instâncias. O throttle padrão usa o cache local do Django, não é uma defesa distribuída completa.
10. Revise a política de privacidade/termos, identifique o controlador e canal de contato, defina retenção de dados, controle acesso aos backups e mantenha as dependências atualizadas antes de usar dados reais.

### Docker opcional

```bash
# Configure backend/.env e exporte uma senha root exclusiva para o banco local.
export MYSQL_ROOT_PASSWORD="$(openssl rand -hex 24)"
docker compose --env-file backend/.env up -d --build
docker compose --env-file backend/.env exec api python manage.py migrate
docker compose --env-file backend/.env exec api python manage.py collectstatic --noinput
docker compose --env-file backend/.env exec api python manage.py createsuperuser
```

A API fica na porta 8000. MySQL fica apenas na rede interna do Compose. O arquivo não inclui um terminador TLS: em produção coloque um proxy na frente, configure hosts/origens e sirva o volume `staticfiles` no proxy. Guarde os secrets no ambiente do provedor. `docker compose down -v` **apaga os dados**; não o use sem um backup.

## API e documentação adicional

- [Back-end e endpoints](backend/README.md)
- [Front-end, build e rotas](frontend/README.md)

### Estado da validação desta entrega

- Testes de API executados localmente em SQLite; teste de concorrência MySQL é separado e não é validado pelo SQLite.
- Testes de navegador executados contra a API real da demonstração, incluindo viewport móvel.
- CI preparado para MySQL 8.4; publicação e execução do CI dependem da configuração do repositório. Nenhum deploy público de Django/MySQL/Pages foi efetuado automaticamente.

O banner é uma imagem gerada para este projeto. DM Sans e Manrope são distribuídas localmente sob SIL Open Font License (licenças em `frontend/assets/fonts/`). Nenhum serviço de fontes externo é necessário.

## Instância de teste limpa, separada da demonstração normal

Para testar autenticação sem reutilizar banco, cookies ou chave de sessão anteriores:

```bash
# Na raiz, com o Python do ambiente virtual e dependências instaladas:
python scripts/setup-test-preview.py
DJANGO_ENV_FILE=backend/.env.test-preview python backend/manage.py createsuperuser
DJANGO_ENV_FILE=backend/.env.test-preview python backend/manage.py runserver 0.0.0.0:8001 --noreload
# Outro terminal:
node --env-file=backend/.env.test-preview scripts/dev-server.mjs
```

- Interface: porta **8080**, identificada como **Aura — Teste limpo**, começando no login, sem login automático.
- API: porta **8001**; todas as chamadas do navegador continuam relativas à interface.
- Banco: `backend/test-preview.sqlite3`, independente de `backend/db.sqlite3`.
- Configuração: `backend/.env.test-preview`, chave aleatória própria e cookies `aura_test_session` / `aura_test_csrf`.
- A senha de administrador é definida por `createsuperuser`, nunca escrita no código. Os dados semeados são fictícios.
- Cookies: `Secure; SameSite=None; Partitioned`. Nesta instância dedicada HTTPS, a política é explícita e não depende do `Host` interno que o proxy da plataforma pode reescrever. Não confia em headers de encaminhamento fornecidos pelo cliente; o Django continua validando o token, cookie e a origem CSRF.
- Recuperação de senha: e-mails simulados em `backend/.test-preview-emails/`, sem enviar mensagens reais. Esses arquivos contêm links sensíveis e são excluídos do Git e do Docker build.
- O script **recusa sobrescrever** um ambiente/banco de teste existente. Não apaga nem modifica a base normal.

A configuração é **HTTPS-only**. No Arena a origem é detectada automaticamente. Fora dele, defina `TEST_PREVIEW_ORIGIN=https://origem-do-seu-proxy` antes de executar o setup e configure o terminador TLS. Não use esta instância com dados reais nem publique suas credenciais de teste.

### Acesso protegido à prévia do Arena

Abra **Aura — Teste limpo** pelo painel de prévia da plataforma. A URL direta `*.e2b.app` pode exigir um header de acesso de infraestrutura e responder **Missing Traffic Access Token** fora desse painel. Esse header não é a senha nem o token CSRF do Django. Não inclua tokens da plataforma no front-end, no repositório ou em links públicos.

O isolamento acima cria uma nova instância da aplicação **dentro do mesmo sandbox**, não provisiona um novo sandbox Arena nem remove seu controle de acesso. Se o próprio painel autorizado da plataforma apresentar essa mensagem, a conexão da prévia precisa ser restaurada pelo Arena; alterar Django ou desativar CSRF não resolve a autorização de infraestrutura.

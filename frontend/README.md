# Front-end Aura

HTML5, CSS3 e JavaScript ES Modules, com Fetch API. Sem framework ou bundler necessário. Fontes locais e assets relativos; funciona em subdiretórios do GitHub Pages.

## Desenvolvimento

Na raiz do projeto:

```bash
npm ci
npm run dev
```

Servidor em `0.0.0.0:5173`. `/api/` é encaminhado pelo servidor Node para o Django em `127.0.0.1:8000`; o navegador nunca precisa alcançar o localhost do back-end. Inicie o Django separadamente.

`frontend/js/config.js` contém somente configuração pública:

```javascript
window.AURA_CONFIG = {
  API_URL: 'https://api.seudominio.com/api',
  DEMO: false,
};
```

Para servir os arquivos sem o proxy Node durante desenvolvimento, é possível usar `API_URL: 'http://localhost:8000/api'` **apenas quando o navegador está na mesma máquina do Django**. Nesse caso configure CORS/CSRF para a origem do front-end. Em prévia remota, mantenha `/api` e o proxy.

## Build e Pages

```bash
API_URL=https://api.seudominio.com/api npm run build
```

O script copia `frontend/` para `dist/`, gera uma configuração sem demo e inclui `.nojekyll`. Publique **somente** `dist/`. Nenhum Python é copiado. Para Pages, configure a variável de repositório `API_URL` e habilite GitHub Actions em Settings → Pages; o workflow da raiz executa o build e a publicação.

## Navegação

| Rota hash | Tela |
|---|---|
| `#inicio` | Início e apresentação dos serviços |
| `#servicos` | Catálogo; detalhes em diálogo acessível |
| `#login`, `#cadastro` | Acesso e cadastro |
| `#recuperar-senha`, `#redefinir-senha?uid=…&token=…` | Recuperação por e-mail |
| `#perfil` | Perfil da cliente |
| `#meus-agendamentos` | Reservas e reagendamentos da cliente |
| `#historico` | Atendimentos finalizados |
| `#painel` | Painel da profissional |
| `#agenda` | Agenda diária/semanal e bloqueios |
| `#clientes` | Clientes, cadastro e histórico individual |
| `#horarios` | Expediente e pausas |
| `#configuracoes` | Studio, intervalos e política de cancelamento |

Reserva, escolha de horário, detalhes, edição e confirmação utilizam diálogos com foco gerenciado e fechamento por Escape. A busca global também abre com `Ctrl/Cmd + K`. Menu responsivo, tabelas com rolagem **interna** no celular, labels, mensagens de validação e estados vazios.

## Sessão e segurança

- `credentials: 'include'` em toda requisição.
- CSRF buscado na API e guardado apenas em memória; renovado depois do login.
- Nenhum token em localStorage, nenhuma senha no build.
- `api.js` centraliza erros JSON, CSRF, cookies e URL configurável.
- O back-end é a autoridade de permissões e regras, não os botões da interface.
- Se o token CSRF ficar desatualizado, o cliente o renova uma vez. Se a sessão de login expirar, entre novamente. Cookies bloqueados recebem orientação para abrir a aplicação em nova aba.
- Em hospedagem cross-site, verifique bloqueio de cookies de terceiros. Domínios personalizados do mesmo site são recomendados; leia o README principal.

## Testes

```bash
npm test
npm run test:e2e
```

O segundo comando exige demonstração descartável com dados semeados e Playwright instalado. Veja o guia principal. A imagem do banner foi gerada para este projeto; fontes DM Sans e Manrope incluem suas licenças locais.

### Prévia incorporada e recuperação automática de CSRF

Em uma prévia dentro de um iframe de outro site, `SameSite=Lax` impede o envio dos cookies, mesmo que o usuário informe a senha correta. O proxy **de desenvolvimento** reconhece a origem HTTPS exata configurada em `PREVIEW_ORIGIN` (ou a origem deste sandbox Arena, automaticamente) e acrescenta `SameSite=None; Secure; Partitioned` somente aos cookies Django nessa origem. Cookies HTTP-only continuam HTTP-only, inclusive na exclusão durante logout. Requisições locais HTTP e o build de produção não recebem essa alteração.

O cliente busca tokens com `cache: 'no-store'`. Em uma rejeição explícita de CSRF por cookie/token, busca um token novo e repete a requisição **uma única vez**. Não repete erros de senha, falta de permissão, limite de tentativas, erro de origem nem falhas de rede. Fora de uma prévia gerenciada, a mensagem pode oferecer **Abrir Aura em nova aba**. No Arena, orienta usar/recarregar o painel autorizado de prévia, sem gerar um link direto que perderia a autorização de tráfego da plataforma. Nenhuma proteção CSRF é desativada.

Além dos testes unitários (`npm test`), o teste `embedded-preview.spec.js` usa um iframe HTTPS de outro site, um certificado temporário e o proxy/API reais para verificar cookies particionados, login, persistência de sessão, escrita protegida, logout e recuperação de senha. O transporte não simula respostas de autenticação nem injeta cookies. Para rodá-lo sem privilégios de porta em desenvolvimento, pare os servidores existentes e execute `PREVIEW_ORIGIN=https://aura-preview.example:4443 npm run test:e2e`; o Playwright inicia os servidores com essa mesma origem. Chrome ignora somente a autoridade do certificado temporário do teste, não as regras de cookies, CORS ou CSRF.


### Instância limpa e versões de assets

O script `scripts/setup-test-preview.py` prepara a instância HTTPS de teste da porta 8080 com banco e nomes de cookies independentes, login manual e faixa de identificação. Leia o guia na raiz. Os arquivos do servidor de desenvolvimento usam `Cache-Control: no-store`, e os entrypoints da interface têm versão explícita para evitar reutilizar os módulos antigos durante correções de sessão.

`PREVIEW_COOKIE_POLICY=partitioned` é uma opção explícita apenas do proxy de desenvolvimento (`DEBUG=True` + origem HTTPS). Na instância dedicada, preserva cookies isolados mesmo quando o proxy da plataforma substitui o Host pelo endereço interno. Não altera a autenticação da API, não forja cookies e não autoriza novas origens de requisição. O build estático não inclui essa opção nem as credenciais da instância.

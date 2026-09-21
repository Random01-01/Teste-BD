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
- Se a sessão expirar, novas operações são rejeitadas pela API; atualize a página e entre novamente.
- Em hospedagem cross-site, verifique bloqueio de cookies de terceiros. Domínios personalizados do mesmo site são recomendados; leia o README principal.

## Testes

```bash
npm test
npm run test:e2e
```

O segundo comando exige demonstração descartável com dados semeados e Playwright instalado. Veja o guia principal. A imagem do banner foi gerada para este projeto; fontes DM Sans e Manrope incluem suas licenças locais.

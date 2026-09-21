# Instaladores Windows do Aura

Dois instaladores **online** para Windows 10/11 x64:

| Pacote | Aplicação | Bibliotecas Python | Python / VC++ / MySQL |
|---|---|---|---|
| Essencial | Incluída | Baixadas do PyPI em venv privado | Devem estar preparados no computador |
| Completo | Incluída | Baixadas do PyPI em venv privado | Preparados via winget, se ausentes |

Ambos incluem **LEIAME.txt**, **CONTEUDO.txt**, atalhos, manifesto de arquivos e versão. Os ZIPs `Aura-Arquivos-*` são alternativas sem o assistente gráfico: extraia e execute `INSTALAR.cmd`. O EXE é recomendado para instalar/atualizar/desinstalar os arquivos e atalhos.

**Não são instaladores offline nem publicação em hospedagem.** A aplicação instalada escuta apenas em `127.0.0.1:8765`, com front-end/API na mesma origem, Django + Waitress e MySQL. Não requer Node.js no computador do usuário e não usa a prévia/token do Arena.

## Dados e segurança

- Programa em `%LOCALAPPDATA%\Programs\Aura`; dados em `%LOCALAPPDATA%\Aura`.
- O Completo cria uma instância privada de MySQL 8.4, normalmente na porta 3307. Não reutiliza dados/serviços existentes na porta 3306.
- Durante o bootstrap, MySQL usa apenas shared memory, sem TCP; as senhas técnicas são aleatórias. A conta web administradora é criada interativamente com validação de senha Django.
- Configuração e dados recebem ACL restrita ao usuário e SYSTEM. Não há senha padrão ou credenciais nos EXEs/ZIPs.
- Dados e pré-requisitos compartilhados são preservados na desinstalação. Faça backup antes de atualizar.
- O perfil `config.desktop` mantém `DEBUG=False`, validação de host/origem, sessões HTTP-only e CSRF. Permite HTTP **somente no servidor ligado a loopback**. Não o use em servidor público.
- A função de backup exporta SQL, não copia arquivos MySQL vivos. O ZIP de backup contém credenciais e não é criptografado: proteja a cópia externa.

## Gerar os arquivos no Linux ou Windows

```bash
python scripts/build-windows.py --version 0.1.0
```

Saída: `dist/windows/`, com dois ZIPs, documentos e checksums. O empacotamento usa **lista permitida**, não `zip` do repositório inteiro. Não inclui `.env`, bancos, demos, testes, caches, `.git`, node_modules ou dados privados. Os scripts PowerShell são convertidos para UTF-8 com BOM para Windows PowerShell 5.1.

Para compilar os dois EXEs, execute no Windows com Inno Setup 6 atualizado:

```powershell
$compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
foreach ($edition in @('Essential','Complete')) {
  $payload = (Resolve-Path "dist/windows/payload/$edition").Path
  $output = (Resolve-Path 'dist/windows').Path
  & $compiler '/DAppVersion=0.1.0' "/DEdition=$edition" "/DPayloadDir=$payload" "/DOutputPath=$output" installer/windows/Aura.iss
}
python scripts/build-windows.py --checksums-only
```

## Testes e release

O workflow **Windows installers** roda em pushes da branch de trabalho e de `main`, ou manualmente quando registrado no repositório. Ele:

1. Instala dependências Python no Windows x64.
2. Executa testes do empacotador/WSGI e valida sintaxe PowerShell.
3. Gera payloads sem segredos.
4. Obtém o MSI oficial MySQL 8.4.9, verificando o SHA256 publicado no manifesto winget dessa versão.
5. Testa uma base MySQL privada real, migrations, servidor local, CSRF, login/logout e backup.
6. Compila os dois EXEs e testa a extração silenciosa dos arquivos.
7. Publica os arquivos como **artefato do workflow**, com SHA256SUMS.

A instalação completa interativa via winget/UAC e a criação manual da administradora ainda devem passar por validação em uma VM Windows 10/11 limpa antes de uma release estável. O teste de CI verifica os componentes nativos, mas não substitui esse teste de experiência do usuário.

Para uma release, baixe o artefato aprovado e use `gh release create`/`gh release upload`. Não envie `dist/` ao Git. Prefira uma **pré-release** para a primeira distribuição. Inclua os dois EXEs, dois ZIPs, LEIAME, CONTEUDO e SHA256SUMS. Se a compilação Windows falhar, não publique EXEs como validados.

Os EXEs não são assinados digitalmente nesta versão; distribuição estável requer certificado Authenticode/assinatura e nova geração dos checksums **após** assinar. Nunca desative SmartScreen como solução de distribuição.

## Manutenção dos pré-requisitos

O setup completo usa os IDs `Python.Python.3.13`, `Microsoft.VCRedist.2015+.x64` e `Oracle.MySQL` (8.4.9) na fonte winget. Atualizações do pin MySQL exigem revisar também URL/SHA256 no workflow e executar os testes. Um download indisponível deve falhar claramente, nunca desativar a verificação ou recorrer a executáveis sem origem conhecida.

Veja o guia completo para o usuário em [windows/LEIAME.txt](windows/LEIAME.txt).

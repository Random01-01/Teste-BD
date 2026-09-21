## Aura 0.1.0 — Windows 10/11 x64 (pré-release)

Duas opções **online** para instalar o Aura no computador:

| Download | Quando usar |
|---|---|
| **Aura-Setup-Essencial-0.1.0.exe** | Python 3.12/3.13 x64, Visual C++ Runtime e MySQL local já preparados. |
| **Aura-Setup-Completo-0.1.0.exe** | Preparar também Python, Visual C++ Runtime e MySQL 8.4 via winget, se ausentes. |

**Comece pelo `LEIAME.txt`.** O `CONTEUDO.txt` explica os arquivos incluídos. Os ZIPs `Aura-Arquivos-*` são alternativas sem o assistente gráfico; extraia tudo e execute `INSTALAR.cmd`.

### Incluído
- Front-end e API Django locais, migrations e servidor Waitress.
- Configurador, atalhos de início/configuração/backup, manifesto de arquivos.
- No Completo: banco MySQL privado, normalmente na porta 3307, sem apagar/reutilizar bancos existentes.
- Conta administradora criada durante a configuração. **Não existe usuário/senha padrão.**
- Dados separados dos programas e preservados na desinstalação.

### Importante
- É uma instalação **local**: abre `http://127.0.0.1:8765/#login`, não publica um site na internet.
- Não depende da prévia do Arena ou de Traffic Access Token.
- Requer internet; não inclui os runtimes/dependências já baixados para uso offline.
- O Completo requer o **App Installer/winget** do Windows e autorização de UAC quando os instaladores oficiais solicitarem.
- EXEs **não assinados digitalmente**; SmartScreen pode avisar sobre editor desconhecido. Verifique origem e SHA256, sem desativar proteções do Windows.
- Recuperação de senha usa e-mails simulados em pasta privada até configurar SMTP.
- Faça backup antes de atualizar. O ZIP de backup contém dados/credenciais e não é criptografado.

### Validação
Compilação dos dois EXEs em Windows, extração silenciosa, testes do empacotamento e teste funcional com MySQL real (inicialização privada, migrations, interface, CSRF, login/logout e backup).

A interação completa do assistente/winget/UAC em uma VM Windows 10/11 limpa ainda precisa de validação manual. Por isso esta entrega é uma **pré-release para testes**, não uma versão estável.

`SHA256SUMS.txt` acompanha os arquivos. Para conferir um download:
```powershell
Get-FileHash .\Aura-Setup-Completo-0.1.0.exe -Algorithm SHA256
```
Compare com a entrada de mesmo nome no arquivo de checksums.

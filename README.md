# Cyberia Bot

Cyberia Bot é um projeto desenvolvido para oferecer funcionalidades diretamente em servidores Discord. 

## Funcionalidades

- **Música**: Toque músicas do YouTube em canais de voz do Discord.
- **Comandos Personalizados**: Diversos comandos interativos para membros.
- **Efemeridade & Mensagens Temporárias**: Suporte a respostas temporárias e notificações automáticas.

## Requisitos

- **Python**: v3.11 ou superior
- **Pip**: Gerenciador de pacotes para Python
- **Variáveis de ambiente**:
    - `DISCORD_TOKEN_TEST/DISCORD_TOKEN_PROD`: Token do bot no Discord
    - `GUILD_ID`: ID do servidor Discord onde o bot será utilizado
    - `BOT_VERSION`: No momento estou usando 0.0.1 pois ainda não lancei oficialmente
    


## Instalação

1. Clone este repositório:
    ```bash
    git clone https://github.com/rafaax/cyberia-bot.git
    ```
2. Navegue até o diretório do projeto:
    ```bash
    cd cyberia-bot
    ```
3. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```

## Uso

Configure suas variáveis de ambiente no arquivo .env (as quais falo no topico de requisitos), depois inicie o bot com o seguinte comando:
```bash
python index.py
```

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

## Contato

Para dúvidas ou sugestões, entre em contato pelo e-mail: `raphael.meireles@ssector7.com`.
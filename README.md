# ChatSocket

Chat TCP e HTTP simples com login, status online/offline, pendências e lista de conversas.

## Requisitos
- Python 3.9+
- (Opcional) venv
- Para HTTP: Flask

## Setup (com venv)
```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install flask
```

## Servidores
- TCP (central telefônica):
```sh
python3 chat_server.py 12345
```
- HTTP (web, porta 10000):
```sh
python3 http_server.py
```
Acesse: http://localhost:10000

## Clientes TCP
- Cliente com login automático:
```sh
python3 chat_client.py 127.0.0.1 12345 --nome lucas
python3 chat_client.py 127.0.0.1 12345 --nome pedro
```
- Comandos no cliente TCP:
  - `/login <seu_nome>`: faz login
  - `/dial <usuario>`: escolhe destinatário
  - digite mensagem: envia para o destinatário (offline vira pendente)
  - `/quit`: sai

## HTTP (web)
- Login por nome; Status ON/OFF; entrega automática de pendências ao ficar ON.
- Lista de conversas à esquerda; campo "Nova conversa" para abrir chat.
- Botão "Apagar" para remover usuário e conversas.
- A página atualiza automaticamente a cada 1s.

## Dicas
- Para dois usuários no web: use janelas anônimas distintas ou dois navegadores.
- Para acessar pela rede: use IP local do servidor e garanta firewall/port forwarding.

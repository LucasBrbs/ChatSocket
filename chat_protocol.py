#!/usr/bin/env python3
"""
Protocolo simples de mensagens para chat via TCP.
- send_message(sock, text): envia texto como linha UTF-8 com \n.
- recv_lines(sock): iterador de linhas recebidas (sem \n).
- system_message(text): formata mensagem de sistema.
- user_message(name, text): formata mensagem de usuário.

Comandos do cliente (convenção do servidor):
  /login <nome>
  /dial <usuario>
  /quit
"""
import socket
from typing import Iterator


def send_message(sock: socket.socket, text: str) -> None:
    data = (text + "\n").encode("utf-8")
    sock.sendall(data)


def recv_lines(sock: socket.socket) -> Iterator[str]:
    f = sock.makefile('r', encoding='utf-8', newline='\n')
    for line in f:
        yield line.rstrip('\n')


def system_message(text: str) -> str:
    return f"[sistema] {text}"


def user_message(name: str, text: str) -> str:
    return f"{name}: {text}"

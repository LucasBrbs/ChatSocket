#!/usr/bin/env python3
# Servidor de chat tipo "central telefônica":
# - Clientes fazem login com /login <nome>
# - Selecionam destinatário com /dial <usuario>
# - Mensagens são roteadas pelo servidor; se destinatário estiver offline, ficam pendentes.
import argparse
import socket
import threading
from typing import Dict, List, Optional
from chat_protocol import send_message, recv_lines, system_message, user_message

# Estado global protegido por lock
USERS: Dict[str, socket.socket] = {}           # mapa: nome -> conexão
MAILBOX: Dict[str, List[str]] = {}            # mapa: nome -> mensagens pendentes (strings)
CONNECTIONS: Dict[socket.socket, str] = {}    # mapa: conexão -> nome logado
TARGET: Dict[socket.socket, Optional[str]] = {}  # mapa: conexão -> destinatário atual
LOCK = threading.Lock()


def deliver_mailbox(username: str, conn: socket.socket) -> None:
    """Envia todas as mensagens pendentes do usuário (se houver)."""
    with LOCK:
        pendentes = MAILBOX.get(username, [])
        if not pendentes:
            return
        msgs = pendentes[:]
        MAILBOX[username] = []
    send_message(conn, system_message(f"Você tem {len(msgs)} mensagem(ns) pendente(s):"))
    for m in msgs:
        send_message(conn, m)


def send_to_user(dest: str, text: str) -> None:
    """Envia ao usuário se online; caso contrário, acumula no MAILBOX."""
    with LOCK:
        conn = USERS.get(dest)
        if conn:
            try:
                send_message(conn, text)
                return
            except Exception:
                # Em caso de erro no envio, trata como offline e acumula
                pass
        # Acumula
        MAILBOX.setdefault(dest, []).append(text)


def handle_client(conn: socket.socket, addr) -> None:
    name: Optional[str] = None
    TARGET[conn] = None
    try:
        send_message(conn, system_message("Bem-vindo. Use: /login <seu_nome>"))
        for line in recv_lines(conn):
            line = line.strip()
            if not line:
                continue

            if name is None:
                # Aguardando login
                if line.startswith('/login '):
                    candidato = line.split(' ', 1)[1].strip()
                    if not candidato:
                        send_message(conn, system_message("Nome inválido."))
                        continue
                    with LOCK:
                        if candidato in USERS:
                            send_message(conn, system_message("Nome já em uso. Tente outro."))
                            continue
                        USERS[candidato] = conn
                        CONNECTIONS[conn] = candidato
                        name = candidato
                    send_message(conn, system_message(f"Logado como {name}."))
                    send_message(conn, system_message("Use /dial <usuario> para escolher destinatário."))
                    deliver_mailbox(name, conn)
                else:
                    send_message(conn, system_message("Faça login primeiro: /login <seu_nome>"))
                continue

            # Já logado
            if line == '/quit':
                send_message(conn, system_message("Saindo..."))
                break

            if line.startswith('/dial '):
                dest = line.split(' ', 1)[1].strip()
                if not dest:
                    send_message(conn, system_message("Informe um usuário: /dial <usuario>"))
                    continue
                TARGET[conn] = dest
                online = False
                with LOCK:
                    online = dest in USERS
                if online:
                    send_message(conn, system_message(f"Canal com {dest} pronto. Envie sua mensagem."))
                else:
                    send_message(conn, system_message(f"{dest} está offline. Mensagens serão entregues quando entrar."))
                continue

            # Mensagem normal
            dest = TARGET.get(conn)
            if not dest:
                send_message(conn, system_message("Selecione um destinatário: /dial <usuario>"))
                continue

            # Roteia ou guarda
            send_to_user(dest, user_message(name, line))
            # Feedback opcional para o remetente
            send_message(conn, system_message(f"Mensagem para {dest} enviada/pendente."))
    except Exception as e:
        # Log mínimo no servidor
        try:
            print(f"[Servidor] Erro com {addr}: {e}")
        except Exception:
            pass
    finally:
        # Limpeza no logout/desconexão
        with LOCK:
            u = CONNECTIONS.pop(conn, None)
            TARGET.pop(conn, None)
            if u and USERS.get(u) is conn:
                USERS.pop(u, None)
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def main(porta: int):
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('', porta))
    servidor.listen()
    print(f"[Servidor] Central ouvindo em 0.0.0.0:{porta}")

    try:
        while True:
            conn, addr = servidor.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[Servidor] Interrompido.")
    finally:
        try:
            servidor.close()
        except Exception:
            pass
        print("[Servidor] Encerrado.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Servidor de chat (central com login, dial e mensagens offline).')
    parser.add_argument('porta', type=int, nargs='?', default=12345, help='Porta para escutar (padrão: 12345)')
    args = parser.parse_args()
    main(args.porta)

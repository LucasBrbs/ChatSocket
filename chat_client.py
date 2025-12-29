#!/usr/bin/env python3
# Cliente de chat simples (terminal)
import argparse
import socket
import sys
import threading
from chat_protocol import send_message, recv_lines


def leitor(sock: socket.socket):
    try:
        for line in recv_lines(sock):
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
    except Exception:
        pass
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass


def escritor(sock: socket.socket, nome_inicial: str | None):
    try:
        if nome_inicial:
            try:
                send_message(sock, f"/login {nome_inicial}")
            except Exception:
                return
        for line in sys.stdin:
            msg = line.rstrip('\n')
            if not msg:
                continue
            try:
                send_message(sock, msg)
            except Exception:
                break
            if msg.strip() == '/quit':
                break
    except Exception:
        pass
    finally:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass


def main(ip: str, porta: int, nome: str | None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((ip, porta))
        print(f"[Cliente] Conectado a {ip}:{porta}.")
        print("Comandos: /login <seu_nome>, /dial <usuario>, /quit")

        t_r = threading.Thread(target=leitor, args=(sock,), daemon=True)
        t_w = threading.Thread(target=escritor, args=(sock, nome), daemon=True)
        t_r.start()
        t_w.start()

        # Aguarda até que os dois threads terminem
        t_r.join()
        t_w.join()
    finally:
        try:
            sock.close()
        except Exception:
            pass
        print("[Cliente] Encerrado.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cliente de chat simples (terminal).')
    parser.add_argument('ip', nargs='?', default='127.0.0.1', help='IP do servidor (padrão: 127.0.0.1)')
    parser.add_argument('porta', type=int, nargs='?', default=12345, help='Porta (padrão: 12345)')
    parser.add_argument('--nome', help='Faz login automático com este nome', default=None)
    args = parser.parse_args()
    try:
        main(args.ip, args.porta, args.nome)
    except KeyboardInterrupt:
        print('\n[Cliente] Interrompido.')

#!/usr/bin/env python3
# HTTP chat simples (estilo "zap"), com login, online/offline, mensagens pendentes e lista de conversas.
import time
import threading
from typing import Dict, List, Tuple, Set, Optional
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app = Flask(__name__)
app.secret_key = "dev-secret-key"  # troque em produção

# Estado em memória (demo)
USERS: Dict[str, dict] = {}  # {nome: {online: bool, conversations: set[str]}}
INBOX: Dict[str, List[dict]] = {}  # destinatário -> msgs pendentes p/ entregar quando ficar online
OUTBOX: Dict[str, List[dict]] = {}  # remetente -> msgs pendentes p/ serem liberadas quando remetente ficar online
CONV: Dict[Tuple[str, str], List[dict]] = {}  # (a,b) ordenado -> lista de mensagens (entregues)
LOCK = threading.Lock()


def _key(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def ensure_user(name: str):
    with LOCK:
        USERS.setdefault(name, {"online": False, "conversations": set()})
        INBOX.setdefault(name, [])
        OUTBOX.setdefault(name, [])


def add_conv(a: str, b: str):
    with LOCK:
        USERS.setdefault(a, {"online": False, "conversations": set()})["conversations"].add(b)
        USERS.setdefault(b, {"online": False, "conversations": set()})["conversations"].add(a)


def add_to_conv_delivered(msg: dict):
    a, b = msg["from"], msg["to"]
    with LOCK:
        CONV.setdefault(_key(a, b), []).append(msg)
        USERS[a]["conversations"].add(b)
        USERS[b]["conversations"].add(a)


def deliver_inbox(user: str):
    with LOCK:
        pend = INBOX.get(user, [])
        to_deliver = pend[:]
        INBOX[user] = []
    for m in to_deliver:
        add_to_conv_delivered(m)


def deliver_outbox(user: str):
    with LOCK:
        pend = OUTBOX.get(user, [])
        to_attempt = pend[:]
        OUTBOX[user] = []
    for m in to_attempt:
        dest = m["to"]
        with LOCK:
            dest_online = USERS.get(dest, {"online": False}).get("online", False)
        if dest_online:
            add_to_conv_delivered(m)
        else:
            with LOCK:
                INBOX.setdefault(dest, []).append(m)
            add_conv(user, dest)  # conversa aparece para o remetente


def current_user() -> Optional[str]:
    return session.get("user")


@app.route("/")
def index():
    if not current_user():
        return render_template("login.html")
    return redirect(url_for("chat"))


@app.post("/login")
def login():
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Informe um nome.")
        return redirect(url_for("index"))
    ensure_user(name)
    with LOCK:
        # impede login duplo no mesmo nome
        if USERS[name]["online"]:
            flash("Nome já está online.")
            return redirect(url_for("index"))
        USERS[name]["online"] = True
    deliver_inbox(name)
    deliver_outbox(name)
    session["user"] = name
    return redirect(url_for("chat"))


@app.get("/logout")
def logout():
    user = current_user()
    if user:
        with LOCK:
            if user in USERS:
                USERS[user]["online"] = False
        session.pop("user", None)
    return redirect(url_for("index"))


@app.post("/toggle")
def toggle():
    user = current_user()
    if not user:
        return redirect(url_for("index"))
    became_online = False
    with LOCK:
        st = USERS.get(user)
        if st:
            st["online"] = not st["online"]
            became_online = st["online"]
    if became_online:
        deliver_inbox(user)
        deliver_outbox(user)
    return redirect(url_for("chat", **({"with": request.args.get("with")} if request.args.get("with") else {})))


@app.get("/chat")
def chat():
    user = current_user()
    if not user:
        return redirect(url_for("index"))

    target = request.args.get("with") or ""
    ensure_user(user)
    if target:
        ensure_user(target)

    with LOCK:
        status = USERS[user]["online"]
        conv_names = set(USERS[user]["conversations"])  # quem já falou
        # incluir remetentes com pendências quando offline
        if not status:
            senders = {m["from"] for m in INBOX.get(user, [])}
            conv_names |= senders
        conv_list = sorted(conv_names)
        thread = list(CONV.get(_key(user, target), [])) if target else []
        pending_out = [m for m in OUTBOX.get(user, []) if m["to"] == target]

    return render_template(
        "chat.html",
        user=user,
        online=status,
        conv_list=conv_list,
        target=target,
        thread=thread,
        pending_out=pending_out,
    )


@app.post("/send")
def send():
    user = current_user()
    if not user:
        return redirect(url_for("index"))
    to = (request.form.get("to") or "").strip()
    text = (request.form.get("text") or "").strip()
    if not to or not text:
        flash("Preencha destinatário e mensagem.")
        return redirect(url_for("chat", **({"with": to} if to else {})))
    ensure_user(to)

    msg = {"from": user, "to": to, "text": text, "ts": time.time()}

    with LOCK:
        sender_online = USERS[user]["online"]
        dest_online = USERS[to]["online"]

    if not sender_online:
        with LOCK:
            OUTBOX[user].append(msg)
        add_conv(user, to)
    else:
        if dest_online:
            add_to_conv_delivered(msg)
        else:
            with LOCK:
                INBOX[to].append(msg)
            add_conv(user, to)

    return redirect(url_for("chat", **({"with": to})))


@app.post("/delete_user")
def delete_user():
    user = current_user()
    if not user:
        return redirect(url_for("index"))
    target = (request.form.get("target") or "").strip()
    if not target:
        flash("Nenhum usuário selecionado para apagar.")
        return redirect(url_for("chat"))

    with LOCK:
        # Remover alvo de USERS e caixas
        USERS.pop(target, None)
        INBOX.pop(target, None)
        OUTBOX.pop(target, None)
        # Remover conversas em CONV onde target participa
        keys_to_delete = []
        for k in list(CONV.keys()):
            a, b = k
            if target in k:
                keys_to_delete.append(k)
        for k in keys_to_delete:
            try:
                CONV.pop(k, None)
            except Exception:
                pass
        # Remover referência de conversas dos demais usuários
        for u, st in USERS.items():
            try:
                st["conversations"].discard(target)
            except Exception:
                pass

    flash(f"Usuário '{target}' apagado (conversas removidas).")
    return redirect(url_for("chat"))


@app.get("/poll")
def poll():
    user = current_user()
    if not user:
        return jsonify({"error": "not_logged"}), 401
    target = (request.args.get("with") or "").strip()
    ensure_user(user)
    if target:
        ensure_user(target)
    with LOCK:
        thread = list(CONV.get(_key(user, target), [])) if target else []
        pending_out = [m for m in OUTBOX.get(user, []) if m["to"] == target]
    return jsonify({
        "thread": thread,
        "pending_out": pending_out,
        "count": len(thread) + len(pending_out)
    })


if __name__ == "__main__":
    # flask --app http_server run --debug
    app.run(host="0.0.0.0", port=10000, debug=True)

import socket
import threading
import json
import random

# Professroes Database

PROFESSORS = [
    {"nome": "Alcides Teixeira Barboza Junior",       "area": "Algoritmos e Prog 2",                        "genero": "M", "semestre": [1, 2],    "estilo": "Misto"},
    {"nome": "Alexandre dos Santos Mignon",            "area": "Algoritmos e Programação I",                 "genero": "M", "semestre": [1, 3],    "estilo": "Misto"},
    {"nome": "Andreia Cristina dos Santos Gusmão",     "area": "Banco de Dados",                             "genero": "F", "semestre": [3],       "estilo": "Misto"},
    {"nome": "Antonio Luiz Basile",                    "area": "Proj e Análise de Algoritmos I",             "genero": "M", "semestre": [3, 4, 5], "estilo": "Misto"},
    {"nome": "Bruno da Silva Rodrigues",               "area": "Redes de Computadores",                      "genero": "M", "semestre": [5],       "estilo": "Misto"},
    {"nome": "Bruno Mascaro",                          "area": "Modelagem Matemática II",                    "genero": "M", "semestre": [4],       "estilo": "Prático"},
    {"nome": "Calebe de Paula Bianchini",              "area": "Computação Paralela",                        "genero": "M", "semestre": [5],       "estilo": "Teórico"},
    {"nome": "Charles Boulhosa Rodamilans",            "area": "Projeto e Análise de Algoritmos II",         "genero": "M", "semestre": [4],       "estilo": "Misto"},
    {"nome": "Débora Bezerra Linhares Libório",        "area": "Matemática Discreta I/II",                   "genero": "F", "semestre": [3, 4],    "estilo": "Misto"},
    {"nome": "Eurico Luiz Prospero Ruivo",             "area": "Matemática Discreta I",                      "genero": "M", "semestre": [1],       "estilo": "Teórico"},
    {"nome": "Everton Knihs",                          "area": "CTS",                                        "genero": "M", "semestre": [1],       "estilo": "Teórico"},
    {"nome": "Fabio Aparecido Gamarra Lubacheski",     "area": "Paradigmas",                                 "genero": "M", "semestre": [5],       "estilo": "Misto"},
    {"nome": "Felipe Albino dos Santos",               "area": "Modelagem Matemática I/II",                  "genero": "M", "semestre": [3, 4],    "estilo": "Misto"},
    {"nome": "Gastón Alberto Concha Henriquez",        "area": "Modelagem Matemática I",                     "genero": "M", "semestre": [3],       "estilo": "Teórico"},
    {"nome": "Ivan Carlos Alcantara de Oliveira",      "area": "Estrutura de Dados I",                       "genero": "M", "semestre": [3],       "estilo": "Teórico"},
    {"nome": "Jamil Kalil Naufal Junior",              "area": "Circuitos Elétricos / Álgebra Booleana",     "genero": "M", "semestre": [1, 2],    "estilo": "Misto"},
    {"nome": "Jean Marcos Laine",                      "area": "Organização de Computadores / ED2",          "genero": "M", "semestre": [3, 4, 5], "estilo": "Misto"},
    {"nome": "Jefferson Zanutto",                      "area": "Algoritmos e Programação II",                "genero": "M", "semestre": [2],       "estilo": "Teórico"},
    {"nome": "Joaquim Pessoa Filho",                   "area": "Estrutura de Dados / Algoritmos / ED2",      "genero": "M", "semestre": [3, 4],    "estilo": "Misto"},
    {"nome": "Jonatas Abdias de Macedo",               "area": "Introdução à Cosmovisão Reformada",          "genero": "M", "semestre": [2],       "estilo": "Teórico"},
    {"nome": "Leandro Zerbinatti",                     "area": "Análise de Dados",                           "genero": "M", "semestre": [2],       "estilo": "Misto"},
    {"nome": "Leonardo Massayuki Takuno",              "area": "Algoritmos I / Algoritmos II / ED II / LFA", "genero": "M", "semestre": [1, 2, 3, 4, 5], "estilo": "Misto"},
    {"nome": "Lucas Cerqueira Figueiredo",             "area": "Sistemas Operacionais",                      "genero": "M", "semestre": [4],       "estilo": "Misto"},
    {"nome": "Péricles P. Turnes Junior",              "area": "Algoritmos Numéricos",                       "genero": "M", "semestre": [4],       "estilo": "Misto"},
    {"nome": "Renata Maria Nogueira de Oliveira",      "area": "Engenharia de Software",                     "genero": "F", "semestre": [5],       "estilo": "Misto"},
    {"nome": "Ricardo de Abreu Barbosa",               "area": "Princípios de Empreendedorismo",             "genero": "M", "semestre": [5],       "estilo": "Teórico"},
    {"nome": "Rodrigo Cardoso Silva",                  "area": "Projeto de Software",                        "genero": "M", "semestre": [4],       "estilo": "Misto"},
    {"nome": "Wallace Rodrigues de Santana",           "area": "Circuitos Elétricos e Eletrônicos",          "genero": "M", "semestre": [1],       "estilo": "Prático"},
]

# Lógica de comparação

def compare(guess_name, secret):
    guess = next((p for p in PROFESSORS if p["nome"].lower() == guess_name.lower()), None)
    if guess is None:
        return None

    result = {"nome": guess["nome"], "fields": {}}

    # Área
    if guess["area"].lower() == secret["area"].lower():
        result["fields"]["area"] = {"value": guess["area"], "status": "correct"}
    else:
        result["fields"]["area"] = {"value": guess["area"], "status": "wrong"}

    # Gênero
    if guess["genero"] == secret["genero"]:
        result["fields"]["genero"] = {"value": guess["genero"], "status": "correct"}
    else:
        result["fields"]["genero"] = {"value": guess["genero"], "status": "wrong"}

    # Semestre — partial if any overlap
    guess_sem  = set(guess["semestre"])
    secret_sem = set(secret["semestre"])
    if guess_sem == secret_sem:
        sem_status = "correct"
    elif guess_sem & secret_sem:
        sem_status = "partial"
    else:
        sem_status = "wrong"
    result["fields"]["semestre"] = {"value": guess["semestre"], "status": sem_status}

    # Estilo
    if guess["estilo"] == secret["estilo"]:
        result["fields"]["estilo"] = {"value": guess["estilo"], "status": "correct"}
    else:
        result["fields"]["estilo"] = {"value": guess["estilo"], "status": "wrong"}

    # Win?
    result["win"] = guess["nome"].lower() == secret["nome"].lower()
    return result

# Server

HOST = "0.0.0.0"
PORT = 5555

clients   = {}   # conn -> {"name": str, "ready": bool}
lock      = threading.Lock()

game_state = {
    "started":        False,
    "secret":         None,
    "current_turn":   None,   # player name
    "players":        [],     # [name, name]
    "round":          0,
    "winner":         None,
}

def broadcast(msg: dict, exclude=None):
    data = (json.dumps(msg) + "\n").encode()
    dead = []
    for conn in list(clients):
        if conn is exclude:
            continue
        try:
            conn.sendall(data)
        except Exception:
            dead.append(conn)
    for c in dead:
        clients.pop(c, None)

def send(conn, msg: dict):
    try:
        conn.sendall((json.dumps(msg) + "\n").encode())
    except Exception:
        pass

def try_start_game():
    """Called when both players are ready."""
    with lock:
        if game_state["started"]:
            return
        ready = [c for c, info in clients.items() if info["ready"]]
        if len(ready) < 2:
            return

        secret  = random.choice(PROFESSORS)
        players = [clients[c]["name"] for c in ready]
        random.shuffle(players)

        game_state.update({
            "started":      True,
            "secret":       secret,
            "current_turn": players[0],
            "players":      players,
            "round":        1,
            "winner":       None,
        })

    broadcast({
        "type":    "game_start",
        "players": game_state["players"],
        "turn":    game_state["current_turn"],
        "round":   game_state["round"],
        "professors": [p["nome"] for p in PROFESSORS],
    })
    print(f"[SERVER] Game started! Secret: {secret['nome']} | First turn: {game_state['current_turn']}")

def next_turn():
    players = game_state["players"]
    current = game_state["current_turn"]
    idx     = players.index(current)
    game_state["current_turn"] = players[(idx + 1) % 2]
    game_state["round"] += 1

def handle_client(conn, addr):
    print(f"[SERVER] New connection from {addr}")
    buffer = ""
    try:
        while True:
            data = conn.recv(4096).decode()
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                msg = json.loads(line)
                handle_message(conn, msg)
    except Exception as e:
        print(f"[SERVER] Client {addr} error: {e}")
    finally:
        with lock:
            info = clients.pop(conn, None)
        conn.close()
        if info:
            name = info.get("name", "?")
            print(f"[SERVER] {name} disconnected")
            broadcast({"type": "player_left", "name": name})

def handle_message(conn, msg):
    t = msg.get("type")

    if t == "join":
        name = msg["name"]
        with lock:
            if len(clients) >= 2:
                send(conn, {"type": "error", "msg": "Sala cheia!"})
                return
            clients[conn] = {"name": name, "ready": False}
        print(f"[SERVER] {name} joined")
        send(conn, {"type": "joined", "name": name})
        broadcast({"type": "player_joined", "name": name}, exclude=conn)

    elif t == "ready":
        with lock:
            if conn in clients:
                clients[conn]["ready"] = True
                name = clients[conn]["name"]
        print(f"[SERVER] {name} is ready")
        broadcast({"type": "player_ready", "name": name})
        try_start_game()

    elif t == "guess":
        if not game_state["started"]:
            return
        player_name = clients[conn]["name"]
        if player_name != game_state["current_turn"]:
            send(conn, {"type": "not_your_turn"})
            return

        guess_name = msg["guess"]
        result     = compare(guess_name, game_state["secret"])
        if result is None:
            send(conn, {"type": "invalid_guess", "msg": "Professor não encontrado"})
            return

        if result["win"]:
            game_state["winner"] = player_name
            broadcast({
                "type":   "guess_result",
                "player": player_name,
                "result": result,
                "win":    True,
                "winner": player_name,
                "secret": game_state["secret"]["nome"],
            })
            print(f"[SERVER] {player_name} WON! Answer: {game_state['secret']['nome']}")
        else:
            next_turn()
            broadcast({
                "type":   "guess_result",
                "player": player_name,
                "result": result,
                "win":    False,
                "turn":   game_state["current_turn"],
                "round":  game_state["round"],
            })

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(2)
    print(f"[SERVER] Listening on {HOST}:{PORT}")
    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        t.start()

if __name__ == "__main__":
    main()

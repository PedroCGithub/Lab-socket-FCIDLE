import pygame
import socket
import threading
import json
import sys
import textwrap

# Configurações básicas do cliente
SERVIDOR_HOST = "127.0.0.1"
SERVIDOR_PORTA = 5555
JANELA_L, JANELA_A = 1100, 750

# Paleta de cores da interface
FUNDO_ESCURO  = (15,  17,  26)
FUNDO_PAINEL  = (22,  26,  40)
FUNDO_CARD    = (30,  35,  52)
DESTAQUE      = (99, 179, 237)
DESTAQUE_DIM  = (55,  90, 130)
BRANCO        = (235, 238, 245)
CINZA         = (120, 128, 150)
CINZA_ESCURO  = (50,  55,  75)
VERDE         = (72, 199, 142)
VERDE_DIM     = (30,  90,  60)
AMARELO       = (251, 189,  35)
AMARELO_DIM   = (110,  80,  10)
VERMELHO      = (252,  90,  90)
VERMELHO_DIM  = (110,  30,  30)
OURO          = (255, 215,   0)

COR_STATUS = {
    "correct": VERDE,
    "partial": AMARELO,
    "wrong":   VERMELHO,
}

FUNDO_STATUS = {
    "correct": VERDE_DIM,
    "partial": AMARELO_DIM,
    "wrong":   VERMELHO_DIM,
}

ROTULO_ESTILO = {"Misto": "Misto", "Teórico": "Teórico", "Prático": "Prático"}

# Estrutura da tabela de palpites
CABECALHOS    = ["Professor", "Área", "Gênero", "Semestre", "Estilo"]
LARGURAS_COL  = [220, 260, 80, 130, 110]
CHAVES_COL    = [None, "area", "genero", "semestre", "estilo"]


# Gerenciador de estado global
# Centraliza as informações para facilitar o acesso entre as diferentes telas
class Estado:
    def __init__(self):
        self.tela_atual    = "lobby"
        self.meu_nome      = ""
        self.outro_nome    = ""
        self.jogadores     = []
        self.vez_atual     = ""
        self.rodada        = 0
        self.historico     = []
        self.vencedor      = None
        self.segredo       = None
        self.professores   = []
        self.msg_erro      = ""
        self.msg_status    = ""
        self.outro_pronto  = False
        self.eu_pronto     = False

estado = Estado()
trava_rede = threading.Lock()


# Módulo de Rede
# Lida com a conexão socket e processa os dados recebidos do servidor em background
conexao  = None
buffer_rede = ""

def conectar(host, porta):
    global conexao
    conexao = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conexao.connect((host, porta))
    # Inicia thread separada para não travar a interface do jogo
    thread = threading.Thread(target=loop_recepcao, daemon=True)
    thread.start()

def enviar_mensagem(msg: dict):
    try:
        conexao.sendall((json.dumps(msg) + "\n").encode())
    except Exception as e:
        estado.msg_erro = f"Erro de rede: {e}"

def loop_recepcao():
    global buffer_rede
    while True:
        try:
            dados = conexao.recv(4096).decode()
            if not dados:
                break
            buffer_rede += dados
            # Processa mensagens completas separadas por quebra de linha
            while "\n" in buffer_rede:
                linha, buffer_rede = buffer_rede.split("\n", 1)
                linha = linha.strip()
                if linha:
                    processar_mensagem_servidor(json.loads(linha))
        except Exception as e:
            estado.msg_erro = f"Conexão perdida: {e}"
            break

# Atualiza o estado do jogo baseado nos eventos do servidor
def processar_mensagem_servidor(msg):
    tipo = msg.get("type")
    if tipo == "joined":
        estado.msg_status = "Conectado! Aguardando outro jogador…"
        estado.tela_atual = "aguardando"

    elif tipo == "player_joined":
        estado.outro_nome  = msg["name"]
        estado.msg_status  = f"{msg['name']} entrou na sala!"

    elif tipo == "player_ready":
        if msg["name"] != estado.meu_nome:
            estado.outro_pronto = True
            estado.msg_status   = f"{msg['name']} está pronto!"

    elif tipo == "game_start":
        estado.jogadores   = msg["players"]
        estado.vez_atual   = msg["turn"]
        estado.rodada      = msg["round"]
        estado.professores = msg["professors"]
        estado.tela_atual  = "jogo"
        
        for j in estado.jogadores:
            if j != estado.meu_nome:
                estado.outro_nome = j

    elif tipo == "guess_result":
        entrada = {"jogador": msg["player"], "resultado": msg["result"]}
        estado.historico.append(entrada)
        
        if msg["win"]:
            estado.vencedor  = msg["winner"]
            estado.segredo   = msg.get("secret")
            estado.tela_atual = "fim_de_jogo"
        else:
            estado.vez_atual = msg["turn"]
            estado.rodada    = msg["round"]

    elif tipo == "not_your_turn":
        estado.msg_erro = "Não é sua vez!"

    elif tipo == "invalid_guess":
        estado.msg_erro = msg.get("msg", "Professor inválido")

    elif tipo == "error":
        estado.msg_erro = msg.get("msg", "Erro")

    elif tipo == "player_left":
        estado.msg_erro = f"{msg['name']} saiu da partida."


# Utilitários de desenho do Pygame
def desenhar_retangulo(surf, cor, rect, r=8):
    pygame.draw.rect(surf, cor, rect, border_radius=r)

def desenhar_texto(surf, texto, fonte, cor, x, y, ancora="topleft", largura_max=None):
    if largura_max:
        palavras = texto.split()
        linhas = []
        atual = ""
        for p in palavras:
            teste = atual + (" " if atual else "") + p
            if fonte.size(teste)[0] <= largura_max:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        for i, linha in enumerate(linhas):
            s = fonte.render(linha, True, cor)
            r = s.get_rect(**{ancora: (x, y + i * fonte.get_linesize())})
            surf.blit(s, r)
        return
        
    s = fonte.render(texto, True, cor)
    r = s.get_rect(**{ancora: (x, y)})
    surf.blit(s, r)

def semestres_str(lista_sem):
    return ", ".join(str(s) for s in lista_sem)


# Classes de Interface (Telas)

# Tela de entrada de nome e IP
class TelaLobby:
    def __init__(self, fontes):
        self.fontes      = fontes
        self.texto_nome  = ""
        self.texto_host  = SERVIDOR_HOST
        self.ativo       = "nome"
        self.erro        = ""
        self.conectando  = False

    def processar_evento(self, evento):
        # Trata entrada do teclado para preencher os campos
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_TAB:
                self.ativo = "host" if self.ativo == "nome" else "nome"
            elif evento.key == pygame.K_BACKSPACE:
                if self.ativo == "nome":
                    self.texto_nome = self.texto_nome[:-1]
                else:
                    self.texto_host = self.texto_host[:-1]
            elif evento.key == pygame.K_RETURN:
                self._conectar()
            else:
                ch = evento.unicode
                if ch:
                    if self.ativo == "nome":
                        self.texto_nome += ch
                    else:
                        self.texto_host += ch

        # Trata cliques nos campos ou botão
        if evento.type == pygame.MOUSEBUTTONDOWN:
            mx, my = evento.pos
            if 380 <= mx <= 720 and 340 <= my <= 380:
                self.ativo = "nome"
            elif 380 <= mx <= 720 and 430 <= my <= 470:
                self.ativo = "host"
            elif 450 <= mx <= 650 and 510 <= my <= 550:
                self._conectar()

    def _conectar(self):
        if not self.texto_nome.strip():
            self.erro = "Digite seu nome!"
            return
        self.conectando = True
        self.erro = ""
        estado.meu_nome = self.texto_nome.strip()
        thread = threading.Thread(target=self._fazer_conexao, daemon=True)
        thread.start()

    def _fazer_conexao(self):
        try:
            conectar(self.texto_host.strip(), SERVIDOR_PORTA)
            enviar_mensagem({"type": "join", "name": estado.meu_nome})
        except Exception as e:
            self.erro = f"Não foi possível conectar: {e}"
            self.conectando = False

    def desenhar(self, surf):
        f_titulo = self.fontes["titulo"]
        f_corpo  = self.fontes["corpo"]
        f_pequena = self.fontes["pequena"]

        surf.fill(FUNDO_ESCURO)

        # Grade de fundo
        for x in range(0, JANELA_L, 60):
            pygame.draw.line(surf, (25, 28, 42), (x, 0), (x, JANELA_A))
        for y in range(0, JANELA_A, 60):
            pygame.draw.line(surf, (25, 28, 42), (0, y), (JANELA_L, y))

        brilho = pygame.Surface((400, 400), pygame.SRCALPHA)
        pygame.draw.circle(brilho, (99, 179, 237, 18), (200, 200), 200)
        surf.blit(brilho, (350, 150))

        desenhar_texto(surf, "FCIDLE", f_titulo, DESTAQUE, JANELA_L//2, 140, "center")
        desenhar_texto(surf, "Adivinhe o professor do semestre!", f_corpo, CINZA, JANELA_L//2, 255, "center")

        # Renderização do campo de nome
        desenhar_texto(surf, "Seu nome:", f_pequena, CINZA, 380, 315)
        cor = DESTAQUE if self.ativo == "nome" else CINZA_ESCURO
        desenhar_retangulo(surf, cor, (380, 340, 340, 42), 6)
        desenhar_retangulo(surf, FUNDO_CARD, (382, 342, 336, 38), 5)
        exibir = self.texto_nome + ("|" if self.ativo == "nome" and pygame.time.get_ticks() % 1000 < 500 else "")
        desenhar_texto(surf, exibir, f_corpo, BRANCO, 392, 352)

        # Renderização do campo de IP
        desenhar_texto(surf, "IP do servidor:", f_pequena, CINZA, 380, 408)
        cor = DESTAQUE if self.ativo == "host" else CINZA_ESCURO
        desenhar_retangulo(surf, cor, (380, 430, 340, 42), 6)
        desenhar_retangulo(surf, FUNDO_CARD, (382, 432, 336, 38), 5)
        exibir = self.texto_host + ("|" if self.ativo == "host" and pygame.time.get_ticks() % 1000 < 500 else "")
        desenhar_texto(surf, exibir, f_corpo, BRANCO, 392, 442)

        # Botão de conectar
        cor_btn = DESTAQUE_DIM if self.conectando else DESTAQUE
        desenhar_retangulo(surf, cor_btn, (450, 510, 200, 44), 8)
        rotulo = "Conectando…" if self.conectando else "Conectar"
        desenhar_texto(surf, rotulo, f_corpo, FUNDO_ESCURO, 550, 532, "center")

        if self.erro:
            desenhar_texto(surf, self.erro, f_pequena, VERMELHO, JANELA_L//2, 575, "center")


# Tela de espera enquanto o outro jogador entra ou clica em pronto
class TelaAguardando:
    def __init__(self, fontes):
        self.fontes = fontes

    def processar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN:
            mx, my = evento.pos
            if 400 <= mx <= 700 and 440 <= my <= 490 and not estado.eu_pronto:
                estado.eu_pronto = True
                enviar_mensagem({"type": "ready"})

    def desenhar(self, surf):
        surf.fill(FUNDO_ESCURO)
        f_titulo  = self.fontes["titulo"]
        f_corpo   = self.fontes["corpo"]
        f_pequena = self.fontes["pequena"]

        desenhar_texto(surf, "Sala de Espera", f_titulo, DESTAQUE, JANELA_L//2, 120, "center")

        j1 = estado.meu_nome or "Você"
        j2 = estado.outro_nome or "Aguardando…"

        for i, (nome, pronto) in enumerate([(j1, estado.eu_pronto), (j2, estado.outro_pronto)]):
            x = 200 + i * 480
            desenhar_retangulo(surf, FUNDO_CARD, (x - 150, 230, 300, 120), 10)
            desenhar_texto(surf, nome, f_corpo, BRANCO, x, 260, "center")
            rotulo = "✔ Pronto" if pronto else "⏳ Aguardando"
            cor    = VERDE if pronto else CINZA
            desenhar_texto(surf, rotulo, f_pequena, cor, x, 300, "center")

        desenhar_texto(surf, "VS", f_titulo, AMARELO, JANELA_L//2, 265, "center")

        if not estado.eu_pronto:
            desenhar_retangulo(surf, DESTAQUE, (400, 440, 300, 50), 8)
            desenhar_texto(surf, "Estou Pronto!", f_corpo, FUNDO_ESCURO, JANELA_L//2, 465, "center")
        else:
            desenhar_texto(surf, "Aguardando o outro jogador…", f_corpo, CINZA, JANELA_L//2, 460, "center")

        if estado.msg_status:
            desenhar_texto(surf, estado.msg_status, f_pequena, DESTAQUE, JANELA_L//2, 530, "center")


# Tela principal onde o jogo acontece (digitar palpites, ver histórico, etc)
class TelaJogo:
    def __init__(self, fontes):
        self.fontes          = fontes
        self.texto_digitado  = ""
        self.sugestoes       = []
        self.mostrar_sugest  = False
        self.rolagem_hist    = 0
        self.timer_erro      = 0

    # Lógica do autocompletar baseada na lista enviada pelo servidor
    def _atualizar_sugestoes(self):
        q = self.texto_digitado.strip().lower()
        if not q:
            self.sugestoes      = []
            self.mostrar_sugest = False
            return
        self.sugestoes = [p for p in estado.professores
                          if p.lower().startswith(q)][:8]
        self.mostrar_sugest = bool(self.sugestoes)

    def _enviar_chute(self, nome):
        if estado.vez_atual != estado.meu_nome:
            estado.msg_erro  = "Não é sua vez!"
            self.timer_erro  = 120
            return
        enviar_mensagem({"type": "guess", "guess": nome})
        self.texto_digitado = ""
        self.sugestoes      = []
        self.mostrar_sugest = False

    def processar_evento(self, evento):
        # Trata teclado na hora de buscar um professor
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_BACKSPACE:
                self.texto_digitado = self.texto_digitado[:-1]
                self._atualizar_sugestoes()
            elif evento.key == pygame.K_RETURN:
                if self.texto_digitado.strip():
                    self._enviar_chute(self.texto_digitado.strip())
            elif evento.key == pygame.K_ESCAPE:
                self.mostrar_sugest = False
            else:
                ch = evento.unicode
                if ch and ch.isprintable():
                    self.texto_digitado += ch
                    self._atualizar_sugestoes()

        # Clique nas sugestões ou botão de enviar
        if evento.type == pygame.MOUSEBUTTONDOWN:
            mx, my = evento.pos
            if self.mostrar_sugest:
                sugg_y = 128 + 44 
                for i, s in enumerate(self.sugestoes):
                    ry = sugg_y + 2 + i * 30
                    if 10 <= mx <= 480 and ry <= my <= ry + 30:
                        self.texto_digitado = s
                        self.mostrar_sugest  = False
                        self._enviar_chute(s)
                        return
                        
            if 490 <= mx <= 590 and 130 <= my <= 165:
                if self.texto_digitado.strip():
                    self._enviar_chute(self.texto_digitado.strip())

        if evento.type == pygame.MOUSEWHEEL:
            self.rolagem_hist = max(0, self.rolagem_hist - evento.y * 40)

    def desenhar(self, surf):
        surf.fill(FUNDO_ESCURO)
        f_titulo  = self.fontes["titulo"]
        f_corpo   = self.fontes["corpo"]
        f_pequena = self.fontes["pequena"]
        f_minima  = self.fontes["minima"]

        minha_vez = (estado.vez_atual == estado.meu_nome)

        # Renderiza a barra superior de status (rodada e jogadores)
        desenhar_retangulo(surf, FUNDO_PAINEL, (0, 0, JANELA_L, 115), 0)
        pygame.draw.line(surf, DESTAQUE_DIM, (0, 115), (JANELA_L, 115))

        for i, nome in enumerate(estado.jogadores):
            x = 30 + i * 320
            ativo = (nome == estado.vez_atual)
            if ativo:
                desenhar_retangulo(surf, DESTAQUE_DIM, (x - 5, 8, 280, 55), 8)
            rotulo = "▶ " + nome if ativo else nome
            cor    = DESTAQUE if ativo else CINZA
            desenhar_texto(surf, rotulo, f_corpo, cor, x, 15)
            sub = "Sua vez!" if (ativo and nome == estado.meu_nome) else ("Vez dele(a)" if ativo else "")
            desenhar_texto(surf, sub, f_minima, AMARELO if ativo else CINZA, x, 42)

        desenhar_texto(surf, f"Rodada {estado.rodada}", f_corpo, BRANCO, JANELA_L//2, 25, "center")

        if estado.msg_erro:
            desenhar_texto(surf, estado.msg_erro, f_pequena, VERMELHO, JANELA_L - 20, 20, "topright")

        # Campo de entrada de palpite
        inp_y = 128
        desenhar_retangulo(surf, FUNDO_CARD, (10, inp_y, 470, 42), 7)
        cor_borda = DESTAQUE if minha_vez else CINZA_ESCURO
        pygame.draw.rect(surf, cor_borda, (10, inp_y, 470, 42), 2, border_radius=7)

        cursor = "|" if pygame.time.get_ticks() % 1000 < 500 and minha_vez else ""
        desenhar_texto(surf, self.texto_digitado + cursor, f_corpo,
                       BRANCO if minha_vez else CINZA, 20, inp_y + 10)

        if not minha_vez and not self.texto_digitado:
            desenhar_texto(surf, "Aguardando o outro jogador…", f_corpo, CINZA, 20, inp_y + 10)
        elif not self.texto_digitado:
            desenhar_texto(surf, "Digite o nome do professor…", f_corpo, CINZA, 20, inp_y + 10)

        cor_btn = DESTAQUE if minha_vez else CINZA_ESCURO
        desenhar_retangulo(surf, cor_btn, (490, inp_y, 100, 42), 7)
        desenhar_texto(surf, "Enviar", f_corpo, FUNDO_ESCURO if minha_vez else CINZA, 540, inp_y + 11, "center")

        # Histórico de jogadas passadas com máscara de corte (clip)
        topo_tabela = 185
        altura_tab  = JANELA_A - topo_tabela - 10

        desenhar_retangulo(surf, FUNDO_PAINEL, (0, topo_tabela, JANELA_L, 32), 0)
        pygame.draw.line(surf, DESTAQUE_DIM, (0, topo_tabela + 32), (JANELA_L, topo_tabela + 32))
        
        cx = 10
        for cab, larg in zip(CABECALHOS, LARGURAS_COL):
            desenhar_texto(surf, cab, f_minima, DESTAQUE, cx + larg//2, topo_tabela + 8, "center")
            cx += larg
        desenhar_texto(surf, "Jogador", f_minima, DESTAQUE, cx + 80, topo_tabela + 8, "center")

        area_clip = pygame.Rect(0, topo_tabela + 34, JANELA_L, altura_tab - 34)
        clip_ant  = surf.get_clip()
        surf.set_clip(area_clip)

        alt_linha = 56
        y_offset  = topo_tabela + 36 - self.rolagem_hist

        for entrada in estado.historico:
            res     = entrada["resultado"]
            jogador = entrada["jogador"]
            campos  = res["fields"]

            # Desenha a linha apenas se estiver visível na área de rolagem
            if y_offset + alt_linha > topo_tabela + 34:
                desenhar_retangulo(surf, FUNDO_CARD, (0, y_offset, JANELA_L, alt_linha - 2), 4)

                cx = 10
                desenhar_retangulo(surf, FUNDO_PAINEL, (cx, y_offset + 4, LARGURAS_COL[0] - 6, alt_linha - 10), 4)
                desenhar_texto(surf, res["nome"], f_pequena, BRANCO, cx + 6, y_offset + 14, largura_max=LARGURAS_COL[0] - 14)
                cx += LARGURAS_COL[0]

                # Desenha as colunas de dicas aplicando a cor do status
                for chave, larg in zip(CHAVES_COL[1:], LARGURAS_COL[1:]):
                    if chave and chave in campos:
                        info   = campos[chave]
                        status = info["status"]
                        val    = info["value"]
                        
                        if isinstance(val, list):
                            val = semestres_str(val)
                        elif chave == "estilo":
                            val = ROTULO_ESTILO.get(val, val)

                        fundo = FUNDO_STATUS[status]
                        fg    = COR_STATUS[status]
                        desenhar_retangulo(surf, fundo, (cx, y_offset + 4, larg - 6, alt_linha - 10), 4)
                        pygame.draw.rect(surf, fg, (cx, y_offset + 4, larg - 6, alt_linha - 10), 1, border_radius=4)
                        desenhar_texto(surf, str(val), f_pequena, fg, cx + (larg - 6)//2, y_offset + 18, "center", largura_max=larg - 12)
                    cx += larg

                cor_j = DESTAQUE if jogador == estado.meu_nome else AMARELO
                desenhar_texto(surf, jogador, f_pequena, cor_j, cx + 5, y_offset + 18)

            y_offset += alt_linha

        surf.set_clip(clip_ant)

        # Lógica visual da barra de rolagem
        total_h = len(estado.historico) * alt_linha
        if total_h > altura_tab - 34:
            ratio = (altura_tab - 34) / total_h
            bar_h = max(30, int((altura_tab - 34) * ratio))
            bar_y = topo_tabela + 34 + int(self.rolagem_hist / total_h * (altura_tab - 34))
            pygame.draw.rect(surf, DESTAQUE_DIM, (JANELA_L - 8, bar_y, 6, bar_h), border_radius=3)

        # Autocomplete (precisa ser renderizado no final para ficar sobre a tabela)
        if self.mostrar_sugest and self.sugestoes:
            sugg_y = inp_y + 44
            altura_dropdown = len(self.sugestoes) * 30 + 4
            drop = pygame.Surface((472, altura_dropdown + 2), pygame.SRCALPHA)
            drop.fill((0, 0, 0, 0))
            pygame.draw.rect(drop, FUNDO_CARD,   (0, 0, 472, altura_dropdown), border_radius=6)
            pygame.draw.rect(drop, DESTAQUE_DIM, (0, 0, 472, altura_dropdown), 1, border_radius=6)
            
            mx, my_ = pygame.mouse.get_pos()
            for i, s in enumerate(self.sugestoes):
                ry      = 2 + i * 30
                real_ry = sugg_y + ry
                hover   = (10 <= mx <= 480 and real_ry <= my_ <= real_ry + 30)
                if hover:
                    pygame.draw.rect(drop, DESTAQUE_DIM, (1, ry, 470, 29), border_radius=4)
                texto_surf = f_pequena.render(s, True, BRANCO if hover else CINZA)
                drop.blit(texto_surf, (10, ry + 6))
            surf.blit(drop, (10, sugg_y))


# Modal de fim de jogo exibido em cima da tela do jogo
class TelaFimDeJogo:
    def __init__(self, fontes, tela_jogo):
        self.fontes     = fontes
        self.tela_jogo  = tela_jogo

    def processar_evento(self, evento):
        pass

    def desenhar(self, surf):
        # Renderiza a tela do jogo no fundo para efeito de contexto
        self.tela_jogo.desenhar(surf)

        # Aplica uma camada semi-transparente para escurecer o fundo
        overlay = pygame.Surface((JANELA_L, JANELA_A), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surf.blit(overlay, (0, 0))

        f_titulo  = self.fontes["titulo"]
        f_corpo   = self.fontes["corpo"]
        f_pequena = self.fontes["pequena"]

        pw, ph = 500, 260
        px, py = (JANELA_L - pw) // 2, (JANELA_A - ph) // 2
        desenhar_retangulo(surf, FUNDO_PAINEL, (px, py, pw, ph), 16)
        pygame.draw.rect(surf, OURO, (px, py, pw, ph), 3, border_radius=16)

        desenhar_texto(surf, "🏆 PARABÉNS!", f_titulo, OURO, JANELA_L//2, py + 28, "center")

        nome_vencedor = estado.vencedor or ""
        eu_ganhei     = (nome_vencedor == estado.meu_nome)
        msg = "Você ganhou!" if eu_ganhei else f"{nome_vencedor} ganhou!"
        desenhar_texto(surf, msg, f_corpo, BRANCO, JANELA_L//2, py + 100, "center")

        if estado.segredo:
            desenhar_texto(surf, "O professor era:", f_pequena, CINZA, JANELA_L//2, py + 148, "center")
            desenhar_texto(surf, estado.segredo, f_corpo, DESTAQUE, JANELA_L//2, py + 176, "center")

        desenhar_texto(surf, "Feche a janela para sair.", f_pequena, CINZA, JANELA_L//2, py + 222, "center")


# Loop principal da aplicação
def main():
    pygame.init()
    surf  = pygame.display.set_mode((JANELA_L, JANELA_A))
    pygame.display.set_caption("FCIDLE")
    relogio = pygame.time.Clock()

    def criar_fonte(tamanho, negrito=False):
        for nome in ["Segoe UI", "Ubuntu", "DejaVu Sans", "Arial", None]:
            try:
                return pygame.font.SysFont(nome, tamanho, bold=negrito)
            except Exception:
                pass
        return pygame.font.Font(None, tamanho)

    fontes = {
        "titulo":  criar_fonte(46, negrito=True),
        "corpo":   criar_fonte(22),
        "pequena": criar_fonte(18),
        "minima":  criar_fonte(14, negrito=True),
    }

    lobby    = TelaLobby(fontes)
    aguardando = TelaAguardando(fontes)
    jogo     = TelaJogo(fontes)
    fim      = None

    # Loop de eventos e renderização
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Roteamento de eventos dependendo da tela atual
            modo = estado.tela_atual
            if modo == "lobby":
                lobby.processar_evento(evento)
            elif modo == "aguardando":
                aguardando.processar_evento(evento)
            elif modo == "jogo":
                jogo.processar_evento(evento)
            elif modo == "fim_de_jogo":
                if fim:
                    fim.processar_evento(evento)

        # Remove mensagens de erro visuais após cerca de 3 segundos
        if estado.msg_erro and estado.tela_atual == "jogo":
            jogo.timer_erro = getattr(jogo, "timer_erro", 0) + 1
            if jogo.timer_erro > 180:
                estado.msg_erro  = ""
                jogo.timer_erro  = 0

        # Roteamento de desenho dependendo da tela atual
        modo = estado.tela_atual
        if modo == "lobby":
            lobby.desenhar(surf)
        elif modo == "aguardando":
            aguardando.desenhar(surf)
        elif modo == "jogo":
            jogo.desenhar(surf)
        elif modo == "fim_de_jogo":
            if fim is None:
                fim = TelaFimDeJogo(fontes, jogo)
            fim.desenhar(surf)

        pygame.display.flip()
        relogio.tick(60)

if __name__ == "__main__":
    main()

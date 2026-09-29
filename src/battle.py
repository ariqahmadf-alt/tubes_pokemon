import pygame
import config
from copy import deepcopy
from math import inf

box = pygame.image.load("assets/box.png")
vert_box = pygame.image.load("assets/vert_box.png")
options = pygame.image.load("assets/options.png")
pikachu = pygame.image.load("assets/pikachu.png")
charizard = pygame.image.load("assets/charizard.png")
move_logs = []
chosen_move = 0
battle_text = ""
chosen_log = 0
showing_log = True
last_rival_turn = 0

# 0 - player chooses move
# 1 - player uses move
# 2 - enemy chooses move
# 3 - enemy uses move
turn_step = 0


class MoveLogEntry:
    def __init__(self, move, user):
        self.move = move
        self.user = user
        self.player = deepcopy(player)
        self.rival = deepcopy(rival)


class Move:
    def __init__(self, name, pp, value):
        self.name = name

        # power points
        self.pp = pp
        self.max_pp = pp

        # generic value corresponding to the move.
        # eg; ATTACK move of 10 will reduce HP by 10
        self.value = value


class Pokemon:
    def __init__(self, name, hp, moves):
        self.name = name
        self.hp = hp
        self.defense = 0
        self.max_hp = hp
        self.moves = moves

    def choose_move(self, move_idx, b_text, logs, enemy):
        move = self.moves[move_idx]

        simulate_move(self, enemy, move_idx)

        b_text = self.name + " used " + move.name + "!\n(" + str(move.value) + ")"

        move_entry = MoveLogEntry(move, self.name)
        logs.append(move_entry)

        return (b_text, logs)


player = Pokemon(
    "PIKACHU",
    100,
    [
        Move("ATTACK", 5, 10),
        Move("DEFEND", 5, 10),
        Move("HEAL", 5, 10),
        Move("REST", -1, -1),  # -1 PP means infinite move
    ],
)
rival = Pokemon(
    "CHARIZARD",
    100,
    [
        Move("ATTACK", 5, 10),
        Move("DEFEND", 5, 10),
        Move("HEAL", 5, 10),
        Move("REST", -1, -1),  # -1 PP means infinite move
    ],
)


def available_moves(pokemon):
    return [index for index, move in enumerate(pokemon.moves) if move.pp != 0]


def simulate_move(actor, enemy, move_idx):
    move = actor.moves[move_idx]

    if move_idx == 0:  # ATTACK
        damage = max(move.value - enemy.defense, 0)
        enemy.hp = max(enemy.hp - damage, 0)
        enemy.defense = max(enemy.defense - move.value, 0)

    elif move_idx == 1:  # DEFEND
        actor.defense += move.value

    elif move_idx == 2:  # HEAL
        actor.hp = min(actor.hp + move.value, actor.max_hp)

    elif move_idx == 3:  # REST
        for actor_move in actor.moves:
            actor_move.pp = actor_move.max_pp

    if move.pp != -1:
        move.pp -= 1


def evaluate(rival_state, player_state):
    if player_state.hp <= 0:
        return 100000

    if rival_state.hp <= 0:
        return -100000

    return (rival_state.hp - player_state.hp) * 10 + (
        rival_state.defense - player_state.defense
    ) * 2


def minimax(rival_state, player_state, depth, maximizing):
    if depth == 0 or rival_state.hp <= 0 or player_state.hp <= 0:
        return evaluate(rival_state, player_state)

    actor = rival_state if maximizing else player_state
    best_score = -inf if maximizing else inf

    for move_idx in available_moves(actor):
        next_rival = deepcopy(rival_state)
        next_player = deepcopy(player_state)

        if maximizing:
            simulate_move(next_rival, next_player, move_idx)
        else:
            simulate_move(next_player, next_rival, move_idx)

        score = minimax(
            next_rival,
            next_player,
            depth - 1,
            not maximizing,
        )

        if maximizing:
            best_score = max(best_score, score)
        else:
            best_score = min(best_score, score)

    return best_score

def alpha_beta(rival_state, player_state, depth, alpha, beta, maximizing):
    if depth == 0 or rival_state.hp <= 0 or player_state.hp <= 0:
        return evaluate(rival_state, player_state)

    actor = rival_state if maximizing else player_state
    best_score = -inf if maximizing else inf

    for move_idx in available_moves(actor):
        next_rival = deepcopy(rival_state)
        next_player = deepcopy(player_state)

        if maximizing:
            simulate_move(next_rival, next_player, move_idx)
        else:
            simulate_move(next_player, next_rival, move_idx)

        score = alpha_beta(
            next_rival,
            next_player,
            depth - 1,
            alpha,
            beta,
            not maximizing,
        )

        if maximizing:
            best_score = max(best_score, score)
            alpha = max(alpha, best_score)
        else:
            best_score = min(best_score, score)
            beta = min(beta, best_score)

        if beta <= alpha:
            break

    return best_score


def choose_rival_move(depth=2, type="minimax"):
    best_move = 0
    best_score = -inf
    alpha = -inf
    beta = inf

    for move_idx in available_moves(rival):
        simulated_rival = deepcopy(rival)
        simulated_player = deepcopy(player)

        simulate_move(
            simulated_rival,
            simulated_player,
            move_idx,
        )

        score = 0
        if type == "minimax":
            score = minimax(
                simulated_rival,
                simulated_player,
                depth - 1,
                False,
            )

        elif type == "alpha-beta":
            score = alpha_beta(
                simulated_rival,
                simulated_player,
                depth - 1,
                alpha,
                beta,
                False,
            )

        if score > best_score:
            best_score = score
            best_move = move_idx

        alpha = max(alpha, best_score)

    return best_move


def printLogs():
    for log in move_logs:
        print(log.name, log.user)


def scale_sprite(sprite, scale, pos, rot=0):
    scaled = pygame.transform.scale(
        sprite,
        (
            sprite.get_width() * scale,
            sprite.get_height() * scale,
        ),
    )
    scaled = pygame.transform.rotate(scaled, rot)
    rect = scaled.get_rect()
    rect.x = pos[0]
    rect.y = pos[1]
    return (scaled, rect)


# cycle thru moves when pressing up/down
def inc_chosen_move(inc, co):
    co += inc
    if co > 3:
        co = 0
    elif co < 0:
        co = 3
    return co


def draw_moves(screen, font):
    sprite = scale_sprite(box, 5, (0, 380))
    screen.blit(sprite[0], sprite[1])

    def chosen(move):
        str = ""
        if chosen_move == move:
            str = ">"
        else:
            str = "-"
        str += moves[move].name
        if moves[move].pp != -1:
            str += f"  ({moves[move].pp}/{moves[move].max_pp})"

        return str

    moves = player.moves

    screen.blit(font.render(chosen(0), False, "black"), (30, 410))
    screen.blit(font.render(chosen(1), False, "black"), (30, 450))
    screen.blit(font.render(chosen(2), False, "black"), (30, 490))
    screen.blit(font.render(chosen(3), False, "black"), (30, 530))


def draw_battle_text(screen, font):
    sprite = scale_sprite(box, 5, (0, 380))
    screen.blit(sprite[0], sprite[1])

    screen.blit(
        font.render(
            battle_text,
            False,
            "black",
        ),
        (30, 410),
    )


def draw_pokemon(screen):
    scaled = scale_sprite(pikachu, 4, (60, 132))
    screen.blit(scaled[0], scaled[1])

    scaled = scale_sprite(charizard, 4, (410, 10))
    screen.blit(scaled[0], scaled[1])


def draw_stats(screen, font):
    screen.blit(font.render(player.name, False, "black"), (380, 250))
    screen.blit(font.render(f"HP: {player.hp}/{player.max_hp}", False, "black"), (380, 300))
    screen.blit(font.render(f"DEF: {player.defense}", False, "black"), (380, 340))
    
    screen.blit(font.render(rival.name, False, "black"), (70, 20))
    screen.blit(font.render(f"HP: {rival.hp}/{rival.max_hp}", False, "black"), (70, 70))
    screen.blit(font.render(f"DEF: {rival.defense}", False, "black"), (70, 110))

def draw_logs(screen, font):
    scaled = scale_sprite(vert_box, 8, (900 - 260, -50))
    screen.blit(scaled[0], scaled[1])

    screen.blit(
        font.render("MOVE LOG:", False, "black"),
        (675, 0),
    )

    for i in range(len(move_logs)):
        if i < chosen_log:
            continue
        y = 40 + ((i - chosen_log) * 150)
        log = move_logs[i]
        screen.blit(
            font.render(f"{i + 1}", False, "black"),
            (900 - 230, y),
        )
        screen.blit(
            font.render(f"{log.player.hp}", False, (0, 205, 0)),
            (900 - 130, y),
        )
        screen.blit(
            font.render("/", False, "black"),
            (900 - 50, y),
        )
        screen.blit(
            font.render(f"{log.rival.hp}", False, (205, 0, 0)),
            (900 - 10, y),
        )
        screen.blit(
            font.render(f"{log.player.defense}", False, (0, 0, 205)),
            (900 - 130, y+40),
        )
        screen.blit(
            font.render(f"{log.rival.defense}", False, (0, 0, 205)),
            (900 - 10, y+40),
        )
        text = font.render(f"{log.move.name}", False, "black")
        side = text.get_rect(topleft=(900 - 230, y + 80))
        if log.user == "CHARIZARD":
            side = text.get_rect(topright=(900 + 40, y + 80))
        screen.blit(text, side)


# AI OVERLAY GOES HERE
def draw_ai_brain(screen, font):
    left = 625

    scaled = scale_sprite(vert_box, 10, (900 - 325, -50))
    screen.blit(scaled[0], scaled[1])

    screen.blit(
        font.render(f"AI (TURN {last_rival_turn}):", False, "black"),
        (left, 0),
    )

    # The battle AI searches two plies in next_step().  Rebuild that same
    # decision here so the overlay can show the moves/scores and search cost
    # without changing the actual Minimax / Alpha-Beta implementation.
    search_depth = 2
    ai_mode = config.ai_type

    # Once the rival has taken its move, the live Pokemon state has already
    # changed.  The preceding player log stores the state the AI actually saw
    # when it made that decision, so use it when available.
    debug_player = player
    debug_rival = rival
    log_idx = last_rival_turn - 2
    if 0 <= log_idx < len(move_logs):
        debug_player = move_logs[log_idx].player
        debug_rival = move_logs[log_idx].rival

    node_count = 1  # decision/root node
    leaf_count = 0
    pruned_count = 0

    # These traced versions intentionally mirror the current search functions.
    # Their only extra responsibility is collecting debug statistics.
    def traced_minimax(rival_state, player_state, depth, maximizing):
        nonlocal node_count, leaf_count
        node_count += 1

        if depth == 0 or rival_state.hp <= 0 or player_state.hp <= 0:
            leaf_count += 1
            return evaluate(rival_state, player_state)

        actor = rival_state if maximizing else player_state
        best_score = -inf if maximizing else inf

        for move_idx in available_moves(actor):
            next_rival = deepcopy(rival_state)
            next_player = deepcopy(player_state)

            if maximizing:
                simulate_move(next_rival, next_player, move_idx)
            else:
                simulate_move(next_player, next_rival, move_idx)

            score = traced_minimax(
                next_rival,
                next_player,
                depth - 1,
                not maximizing,
            )

            if maximizing:
                best_score = max(best_score, score)
            else:
                best_score = min(best_score, score)

        return best_score

    def traced_alpha_beta(
        rival_state,
        player_state,
        depth,
        alpha,
        beta,
        maximizing,
    ):
        nonlocal node_count, leaf_count, pruned_count
        node_count += 1

        if depth == 0 or rival_state.hp <= 0 or player_state.hp <= 0:
            leaf_count += 1
            return evaluate(rival_state, player_state)

        actor = rival_state if maximizing else player_state
        best_score = -inf if maximizing else inf
        moves_to_check = available_moves(actor)
        for move_pos, move_idx in enumerate(moves_to_check):
            next_rival = deepcopy(rival_state)
            next_player = deepcopy(player_state)

            if maximizing:
                simulate_move(next_rival, next_player, move_idx)
            else:
                simulate_move(next_player, next_rival, move_idx)

            score = traced_alpha_beta(
                next_rival,
                next_player,
                depth - 1,
                alpha,
                beta,
                not maximizing,
            )

            if maximizing:
                best_score = max(best_score, score)
                alpha = max(alpha, best_score)
            else:
                best_score = min(best_score, score)
                beta = min(beta, best_score)

            if beta <= alpha:
                pruned_count += len(moves_to_check) - move_pos - 1
                break

        return best_score

    action_scores = []
    best_move = None
    best_score = -inf
    alpha = -inf
    beta = inf

    for move_idx in available_moves(debug_rival):
        simulated_rival = deepcopy(debug_rival)
        simulated_player = deepcopy(debug_player)
        simulate_move(simulated_rival, simulated_player, move_idx)

        if ai_mode == "alpha-beta":
            score = traced_alpha_beta(
                simulated_rival,
                simulated_player,
                search_depth - 1,
                alpha,
                beta,
                False,
            )
        else:
            score = traced_minimax(
                simulated_rival,
                simulated_player,
                search_depth - 1,
                False,
            )

        action_scores.append((move_idx, score))

        if score > best_score:
            best_score = score
            best_move = move_idx

        # choose_rival_move() also carries the root alpha value from one
        # candidate action to the next when Alpha-Beta is selected.
        alpha = max(alpha, best_score)

    mode_text = "A-B" if ai_mode == "alpha-beta" else "MINIMAX"
    pruning_text = "ON" if ai_mode == "alpha-beta" else "OFF"

    screen.blit(font.render(f"MODE: {mode_text}", False, "black"), (left, 45))
    screen.blit(font.render(f"PRUNING: {pruning_text}", False, "black"), (left, 80))
    screen.blit(font.render(f"DEPTH: {search_depth}", False, "black"), (left, 115))
    y = 175

    pygame.draw.line(screen, "black", (left, y), (925, y), 2)
    screen.blit(font.render("MOVES / SCORE", False, "black"), (left, y + 5))

    y += 50
    for move_idx, score in action_scores:
        prefix = ">" if move_idx == best_move else "-"
        col = (0, 150, 0) if move_idx == best_move else "black"
        screen.blit(
            font.render(
                f"{prefix}{debug_rival.moves[move_idx].name}: {score}",
                False,
                col,
            ),
            (left, y),
        )
        y += 40

    y += 20
    pygame.draw.line(screen, "black", (left, y + 10), (925, y + 10), 2)
    y += 20

    screen.blit(font.render(f"NODES: {node_count}", False, "black"), (left, y))
    y += 40
    screen.blit(font.render(f"LEAVES: {leaf_count}", False, "black"), (left, y))
    y += 40

    if ai_mode == "alpha-beta":
        screen.blit(
            font.render(f"PRUNED: {pruned_count}", False, (190, 0, 0)),
            (left, y),
        )
        y += 40

    if best_move is not None:
        screen.blit(
            font.render(
                f"BEST: {debug_rival.moves[best_move].name}",
                False,
                (0, 150, 0),
            ),
            (left, y),
        )

# NODE OVERLAY GOES HERE
# Toggle dengan tombol N (lihat main.py). Menampilkan pohon pencarian AI:
#   root (Charizard / MAX) -> tiap move Charizard (MIN) -> tiap balasan Pikachu (leaf)
showing_nodes = False
_node_cache = {"key": None, "data": None}
_node_fonts = {}


def _node_font(size):
    if size not in _node_fonts:
        _node_fonts[size] = pygame.font.Font("assets/pkmn.ttf", size)
    return _node_fonts[size]


def _fmt_score(value):
    if value is None:
        return ""
    if value >= 100000:
        return "WIN"
    if value <= -100000:
        return "LOSE"
    return str(int(value))


def _fmt_bound(value):
    if value == inf:
        return "inf"
    if value == -inf:
        return "-inf"
    return _fmt_score(value)


def _build_search_tree(rival_state, player_state, depth, mode):
    """Rebuild keputusan AI yang sama dengan choose_rival_move(), tapi
    setiap node disimpan sebagai dict supaya bisa digambar."""
    prune = mode == "alpha-beta"

    def new_node(label, kind):
        return {
            "label": label,
            "kind": kind,  # "MAX" / "MIN"
            "value": None,
            "alpha": None,
            "beta": None,
            "pruned": False,
            "on_path": False,
            "children": [],
        }

    def search(rival_s, player_s, d, alpha, beta, maximizing, node):
        if d == 0 or rival_s.hp <= 0 or player_s.hp <= 0:
            node["value"] = evaluate(rival_s, player_s)
            return node["value"]

        actor = rival_s if maximizing else player_s
        best = -inf if maximizing else inf
        moves = available_moves(actor)

        for pos, move_idx in enumerate(moves):
            next_rival = deepcopy(rival_s)
            next_player = deepcopy(player_s)
            if maximizing:
                simulate_move(next_rival, next_player, move_idx)
            else:
                simulate_move(next_player, next_rival, move_idx)

            child = new_node(actor.moves[move_idx].name, "MAX" if not maximizing else "MIN")
            node["children"].append(child)
            score = search(next_rival, next_player, d - 1, alpha, beta, not maximizing, child)

            if maximizing:
                best = max(best, score)
                alpha = max(alpha, best)
            else:
                best = min(best, score)
                beta = min(beta, best)

            if prune and beta <= alpha:
                # sisa cabang tidak pernah dievaluasi -> tandai sebagai pruned
                for rest_idx in moves[pos + 1:]:
                    cut = new_node(actor.moves[rest_idx].name, "MAX" if not maximizing else "MIN")
                    cut["pruned"] = True
                    node["children"].append(cut)
                break

        node["value"] = best
        node["alpha"] = alpha
        node["beta"] = beta
        return best

    root = new_node(rival_state.name, "MAX")
    best_score = -inf
    best_child = None
    alpha = -inf
    beta = inf

    for move_idx in available_moves(rival_state):
        sim_rival = deepcopy(rival_state)
        sim_player = deepcopy(player_state)
        simulate_move(sim_rival, sim_player, move_idx)

        child = new_node(rival_state.moves[move_idx].name, "MIN")
        root["children"].append(child)
        if prune:
            score = search(sim_rival, sim_player, depth - 1, alpha, beta, False, child)
        else:
            score = search(sim_rival, sim_player, depth - 1, -inf, inf, False, child)
            child["alpha"] = child["beta"] = None

        if score > best_score:
            best_score = score
            best_child = child
        alpha = max(alpha, best_score)

    root["value"] = best_score
    root["alpha"], root["beta"] = alpha, beta

    # tandai jalur terbaik (root -> move terbaik -> balasan player terbaik)
    node = root
    node["on_path"] = True
    if best_child is not None:
        node = best_child
        while node is not None:
            node["on_path"] = True
            nxt = None
            for c in node["children"]:
                if not c["pruned"] and c["value"] == node["value"]:
                    nxt = c
                    break
            node = nxt
    return root


def _dashed_line(screen, color, p1, p2, dash=6, gap=5, width=1):
    x1, y1 = p1
    x2, y2 = p2
    length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1)
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    pos = 0
    while pos < length:
        end = min(pos + dash, length)
        pygame.draw.line(
            screen, color,
            (x1 + dx * pos, y1 + dy * pos), (x1 + dx * end, y1 + dy * end), width,
        )
        pos += dash + gap


def _center_text(screen, font, text, color, center):
    surf = font.render(text, False, color)
    screen.blit(surf, surf.get_rect(center=center))


def node_overlay(screen, font):
    search_depth = 2
    ai_mode = config.ai_type

    # state yang benar-benar dilihat AI saat memilih move (sama seperti draw_ai_brain)
    debug_player = player
    debug_rival = rival
    log_idx = last_rival_turn - 2
    if 0 <= log_idx < len(move_logs):
        debug_player = move_logs[log_idx].player
        debug_rival = move_logs[log_idx].rival

    # cache supaya pohon tidak dihitung ulang 60x per detik
    key = (
        ai_mode,
        last_rival_turn,
        debug_player.hp, debug_player.defense,
        debug_rival.hp, debug_rival.defense,
        tuple(m.pp for m in debug_rival.moves),
        tuple(m.pp for m in debug_player.moves),
    )
    if _node_cache["key"] != key:
        _node_cache["key"] = key
        _node_cache["data"] = _build_search_tree(
            debug_rival, debug_player, search_depth, ai_mode
        )
    root = _node_cache["data"]

    W, H = screen.get_size()
    f_big = _node_font(16)
    f_mid = _node_font(14)
    f_small = _node_font(12)

    GREEN = (0, 150, 0)
    RED = (190, 0, 0)
    GREY = (170, 170, 170)
    DARK = (70, 70, 70)
    ORANGE = (200, 90, 0)
    BLUE = (20, 90, 170)

    # panel semi-transparan menutupi layar battle
    panel = pygame.Surface((W, H), pygame.SRCALPHA)
    panel.fill((250, 250, 250, 240))
    screen.blit(panel, (0, 0))

    # ---------- header ----------
    mode_text = "ALPHA-BETA (PRUNING)" if ai_mode == "alpha-beta" else "MINIMAX (NO PRUNING)"
    screen.blit(f_big.render(f"AI SEARCH TREE - TURN {last_rival_turn}", False, "black"), (15, 8))
    screen.blit(f_mid.render(f"{mode_text}   DEPTH: {search_depth}   [N] CLOSE", False, DARK), (15, 32))

    # ---------- layout ----------
    mids = root["children"]
    total_slots = sum(max(len(m["children"]), 1) for m in mids) or 1
    margin = 30
    slot_w = (W - margin * 2) / total_slots
    y_root, y_mid, y_leaf = 105, 265, 430

    positions = {}  # id(node) -> (x, y)
    slot = 0
    for m in mids:
        n_kids = max(len(m["children"]), 1)
        first = margin + slot_w * (slot + 0.5)
        last = margin + slot_w * (slot + n_kids - 0.5)
        positions[id(m)] = ((first + last) / 2, y_mid)
        for k, leaf in enumerate(m["children"]):
            positions[id(leaf)] = (margin + slot_w * (slot + k + 0.5), y_leaf)
        slot += n_kids
    if mids:
        positions[id(root)] = (
            (positions[id(mids[0])][0] + positions[id(mids[-1])][0]) / 2, y_root
        )
    else:
        positions[id(root)] = (W / 2, y_root)

    # ---------- garis (edge) ----------
    def draw_edges(node):
        px, py = positions[id(node)]
        for c in node["children"]:
            cx, cy = positions[id(c)]
            if c["pruned"]:
                _dashed_line(screen, GREY, (px, py), (cx, cy))
            elif c["on_path"]:
                pygame.draw.line(screen, GREEN, (px, py), (cx, cy), 4)
            else:
                pygame.draw.line(screen, DARK, (px, py), (cx, cy), 2)
            draw_edges(c)

    draw_edges(root)

    # ---------- node ----------
    # root
    rx, ry = positions[id(root)]
    _center_text(screen, f_mid, f"{root['label']} (MAX)", "black", (rx, ry - 48))
    r_rect = pygame.Rect(0, 0, 56, 56)
    r_rect.center = (rx, ry)
    pygame.draw.rect(screen, (220, 232, 250), r_rect, border_radius=8)
    pygame.draw.rect(screen, ORANGE, r_rect, 4, border_radius=8)
    _center_text(screen, f_mid, _fmt_score(root["value"]), "black", (rx, ry))

    leaves_seen = 0
    leaves_cut = 0

    for m in mids:
        mx, my = positions[id(m)]
        on_path = m["on_path"]
        edge = GREEN if on_path else (GREY if m["pruned"] else DARK)

        _center_text(screen, f_mid, m["label"], "black", (mx, my - 50))
        _center_text(screen, f_small, "MIN", DARK, (mx, my - 36))
        pygame.draw.circle(screen, (225, 245, 230), (mx, my), 26)
        pygame.draw.circle(screen, edge, (mx, my), 26, 4 if on_path else 2)
        _center_text(screen, f_mid, _fmt_score(m["value"]), "black", (mx, my))

        if ai_mode == "alpha-beta" and m["alpha"] is not None:
            _center_text(screen, f_small, f"a={_fmt_bound(m['alpha'])}", DARK, (mx, my + 40))
            _center_text(screen, f_small, f"b={_fmt_bound(m['beta'])}", DARK, (mx, my + 54))

        if not m["children"]:
            leaves_seen += 1  # terminal (HP habis) -> node ini sendiri leaf

        for leaf in m["children"]:
            lx, ly = positions[id(leaf)]
            box = pygame.Rect(0, 0, min(int(slot_w) - 6, 50), 40)
            box.center = (lx, ly)
            if leaf["pruned"]:
                leaves_cut += 1
                pygame.draw.rect(screen, (240, 243, 248), box, border_radius=6)
                pygame.draw.rect(screen, (200, 205, 215), box, 2, border_radius=6)
                _center_text(screen, f_small, leaf["label"][:3], GREY, (lx, ly + 30))
                continue
            leaves_seen += 1
            pygame.draw.rect(screen, (220, 232, 250), box, border_radius=6)
            pygame.draw.rect(screen, GREEN if leaf["on_path"] else BLUE, box, 4 if leaf["on_path"] else 2, border_radius=6)
            _center_text(screen, f_small, _fmt_score(leaf["value"]), "black", (lx, ly))
            _center_text(screen, f_small, leaf["label"][:3], DARK, (lx, ly + 30))

    # ---------- footer ----------
    pygame.draw.line(screen, "black", (15, 510), (W - 15, 510), 2)
    total = leaves_seen + leaves_cut
    stat = f"LEAVES: {leaves_seen}/{total}"
    if ai_mode == "alpha-beta":
        stat += f"   PRUNED: {leaves_cut}"
    screen.blit(f_mid.render(stat, False, "black"), (15, 520))

    best_label = next((c["label"] for c in mids if c["on_path"]), None)
    if best_label is not None:
        screen.blit(
            f_mid.render(f"BEST: {best_label} ({_fmt_score(root['value'])})", False, GREEN),
            (15, 545),
        )
    screen.blit(
        f_small.render("GREEN = CHOSEN PATH   DASHED/FADED = PRUNED   MOVE NAME UNDER LEAF = PIKACHU REPLY", False, DARK),
        (15, 575),
    )

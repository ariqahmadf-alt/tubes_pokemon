import os
import pygame
import asyncio
from copy import deepcopy
import config
import maze
import battle

import heapq
from itertools import count

from collections import deque

ROOT = os.path.dirname(os.path.abspath(__file__))
original_speed = config.rival_speed


def dist(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


window_size = (950, 600)


class Character:
    pos = pygame.Vector2(0, 0)

    # pattern:
    # idle, walk1, walk2
    sprites = []

    # direction (1-4, right left up down)
    dir = 0
    walk_frame = 0
    moving = False
    moving_dir = 0

    # the points to traverse
    path = [maze.points[1][1]]
    queue = []
    queue_curr = 0

    # 2 - A* (rival)
    # 5 - player
    ai_type = 0

    def __init__(self, point, name, ai_type):
        self.pos = pygame.Vector2(point.spos(), point.spos())
        self.path = [point]
        self.sprites = []
        self.last_point = point
        self.ai_type = ai_type
        self.last_target_point = point
        self.walk_frame = 0
        self.moving = False
        self.moving_dir = -1
        for i in range(12):
            sprite = pygame.image.load(f"{ROOT}/assets/{name}/{name}_{i}.png")
            self.sprites.append(sprite)

    def ai(self):
        # safeguard: stay at last point if there's no path
        if len(self.path) == 0:
            self.path = [self.last_point]

        # current point
        point = deepcopy(self.path[0])

        self.moving = False

        # move ghost to their npi
        #
        # when moving, always check against ghost and point pos to ensure
        # that ghost lands on the point instead of overshooting
        if self.pos.x > point.spos().x:
            self.pos.x -= min(config.rival_speed, abs(point.spos().x - self.pos.x))
            self.moving = True
            self.dir = 2
        elif self.pos.x < point.spos().x:
            self.pos.x += min(config.rival_speed, abs(point.spos().x - self.pos.x))
            self.moving = True
            self.dir = 3

        if self.pos.y > point.spos().y:
            self.pos.y -= min(config.rival_speed, abs(point.spos().y - self.pos.y))
            self.moving = True
            self.dir = 1
        elif self.pos.y < point.spos().y:
            self.pos.y += min(config.rival_speed, abs(point.spos().y - self.pos.y))
            self.moving = True
            self.dir = 0

        if self.moving:
            self.walk_frame += 1
        else:
            self.walk_frame = 0

        # move to next point if ghost is close to its current
        if dist(point.spos(), self.pos) < 1:
            # initiate dialog if rival is near player
            if self.ai_type == 2 and (self.pos - characters[0].pos).magnitude() < 45:
                battle.battle_text = "I heard you haven't invested in\nOpenAI. Are you one of those\n'pencil-sloppers'?"

            # prepare points for ghost AI
            for y in range(len(maze.points)):
                for x in range(len(maze.points[y])):
                    maze.points[y][x].prio = -1

            self.last_point = maze.points[int(self.path[0].pos.y)][
                int(self.path[0].pos.x)
            ]
            self.last_point.prio = 0

            # process AI based on type
            match self.ai_type:
                # case 0:
                #     self.path = []
                #     self.dummy(self.last_point, pygame.mouse.get_pos())
                case 1:
                    self.path = []
                    self.queue = []
                    self.queue_curr = 0
                    if hasattr(self, "target_point"):
                        del self.target_point
                    self.ucs_explore(self.last_point)
                    if hasattr(self, "target_point"):
                        self.ucs_path(self.target_point)
                        self.path.reverse()
                        # print(self.path[0].pos)
                case 2:
                    self.path = []
                    self.queue = []
                    self.queue_curr = 0

                    if hasattr(self, "target_point"):
                        del self.target_point

                    self.astar_explore(self.last_point)

                    if hasattr(self, "target_point"):
                        self.ucs_path(self.target_point)
                        self.path.reverse()
                case 3:
                    self.path = []
                    self.queue = []
                    self.queue_curr = 0

                    if hasattr(self, "target_point"):
                        del self.target_point

                    self.greedy_explore(self.last_point)

                    if hasattr(self, "target_point"):
                        self.ucs_path(self.target_point)
                        self.path.reverse()
                case 0:
                    self.path = []
                    self.queue = []
                    self.queue_curr = 0

                    if hasattr(self, "target_point"):
                        del self.target_point

                    self.bfs_explore(self.last_point)

                    if hasattr(self, "target_point"):
                        self.ucs_path(self.target_point)
                        self.path.reverse()
                case 5:
                    path_pos = self.path[0].pos
                    point = maze.Point((path_pos.x, path_pos.y), False)
                    if self.moving_dir != -1:
                        self.dir = self.moving_dir
                    match self.moving_dir:
                        case 0:
                            point = maze.Point((path_pos.x, path_pos.y + 1), False)
                        case 1:
                            point = maze.Point((path_pos.x, path_pos.y - 1), False)
                        case 2:
                            point = maze.Point((path_pos.x - 1, path_pos.y), False)
                        case 3:
                            point = maze.Point((path_pos.x + 1, path_pos.y), False)
                    if not maze.points[int(point.pos.y)][int(point.pos.x)].wall:
                        self.path = [point]

    # from GPT 5.6 (using main.py and maze.py as context)
    def astar_explore(self, start):
        frontier = []
        tie_breaker = count()
        target_pos = pygame.mouse.get_pos()

        def heuristic(point):
            return dist(point.spos(), target_pos)

        start.prio = 0
        self.queue = []

        heapq.heappush(
            frontier,
            (heuristic(start), next(tie_breaker), 0, start),
        )

        while frontier:
            _, _, cost, point = heapq.heappop(frontier)

            # Ignore stale entries after a cheaper route was found.
            if cost != point.prio:
                continue

            self.queue.append(point)

            if dist(target_pos, point.spos()) < 10:
                self.target_point = point
                return

            neighbors = (
                getattr(point, "right", None),
                getattr(point, "left", None),
                getattr(point, "top", None),
                getattr(point, "bottom", None),
            )

            for neighbor in neighbors:
                if neighbor is None:
                    continue

                new_cost = cost + 1

                if neighbor.prio == -1 or new_cost < neighbor.prio:
                    neighbor.prio = new_cost
                    priority = new_cost + heuristic(neighbor)

                    heapq.heappush(
                        frontier,
                        (priority, next(tie_breaker), new_cost, neighbor),
                    )

    # from GPT 5.6 (using main.py and maze.py as context)
    # Osman's first attempt made a FIFO list by accident
    def ucs_explore(self, start):
        frontier = []
        tie_breaker = count()

        start.prio = 0
        self.queue = []

        heapq.heappush(
            frontier,
            (0, next(tie_breaker), start),
        )

        target_pos = pygame.mouse.get_pos()

        while frontier:
            cost, _, point = heapq.heappop(frontier)

            # Ignore stale entries left behind after a cheaper route was found.
            if cost != point.prio:
                continue

            self.queue.append(point)

            if dist(target_pos, point.spos()) < 10:
                self.target_point = point
                return

            neighbors = (
                getattr(point, "right", None),
                getattr(point, "left", None),
                getattr(point, "top", None),
                getattr(point, "bottom", None),
            )

            for neighbor in neighbors:
                if neighbor is None:
                    continue

                new_cost = cost + 1

                if neighbor.prio == -1 or new_cost < neighbor.prio:
                    neighbor.prio = new_cost

                    heapq.heappush(
                        frontier,
                        (new_cost, next(tie_breaker), neighbor),
                    )

    def greedy_explore(self, start):
        frontier = []
        tie_breaker = count()
        target_pos = pygame.mouse.get_pos()

        start.prio = 0
        self.queue = []

        heuristic = lambda point: dist(point.spos(), target_pos)

        heapq.heappush(
            frontier,
            (heuristic(start), next(tie_breaker), 0, start),
        )

        while frontier:
            _, _, cost, point = heapq.heappop(frontier)

            # Ignore stale entries after a cheaper route was found.
            if cost != point.prio:
                continue

            self.queue.append(point)

            if dist(target_pos, point.spos()) < 10:
                self.target_point = point
                return

            neighbors = (
                getattr(point, "right", None),
                getattr(point, "left", None),
                getattr(point, "top", None),
                getattr(point, "bottom", None),
            )

            for neighbor in neighbors:
                if neighbor is None:
                    continue

                new_cost = cost + 1

                if neighbor.prio == -1 or new_cost < neighbor.prio:
                    neighbor.prio = new_cost

                    # Greedy best-first uses only h(n), unlike A*'s g(n) + h(n).
                    heapq.heappush(
                        frontier,
                        (heuristic(neighbor), next(tie_breaker), new_cost, neighbor),
                    )

    def bfs_explore(self, start):
        frontier = deque([start])
        target_pos = pygame.mouse.get_pos()

        start.prio = 0
        self.queue = []

        while frontier:
            point = frontier.popleft()
            self.queue.append(point)

            if dist(target_pos, point.spos()) < 10:
                self.target_point = point
                return

            neighbors = (
                getattr(point, "right", None),
                getattr(point, "left", None),
                getattr(point, "top", None),
                getattr(point, "bottom", None),
            )

            for neighbor in neighbors:
                if neighbor is None or neighbor.prio != -1:
                    continue

                neighbor.prio = point.prio + 1
                frontier.append(neighbor)

    def ucs_path(self, point):
        next_point = point
        closest = point.prio

        # if hasattr(point, "right"):
        #     print("r", point.right.prio)
        # if hasattr(point, "left"):
        #     print("l", point.left.prio)
        # if hasattr(point, "top"):
        #     print("t", point.top.prio)
        # if hasattr(point, "bottom"):
        #     print("b", point.bottom.prio)

        # go to neighbor with smallest prio
        if (
            hasattr(point, "right")
            and point.right.prio != -1
            and point.right.prio < closest
        ):
            next_point = point.right
            closest = point.right.prio
        if (
            hasattr(point, "left")
            and point.left.prio != -1
            and point.left.prio < closest
        ):
            next_point = point.left
            closest = point.left.prio
        if hasattr(point, "top") and point.top.prio != -1 and point.top.prio < closest:
            next_point = point.top
            closest = point.top.prio
        if (
            hasattr(point, "bottom")
            and point.bottom.prio != -1
            and point.bottom.prio < closest
        ):
            next_point = point.bottom
            closest = point.bottom.prio

        if next_point.pos == point.pos:
            return
        self.path.append(point)
        self.ucs_path(next_point)

    # recursively find the closest point to target
    def dummy(self, next_point, target):
        mouse = pygame.mouse.get_pos()

        # find next point's closest neighbor to target
        closest_point = next_point
        closest = dist(mouse, closest_point.spos())

        if hasattr(next_point, "right"):
            distance = dist(mouse, next_point.right.spos())
            if distance < closest:
                closest_point = next_point.right
                closest = dist(mouse, closest_point.spos())

        if hasattr(next_point, "left"):
            distance = dist(mouse, next_point.left.spos())
            if distance < closest:
                closest_point = next_point.left
                closest = dist(mouse, closest_point.spos())

        if hasattr(next_point, "top"):
            distance = dist(mouse, next_point.top.spos())
            if distance < closest:
                closest_point = next_point.top
                closest = dist(mouse, closest_point.spos())

        if hasattr(next_point, "bottom"):
            distance = dist(mouse, next_point.bottom.spos())
            if distance < closest:
                closest_point = next_point.bottom
                closest = dist(mouse, closest_point.spos())

        if closest_point != next_point:
            closest_point.prio = next_point.prio + 1
            self.path.append(closest_point)
            self.dummy(closest_point, mouse)

    def draw(self, screen):
        sprite_idx = self.dir * 3
        if self.moving:
            if self.walk_frame < 15 / config.rival_speed:
                sprite_idx += 1
            elif self.walk_frame < 30 / config.rival_speed:
                sprite_idx += 0
            elif self.walk_frame < 45 / config.rival_speed:
                sprite_idx += 2
            elif self.walk_frame < 60 / config.rival_speed:
                sprite_idx += 0
            else:
                self.walk_frame = 0
        sprite = self.sprites[sprite_idx]
        scaled = pygame.transform.scale(
            sprite,
            (
                sprite.get_width() * config.maze_scale / 13,
                sprite.get_height() * config.maze_scale / 13,
            ),
        )
        rect = scaled.get_rect()
        rect.x = self.pos.x - rect.height / 2
        rect.y = self.pos.y - rect.width / 2
        screen.blit(scaled, rect)

    def draw_points(self, screen):
        font = pygame.font.SysFont("Arial", 16)
        highest_queue_prio = 1
        for queue in self.queue:
            highest_queue_prio = max(highest_queue_prio, queue.prio)
        highest_path_prio = 1
        for path in self.path:
            highest_path_prio = max(highest_path_prio, path.prio)
        for y in range(len(maze.points)):
            for x in range(len(maze.points[y])):
                if maze.points[y][x].wall:
                    continue
                pos = deepcopy(maze.points[y][x].pos)

                # use different points if this point is in the queue, path, or is target
                col = "#dda49c"
                if hasattr(self, "target_point") and self.target_point.pos == pos:
                    col = "green"
                else:
                    for queue in self.queue:
                        if queue.pos == pos:
                            col = "blue" if config.maze_type == 0 else "magenta"
                    for path in self.path:
                        if path.pos == pos:
                            col = "red"
                pos *= config.maze_scale
                pos.x += config.maze_scale / 2
                pos.y += config.maze_scale / 2

                pos.x -= 7.5
                pos.y -= 7.5

                screen.blit(font.render(str(maze.points[y][x].prio), True, col), pos)
                # use different color if this point is in the expanded list
                # pygame.draw.circle(screen, col, pos, 3, 5)

    def stats(self, screen):
        row = 10
        font = pygame.font.SysFont("Arial", 24)
        self.stat("Expanded:", len(self.queue), row, screen, font, "white")
        path_cost = "-"
        if len(self.path) > 0:
            path_cost = self.path[len(self.path) - 1].prio
        row += 40
        self.stat("Path Cost:", path_cost, row, screen, font, "white")

    def help(self, screen):
        row = 130
        font = pygame.font.SysFont("Arial", 24)
        self.stat("Controls:", "", row, screen, font, "white")
        row += 40
        self.stat("A*:", 1, row, screen, font, "red")
        row += 40
        self.stat("UCS:", 2, row, screen, font, "magenta")
        row += 40
        self.stat("BFS:", 3, row, screen, font, "cyan")
        row += 40
        self.stat("Greedy:", 4, row, screen, font, "orange")
        row += 40
        self.stat("All:", 5, row, screen, font, "White")

    def stat(self, left_str, right_str, y, screen, font, col):
        text_surface = font.render(left_str, True, col)
        text_rect = text_surface.get_rect(topleft=(570, y))
        screen.blit(text_surface, text_rect)

        text_surface = font.render(str(right_str), True, col)
        text_rect = text_surface.get_rect(topright=(window_size[0] - 10, y))
        screen.blit(text_surface, text_rect)


# initialize characters
characters = []
characters.append(Character(maze.points[9][7], "player", 5))
characters.append(Character(maze.points[5][6], "rival", 2))


def draw_points(screen):
    for y in range(len(maze.points)):
        for x in range(len(maze.points[y])):
            if maze.points[y][x].wall:
                continue
            pos = deepcopy(maze.points[y][x].pos)
            col = "#dda49c"
            pos *= config.maze_scale
            pos.x += config.maze_scale / 2
            pos.y += config.maze_scale / 2
            pygame.draw.circle(screen, col, pos, 3, 5)


def next_step():
    can_attack = battle.player.moves[battle.chosen_move].pp != 0
    if battle.turn_step == 0 and can_attack:
        (battle.battle_text, battle.move_logs) = battle.player.choose_move(
            battle.chosen_move,
            battle.battle_text,
            battle.move_logs,
            battle.rival,
        )
        battle.turn_step += 1
        battle.last_rival_turn = len(battle.move_logs) + 1
    elif battle.turn_step == 1:
        battle.turn_step += 1

        # enemy AI here
        battle.battle_text = battle.rival.name + " is thinking..."

    elif battle.turn_step == 2:
        rival_move = battle.choose_rival_move(2, "alpha-beta")
        
        (battle.battle_text, battle.move_logs) = battle.rival.choose_move(
            rival_move,
            battle.battle_text,
            battle.move_logs,
            battle.player,
        )
        battle.turn_step += 1
    elif battle.turn_step == 3:
        battle.turn_step = 0


async def main():
    pygame.init()
    screen = pygame.display.set_mode((int(window_size[0]), int(window_size[1])))
    clock = pygame.time.Clock()
    running = True
    maze_og_toggle = True
    active_ghost = 0
    font = pygame.font.Font("assets/pkmn.ttf", 24)
    state = "overworld"

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # register arrow keys as player movement
                if event.key == pygame.K_UP:
                    if state == "battle":
                        battle.chosen_move = battle.inc_chosen_move(
                            -1, battle.chosen_move
                        )
                    elif battle.battle_text == "":
                        characters[0].moving_dir = 1
                elif event.key == pygame.K_DOWN:
                    if state == "battle":
                        battle.chosen_move = battle.inc_chosen_move(
                            1, battle.chosen_move
                        )
                    elif battle.battle_text == "":
                        characters[0].moving_dir = 0
                elif event.key == pygame.K_LEFT and battle.battle_text == "":
                    characters[0].moving_dir = 2
                elif event.key == pygame.K_RIGHT and battle.battle_text == "":
                    characters[0].moving_dir = 3
                elif event.key == pygame.K_s and state == "battle":
                    battle.chosen_log = min(
                        battle.chosen_log + 1, len(battle.move_logs) - 1
                    )
                elif event.key == pygame.K_w and state == "battle":
                    battle.chosen_log = max(battle.chosen_log - 1, 0)
                elif event.key == pygame.K_SPACE:
                    if state == "battle":
                        next_step()
                    elif battle.battle_text != "":
                        state = "battle"
                elif event.key == pygame.K_m:
                    maze_og_toggle = not maze_og_toggle
                    battle.showing_log = not battle.showing_log

            elif event.type == pygame.KEYUP:
                # player will stop moving upon reaching its target
                if event.key == pygame.K_UP:
                    characters[0].moving_dir = -1
                elif event.key == pygame.K_DOWN:
                    characters[0].moving_dir = -1
                elif event.key == pygame.K_LEFT:
                    characters[0].moving_dir = -1
                elif event.key == pygame.K_RIGHT:
                    characters[0].moving_dir = -1

        if state == "overworld":
            screen.fill("black")
        elif state == "battle":
            screen.fill("white")

        if state == "overworld":
            img_to_use = maze.maze_og_img if maze_og_toggle else maze.img
            divisor = 16.0 if maze_og_toggle else 1.0
            final_img = pygame.transform.scale(
                img_to_use,
                (
                    img_to_use.get_width() * config.maze_scale / divisor,
                    img_to_use.get_height() * config.maze_scale / divisor,
                ),
            )
            screen.blit(final_img, maze.rect)

            # draw_points(screen)
            characters[1].ai()
            characters[1].draw(screen)
            characters[0].ai()
            characters[0].draw(screen)
            if battle.battle_text != "":
                battle.draw_battle_text(screen, font)
        elif state == "battle":
            if battle.turn_step != 0:
                battle.draw_battle_text(screen, font)
            else:
                battle.draw_moves(screen, font)
            battle.draw_pokemon(screen)
            battle.draw_stats(screen, font)
            if battle.showing_log:
                battle.draw_logs(screen, font)
            else:
                battle.draw_ai_brain(screen, font)

        pygame.display.flip()
        # print(pygame.mouse.get_pos())

        clock.tick(60)
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())

import pygame
import config
import os
from copy import deepcopy

ROOT = os.path.dirname(os.path.abspath(__file__))
# initialize maze
img = pygame.image.load(f"{ROOT}/assets/map{config.maze_type}.png")
rect = img.get_rect()
rect.topleft = (0, 0)

maze_og_img = pygame.image.load(f"{ROOT}/assets/map{config.maze_type}_og.png")

def dist(p1, p2):
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

class Point:
    pos: pygame.Vector2
    wall = True
    dist_start = 0
    dist_target = 0
    prio = -1

    def __init__(self, pos, wall):
        self.pos = pygame.Vector2(pos[0], pos[1])
        self.wall = wall

    def print(self):
        print(self.pos, self.right, self.left, self.top, self.bottom, self.wall)

    def spos(self):
        pos = deepcopy(self.pos)
        pos *= config.maze_scale
        pos.x += config.maze_scale / 2
        pos.y += config.maze_scale / 2
        return pos

    def set_queue_properties(self, start_pos, prio):
        if self.prio != -1:
            return
        self.dist_start = dist(self.spos(), start_pos)
        self.dist_target = dist(self.spos(), pygame.mouse.get_pos())
        self.prio = prio

    def not_in_queue(self, point, queue):
        for queue_point in queue:
            if point.pos.x == queue_point.pos.x and point.pos.y == queue_point.pos.y:
                return False
        return True

    def add_to_queue(self, queue):
        if hasattr(self, 'right') and self.not_in_queue(self.right, queue):
            queue.append(self.right)
        if hasattr(self, 'left') and self.not_in_queue(self.left, queue):
            queue.append(self.left)
        if hasattr(self, 'top') and self.not_in_queue(self.top, queue):
            queue.append(self.top)
        if hasattr(self, 'bottom') and self.not_in_queue(self.bottom, queue):
            queue.append(self.bottom)


points = []
# get raw points from maze image
for y in range(img.height):
    row = []
    for x in range(img.width):
        col = img.get_at((x, y))

        # this is a point if the pixel is black
        point = Point((x, y), col.r > 10 or col.g > 10 or col.b > 10)
        row.append(point)

        if point.wall:
            continue

        # add this point as a neighbor to the left one, and vice versa
        left_point = row[x - 1]
        if x > 0 and not left_point.wall and left_point.pos.x == row[x].pos.x - 1:
            row[x - 1].right = row[x]
            row[x].left = row[x - 1]

        # add this point as a neighbor to the top one, and vice versa
        top_point = points[y - 1][x]
        if y > 0 and not top_point.wall and top_point.pos.y == row[x].pos.y - 1:
            points[y - 1][x].bottom = row[x]
            row[x].top = points[y - 1][x]

    points.append(row)

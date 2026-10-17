import pygame


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


def scale_sprite_vec2(sprite, scale, pos, rot=0):
    scaled = pygame.transform.scale(
        sprite,
        (
            sprite.get_width() * scale[0],
            sprite.get_height() * scale[1],
        ),
    )
    scaled = pygame.transform.rotate(scaled, rot)
    rect = scaled.get_rect()
    rect.x = pos[0]
    rect.y = pos[1]
    return (scaled, rect)

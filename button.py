import pygame
import string


TEXT_BOX_CHARACTERS = string.ascii_lowercase + " "


class TextBox:
    def __init__(self, pos, font, colour=(255, 255, 255), text_colour=(0, 0, 0)):
        self.text = ""
        self.pos = pos
        self.colour = colour
        self.font = font
        self.text_colour = text_colour
        self.update_size()
        self.active = False

    def draw(self, surface):
        self.update_size()
        text = self.font.render(self.text, False, self.text_colour)
        if self.active:
            pygame.draw.rect(surface, (255, 150, 150), (self.pos[0], self.pos[1], self.size[0], self.size[1]), width=0)
        pygame.draw.rect(surface, self.colour, (self.pos[0], self.pos[1], self.size[0], self.size[1]), width=3)
        surface.blit(text, (self.pos[0]+5, self.pos[1]))

    def update_size(self):
        self.size = self.font.size(self.text)
        self.size = (self.size[0]+10, self.size[1])

    def on_click(self, x, y):
        if self.pos[0] <= x <= self.pos[0]+self.size[0]:
            if self.pos[1] <= y <= self.pos[1] + self.size[1]:
                self.active = not self.active
            else:
                self.active = False
        else:
            self.active = False

    def on_key(self, key ,keys):
        if self.active:
            if key == keys.BACKSPACE:
                self.text = self.text[:-1]
            try:
                if chr(key) in TEXT_BOX_CHARACTERS:
                    self.text = self.text + chr(key)
            except ValueError:
                pass


class Button:
    def __init__(self, text, func, pos, font, colour=(255, 255, 255), text_colour=(0, 0, 0)):
        self.text = text
        self.func = func
        self.pos = pos
        self.colour = colour
        self.font = font
        self.text_colour = text_colour
        self.size = font.size(text)
        self.size = (self.size[0]+10, self.size[1])

    def draw(self, surface):
        text = self.font.render(self.text, False, self.text_colour)
        pygame.draw.rect(surface, self.colour, (self.pos[0], self.pos[1], self.size[0], self.size[1]), width=3)
        surface.blit(text, (self.pos[0]+5, self.pos[1]))

    def on_click(self, x, y):
        if self.pos[0] <= x <= self.pos[0]+self.size[0]:
            if self.pos[1] <= y <= self.pos[1] + self.size[1]:
                self.func()

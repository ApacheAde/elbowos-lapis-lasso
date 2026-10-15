#!/usr/bin/env python3
"""Lapis Lasso — neon grappling-swing arcade for ElbowOS. Python 3 + pygame."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/LAPIS_LASSO_ElbowOS.mp4")
TITLE, HANDLE = "LAPIS LASSO", "x.com/ElbowOS"

VOID = (6, 8, 28)
INK = (14, 22, 58)
AZURE = (64, 140, 255)
LAPIS = (28, 72, 180)
GOLD = (255, 214, 72)
MAG = (255, 72, 168)
LIME = (120, 255, 140)
CYAN = (48, 220, 255)
WHITE = (240, 246, 255)
ROSE = (255, 96, 128)
AMBER = (255, 180, 48)

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.font_lg = pygame.font.SysFont("DejaVu Sans", 72, bold=True)
        self.font = pygame.font.SysFont("DejaVu Sans", 42, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans", 28)
        self.clock = pygame.time.Clock()
        self.score = self.combo = self.t = self.flash = 0
        self.px, self.py = W // 2, 1400
        self.vx, self.vy = 0.0, 0.0
        self.attached = None  # (ax, ay, length)
        self.anchors = []
        self.orbs = []
        self.sparks = []
        self.stars = []
        for _ in range(60):
            self.stars.append([
                random.randint(0, W), random.randint(0, H),
                random.uniform(0.4, 1.6), random.choice([AZURE, CYAN, GOLD])
            ])
        self.spawn_world()
        self.cooldown = 0

    def spawn_world(self):
        self.anchors = []
        for i in range(8):
            x = 180 + (i % 4) * 220 + random.randint(-30, 30)
            y = 400 + (i // 4) * 420 + random.randint(-40, 40)
            self.anchors.append([x, y, random.choice([AZURE, LAPIS, CYAN])])
        self.orbs = []
        for _ in range(6):
            self.orbs.append([
                random.randint(200, W-200), random.randint(500, 1500),
                random.uniform(-1.2, 1.2), random.uniform(-0.6, 0.6),
                random.choice([MAG, LIME, GOLD, AMBER])
            ])

    def burst(self, x, y, col, n=10):
        for _ in range(n):
            a = random.uniform(0, 6.28)
            sp = random.uniform(1.5, 8)
            self.sparks.append([x, y, math.cos(a)*sp, math.sin(a)*sp, 16, col])

    def attach_to(self, ax, ay):
        dx, dy = ax - self.px, ay - self.py
        L = math.hypot(dx, dy) or 40
        self.attached = (ax, ay, L)
        self.burst(self.px, self.py, CYAN, 6)

    def release(self):
        if self.attached:
            self.attached = None
            self.burst(self.px, self.py, GOLD, 5)

    def autoplay(self):
        # simple AI: if free and near an orb or timer, attach to a good anchor
        if self.attached is None and self.cooldown <= 0:
            # pick an anchor that is above and not too far
            candidates = [a for a in self.anchors if a[1] < self.py - 80]
            if candidates:
                best = min(candidates, key=lambda a: abs(a[0] - self.px) + abs(a[1] - self.py)*0.6)
                self.attach_to(best[0], best[1])
                self.cooldown = 40
        elif self.attached and random.random() < 0.015:
            self.release()
        # slight boost toward orbs when free
        if self.attached is None:
            if self.orbs:
                ox, oy = min(self.orbs, key=lambda o: math.hypot(o[0]-self.px, o[1]-self.py))[:2]
                dx, dy = ox - self.px, oy - self.py
                d = math.hypot(dx, dy) or 1
                if d < 600:
                    self.vx += dx / d * 0.4
                    self.vy += dy / d * 0.25

    def tick(self):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        self.cooldown = max(0, self.cooldown - 1)
        # gravity when free
        if self.attached is None:
            self.vy += 0.22
            self.vx *= 0.992
        else:
            ax, ay, L = self.attached
            dx, dy = self.px - ax, self.py - ay
            dist = math.hypot(dx, dy) or 1
            # constraint
            if dist > L * 1.01 or dist < L * 0.99:
                scale = L / dist
                self.px = ax + dx * scale
                self.py = ay + dy * scale
            # tangential velocity (simple)
            # project velocity perpendicular to radius
            rx, ry = dx / dist, dy / dist
            vdot = self.vx * rx + self.vy * ry
            self.vx -= vdot * rx
            self.vy -= vdot * ry
            # add a bit of swing energy
            self.vx += ry * 0.18
            self.vy -= rx * 0.18
        self.px += self.vx
        self.py += self.vy
        # bounds
        self.px = max(40, min(W-40, self.px))
        self.py = max(100, min(H-100, self.py))
        if self.py > H - 120:
            self.vy = -abs(self.vy) * 0.6
        # orbs
        for o in self.orbs:
            o[0] += o[2]
            o[1] += o[3]
            if o[0] < 120 or o[0] > W-120:
                o[2] *= -1
            if o[1] < 300 or o[1] > 1600:
                o[3] *= -1
            if math.hypot(o[0]-self.px, o[1]-self.py) < 48:
                self.score += 50 + self.combo * 10
                self.combo += 1
                self.flash = 10
                self.burst(o[0], o[1], o[4], 14)
                o[0] = random.randint(200, W-200)
                o[1] = random.randint(400, 1400)
                o[4] = random.choice([MAG, LIME, GOLD, AMBER])
        # sparks
        for p in self.sparks:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.sparks = [p for p in self.sparks if p[4] > 0]
        # stars drift
        for e in self.stars:
            e[1] -= e[2]
            if e[1] < 0:
                e[1] = H
                e[0] = random.randint(0, W)

    def draw(self, surf):
        surf.fill(VOID)
        # stars
        for x, y, s, c in self.stars:
            pygame.draw.circle(surf, c, (int(x), int(y)), int(s))
        # anchors
        for ax, ay, col in self.anchors:
            pygame.draw.circle(surf, col, (int(ax), int(ay)), 18)
            pygame.draw.circle(surf, WHITE, (int(ax), int(ay)), 18, 2)
        # lasso line
        if self.attached:
            ax, ay, _ = self.attached
            pygame.draw.line(surf, CYAN, (int(self.px), int(self.py)), (int(ax), int(ay)), 3)
        # orbs
        for ox, oy, _, _, col in self.orbs:
            pygame.draw.circle(surf, col, (int(ox), int(oy)), 22)
            pygame.draw.circle(surf, WHITE, (int(ox), int(oy)), 22, 2)
        # player
        pygame.draw.circle(surf, GOLD, (int(self.px), int(self.py)), 28)
        pygame.draw.circle(surf, AMBER, (int(self.px), int(self.py)), 28, 3)
        if self.flash:
            pygame.draw.circle(surf, WHITE, (int(self.px), int(self.py)), 36, 2)
        # sparks
        for x, y, _, _, life, col in self.sparks:
            pygame.draw.circle(surf, col, (int(x), int(y)), max(1, life//4))
        # UI
        title = self.font_lg.render(TITLE, True, GOLD)
        surf.blit(title, title.get_rect(center=(W//2, 120)))
        sc = self.font.render(f"SCORE  {self.score}", True, WHITE)
        surf.blit(sc, sc.get_rect(center=(W//2, H-180)))
        handle = self.font_sm.render(HANDLE, True, CYAN)
        surf.blit(handle, handle.get_rect(center=(W//2, H-110)))
        if self.combo > 1:
            cb = self.font_sm.render(f"COMBO x{self.combo}", True, MAG)
            surf.blit(cb, cb.get_rect(center=(W//2, H-50)))

    def play_interactive(self):
        running = True
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                    if self.attached:
                        self.release()
                    else:
                        # attach to nearest above
                        cands = [a for a in self.anchors if a[1] < self.py]
                        if cands:
                            best = min(cands, key=lambda a: math.hypot(a[0]-self.px, a[1]-self.py))
                            self.attach_to(best[0], best[1])
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.vx -= 0.5
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.vx += 0.5
            self.tick()
            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def record(self):
        frames = FPS * SECS
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{W}x{H}", "-pix_fmt", "rgb24", "-r", str(FPS),
            "-i", "-", "-an", "-vcodec", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
            OUT
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        canvas = pygame.Surface((W, H))
        try:
            for i in range(frames):
                self.autoplay()
                self.tick()
                self.draw(canvas)
                raw = pygame.image.tostring(canvas, "RGB")
                proc.stdin.write(raw)
        finally:
            proc.stdin.close()
            err = proc.stderr.read().decode()
            rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", OUT)
        pygame.quit()

def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()

if __name__ == "__main__":
    main()

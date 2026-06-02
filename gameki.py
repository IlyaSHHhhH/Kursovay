import pygame
import sys
import random
import math
import json
import os

# Инициализация Pygame и звука
pygame.init()
pygame.mixer.init()

# ========== НАСТРОЙКИ ЭКРАНА (ПОЛНОЭКРАННЫЙ РЕЖИМ) ==========
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("2-D Стратегия")

# ========== РАЗМЕР КАРТЫ ==========
MAP_WIDTH = 12      # количество гексов по горизонтали (координата q)
MAP_HEIGHT = 10     # количество гексов по вертикали (координата r)

# ========== АДАПТИВНЫЙ РАЗМЕР ГЕКСА ==========
# Вычисляем радиус гекса так, чтобы карта помещалась на экране с отступами
HEX_RADIUS = min(
    (WIDTH - 200) // (MAP_WIDTH * 1.8),
    (HEIGHT - 200) // (MAP_HEIGHT * 1.6)
)
HEX_RADIUS = max(30, min(80, HEX_RADIUS))  # но не слишком мелко/крупно
HEX_WIDTH = HEX_RADIUS * 2
HEX_HEIGHT = math.sqrt(3) * HEX_RADIUS
FPS = 60
clock = pygame.time.Clock()

# ========== ЦВЕТА ==========
COLOR_BG = (20, 25, 40)                  # фон
COLOR_HEX_DARK = (60, 70, 90)            # тёмный гекс
COLOR_HEX_LIGHT = (90, 100, 120)         # светлый гекс
COLOR_HEX_HOVER = (130, 140, 160)        # подсветка при наведении
PLAYER_UNIT = (0, 180, 255)              # цвет юнитов игрока
ENEMY_UNIT = (230, 70, 70)               # цвет юнитов врага
PLAYER_BUILD = (0, 150, 200)             # цвет зданий игрока
ENEMY_BUILD = (180, 50, 50)              # цвет зданий врага
WALL_COLOR = (140, 140, 160)             # цвет стен
UI_PANEL = (0, 0, 0, 220)               # полупрозрачная панель интерфейса
TEXT_COLOR = (255, 255, 255)             # цвет текста
HEALTH_GREEN = (100, 200, 100)           # цвет полоски здоровья
BUTTON_COLOR = (80, 100, 140)            # цвет кнопок
BUTTON_HOVER = (120, 140, 180)           # цвет кнопки при наведении
ATTACK_RANGE_COLOR = (200, 70, 70, 100)  # подсветка радиуса атаки
MOVE_RANGE_COLOR = (70, 200, 70, 100)    # подсветка радиуса движения
SELECTION_COLOR = (255, 255, 0)          # цвет рамки выделения
RES_BG_COLOR = (40, 50, 70)              # фон для блока ресурсов
CRIT_COLOR = (255, 215, 0)               # цвет критического удара (золотой)
EXIT_BUTTON_COLOR = (180, 60, 60)        # цвет кнопки выхода

# ========== ДАННЫЕ О ЗДАНИЯХ ==========
BUILDINGS = {
    "ферма":   {"cost": {"gold": 80, "wood": 20}, "production": {"food": 10}, "hp": 100},
    "шахта":   {"cost": {"gold": 100, "stone": 30}, "production": {"gold": 15}, "hp": 100},
    "лесопилка":{"cost": {"gold": 70, "wood": 40}, "production": {"wood": 12}, "hp": 100},
    "казарма": {"cost": {"gold": 150, "wood": 50}, "production": {}, "hp": 150},
    "стена":   {"cost": {"gold": 50, "stone": 40}, "production": {}, "hp": 250},
}

# Данные о юнитах
UNITS = {
    "рабочий":   {"hp": 50, "attack": 5, "cost": {"gold": 50, "food": 10}, "speed": 3},
    "мечник":    {"hp": 120, "attack": 30, "cost": {"gold": 100, "food": 20}, "speed": 3},
    "лучник":    {"hp": 80, "attack": 25, "cost": {"gold": 120, "wood": 30}, "speed": 4},
    "кавалерия": {"hp": 100, "attack": 28, "cost": {"gold": 140, "food": 30}, "speed": 5},
}

# Стартовые ресурсы
START_RES = {"gold": 500, "wood": 300, "stone": 200, "food": 400}

# Модификаторы сложности
DIFFICULTY_MOD = {
    "easy":   {"enemy_damage": 0.8, "enemy_hire_cooldown": 3, "player_bonus_gold": 200},
    "medium": {"enemy_damage": 1.0, "enemy_hire_cooldown": 2, "player_bonus_gold": 0},
    "hard":   {"enemy_damage": 1.3, "enemy_hire_cooldown": 1, "player_bonus_gold": -100},
}

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
resources = START_RES.copy()      # текущие ресурсы игрока
buildings = []                    # список зданий
units = []                        # список юнитов
particles = []                    # список частиц для эффектов
difficulty = "medium"             # текущая сложность
enemy_hire_timer = 0              # таймер найма врага
sound_volume = 0.5                # громкость (заготовка)
show_settings = False             # показывать ли меню настроек

turn = "player"                   # чей ход: "player" или "enemy"
selected_units = []               # СПИСОК выделенных юнитов (мультивыделение)
selected_building = None          # выделенное здание (одиночное)
pending_build = None              # тип здания, ожидающего постройки
message = "Ваш ход. Выберите рабочего для стройки."
attack_range_hexes = []           # список гексов, доступных для атаки
move_range_hexes = []             # список гексов, доступных для перемещения

# Шрифты (размер адаптируется под высоту экрана)
fonts = {
    "normal": pygame.font.SysFont("Arial", int(HEIGHT/30)),
    "small": pygame.font.SysFont("Arial", int(HEIGHT/35)),
    "large": pygame.font.SysFont("Arial", int(HEIGHT/25)),
}

# ========== ГЕКСАГОНАЛЬНАЯ ГЕОМЕТРИЯ ==========

def hex_to_pixel(q, r):
    """Преобразует гексагональные координаты (q, r) в экранные пиксели"""
    x = HEX_RADIUS * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
    y = HEX_RADIUS * (3/2 * r)
    # Смещение для центрирования карты
    offset_x = WIDTH // 2 - (MAP_WIDTH * HEX_WIDTH * 0.75) // 2
    offset_y = HEIGHT // 2 - (MAP_HEIGHT * HEX_HEIGHT) // 2
    return int(x + offset_x), int(y + offset_y)

def pixel_to_hex(x, y):
    """Преобразует экранные координаты в гексагональные (q, r)"""
    offset_x = WIDTH // 2 - (MAP_WIDTH * HEX_WIDTH * 0.75) // 2
    offset_y = HEIGHT // 2 - (MAP_HEIGHT * HEX_HEIGHT) // 2
    x -= offset_x
    y -= offset_y
    q = (math.sqrt(3)/3 * x - 1/3 * y) / HEX_RADIUS
    r = (2/3 * y) / HEX_RADIUS
    return round(q), round(r)

def get_hex_polygon(q, r):
    """Возвращает список точек (x, y) для отрисовки шестиугольника"""
    cx, cy = hex_to_pixel(q, r)
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        x = cx + HEX_RADIUS * math.cos(angle)
        y = cy + HEX_RADIUS * math.sin(angle)
        points.append((x, y))
    return points

def hex_distance(q1, r1, q2, r2):
    """Расстояние между двумя гексами в гексагональных координатах"""
    # Преобразуем в кубические координаты для простоты
    x1, z1 = q1, r1
    y1 = -x1 - z1
    x2, z2 = q2, r2
    y2 = -x2 - z2
    return (abs(x1 - x2) + abs(y1 - y2) + abs(z1 - z2)) // 2

def get_neighbors(q, r):
    """Возвращает список координат соседних гексов (6 направлений)"""
    directions = [(1,0), (0,1), (-1,1), (-1,0), (0,-1), (1,-1)]
    return [(q+dq, r+dr) for dq, dr in directions]

# ========== ОТРИСОВКА ИКОНОК (СВОИМИ СИЛАМИ) ==========

def draw_infantry_icon(surf, x, y, color, size=20):
    """Рисует иконку пехотинца (перекрещенные мечи)"""
    cx, cy = x + size//2, y + size//2
    pygame.draw.line(surf, color, (cx-8, cy-6), (cx+8, cy+6), 3)
    pygame.draw.line(surf, color, (cx-8, cy+6), (cx+8, cy-6), 3)
    pygame.draw.circle(surf, color, (cx, cy), 5, 1)

def draw_archer_icon(surf, x, y, color, size=20):
    """Рисует иконку лучника (лук со стрелой)"""
    cx, cy = x + size//2, y + size//2
    pygame.draw.arc(surf, color, (cx-10, cy-8, 20, 16), 0, math.pi, 3)
    pygame.draw.line(surf, color, (cx+6, cy-4), (cx+14, cy-10), 3)
    pygame.draw.circle(surf, color, (cx+14, cy-10), 3, 1)

def draw_worker_icon(surf, x, y, color, size=20):
    """Рисует иконку рабочего (молоток)"""
    cx, cy = x + size//2, y + size//2
    pygame.draw.rect(surf, color, (cx-5, cy-10, 10, 14), 2)
    pygame.draw.rect(surf, color, (cx-8, cy+4, 16, 6), 2)

def draw_cavalry_icon(surf, x, y, color, size=20):
    """Рисует иконку кавалерии (лошадь)"""
    cx, cy = x + size//2, y + size//2
    pygame.draw.ellipse(surf, color, (cx-10, cy-8, 20, 14), 2)
    pygame.draw.line(surf, color, (cx-2, cy-8), (cx-2, cy-18), 3)
    pygame.draw.line(surf, color, (cx+2, cy-8), (cx+2, cy-18), 3)

def draw_building_icon(surf, x, y, btype, color, size=20):
    """Рисует иконку здания в зависимости от типа"""
    cx, cy = x + size//2, y + size//2
    if btype == "ферма":
        pygame.draw.rect(surf, color, (cx-12, cy-10, 24, 20), 2)
        pygame.draw.line(surf, color, (cx, cy-10), (cx, cy+10), 2)
        pygame.draw.line(surf, color, (cx-12, cy), (cx+12, cy), 2)
    elif btype == "шахта":
        pygame.draw.polygon(surf, color, [(cx, cy-15), (cx-15, cy+5), (cx+15, cy+5)], 2)
        pygame.draw.rect(surf, color, (cx-5, cy+5, 10, 10), 2)
    elif btype == "лесопилка":
        pygame.draw.circle(surf, color, (cx-8, cy-8), 8, 2)
        pygame.draw.rect(surf, color, (cx-3, cy-2, 6, 14), 2)
    elif btype == "казарма":
        pygame.draw.rect(surf, color, (cx-15, cy-12, 30, 24), 2)
        pygame.draw.line(surf, color, (cx, cy-12), (cx, cy+12), 2)
    elif btype == "стена":
        pygame.draw.rect(surf, color, (cx-15, cy-5, 30, 10), 2)
        for i in range(-10, 11, 10):
            pygame.draw.rect(surf, color, (cx+i, cy-10, 4, 8), 2)

def draw_resource_icon(surf, x, y, res_type, color):
    """Рисует иконку ресурса (золото, дерево, камень, еда)"""
    cx, cy = x + 15, y + 15
    if res_type == "gold":
        pygame.draw.circle(surf, color, (cx, cy), 10, 2)
        pygame.draw.circle(surf, color, (cx, cy), 4, 0)
        pygame.draw.line(surf, color, (cx-8, cy), (cx+8, cy), 2)
    elif res_type == "wood":
        pygame.draw.rect(surf, color, (cx-5, cy-10, 10, 20), 2)
        pygame.draw.line(surf, color, (cx-8, cy-5), (cx+8, cy-5), 2)
    elif res_type == "stone":
        pygame.draw.polygon(surf, color, [(cx, cy-10), (cx-10, cy+5), (cx+10, cy+5)], 2)
        pygame.draw.line(surf, color, (cx-5, cy-2), (cx+5, cy-2), 2)
    elif res_type == "food":
        pygame.draw.circle(surf, color, (cx, cy), 10, 2)
        pygame.draw.line(surf, color, (cx-3, cy-3), (cx+3, cy+3), 2)
        pygame.draw.line(surf, color, (cx-3, cy+3), (cx+3, cy-3), 2)

# ========== ИНИЦИАЛИЗАЦИЯ ИГРЫ ==========
def init_game():
    global resources, buildings, units, enemy_hire_timer, message
    resources = START_RES.copy()
    if difficulty == "easy":
        resources["gold"] += 200
    elif difficulty == "hard":
        resources["gold"] -= 100
    buildings.clear()
    units.clear()
    # Игрок
    units.append({"type": "рабочий", "q": 2, "r": 2, "owner": "player", "hp": 50, "max_hp": 50, "attack": 5, "speed": 3})
    units.append({"type": "мечник", "q": 3, "r": 2, "owner": "player", "hp": 120, "max_hp": 120, "attack": 30, "speed": 3})
    buildings.append({"type": "ферма", "q": 1, "r": 4, "owner": "player", "hp": 100, "max_hp": 100})
    buildings.append({"type": "шахта", "q": 5, "r": 1, "owner": "player", "hp": 100, "max_hp": 100})
    # Враг
    units.append({"type": "мечник", "q": 9, "r": 7, "owner": "enemy", "hp": 120, "max_hp": 120, "attack": 30, "speed": 3})
    units.append({"type": "лучник", "q": 8, "r": 8, "owner": "enemy", "hp": 80, "max_hp": 80, "attack": 25, "speed": 4})
    buildings.append({"type": "казарма", "q": 10, "r": 4, "owner": "enemy", "hp": 150, "max_hp": 150})
    buildings.append({"type": "шахта", "q": 9, "r": 2, "owner": "enemy", "hp": 100, "max_hp": 100})
    enemy_hire_timer = 0
    message = "Новая игра. Ваш ход."

# ========== СОХРАНЕНИЕ / ЗАГРУЗКА ==========
def save_game():
    global message
    data = {
        "resources": resources,
        "buildings": buildings,
        "units": units,
        "turn": turn,
        "difficulty": difficulty,
    }
    with open("savegame.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    message = "Игра сохранена"

def load_game():
    global resources, buildings, units, turn, difficulty, message
    if not os.path.exists("savegame.json"):
        message = "Нет сохранений"
        return
    with open("savegame.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    resources = data["resources"]
    buildings = data["buildings"]
    units = data["units"]
    turn = data["turn"]
    difficulty = data["difficulty"]
    message = "Игра загружена"
    # Сбросим выделение после загрузки
    global selected_units, selected_building
    selected_units = []
    selected_building = None

# ========== ЭКОНОМИКА ==========
def can_afford(cost):
    """Проверяет, хватает ли ресурсов на покупку"""
    for r, a in cost.items():
        if resources.get(r, 0) < a:
            return False
    return True

def deduct_cost(cost):
    """Списывает стоимость с ресурсов"""
    for r, a in cost.items():
        resources[r] -= a

def collect_resources():
    """Собирает ресурсы со всех зданий игрока в начале хода"""
    if turn == "player":
        for b in buildings:
            if b["owner"] == "player":
                prod = BUILDINGS[b["type"]].get("production", {})
                for r, v in prod.items():
                    resources[r] = resources.get(r, 0) + v

# ========== ЧАСТИЦЫ ДЛЯ ЭФФЕКТОВ ==========
def add_particle(x, y, color):
    particles.append({"x": x, "y": y, "life": 10, "color": color})

def update_particles():
    for p in particles[:]:
        p["life"] -= 1
        if p["life"] <= 0:
            particles.remove(p)

# ========== БОЕВЫЕ ДЕЙСТВИЯ ==========
def calculate_damage(base_damage, is_critical=False):
    """Вычисляет урон с учётом критического удара (х2)"""
    return int(base_damage * (2 if is_critical else 1))

def try_attack(attacker, target):
    """Атака одного юнита другим (или зданием) с шансом крита"""
    global message
    is_critical = random.random() < 0.2   # 20% шанс крита
    damage = calculate_damage(attacker["attack"], is_critical)
    target["hp"] -= damage
    crit_text = " КРИТИЧЕСКИЙ УДАР!" if is_critical else ""
    message = f"Атака! {damage} урона.{crit_text}"
    # Эффект частиц
    cx, cy = hex_to_pixel(target["q"], target["r"])
    add_particle(cx, cy, CRIT_COLOR if is_critical else (255,100,100))
    if target["hp"] <= 0:
        if target in units:
            units.remove(target)
        else:
            buildings.remove(target)
        message += " Цель уничтожена."
    return True

# ========== СТРОИТЕЛЬСТВО И НАЁМ ==========
def try_build(btype, q, r):
    """Попытка построить здание рабочим на свободной соседней клетке"""
    global message, pending_build
    if turn != "player":
        return False
    # Проверяем, есть ли рабочий рядом с целевой клеткой
    worker_near = any(u["owner"]=="player" and u["type"]=="рабочий" and hex_distance(u["q"], u["r"], q, r) == 1 for u in units)
    if not worker_near:
        message = "Рядом должен быть рабочий!"
        return False
    # Проверяем, свободна ли клетка
    if any(b["q"]==q and b["r"]==r for b in buildings) or any(u["q"]==q and u["r"]==r for u in units):
        message = "Клетка занята"
        return False
    cost = BUILDINGS[btype]["cost"]
    if not can_afford(cost):
        message = "Не хватает ресурсов!"
        return False
    deduct_cost(cost)
    buildings.append({"type": btype, "q": q, "r": r, "owner": "player",
                      "hp": BUILDINGS[btype]["hp"], "max_hp": BUILDINGS[btype]["hp"]})
    message = f"Построена {btype}!"
    pending_build = None
    return True

def try_hire(utype, q, r):
    """Наём юнита из казармы на соседнюю свободную клетку"""
    global message
    if turn != "player":
        return False
    # Ищем казарму по координатам
    barracks = next((b for b in buildings if b["q"]==q and b["r"]==r and b["type"]=="казарма" and b["owner"]=="player"), None)
    if barracks is None:
        message = "Нужна своя казарма!"
        return False
    cost = UNITS[utype]["cost"]
    if not can_afford(cost):
        message = "Не хватает ресурсов!"
        return False
    for nq, nr in get_neighbors(barracks["q"], barracks["r"]):
        if 0 <= nq < MAP_WIDTH and 0 <= nr < MAP_HEIGHT:
            if not any(b["q"]==nq and b["r"]==nr for b in buildings) and not any(u["q"]==nq and u["r"]==nr for u in units):
                deduct_cost(cost)
                units.append({"type": utype, "q": nq, "r": nr, "owner": "player",
                              "hp": UNITS[utype]["hp"], "max_hp": UNITS[utype]["hp"],
                              "attack": UNITS[utype]["attack"], "speed": UNITS[utype]["speed"]})
                message = f"Нанят {utype}!"
                return True
    message = "Нет места рядом с казармой"
    return False

# ========== ХОД ВРАГА (ИИ) ==========
def enemy_turn():
    global message, enemy_hire_timer
    mod = DIFFICULTY_MOD[difficulty]
    has_barracks = any(b["type"]=="казарма" and b["owner"]=="enemy" for b in buildings)
    # Враг нанимает юнитов, если есть казарма и прошло достаточно ходов
    if has_barracks and enemy_hire_timer <= 0:
        enemy_hire_timer = mod["enemy_hire_cooldown"]
        barracks = next((b for b in buildings if b["type"]=="казарма" and b["owner"]=="enemy"), None)
        if barracks is not None and len([u for u in units if u["owner"]=="enemy"]) < 6:
            utype = random.choice(["мечник", "лучник", "кавалерия"])
            for nq, nr in get_neighbors(barracks["q"], barracks["r"]):
                if 0 <= nq < MAP_WIDTH and 0 <= nr < MAP_HEIGHT:
                    if not any(b["q"]==nq and b["r"]==nr for b in buildings) and not any(u["q"]==nq and u["r"]==nr for u in units):
                        units.append({"type": utype, "q": nq, "r": nr, "owner": "enemy",
                                      "hp": UNITS[utype]["hp"], "max_hp": UNITS[utype]["hp"],
                                      "attack": int(UNITS[utype]["attack"] * mod["enemy_damage"]),
                                      "speed": UNITS[utype]["speed"]})
                        message = f"Враг нанял {utype}!"
                        break
    else:
        if enemy_hire_timer > 0:
            enemy_hire_timer -= 1

    # Движение и атака врагов
    for u in units:
        if u["owner"] != "enemy":
            continue
        # Поиск ближайшей цели игрока
        closest = None
        min_dist = 999
        for target in units + buildings:
            if target["owner"] == "player":
                d = hex_distance(u["q"], u["r"], target["q"], target["r"])
                if d < min_dist:
                    min_dist = d
                    closest = target
        if closest is None:
            continue
        if min_dist == 1:
            try_attack(u, closest)
        else:
            # Движение к цели: выбираем соседний гекс, который уменьшает расстояние
            best_n = None
            best_dist = min_dist
            for nq, nr in get_neighbors(u["q"], u["r"]):
                if 0 <= nq < MAP_WIDTH and 0 <= nr < MAP_HEIGHT:
                    if not any(b["q"]==nq and b["r"]==nr for b in buildings) and not any(u2["q"]==nq and u2["r"]==nr for u2 in units):
                        d = hex_distance(nq, nr, closest["q"], closest["r"])
                        if d < best_dist:
                            best_dist = d
                            best_n = (nq, nr)
            if best_n:
                u["q"], u["r"] = best_n

# ========== ЗАВЕРШЕНИЕ ХОДА ==========
def end_turn():
    global turn, selected_units, selected_building, pending_build, message, attack_range_hexes, move_range_hexes
    # Сброс выделения после хода
    selected_units.clear()
    selected_building = None
    pending_build = None
    attack_range_hexes.clear()
    move_range_hexes.clear()
    if turn == "player":
        turn = "enemy"
        message = "Ход врага..."
        enemy_turn()
        turn = "player"
        collect_resources()
        message = "Ваш ход."
    else:
        turn = "player"
        collect_resources()
        message = "Ваш ход."

# ========== ПОДСВЕТКА РАДИУСА ДВИЖЕНИЯ И АТАКИ ==========
def update_range_highlight(units_list):
    """
    Обновляет глобальные списки attack_range_hexes и move_range_hexes
    на основе переданного списка выделенных юнитов. Если юнитов несколько,
    объединяются зоны движения и атаки всех.
    """
    global attack_range_hexes, move_range_hexes
    attack_range_hexes.clear()
    move_range_hexes.clear()
    if not units_list:
        return
    # Для каждого выделенного юнита
    for unit in units_list:
        for q in range(MAP_WIDTH):
            for r in range(MAP_HEIGHT):
                d = hex_distance(unit["q"], unit["r"], q, r)
                # Зона движения (0 < d <= speed, клетка свободна)
                if 0 < d <= unit["speed"]:
                    if not any(b["q"]==q and b["r"]==r for b in buildings) and not any(u2["q"]==q and u2["r"]==r for u2 in units):
                        if (q, r) not in move_range_hexes:
                            move_range_hexes.append((q, r))
                # Зона атаки (d == 1 и есть враг)
                if d == 1:
                    target = next((t for t in units+buildings if t["q"]==q and t["r"]==r and t["owner"]!=unit["owner"]), None)
                    if target is not None and (q, r) not in attack_range_hexes:
                        attack_range_hexes.append((q, r))

# ========== ОТРИСОВКА ==========
def draw_hex_grid():
    """Отрисовка гексагональной сетки с подсветкой при наведении и зон"""
    mouse_pos = pygame.mouse.get_pos()
    for q in range(MAP_WIDTH):
        for r in range(MAP_HEIGHT):
            points = get_hex_polygon(q, r)
            color = COLOR_HEX_DARK
            # Определяем цвет и наложение полупрозрачных слоёв
            if pygame.draw.polygon(screen, (0,0,0), points, 0).collidepoint(mouse_pos):
                color = COLOR_HEX_HOVER
            elif (q, r) in move_range_hexes:
                s = pygame.Surface((HEX_RADIUS*2, HEX_RADIUS*2), pygame.SRCALPHA)
                s.fill(MOVE_RANGE_COLOR)
                screen.blit(s, (hex_to_pixel(q, r)[0]-HEX_RADIUS, hex_to_pixel(q, r)[1]-HEX_RADIUS))
            elif (q, r) in attack_range_hexes:
                s = pygame.Surface((HEX_RADIUS*2, HEX_RADIUS*2), pygame.SRCALPHA)
                s.fill(ATTACK_RANGE_COLOR)
                screen.blit(s, (hex_to_pixel(q, r)[0]-HEX_RADIUS, hex_to_pixel(q, r)[1]-HEX_RADIUS))
            else:
                color = COLOR_HEX_LIGHT if (q + r) % 2 == 0 else COLOR_HEX_DARK
            pygame.draw.polygon(screen, color, points, 0)
            pygame.draw.polygon(screen, (150,150,170), points, 2)

def draw_buildings():
    """Отрисовка всех зданий с иконками, полосками здоровья и рамкой выбора"""
    for b in buildings:
        cx, cy = hex_to_pixel(b["q"], b["r"])
        if b["type"] == "стена":
            color = WALL_COLOR
        else:
            color = PLAYER_BUILD if b["owner"] == "player" else ENEMY_BUILD
        pygame.draw.rect(screen, color, (cx-20, cy-20, 40, 40), border_radius=8)
        draw_building_icon(screen, cx-15, cy-15, b["type"], TEXT_COLOR, 30)
        # Полоска здоровья
        hp_percent = b["hp"] / b["max_hp"]
        pygame.draw.rect(screen, (60,60,60), (cx-20, cy+15, 40, 6))
        pygame.draw.rect(screen, HEALTH_GREEN, (cx-20, cy+15, 40*hp_percent, 6))
        # Рамка выделения для одиночных зданий
        if selected_building == b:
            pygame.draw.rect(screen, SELECTION_COLOR, (cx-20, cy-20, 40, 40), 3, border_radius=8)

def draw_units():
    """Отрисовка всех юнитов с иконками, полосками здоровья и рамками выделения (для нескольких)"""
    for u in units:
        cx, cy = hex_to_pixel(u["q"], u["r"])
        color = PLAYER_UNIT if u["owner"] == "player" else ENEMY_UNIT
        pygame.draw.ellipse(screen, color, (cx-25, cy-20, 50, 40))
        # Иконка в зависимости от типа
        if u["type"] == "рабочий":
            draw_worker_icon(screen, cx-15, cy-15, TEXT_COLOR, 30)
        elif u["type"] == "мечник":
            draw_infantry_icon(screen, cx-15, cy-15, TEXT_COLOR, 30)
        elif u["type"] == "лучник":
            draw_archer_icon(screen, cx-15, cy-15, TEXT_COLOR, 30)
        elif u["type"] == "кавалерия":
            draw_cavalry_icon(screen, cx-15, cy-15, TEXT_COLOR, 30)
        # Полоска здоровья
        hp_percent = u["hp"] / u["max_hp"]
        pygame.draw.rect(screen, (60,60,60), (cx-25, cy+15, 50, 6))
        pygame.draw.rect(screen, HEALTH_GREEN, (cx-25, cy+15, 50*hp_percent, 6))
        # Рамка выделения, если юнит в списке selected_units
        if u in selected_units:
            pygame.draw.ellipse(screen, SELECTION_COLOR, (cx-27, cy-22, 54, 44), 3)

def draw_particles():
    for p in particles:
        pygame.draw.circle(screen, p["color"], (int(p["x"]), int(p["y"])), max(1, 5 - p["life"]//2))

def draw_resources_panel():
    """Отображает панель ресурсов вверху экрана с иконками и числами"""
    panel_rect = pygame.Rect(10, 10, WIDTH-20, 70)
    pygame.draw.rect(screen, UI_PANEL, panel_rect, border_radius=12)
    pygame.draw.rect(screen, (100,100,130), panel_rect, 2, border_radius=12)
    x_start = 30
    res_items = [
        ("gold", resources["gold"]),
        ("wood", resources["wood"]),
        ("stone", resources["stone"]),
        ("food", resources["food"])
    ]
    for i, (rtype, val) in enumerate(res_items):
        bg_rect = pygame.Rect(x_start + i*170, 20, 150, 50)
        pygame.draw.rect(screen, RES_BG_COLOR, bg_rect, border_radius=8)
        pygame.draw.rect(screen, (150,150,180), bg_rect, 1, border_radius=8)
        draw_resource_icon(screen, bg_rect.x+10, bg_rect.y+10, rtype, TEXT_COLOR)
        surf = fonts["large"].render(str(val), True, TEXT_COLOR)
        screen.blit(surf, (bg_rect.x+70, bg_rect.y+12))

def draw_ui():
    """Отрисовка интерфейса: панель сообщений, кнопки, меню строительства/найма"""
    global selected_units, selected_building, pending_build, message
    panel_h = 130
    panel_rect = pygame.Rect(0, HEIGHT-panel_h, WIDTH, panel_h)
    s = pygame.Surface((WIDTH, panel_h), pygame.SRCALPHA)
    s.fill(UI_PANEL)
    screen.blit(s, (0, HEIGHT-panel_h))
    pygame.draw.rect(screen, (100,100,130), panel_rect, 2)

    # Сообщение
    msg_surf = fonts["small"].render(message, True, TEXT_COLOR)
    screen.blit(msg_surf, (20, HEIGHT-panel_h+20))

    # Кнопка выхода
    exit_btn_w, exit_btn_h = 100, 40
    exit_btn = pygame.Rect(WIDTH - exit_btn_w - 20, 20, exit_btn_w, exit_btn_h)
    mouse_over = exit_btn.collidepoint(pygame.mouse.get_pos())
    btn_color = EXIT_BUTTON_COLOR if mouse_over else (150, 50, 50)
    pygame.draw.rect(screen, btn_color, exit_btn, border_radius=10)
    pygame.draw.rect(screen, (200,200,200), exit_btn, 2, border_radius=10)
    exit_text = fonts["normal"].render("Выйти", True, TEXT_COLOR)
    screen.blit(exit_text, (exit_btn.x+15, exit_btn.y+10))

    # Основные кнопки
    btn_w, btn_h = 120, 55
    btn_end = pygame.Rect(WIDTH - btn_w - 20, HEIGHT - panel_h + 20, btn_w, btn_h)
    mouse_over = btn_end.collidepoint(pygame.mouse.get_pos())
    pygame.draw.rect(screen, BUTTON_HOVER if mouse_over else BUTTON_COLOR, btn_end, border_radius=10)
    pygame.draw.rect(screen, (200,200,200), btn_end, 2, border_radius=10)
    btn_text = fonts["normal"].render("Завершить ход", True, TEXT_COLOR)
    screen.blit(btn_text, (btn_end.x+10, btn_end.y+15))

    # Кнопки Сохранить, Загрузить, Настройки
    btn_save = pygame.Rect(btn_end.x - btn_w - 20, btn_end.y, btn_w, btn_h)
    btn_load = pygame.Rect(btn_save.x - btn_w - 20, btn_end.y, btn_w, btn_h)
    btn_sett = pygame.Rect(btn_load.x - btn_w - 20, btn_end.y, btn_w, btn_h)
    for rect, txt in [(btn_save, "Сохранить"), (btn_load, "Загрузить"), (btn_sett, "Настройки")]:
        mouse_over = rect.collidepoint(pygame.mouse.get_pos())
        color = BUTTON_HOVER if mouse_over else BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.rect(screen, (200,200,200), rect, 2, border_radius=10)
        txt_surf = fonts["normal"].render(txt, True, TEXT_COLOR)
        screen.blit(txt_surf, (rect.x+10, rect.y+15))

    # Кнопки строительства, если выделен рабочий (или несколько, но сработает только если первый в списке)
    if len(selected_units) == 1 and selected_units[0]["type"] == "рабочий" and selected_units[0]["owner"] == "player":
        y_off = HEIGHT - panel_h - 55 * len(BUILDINGS) - 20
        for btype, data in BUILDINGS.items():
            rect = pygame.Rect(WIDTH-130, y_off, 110, 45)
            mouse_over = rect.collidepoint(pygame.mouse.get_pos())
            color = (60, 120, 60) if mouse_over else (60, 90, 60)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, (200,200,200), rect, 1, border_radius=8)
            cost_txt = f"{data['cost'].get('gold',0)}💰"
            c_surf = fonts["small"].render(cost_txt, True, TEXT_COLOR)
            screen.blit(c_surf, (rect.x+5, rect.y+5))
            draw_building_icon(screen, rect.x+80, rect.y+10, btype, TEXT_COLOR, 30)
            y_off += 55

    # Кнопки найма, если выделена казарма
    if selected_building and selected_building["type"] == "казарма" and selected_building["owner"] == "player":
        y_off = HEIGHT - panel_h - 55 * len(UNITS) - 20
        for utype, data in UNITS.items():
            rect = pygame.Rect(WIDTH-130, y_off, 110, 45)
            mouse_over = rect.collidepoint(pygame.mouse.get_pos())
            color = (100, 100, 160) if mouse_over else (70, 70, 120)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, (200,200,200), rect, 1, border_radius=8)
            cost_txt = f"{data['cost'].get('gold',0)}💰"
            c_surf = fonts["small"].render(cost_txt, True, TEXT_COLOR)
            screen.blit(c_surf, (rect.x+5, rect.y+5))
            if utype == "рабочий":
                draw_worker_icon(screen, rect.x+80, rect.y+10, TEXT_COLOR, 30)
            elif utype == "мечник":
                draw_infantry_icon(screen, rect.x+80, rect.y+10, TEXT_COLOR, 30)
            elif utype == "лучник":
                draw_archer_icon(screen, rect.x+80, rect.y+10, TEXT_COLOR, 30)
            elif utype == "кавалерия":
                draw_cavalry_icon(screen, rect.x+80, rect.y+10, TEXT_COLOR, 30)
            y_off += 55

    # Возвращаем словарь с ректами кнопок для обработки кликов
    return {
        "end": btn_end,
        "save": btn_save,
        "load": btn_load,
        "settings": btn_sett,
        "exit": exit_btn
    }

def draw_settings_menu():
    """Меню настроек (сложность, громкость)"""
    global difficulty, sound_volume
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,200))
    screen.blit(overlay, (0,0))
    panel_w, panel_h = 400, 300
    panel = pygame.Rect(WIDTH//2 - panel_w//2, HEIGHT//2 - panel_h//2, panel_w, panel_h)
    pygame.draw.rect(screen, (50,60,80), panel, border_radius=10)
    pygame.draw.rect(screen, (200,200,200), panel, 2, border_radius=10)

    # Кнопки выбора сложности
    levels = ["easy", "medium", "hard"]
    for i, lev in enumerate(levels):
        rect = pygame.Rect(panel.x+30, panel.y+50 + i*50, 150, 40)
        color = BUTTON_HOVER if difficulty == lev else BUTTON_COLOR
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, (200,200,200), rect, 1, border_radius=8)
        txt = fonts["small"].render(lev.capitalize(), True, TEXT_COLOR)
        screen.blit(txt, (rect.x+10, rect.y+10))

    # Ползунок громкости
    vol_rect = pygame.Rect(panel.x+30, panel.y+220, 200, 20)
    pygame.draw.rect(screen, (100,100,100), vol_rect)
    vol_pos = vol_rect.x + int(sound_volume * vol_rect.width)
    pygame.draw.rect(screen, HEALTH_GREEN, (vol_rect.x, vol_rect.y, vol_pos - vol_rect.x, vol_rect.height))
    pygame.draw.circle(screen, TEXT_COLOR, (vol_pos, vol_rect.y+10), 10)

    # Кнопка закрытия
    close_btn = pygame.Rect(panel.x+panel.width-80, panel.y+10, 70, 30)
    pygame.draw.rect(screen, BUTTON_COLOR, close_btn, border_radius=5)
    close_txt = fonts["small"].render("Закрыть", True, TEXT_COLOR)
    screen.blit(close_txt, (close_btn.x+10, close_btn.y+5))

    return {"close": close_btn, "vol_slider": vol_rect, "panel": panel, "levels": levels}

# ========== ОБРАБОТКА КЛИКОВ МЫШИ (С ПОДДЕРЖКОЙ SHIFT ДЛЯ МУЛЬТИВЫДЕЛЕНИЯ) ==========
def handle_click(pos, shift_held):
    """
    Обрабатывает клик по игровому полю.
    shift_held: зажата ли клавиша Shift (добавление/удаление из выделения)
    """
    global selected_units, selected_building, pending_build, turn, message, attack_range_hexes, move_range_hexes
    if turn != "player" or show_settings:
        return
    q, r = pixel_to_hex(*pos)
    if not (0 <= q < MAP_WIDTH and 0 <= r < MAP_HEIGHT):
        return

    # Если ожидается постройка, строим
    if pending_build is not None:
        try_build(pending_build, q, r)
        return

    # Ищем, на что кликнули: юнит игрока или здание игрока
    clicked_unit = next((u for u in units if u["q"]==q and u["r"]==r and u["owner"]=="player"), None)
    clicked_building = next((b for b in buildings if b["q"]==q and b["r"]==r and b["owner"]=="player"), None)

    # Если клик по своему юниту
    if clicked_unit is not None:
        if shift_held:
            # Добавляем/убираем юнит из выделения
            if clicked_unit in selected_units:
                selected_units.remove(clicked_unit)
                message = "Юнит убран из выделения"
            else:
                selected_units.append(clicked_unit)
                message = f"Юнит {clicked_unit['type']} добавлен в выделение"
            # Если после изменения выделение не пусто, обновляем подсветку
            if selected_units:
                update_range_highlight(selected_units)
            else:
                attack_range_hexes.clear()
                move_range_hexes.clear()
        else:
            # Без Shift: выделяем только этого юнита, сбрасываем выделение здания
            selected_units = [clicked_unit]
            selected_building = None
            update_range_highlight(selected_units)
            message = f"Выбран {clicked_unit['type']} ️ {clicked_unit['hp']})"
        return

    # Если клик по своему зданию
    if clicked_building is not None:
        if not shift_held:
            # Выделяем здание, сбрасываем выделение юнитов
            selected_units.clear()
            selected_building = clicked_building
            attack_range_hexes.clear()
            move_range_hexes.clear()
            message = f"Выбрано здание {clicked_building['type']}"
        else:
            # При Shift выделение здания не поддерживается (можно просто игнорировать)
            pass
        return

    # Если клик по пустой клетке (или по врагу) и есть выделенные юниты
    if selected_units:
        # Попытка атаковать, если под курсором враг и кто-то из выделенных может атаковать
        enemy = next((t for t in units+buildings if t["q"]==q and t["r"]==r and t["owner"]=="enemy"), None)
        if enemy is not None:
            # Атакуют все выделенные юниты, которые могут достать до врага (расстояние 1)
            any_attacked = False
            for unit in selected_units[:]:  # копия списка, т.к. юниты могут умереть
                if hex_distance(unit["q"], unit["r"], q, r) == 1:
                    try_attack(unit, enemy)
                    any_attacked = True
                    # Если враг уничтожен, выходим из цикла (дальше атаковать некого)
                    if enemy["hp"] <= 0:
                        break
            if any_attacked:
                # После атаки снимаем выделение (по желанию можно оставить)
                selected_units.clear()
                update_range_highlight(None)
                return
        # Перемещение: для каждого выделенного юнита, который может встать на целевую клетку
        # Но с мультиперемещением сложнее: обычно перемещают одного. Реализуем перемещение только для первого
        # юнита, который может туда встать. Для простоты возьмём первого в списке.
        if (q, r) in move_range_hexes and len(selected_units) > 0:
            unit = selected_units[0]
            unit["q"] = q
            unit["r"] = r
            message = "Юнит перемещён"
            selected_units.clear()
            update_range_highlight(None)
            return
        message = "Недоступное действие"
        selected_units.clear()
        update_range_highlight(None)
        return

    # Если ничего не выделено и клик по пустоте – сброс выделения здания
    if selected_building is not None:
        selected_building = None
        message = "Выделение снято"

# ========== ГЛАВНЫЙ ЦИКЛ ==========
def main():
    global running, show_settings, pending_build, selected_units, selected_building, difficulty, sound_volume, message
    init_game()
    running = True
    while running:
        screen.fill(COLOR_BG)
        draw_hex_grid()
        draw_buildings()
        draw_units()
        draw_particles()
        draw_resources_panel()
        ui_buttons = draw_ui()
        if show_settings:
            sett_buttons = draw_settings_menu()
        else:
            sett_buttons = None
        pygame.display.flip()
        clock.tick(FPS)
        update_particles()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Проверяем, зажат ли Shift
                shift_held = pygame.key.get_mods() & pygame.KMOD_SHIFT
                # Кнопка выхода
                if ui_buttons["exit"].collidepoint(event.pos):
                    running = False
                elif show_settings:
                    if sett_buttons is not None:
                        if sett_buttons["close"].collidepoint(event.pos):
                            show_settings = False
                        elif sett_buttons["vol_slider"].collidepoint(event.pos):
                            vol_rect = sett_buttons["vol_slider"]
                            new_vol = (event.pos[0] - vol_rect.x) / vol_rect.width
                            sound_volume = max(0.0, min(1.0, new_vol))
                        panel = sett_buttons["panel"]
                        for i, lev in enumerate(sett_buttons["levels"]):
                            rect = pygame.Rect(panel.x+30, panel.y+50 + i*50, 150, 40)
                            if rect.collidepoint(event.pos):
                                difficulty = lev
                                init_game()
                                show_settings = False
                else:
                    if ui_buttons["end"].collidepoint(event.pos):
                        end_turn()
                    elif ui_buttons["save"].collidepoint(event.pos):
                        save_game()
                    elif ui_buttons["load"].collidepoint(event.pos):
                        load_game()
                    elif ui_buttons["settings"].collidepoint(event.pos):
                        show_settings = True
                    else:
                        # Обработка кликов по кнопкам строительства (если выделен рабочий)
                        handled = False
                        if len(selected_units) == 1 and selected_units[0]["type"] == "рабочий" and selected_units[0]["owner"] == "player":
                            y_off = HEIGHT-130 - 55 * len(BUILDINGS) - 20
                            for btype in BUILDINGS.keys():
                                rect = pygame.Rect(WIDTH-130, y_off, 110, 45)
                                if rect.collidepoint(event.pos):
                                    pending_build = btype
                                    selected_units.clear()
                                    message = f"Кликните по свободной клетке рядом с рабочим, чтобы построить {btype}"
                                    handled = True
                                    break
                                y_off += 55
                        # Обработка кликов по кнопкам найма (если выделена казарма)
                        if not handled and selected_building and selected_building["type"] == "казарма" and selected_building["owner"] == "player":
                            y_off = HEIGHT-130 - 55 * len(UNITS) - 20
                            for utype in UNITS.keys():
                                rect = pygame.Rect(WIDTH-130, y_off, 110, 45)
                                if rect.collidepoint(event.pos):
                                    try_hire(utype, selected_building["q"], selected_building["r"])
                                    selected_building = None
                                    handled = True
                                    break
                                y_off += 55
                        if not handled:
                            handle_click(event.pos, shift_held)

        # Проверка победы/поражения
        player_alive = any(u["owner"]=="player" for u in units) or any(b["owner"]=="player" for b in buildings)
        enemy_alive = any(u["owner"]=="enemy" for u in units) or any(b["owner"]=="enemy" for b in buildings)
        if not player_alive:
            while True:
                screen.fill(COLOR_BG)
                text = fonts["large"].render("ПОРАЖЕНИЕ! Все ваши силы уничтожены.", True, (255,100,100))
                screen.blit(text, (WIDTH//2-200, HEIGHT//2))
                pygame.display.flip()
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        running = False
                        break
                else:
                    continue
                break
        if not enemy_alive:
            while True:
                screen.fill(COLOR_BG)
                text = fonts["large"].render("ПОБЕДА! Вы захватили земли.", True, (100,255,100))
                screen.blit(text, (WIDTH//2-200, HEIGHT//2))
                pygame.display.flip()
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                        running = False
                        break
                else:
                    continue
                break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
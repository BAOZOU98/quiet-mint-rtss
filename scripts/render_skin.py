"""Render the Quiet Mint RTSS skin from scratch.

Every bitmap and the USF header are generated here; nothing is taken from the
skins shipped with RTSS. Output goes to build/Skins/QuietMintCN (skin sources)
and, with --compile, build/Skins/QuietMintCN.usf.

Control IDs, bitmap slots and the header syntax follow "USF skin format
reference" from the RTSS SDK. Coordinates are this skin's own layout.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import argparse, json, os, shutil, subprocess, time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--cn-font', type=Path, default=Path('C:/Windows/Fonts/NotoSansSC-VF.ttf'),
                    help='Noto Sans SC variable font (SIL OFL), used for Chinese and Latin labels')
parser.add_argument('--compile', action='store_true', help='compile QuietMintCN.usf with the RTSS built-in skin compiler')
parser.add_argument('--rtss', type=Path, default=Path('C:/Program Files (x86)/RivaTuner Statistics Server'))
parser.add_argument('--sync-src', action='store_true', help='copy the generated sources into src/skin')
args = parser.parse_args()

NAME = 'QuietMintCN'
DEST = ROOT / 'build/Skins' / NAME
if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)
MONO = str(ROOT / 'assets/fonts/JetBrainsMono-Medium.ttf')
S = 4  # supersampling factor

# Palette
BG = '#161A20'        # window
CARD = '#1E242C'      # grouped surfaces
TRACK = '#29303A'     # segmented tracks, toggle off
LINE = '#343C47'      # hairlines, field borders
FIELD = '#11151A'     # numeric fields
FG = '#E2E7EE'
MUTED = '#8E9AAA'
DIM = '#5F6B7A'
MINT = '#8DDABD'
MINT_DEEP = '#2D6A56'  # selection / heading fill behind white native text
INK = '#10241C'       # text on mint
W, H = 530, 720


def hexbgr(color):
    """USF placeholders take colors as BBGGRRh."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f'{b:02X}{g:02X}{r:02X}h'


def font(size, kind='cn', weight=500):
    f = ImageFont.truetype(args.cn_font if kind == 'cn' else MONO, round(size * S))
    if kind == 'cn':
        f.set_variation_by_axes([weight])
    return f


class Canvas:
    """A supersampled RGBA drawing surface addressed in output pixels."""

    def __init__(self, w, h, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.im = Image.new('RGBA', (w * S, h * S), fill)
        self.d = ImageDraw.Draw(self.im)

    def rect(self, x, y, w, h, fill, r=0, outline=None):
        box = (round(x * S), round(y * S), round((x + w) * S) - 1, round((y + h) * S) - 1)
        self.d.rounded_rectangle(box, radius=r * S, fill=fill, outline=outline, width=S if outline else 0)

    def line(self, pts, fill, width=1.5):
        self.d.line([(px * S, py * S) for px, py in pts], fill=fill, width=round(width * S), joint='curve')

    def text(self, s, x, y, w, h, size=13, color=FG, align='left', kind='cn', weight=500):
        f = font(size, kind, weight)
        b = self.d.textbbox((0, 0), s, font=f)
        tw = b[2] - b[0]
        if tw > w * S:
            raise ValueError(f'label too wide: {s!r} {tw / S:.1f}px > {w}px')
        dx = {'left': 0, 'center': (w * S - tw) / 2, 'right': w * S - tw}[align]
        # Vertically center on the font's own ascent/descent so mixed labels share a baseline.
        asc, desc = f.getmetrics()
        dy = (h * S - (asc + desc)) / 2
        self.d.text((round(x * S + dx - b[0]), round(y * S + dy)), s, font=f, fill=color)

    def image(self):
        return self.im.resize((self.w, self.h), Image.Resampling.LANCZOS)

    def save(self, name):
        self.image().save(DEST / name)


def chevron(c, cx, cy, color, size=3.0, down=True):
    k = 1 if down else -1
    c.line([(cx - size, cy - k * size / 2), (cx, cy + k * size / 2), (cx + size, cy - k * size / 2)], color, 1.4)


# --------------------------------------------------------------------------
# Layout. Each entry is (x, y) of the control's top-left corner unless noted.
# --------------------------------------------------------------------------
L, R = 12, 270             # left / right column x
LW, RW = 246, 248          # column widths
RX, RX2 = R + 8, R + RW - 8  # right column content edges (278..510)
TOGGLE_W, TOGGLE_H = 36, 16
SEG_H = 20
FIELD_H = 22

cards = [(L, 56, LW, 84), (L, 148, LW, 560), (R, 56, RW, 170), (R, 234, RW, 252), (R, 494, RW, 214)]
toggles = {  # control id -> (x, y); label drawn on the base
    'BUTTON_STARTUP': (L + LW - 8 - TOGGLE_W, 90, '随 Windows 启动'),
    'BUTTON_SHOW_OSD': (L + LW - 8 - TOGGLE_W, 114, '显示 OSD'),
    'BUTTON_ENABLE_STEALTH': (RX2 - TOGGLE_W, 118, '隐身模式'),
    'BUTTON_ENABLE_DYN_OFF': (RX2 - TOGGLE_W, 142, '自定义 Direct3D 支持'),
    'BUTTON_ENABLE_OSD': (RX2 - TOGGLE_W, 244, None),
    'BUTTON_ENABLE_BGND': (RX2 - TOGGLE_W, 364, 'OSD 阴影'),
    'BUTTON_ENABLE_FILL': (RX2 - TOGGLE_W, 388, '背景填充'),
    'BUTTON_ENABLE_STAT': (RX2 - TOGGLE_W, 460, '显示 RTSS 自身统计'),
}
segments = {  # bitmap stem -> (control id, label, x, y, w)
    'Level0': ('BUTTON_NONE', '关闭', 278, 88, 58),
    'Level1': ('BUTTON_LOW', '低', 336, 88, 58),
    'Level2': ('BUTTON_MEDIUM', '中', 394, 88, 58),
    'Level3': ('BUTTON_HIGH', '高', 452, 88, 58),
    'RenderV2': ('BUTTON_OSD_VECTOR2D', '矢量 2D', 278, 288, 77),
    'RenderV3': ('BUTTON_OSD_VECTOR3D', '矢量 3D', 355, 288, 77),
    'RenderR3': ('BUTTON_OSD_RASTER3D', '光栅 3D', 432, 288, 78),
    'SpaceViewport': ('BUTTON_OSD_VIEWPORT', '视口', 278, 334, 116),
    'SpaceFramebuffer': ('BUTTON_OSD_FRAMEBUFFER', '帧缓冲', 394, 334, 116),
}
ACTIONS = [('BUTTON_ADD', 'ActAdd', '添加', 20), ('BUTTON_REMOVE', 'ActRemove', '移除', 78),
           ('BUTTON_DEFAULTS', 'ActDefaults', '默认', 136), ('BUTTON_SETUP', 'ActSetup', '设置', 194)]
ACTION_Y, ACTION_W, ACTION_H = 666, 56, 32
CAPTIONS = [('BUTTON_HELP', 'Help', 440), ('BUTTON_MIN', 'Minimize', 466), ('BUTTON_CLOSE', 'Close', 492)]
CAPTION_Y = 12
CYCLE_W = 124
cycles = {  # control id -> (bitmap stem, labels, y)
    'BUTTON_FRAMETIME': ('CycleLimit', ['帧率上限', '帧时间上限'], 168),
    'BUTTON_SSYNC': ('CycleSync', ['扫描线同步', '扫描线同步 ×2', '扫描线同步 ÷2'], 196),
}
FIELD_X = RX + CYCLE_W + 4  # numeric field next to each cycle button
COLORS = [('BUTTON_COLOR', 'SwatchBase', 450), ('BUTTON_COLOR_BGND', 'SwatchShadow', 472), ('BUTTON_COLOR_FILL', 'SwatchFill', 494)]
COLOR_Y = 414
SLIDER = (RX2 - 64, 437)
PREVIEW = (279, 508, 230, 145)
POS_FIELDS = [(RX, 'X', 'TEXT_OSD_X', 'BUTTON_SPIN_LEFT', 'BUTTON_SPIN_RIGHT', 'SpinLeft', 'SpinRight'),
              (398, 'Y', 'TEXT_OSD_Y', 'BUTTON_SPIN_UP', 'BUTTON_SPIN_DOWN', 'SpinUp', 'SpinDown')]
POS_Y, POS_W = 674, 112
VERSION = (430, 18)  # right edge, top

# --------------------------------------------------------------------------
# Base
# --------------------------------------------------------------------------
base = Canvas(W, H, BG)
base.rect(0, 0, W, H, None, outline=LINE)
for x, y, w, h in cards:
    base.rect(x, y, w, h, CARD, r=8)

# Brand: a leaf drawn from two arcs inside a rounded mint tile.
base.rect(14, 12, 26, 26, MINT, r=7)
# The leaf is the overlap of two discs, tilted 45 degrees, with a mint midrib.
leaf_a, leaf_b = Image.new('L', (26 * S, 26 * S)), Image.new('L', (26 * S, 26 * S))
ImageDraw.Draw(leaf_a).ellipse((-3 * S, 5 * S, 21 * S, 29 * S), fill=255)
ImageDraw.Draw(leaf_b).ellipse((5 * S, -3 * S, 29 * S, 21 * S), fill=255)
leaf = Image.composite(leaf_a, Image.new('L', leaf_a.size), leaf_b)
base.im.paste(Image.new('RGBA', leaf.size, INK), (14 * S, 12 * S), leaf)
base.line([(20, 32), (31.5, 20.5)], MINT, 1.3)
base.text('静谧薄荷', 48, 9, 120, 18, 15, FG, weight=650)
base.text('Quiet Mint for RTSS', 48, 27, 160, 14, 10, MUTED, weight=450)

# Section headings and row labels
base.text('常规', L + 10, 62, 120, 20, 13, MUTED, weight=600)
base.text('应用程序配置文件', L + 10, 154, 200, 20, 13, MUTED, weight=600)
base.text('应用程序检测级别', RX, 62, 200, 20, 13, MUTED, weight=600)
base.text('启用 OSD', RX, 242, 150, 20, 14, FG, weight=650)
base.text('渲染模式', RX, 266, 120, 18, 12, MUTED)
base.text('坐标空间', RX, 312, 120, 18, 12, MUTED)
base.text('颜色', RX, 412, 120, 20, 13)
base.text('缩放', RX, 434, 120, 20, 13)
for cid, (x, y, label) in toggles.items():
    if label:
        lx = L + 10 if x < R else RX
        base.text(label, lx, y - 2, 180, 20, 13)

# Tracks behind segmented controls
for stems in [['Level0', 'Level1', 'Level2', 'Level3'], ['RenderV2', 'RenderV3', 'RenderR3'], ['SpaceViewport', 'SpaceFramebuffer']]:
    first, last = segments[stems[0]], segments[stems[-1]]
    base.rect(first[2], first[3], last[2] + last[4] - first[2], SEG_H, TRACK, r=5)

# Numeric fields
def field(x, y, w):
    base.rect(x, y, w, FIELD_H, FIELD, r=4, outline=LINE)

for cid, (_, _, y) in cycles.items():
    field(FIELD_X, y, RX2 - FIELD_X)
for x, axis, *_ in POS_FIELDS:
    field(x, POS_Y, POS_W)
    base.text(axis, x + 7, POS_Y, 12, FIELD_H, 11, DIM, kind='mono')

# Application list frame and OSD preview frame
base.rect(L + 7, 179, LW - 14, 479, FIELD, r=4, outline=LINE)
px, py, pw, ph = PREVIEW
base.rect(px - 1, py - 1, pw + 2, ph + 2, LINE)
base.save('SkinBase.png')

# --------------------------------------------------------------------------
# Controls
# --------------------------------------------------------------------------
# Segmented buttons: transparent at rest, a mint pill when selected.
for stem, (cid, label, x, y, w) in segments.items():
    for pressed in (False, True):
        c = Canvas(w, SEG_H)
        # Near-zero alpha keeps the whole segment clickable.
        c.rect(0, 0, w, SEG_H, (41, 48, 58, 2))
        if pressed:
            c.rect(2, 2, w - 4, SEG_H - 4, MINT, r=4)
        ink = INK if pressed else MUTED
        if stem == 'RenderR3':
            # Selecting raster 3D opens the font picker; the chevron hints at it.
            c.text(label, 0, 0, w - 12, SEG_H, 12, ink, 'center', weight=600 if pressed else 500)
            chevron(c, w - 12, SEG_H / 2, ink, 2.5)
        else:
            c.text(label, 0, 0, w, SEG_H, 12, ink, 'center', weight=600 if pressed else 500)
        c.save(f'{stem}{"On" if pressed else ""}.png')

# Toggle switch: 16 frames stacked vertically, frame i = i/15 of the way to "on".
# The pressed bitmap runs the same animation backwards.
def toggle_frame(c, y, t):
    mix = lambda a, b: tuple(round(int(a[i:i + 2], 16) * (1 - t) + int(b[i:i + 2], 16) * t) for i in (1, 3, 5))
    c.rect(0, y, TOGGLE_W, TOGGLE_H, mix(TRACK, MINT), r=8)
    kx = 2 + t * (TOGGLE_W - 16)
    c.d.ellipse((kx * S, (y + 2) * S, (kx + 12) * S - 1, (y + 14) * S - 1), fill=mix('#9AA5B4', '#F4FBF8'))

for pressed in (False, True):
    c = Canvas(TOGGLE_W, TOGGLE_H * 16)
    for i in range(16):
        toggle_frame(c, i * TOGGLE_H, (15 - i if pressed else i) / 15)
    c.save('Toggle' + ('On' if pressed else '') + '.png')

# Cycle buttons: one frame per mode, laid out horizontally.
for cid, (stem, labels, y) in cycles.items():
    c = Canvas(CYCLE_W * len(labels), FIELD_H)
    for i, label in enumerate(labels):
        x = i * CYCLE_W
        c.rect(x, 0, CYCLE_W, FIELD_H, TRACK, r=4)
        c.rect(x + 1, 1, 3, FIELD_H - 2, MINT, r=1.5)
        c.text(label, x + 11, 0, CYCLE_W - 30, FIELD_H, 12)
        # Two stacked chevrons: the mode cycles on each click.
        chevron(c, x + CYCLE_W - 12, 8.5, MUTED, 2.5, down=False)
        chevron(c, x + CYCLE_W - 12, 13.5, MUTED, 2.5)
    c.save(stem + '.png')

# Action buttons under the profile list.
for cid, stem, label, x in ACTIONS:
    c = Canvas(ACTION_W, ACTION_H)
    # Setup is the primary action; Remove is destructive and gets a muted red.
    bg, fg = {'ActSetup': ('#24453A', MINT), 'ActRemove': ('#3A2629', '#F2A7AD')}.get(stem, (TRACK, FG))
    c.rect(0, 0, ACTION_W, ACTION_H, bg, r=6)
    c.text(label, 0, 0, ACTION_W, ACTION_H, 13, fg, 'center', weight=600)
    c.save(stem + '.png')

# Caption buttons share one rounded mask; each state is drawn explicitly.
mask = Canvas(24, 24)
mask.rect(0, 0, 24, 24, '#FFFFFF', r=6)
mask.save('CaptionMask.png')
for cid, name, x in CAPTIONS:
    for state in ('', 'Over', 'Down'):
        if not state:
            bg, fg = BG, MUTED
        elif name == 'Close':
            bg, fg = ('#C2525C' if state == 'Over' else '#9E3F48'), '#FFFFFF'
        else:
            bg, fg = ('#2A333E' if state == 'Over' else '#222A33'), MINT
        c = Canvas(24, 24)
        # At rest the button is drawn flush with the title bar; hover states get the rounded tile.
        c.rect(0, 0, 24, 24, bg, r=6 if state else 0)
        if name == 'Close':
            c.line([(8, 8), (16, 16)], fg, 1.6)
            c.line([(16, 8), (8, 16)], fg, 1.6)
        elif name == 'Minimize':
            c.line([(7.5, 12), (16.5, 12)], fg, 1.6)
        else:
            c.text('?', 0, 0, 24, 24, 13, fg, 'center', kind='mono')
        c.save(f'Caption{name}{state}.png')

# Spin buttons: small chevrons on the field color, opaque so the whole cell is clickable.
for stem, direction in [('SpinUp', 'up'), ('SpinDown', 'down'), ('SpinLeft', 'left'), ('SpinRight', 'right')]:
    c = Canvas(8, 16, FIELD)
    pts = {'up': [(1.5, 9.5), (4, 6.5), (6.5, 9.5)], 'down': [(1.5, 6.5), (4, 9.5), (6.5, 6.5)],
           'left': [(5.5, 5.5), (2.5, 8), (5.5, 10.5)], 'right': [(2.5, 5.5), (5.5, 8), (2.5, 10.5)]}[direction]
    c.line(pts, MINT, 1.3)
    c.save(stem + '.png')
Canvas(8, 16, '#FFFFFF').save('SpinMask.png')

# Color swatches: RTSS paints the chosen color; the mask gives it a rounded shape.
for _, stem, _ in COLORS:
    Canvas(16, 16, '#000000').save(stem + '.png')
for stem, alpha in [('SwatchMask', 215), ('SwatchMaskOver', 255)]:
    c = Canvas(16, 16, '#000000')
    c.rect(1, 1, 14, 14, (alpha,) * 3 + (255,), r=4)
    c.save(stem + '.png')

# Zoom slider
c = Canvas(10, 14)
c.rect(0, 0, 10, 14, '#F4FBF8', r=3)
c.rect(4, 4, 2, 6, MINT, r=1)
c.save('SliderKnob.png')
for stem, color in [('SliderTrack', LINE), ('SliderTrackOn', MINT)]:
    c = Canvas(64, 4)
    c.rect(0, 0, 64, 4, color, r=2)
    c.save(stem + '.png')

# OSD position markers around the preview: brackets at corners, ticks at edges.
def marker(stem, w, h, pts):
    for pressed in (False, True):
        c = Canvas(w, h)
        for seg in pts:
            c.line(seg, MINT if pressed else DIM, 2.4)
        c.save(stem + ('On' if pressed else '') + '.png')

M = 16
marker('PosTopLeft', M, M, [[(1.2, 14), (1.2, 1.2), (14, 1.2)]])
marker('PosTopRight', M, M, [[(2, 1.2), (14.8, 1.2), (14.8, 14)]])
marker('PosBottomLeft', M, M, [[(1.2, 2), (1.2, 14.8), (14, 14.8)]])
marker('PosBottomRight', M, M, [[(2, 14.8), (14.8, 14.8), (14.8, 2)]])
marker('PosTopCenter', 16, 6, [[(2, 1.2), (14, 1.2)]])
marker('PosBottomCenter', 16, 6, [[(2, 4.8), (14, 4.8)]])
marker('PosCenterLeft', 6, 16, [[(1.2, 2), (1.2, 14)]])
marker('PosCenterRight', 6, 16, [[(4.8, 2), (4.8, 14)]])
positions = {  # control id -> (stem, x, y)
    'BUTTON_OSD_TOP_LEFT': ('PosTopLeft', px - 8, py - 8),
    'BUTTON_OSD_TOP_CENTER': ('PosTopCenter', px + pw // 2 - 8, py - 8),
    'BUTTON_OSD_TOP_RIGHT': ('PosTopRight', px + pw - 8, py - 8),
    'BUTTON_OSD_CENTER_LEFT': ('PosCenterLeft', px - 8, py + ph // 2 - 8),
    'BUTTON_OSD_CENTER_RIGHT': ('PosCenterRight', px + pw + 2, py + ph // 2 - 8),
    'BUTTON_OSD_BOTTOM_LEFT': ('PosBottomLeft', px - 8, py + ph - 8),
    'BUTTON_OSD_BOTTOM_CENTER': ('PosBottomCenter', px + pw // 2 - 8, py + ph + 2),
    'BUTTON_OSD_BOTTOM_RIGHT': ('PosBottomRight', px + pw - 8, py + ph - 8),
}

# Raster fonts. Digits: '-' .. '9' in 9x16 cells; version: ' ' .. DEL in 9x12 cells.
def raster_font(name, first, count, cw, ch, size, color, blank=''):
    c = Canvas(cw, ch * count)
    f = font(size, 'mono')
    asc, desc = f.getmetrics()
    for i in range(count):
        char = chr(first + i)
        if char in blank:
            continue
        adv = c.d.textlength(char, font=f)
        c.d.text(((cw * S - adv) / 2, (i * ch * S) + (ch * S - asc - desc) / 2), char, font=f, fill=color)
    # RTSS measures proportional glyphs by their visible pixels, so drop resampling haze.
    im = c.image()
    im.putalpha(im.getchannel('A').point(lambda a: 0 if a < 12 else a))
    im.save(DEST / name)

# RTSS pads numeric fields with '/', so that glyph stays empty.
raster_font('Digits.png', ord('-'), 13, 9, 16, 12.5, '#CFEFE3', blank='/')
raster_font('VersionFont.png', 32, 96, 9, 12, 10.5, MUTED)

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
bitmaps = [('BMP_PREVIEW', 'Preview.png'), ('BMP_BASE', 'SkinBase.png')]
buttons = []


def bmp(ident, spec):
    bitmaps.append((ident, spec))
    return ident


def button(cid, x, y, normal, alpha, hot, pressed, pressed_hot, alpha_pressed=None, flags='', extra=''):
    ap = alpha_pressed or alpha
    buttons.append(f'{cid:<24}= {x:03},{y:03},{flags:<9},,,{normal},{alpha},{hot},{alpha},{pressed},{ap},{pressed_hot},{ap}{extra}')


def simple(cid, stem, x, y, pressed_stem=None, flags='', extra=''):
    """Button whose hot state is the Hot effect and alpha comes from the PNG."""
    key = 'BMP_' + stem.upper()
    n = bmp(key, f'{stem}.png')
    a = bmp(key + '_ALPHA', f'{stem}.png,Alpha')
    h = bmp(key + '_HOT', f'{stem}.png,Hot')
    ap = None
    if pressed_stem:
        p = bmp(key + '_ON', f'{pressed_stem}.png')
        ph = bmp(key + '_ON_HOT', f'{pressed_stem}.png,Hot')
        # The selected state has its own shape (e.g. the mint pill), so it needs its own alpha.
        ap = bmp(key + '_ON_ALPHA', f'{pressed_stem}.png,Alpha')
    else:
        p = bmp(key + '_DOWN', f'{stem}.png,Pressed')
        ph = p
    button(cid, x, y, n, a, h, p, ph, alpha_pressed=ap, flags=flags, extra=extra)


bmp('BMP_CPT_MASK', 'CaptionMask.png,Alpha')
for cid, name, x in CAPTIONS:
    k = 'BMP_CPT_' + name.upper()
    button(cid, x, CAPTION_Y, bmp(k, f'Caption{name}.png'), 'BMP_CPT_MASK', bmp(k + '_OVER', f'Caption{name}Over.png'),
           bmp(k + '_DOWN', f'Caption{name}Down.png'), k + '_DOWN')
for cid, stem, label, x in ACTIONS:
    simple(cid, stem, x, ACTION_Y)
bmp('BMP_TOGGLE', 'Toggle.png'); bmp('BMP_TOGGLE_HOT', 'Toggle.png,Hot'); bmp('BMP_TOGGLE_ALPHA', 'Toggle.png,Alpha')
bmp('BMP_TOGGLE_ON', 'ToggleOn.png'); bmp('BMP_TOGGLE_ON_HOT', 'ToggleOn.png,Hot')
for cid, (x, y, _) in toggles.items():
    button(cid, x, y, 'BMP_TOGGLE', 'BMP_TOGGLE_ALPHA', 'BMP_TOGGLE_HOT', 'BMP_TOGGLE_ON', 'BMP_TOGGLE_ON_HOT',
           flags='00010001h', extra=',01,16,15')
for stem, (cid, label, x, y, w) in segments.items():
    simple(cid, stem, x, y, pressed_stem=stem + 'On')
for cid, (stem, labels, y) in cycles.items():
    key = 'BMP_' + stem.upper()
    n, h = bmp(key, f'{stem}.png'), bmp(key + '_HOT', f'{stem}.png,Hot')
    button(cid, RX, y, n, bmp(key + '_ALPHA', f'{stem}.png,Alpha'), h, n, h, extra=f',{len(labels)},1,0')
bmp('BMP_SPIN_MASK', 'SpinMask.png,Alpha')
spins = {'BUTTON_FRL_SPIN_UP': ('SpinUp', RX2 - 19, cycles['BUTTON_FRAMETIME'][2] + 3),
         'BUTTON_FRL_SPIN_DOWN': ('SpinDown', RX2 - 11, cycles['BUTTON_FRAMETIME'][2] + 3),
         'BUTTON_SSYNC_SPIN_UP': ('SpinUp', RX2 - 19, cycles['BUTTON_SSYNC'][2] + 3),
         'BUTTON_SSYNC_SPIN_DOWN': ('SpinDown', RX2 - 11, cycles['BUTTON_SSYNC'][2] + 3)}
for x, axis, text_id, a, b, sa, sb in POS_FIELDS:
    spins[a] = (sa, x + POS_W - 19, POS_Y + 3)
    spins[b] = (sb, x + POS_W - 11, POS_Y + 3)
for stem in ['SpinUp', 'SpinDown', 'SpinLeft', 'SpinRight']:
    k = 'BMP_' + stem.upper()
    bmp(k, f'{stem}.png'); bmp(k + '_HOT', f'{stem}.png,Hot'); bmp(k + '_DOWN', f'{stem}.png,Pressed')
for cid, (stem, x, y) in spins.items():
    k = 'BMP_' + stem.upper()
    button(cid, x, y, k, 'BMP_SPIN_MASK', k + '_HOT', k + '_DOWN', k + '_DOWN')
for cid, (stem, x, y) in positions.items():
    simple(cid, stem, x, y, pressed_stem=stem + 'On')
bmp('BMP_SWATCH_MASK', 'SwatchMask.png'); bmp('BMP_SWATCH_MASK_OVER', 'SwatchMaskOver.png')
for cid, stem, x in COLORS:
    k = bmp('BMP_' + stem.upper(), f'{stem}.png')
    buttons.append(f'{cid:<24}= {x:03},{COLOR_Y:03},{"":<9},,,{k},BMP_SWATCH_MASK,{k},BMP_SWATCH_MASK_OVER,{k},BMP_SWATCH_MASK,{k},BMP_SWATCH_MASK_OVER')
bmp('BMP_SLD', 'SliderKnob.png'); bmp('BMP_SLD_HOT', 'SliderKnob.png,Hot'); bmp('BMP_SLD_ALPHA', 'SliderKnob.png,Alpha')
bmp('BMP_SLD_BGND', 'SliderTrack.png'); bmp('BMP_SLD_BGND_ALPHA', 'SliderTrack.png,Alpha')
bmp('BMP_SLD_BGND_SEL', 'SliderTrackOn.png'); bmp('BMP_SLD_BGND_SEL_ALPHA', 'SliderTrackOn.png,Alpha')
bmp('BMP_DIGITS', 'Digits.png'); bmp('BMP_DIGITS_ALPHA', 'Digits.png,Alpha')
bmp('BMP_VERSION', 'VersionFont.png'); bmp('BMP_VERSION_ALPHA', 'VersionFont.png,Alpha')

texts = [('TEXT_FRAMERATE_LIMIT', RX2 - 23, cycles['BUTTON_FRAMETIME'][2] + 3, 'BMP_DIGITS', '-,-9,16'),
         ('TEXT_SSYNC', RX2 - 23, cycles['BUTTON_SSYNC'][2] + 3, 'BMP_DIGITS', '-,-9,16'),
         ('TEXT_OSD_X', RX + POS_W - 23, POS_Y + 3, 'BMP_DIGITS', '-,-9,16'),
         ('TEXT_OSD_Y', 398 + POS_W - 23, POS_Y + 3, 'BMP_DIGITS', '-,-9,16'),
         ('TEXT_VERSION', VERSION[0], VERSION[1], 'BMP_VERSION', ',9,12')]

ruler = ';' + '-' * 78
header = [
    ';HDR', ruler, '; Quiet Mint / 静谧薄荷 for RTSS. Generated by scripts/render_skin.py.', ruler,
    '[Global]', 'Format\t\t= 00010003h', 'Host\t\t= RTSS.exe', 'Name\t\t= 静谧薄荷 · 简体中文',
    'Author\t\t= BAOZOU', 'Windows\t\t= WND_MAIN', '',
    '[Bitmaps]', *[f'{k:<24}= {v}' for k, v in bitmaps], '',
    '[BitmapEffect.Hot]', 'Brightness\t= 16', '',
    '[BitmapEffect.Pressed]', 'Scroll\t\t= 0,1', '',
    '[WND_MAIN]', 'Base\t\t= ,,,BMP_BASE,', 'Preview\t\t= BMP_PREVIEW', '',
    '[WND_MAIN.Buttons]', *buttons, '',
    '[WND_MAIN.Sliders]',
    f'{"SLIDER_OSD_ZOOM":<24}= {SLIDER[0]:03},{SLIDER[1]:03},00010001h,,,BMP_SLD,BMP_SLD_ALPHA,BMP_SLD_HOT,BMP_SLD_ALPHA,'
    'BMP_SLD_BGND,BMP_SLD_BGND_ALPHA,BMP_SLD_BGND_SEL,BMP_SLD_BGND_SEL_ALPHA', '',
    '[WND_MAIN.Texts]',
    *[f'{t:<24}= {x:03},{y:03},00000011h,,,{b},{b}_ALPHA,{spec}' for t, x, y, b, spec in texts], '',
    '[WND_MAIN.Placeholders]',
    f'{"PLACEHOLDER_APP_WND":<24}= {L + 8:03},180,,,,{LW - 16},477,'
    f'{hexbgr(FIELD)},{hexbgr("#B4BFCC")},{hexbgr(MINT_DEEP)},{hexbgr(MINT_DEEP)},FFFFFFh',
    f'{"PLACEHOLDER_OSD_WND":<24}= {px:03},{py:03},,,,{pw},{ph},{hexbgr("#0C0F13")},{hexbgr("#2A3039")}',
    f'{"PLACEHOLDER_CFG_WND":<24}= 000,000,,,,0,0,{hexbgr(MINT_DEEP)},FFFFFFh', '',
]
(DEST / 'header').write_bytes('\r\n'.join(header).encode('gbk'))
for _, spec in bitmaps:
    f = spec.split(',')[0]
    if f != 'Preview.png' and not (DEST / f).is_file():
        raise SystemExit(f'header references missing bitmap {f}')

# --------------------------------------------------------------------------
# Preview: the base with every control in a representative state.
# --------------------------------------------------------------------------
pv = Image.open(DEST / 'SkinBase.png').convert('RGBA')


def paste(name, x, y, crop=None):
    im = Image.open(DEST / name).convert('RGBA')
    pv.alpha_composite(im.crop(crop) if crop else im, (x, y))


for cid, name, x in CAPTIONS:
    paste(f'Caption{name}.png', x, CAPTION_Y)
for cid, stem, label, x in ACTIONS:
    paste(stem + '.png', x, ACTION_Y)
on = {'BUTTON_STARTUP', 'BUTTON_SHOW_OSD', 'BUTTON_ENABLE_OSD', 'BUTTON_ENABLE_BGND'}
for cid, (x, y, _) in toggles.items():
    paste('Toggle.png', x, y, (0, 15 * TOGGLE_H, TOGGLE_W, 16 * TOGGLE_H) if cid in on else (0, 0, TOGGLE_W, TOGGLE_H))
for stem, (cid, label, x, y, w) in segments.items():
    paste(stem + ('On' if stem in ('Level1', 'RenderR3', 'SpaceViewport') else '') + '.png', x, y)
for cid, (stem, labels, y) in cycles.items():
    paste(stem + '.png', RX, y, (0, 0, CYCLE_W, FIELD_H))
for cid, (stem, x, y) in spins.items():
    paste(stem + '.png', x, y)
for cid, (stem, x, y) in positions.items():
    paste(stem + ('On' if cid == 'BUTTON_OSD_TOP_LEFT' else '') + '.png', x, y)
paste('SliderTrack.png', SLIDER[0], SLIDER[1] + 5)
paste('SliderTrackOn.png', SLIDER[0], SLIDER[1] + 5, (0, 0, 14, 4))
paste('SliderKnob.png', SLIDER[0] + 10, SLIDER[1])
d = ImageDraw.Draw(pv)
for (_, _, x), color in zip(COLORS, ['#FFD34E', '#000000', '#000000']):
    d.rounded_rectangle((x + 1, COLOR_Y + 1, x + 14, COLOR_Y + 14), radius=4, fill=color, outline=LINE)
# Application list with the global profile selected, and the OSD preview sample.
d.rectangle((L + 8, 180, L + LW - 9, 197), fill=MINT_DEEP)
d.rectangle((px, py, px + pw - 1, py + ph - 1), fill='#2A3039')
big = Canvas(W, H)
big.text('Global', L + 14, 180, 120, 18, 11, '#FFFFFF', weight=600)
big.text('60', px + 8, py + 6, 40, 20, 14, '#FFD34E', kind='mono')
pv.alpha_composite(big.image())


def raster(sprite, first, cw, ch, s, right, y, proportional=False):
    """Draw right-aligned text the way RTSS does: fixed cells, or glyph width + 1 px."""
    sheet = Image.open(DEST / sprite).convert('RGBA')
    for char in reversed(s):
        k = ord(char) - first
        glyph = sheet.crop((0, k * ch, cw, (k + 1) * ch))
        if proportional and glyph.getbbox():
            l, _, r, _ = glyph.getbbox()
            glyph = glyph.crop((l, 0, r, ch))
            right -= 1
        right -= glyph.width
        pv.alpha_composite(glyph, (right, y))


for t, x, y, b, spec in texts:
    if b == 'BMP_DIGITS':
        raster('Digits.png', ord('-'), 9, 16, {'TEXT_OSD_X': '0', 'TEXT_OSD_Y': '0'}.get(t, '0'), x, y)
raster('VersionFont.png', 32, 9, 12, '7.3.7', VERSION[0], VERSION[1], proportional=True)
pv.save(DEST / 'Preview.png')
(ROOT / 'build/skin-preview').mkdir(parents=True, exist_ok=True)
pv.save(ROOT / 'build/skin-preview/Preview.png')

if args.sync_src:
    src = ROOT / 'src/skin'
    for old in src.glob('*'):
        old.unlink()
    for f in DEST.iterdir():
        shutil.copy2(f, src / f.name)

result = {'source': str(DEST), 'bitmaps': len(list(DEST.glob('*.png')))}
if args.compile:
    # The compiler is built into RTSS.exe. Run a private copy so the installed
    # RTSS is untouched, and as the invoking user so no elevation is needed.
    tool = ROOT / 'build/rtss-tool'
    (tool / 'Skins').mkdir(parents=True, exist_ok=True)
    for f in ['RTSS.exe', 'RTUI.dll', 'RTMUI.dll', 'RTFC.dll']:
        shutil.copy2(args.rtss / f, tool / f)
    work = tool / 'Skins' / NAME
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(DEST, work)
    usf = tool / 'Skins' / (NAME + '.usf')
    usf.unlink(missing_ok=True)
    proc = subprocess.Popen([str(tool / 'RTSS.exe'), '-cs', NAME], cwd=tool, env={**os.environ, '__COMPAT_LAYER': 'RunAsInvoker'})
    # RTSS reports the result in a message box; stop it once the file is stable.
    deadline, last = time.time() + 60, -1
    while time.time() < deadline:
        time.sleep(1)
        size = usf.stat().st_size if usf.exists() else -1
        if size > 0 and size == last:
            break
        last = size
    proc.kill()
    if not usf.exists():
        raise SystemExit('skin compilation failed: no USF produced')
    shutil.copy2(usf, ROOT / 'build/Skins' / usf.name)
    result['usf'] = str(ROOT / 'build/Skins' / usf.name)
print(json.dumps(result, ensure_ascii=False))

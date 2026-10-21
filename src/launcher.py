# inFAMOUS Second Son launcher window.
#   inFAMOUS Second Son.exe          opens the launcher
#   inFAMOUS Second Son.exe --play   starts the game straight away (Steam / desktop shortcuts)
import os, shutil, subprocess, sys, threading, time, traceback
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageTk

import art as artwork
import cheats
import controllers
import core
import emulator
import gestures
import keys
import mods
import packs
import pad_art
import saveedit
import saves
import steam
import i18n
from i18n import _

BG, PANEL, PANEL2, LINE = '#0c0d11', '#15171d', '#1d2028', '#2a2e39'
TEXT, DIM, ACCENT, ACCENT2, OK, BAD = '#eceef3', '#8d94a5', '#e2452b', '#ff6a3d', '#4cc26a', '#e0a030'
HERO_BLUE, XBOX_BG, XBOX_FG = '#3d9be9', '#1f3a24', '#7ed38f'
ICON_FONT = 'Segoe Fluent Icons'
APP_NAME = 'Conduit Launcher'  # unofficial launcher; the game's name only says what it runs
APP_VERSION = '1.0.1'
EXE = sys.executable if getattr(sys, 'frozen', False) else os.path.join(core.ROOT, APP_NAME + '.exe')
NO_WINDOW = 0x08000000
TITLE = APP_NAME
GAME = core.NAME  # shortcuts in the user's own Steam library and desktop keep the game's name


def art(kind):
    return artwork.path(kind)


def hero_image(w, h):
    p = art('hero')
    return cover_fit(Image.open(p).convert('RGB'), w, h) if p else artwork.background(w, h)


def logo_image(max_w, max_h):
    p = art('logo')
    logo = Image.open(p).convert('RGBA') if p else artwork.title_image()
    s = min(max_w / logo.width, max_h / logo.height)
    return logo.resize((int(logo.width * s), int(logo.height * s)), Image.LANCZOS)


def cover_fit(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((max(w, int(img.width * s + 0.5)), max(h, int(img.height * s + 0.5))), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 3
    return img.crop((x, y, x + w, y + h))


def app_ico():
    if not art('icon'):
        return os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), 'app.ico')
    out = os.path.join(core.USER, 'icon.ico')
    if not os.path.isfile(out):
        os.makedirs(core.USER, exist_ok=True)
        Image.open(art('icon')).convert('RGBA').save(out, sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
    return out


def run_game(s, progress, on_started=None, on_session=None):
    """s: the session's effective settings (core.effective)."""
    if core.emu_running():
        raise RuntimeError(_('O shadPS4 já está aberto. Feche o jogo que está rodando antes.'))
    open(core.LOG, 'w').close()
    progress(4, _('Fazendo backup dos saves…'))
    try:
        b = saves.backup()
        core.log('backup dos saves: %s' % (os.path.basename(b) if b else 'nenhum save ainda'))
    except Exception as e:  # a failed backup must not keep the game from opening
        core.log('backup dos saves falhou: %s' % e)
    eboot = core.prepare(s, progress)
    on = [c for c in cheats.load(core.eboot_path(s) or '') if c['ok'] and c['kind'] == 'toggle'
          and c['id'] in s['cheats_on']]
    session = core.launch(eboot, s, on)
    if on_session:
        on_session(session)
    pad = None
    if s['controller'] and not s['native_touch'] and s['pad_gestures']:
        pad = gestures.Gestures(s, core.log)
    if on_started:
        on_started()
    try:
        code = core.wait(session)
    finally:
        if pad:
            pad.stop()
        if on_session:
            on_session(None)
    core.log('shadPS4 saiu com código %s' % code)
    return code


def sync_mods(s):
    """Installs/removes the .zip mods in the mods folder; saves the settings when that enabled one."""
    try:
        done = mods.sync_zips(s)
    except Exception:
        core.log(traceback.format_exc())
        return []
    if done:
        core.save_settings(s)
    return done


def pad_kind(s, pads):
    """'xbox' / 'playstation' / 'other' for this session, or None when it can't tell."""
    if s['pad_mode'] != 'auto':
        return s['pad_mode']
    k = controllers.kind_of(pads)
    if k == 'nintendo':
        return 'other'
    return None if k == 'mixed' else k


def ask_pad(master, s, pads):
    """Asks which controller will be used. Returns the kind, or None when cancelled."""
    top = tk.Toplevel(master)
    top.title(TITLE)
    top.configure(bg=PANEL)
    top.resizable(False, False)
    top.attributes('-topmost', True)
    try:
        top.iconbitmap(app_ico())
    except Exception:
        pass
    result = {}
    tk.Label(top, text=_('Qual controle você vai usar?'), font=('Bahnschrift SemiBold', 16), fg=TEXT,
             bg=PANEL).pack(anchor='w', padx=24, pady=(20, 4))
    found = ', '.join(p['name'] for p in pads) if pads else _('nenhum controle encontrado')
    tk.Label(top, text=_('Não deu para identificar sozinho (%s).\nOs botões do Xbox nas dicas, os gestos com View '
                       'e a emulação do touchpad só valem com controle do tipo Xbox.') % found,
             font=('Segoe UI', 9), fg=DIM, bg=PANEL, justify='left').pack(anchor='w', padx=24, pady=(0, 12))
    remember = tk.BooleanVar(value=False)
    for kind, name, sub in (('xbox', 'Xbox / XInput', _('Xbox, 8BitDo e outros no modo XInput')),
                            ('playstation', 'PlayStation', _('DualShock 4 ou DualSense: usa o touchpad e o sensor do '
                                                           'próprio controle')),
                            ('other', _('Outro / só teclado'), _('Sem os ajustes do Xbox; touchpad e movimento pelo '
                                                            'teclado'))):
        b = tk.Frame(top, bg=PANEL2, cursor='hand2', highlightthickness=1, highlightbackground=LINE)
        b.pack(fill='x', padx=24, pady=3)
        a = tk.Label(b, text=name, font=('Segoe UI Semibold', 11), fg=TEXT, bg=PANEL2, anchor='w')
        a.pack(fill='x', padx=14, pady=(8, 0))
        c = tk.Label(b, text=sub, font=('Segoe UI', 9), fg=DIM, bg=PANEL2, anchor='w')
        c.pack(fill='x', padx=14, pady=(0, 8))

        def pick(e, kind=kind):
            result['kind'] = kind
            top.destroy()
        for w in (b, a, c):
            w.bind('<Button-1>', pick)
            w.bind('<Enter>', lambda e, b=b: b.configure(highlightbackground=ACCENT))
            w.bind('<Leave>', lambda e, b=b: b.configure(highlightbackground=LINE))
    tk.Checkbutton(top, text=_('Lembrar e não perguntar de novo (muda em Controles > Opções)'), variable=remember,
                   font=('Segoe UI', 9), fg=DIM, bg=PANEL, activebackground=PANEL, activeforeground=TEXT,
                   selectcolor=PANEL2, bd=0, highlightthickness=0).pack(anchor='w', padx=20, pady=(10, 0))
    cancel = tk.Label(top, text=_('Cancelar'), font=('Segoe UI', 10), fg=TEXT, bg=PANEL2, padx=14, pady=6,
                      cursor='hand2')
    cancel.pack(anchor='e', padx=24, pady=(6, 18))
    cancel.bind('<Button-1>', lambda e: top.destroy())
    top.update_idletasks()
    top.geometry('+%d+%d' % ((top.winfo_screenwidth() - top.winfo_width()) // 2,
                             (top.winfo_screenheight() - top.winfo_height()) // 2))
    top.grab_set()
    top.focus_force()
    master.wait_window(top)
    kind = result.get('kind')
    if kind and remember.get():
        s['pad_mode'] = kind
        core.save_settings(s)
    return kind


def short_time(secs):
    h, m = divmod(int(secs) // 60, 60)
    return '%d h %02d min' % (h, m) if h else '%d min' % m


def karma_color(karma):
    """Blue for the good karma levels, red for the evil ones, grey for none (PT-BR and English names)."""
    k = karma.lower()
    if not k or k.startswith(('vând', 'vand', 'nenhum')):
        return LINE
    good = [n.lower() for n in saveedit.GOOD[1:]] + ['protector', 'guardian', 'champion', 'paragon', 'true hero']
    return HERO_BLUE if k in good else ACCENT


# ====================================================================== controller picture

def round_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2, x1, y2,
           x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


SYMBOL_HEX = {k: '#%02x%02x%02x' % v for k, v in pad_art.SYMBOL.items()}


class PadView:
    """The DualShock 4 picture with a chip for each button: PS button, Xbox button, action, keys."""
    W, H = 960, 440
    PAD_W = 440
    LEFT = [('l2', 14), ('l1', 54), ('pad_up', 116), ('pad_left', 154), ('pad_right', 192), ('pad_down', 230),
            ('move', 300), ('l3', 340)]
    RIGHT = [('r2', 14), ('r1', 54), ('triangle', 116), ('circle', 154), ('cross', 192), ('square', 230),
             ('camera', 300), ('r3', 340)]
    BOTTOM = [('options', 214), ('touchpad_center', 484)]
    CHIP_W, CHIP_H = 262, 32
    MOVE = ['axis_left_y_minus', 'axis_left_x_minus', 'axis_left_y_plus', 'axis_left_x_plus']
    CAM = ['axis_right_y_minus', 'axis_right_x_minus', 'axis_right_y_plus', 'axis_right_x_plus']
    PART = {'move': 'lstick', 'camera': 'rstick', 'touchpad_center': 'touchpad'}

    def __init__(self, parent, app):
        self.app = app
        self.c = tk.Canvas(parent, width=self.W, height=self.H, bg=BG, highlightthickness=0)
        img, self.parts = pad_art.render(self.PAD_W)
        self.img = ImageTk.PhotoImage(img)
        self.ox, self.oy = (self.W - self.PAD_W) // 2, 26

    def anchor(self, key):
        x, y, r = self.parts[self.PART.get(key, key)]
        return self.ox + x, self.oy + y, r

    def draw(self):
        c = self.c
        c.delete('all')
        c.create_image(self.ox, self.oy, image=self.img, anchor='nw', tags=('pad',))
        for side, items in (('L', self.LEFT), ('R', self.RIGHT)):
            for key, y in items:
                self._chip(key, 6 if side == 'L' else self.W - self.CHIP_W - 6, y, side)
        for key, x in self.BOTTOM:
            self._chip(key, x, 396, 'B')
        c.tag_lower('lines')  # the lines run under the picture, from the chip to the part's edge

    def _keys(self, key):
        s, b = self.app.s, self.app.s['binds']
        if key == 'move':
            return ' '.join(keys.label(b[k][0]) if b[k] else '—' for k in self.MOVE)
        if key == 'camera':
            return _('Mouse (F7)') if s['mouse_camera'] else ' '.join(keys.label(b[k][0]) if b[k] else '—'
                                                                   for k in self.CAM)
        return ' / '.join(keys.label(k) for k in b[key]) or '—'

    def _chip(self, key, x, y, side):
        c, s = self.c, self.app.s
        if key == 'move':
            ps, xb, desc = 'L', 'LS', _('Andar')
        elif key == 'camera':
            ps, xb, desc = 'R', 'RS', _('Câmera')
        else:
            ps, desc = keys.INPUTS[key]
            xb = keys.XBOX.get(key, '')
            if key == 'touchpad_center':
                ps, desc = 'TOUCH', _('Drenar poder (touchpad)')
        ax, ay, ar = self.anchor(key)
        cy = y + self.CHIP_H / 2
        sx, sy = (x + self.CHIP_W, cy) if side == 'L' else (x, cy) if side == 'R' else (x + self.CHIP_W / 2, y)
        tag = 'chip_' + key
        mid = (sx + 18, sy) if side == 'L' else (sx - 18, sy) if side == 'R' else (sx, sy - 14)
        line = c.create_line(sx, sy, mid[0], mid[1], ax, ay, fill=LINE, width=1, tags=('lines',))
        dot = c.create_oval(ax - 3, ay - 3, ax + 3, ay + 3, fill=LINE, outline='', tags=('lines',))
        body = round_rect(c, x, y, x + self.CHIP_W, y + self.CHIP_H, 10, fill=PANEL, outline=LINE, tags=(tag,))
        # PS badge (coloured symbol for the face buttons) + Xbox badge
        bw = 46 if len(ps) > 2 else 30
        round_rect(c, x + 4, y + 4, x + 4 + bw, y + self.CHIP_H - 4, 7, fill=PANEL2, outline='', tags=(tag,))
        c.create_text(x + 4 + bw / 2, cy, text=ps, fill=SYMBOL_HEX.get(key, TEXT), tags=(tag,),
                      font=('Segoe UI Symbol', 11, 'bold') if len(ps) == 1 else ('Segoe UI Semibold', 8))
        tx = x + 10 + bw
        if xb and s['controller']:
            round_rect(c, tx, y + 7, tx + 34, y + self.CHIP_H - 7, 8, fill='#1f3a24', outline='', tags=(tag,))
            c.create_text(tx + 17, cy, text=xb, fill='#7ed38f', font=('Segoe UI Semibold', 8), tags=(tag,))
            tx += 40
        c.create_text(tx, cy, text=desc, fill=DIM, anchor='w', font=('Segoe UI', 9), tags=(tag,))
        active = s['keyboard'] or key == 'touchpad_center'
        if active:
            c.create_text(x + self.CHIP_W - 10, cy, text=self._keys(key), anchor='e', fill=ACCENT2,
                          font=('Segoe UI Semibold', 9), tags=(tag,))
        ring = []

        def enter(e):
            c.itemconfigure(body, outline=ACCENT)
            c.itemconfigure(line, fill=ACCENT)
            c.itemconfigure(dot, fill=ACCENT)
            ring.append(c.create_oval(ax - ar - 3, ay - ar - 3, ax + ar + 3, ay + ar + 3, outline=ACCENT2, width=2))
            c.configure(cursor='hand2')

        def leave(e):
            c.itemconfigure(body, outline=LINE)
            c.itemconfigure(line, fill=LINE)
            c.itemconfigure(dot, fill=LINE)
            while ring:
                c.delete(ring.pop())
            c.configure(cursor='')

        c.tag_bind(tag, '<Enter>', enter)
        c.tag_bind(tag, '<Leave>', leave)
        c.tag_bind(tag, '<Button-1>', lambda e: self.app.edit_binding(key))


# ====================================================================== binding dialog

class BindDialog:
    """Edits one or more PS4 inputs: two keys each, keyboard or mouse."""

    def __init__(self, app, title, ids, extra=None):
        self.app, self.ids = app, ids
        self.listen = None  # (id, slot)
        top = self.top = tk.Toplevel(app.root)
        top.title(title)
        top.configure(bg=PANEL)
        top.transient(app.root)
        top.resizable(False, False)
        try:
            top.iconbitmap(app_ico())
        except Exception:
            pass
        tk.Label(top, text=title, font=('Bahnschrift SemiBold', 15), fg=TEXT, bg=PANEL).pack(anchor='w', padx=20,
                                                                                          pady=(16, 2))
        tk.Label(top, text=_('Clique num campo e aperte a tecla. Para botões do mouse, clique no campo e depois '
                           'escolha abaixo.\nEsc cancela. Clique com o botão direito num campo para apagar.'),
                 font=('Segoe UI', 9), fg=DIM, bg=PANEL, justify='left').pack(anchor='w', padx=20, pady=(0, 10))
        grid = tk.Frame(top, bg=PANEL)
        grid.pack(fill='x', padx=20)
        self.slots = {}
        for r, i in enumerate(ids):
            badge, desc = keys.INPUTS[i]
            tk.Label(grid, text=badge, font=('Segoe UI Symbol', 10, 'bold'), fg=TEXT, bg=PANEL2, width=10,
                     pady=4).grid(row=r, column=0, sticky='w', pady=3)
            tk.Label(grid, text=desc, font=('Segoe UI', 10), fg=TEXT, bg=PANEL, anchor='w', justify='left',
                     wraplength=280, width=34).grid(
                row=r, column=1, sticky='w', padx=10)
            for slot in (0, 1):
                b = tk.Label(grid, text='', font=('Segoe UI Semibold', 10), fg=TEXT, bg=PANEL2, width=17, pady=5,
                             cursor='hand2', highlightthickness=1, highlightbackground=LINE)
                b.grid(row=r, column=2 + slot, padx=4, pady=3)
                b.bind('<Button-1>', lambda e, i=i, s=slot: self.start(i, s))
                b.bind('<Button-3>', lambda e, i=i, s=slot: self.assign(i, s, None))
                self.slots[(i, slot)] = b
        if extra:
            extra(top)
        mf = tk.Frame(top, bg=PANEL)
        mf.pack(fill='x', padx=20, pady=(14, 0))
        tk.Label(mf, text=_('Mouse:'), font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(side='left')
        for k, lab in keys.MOUSE:
            b = tk.Label(mf, text=lab, font=('Segoe UI', 9), fg=TEXT, bg=PANEL2, padx=7, pady=4, cursor='hand2')
            b.pack(side='left', padx=2)
            b.bind('<Button-1>', lambda e, k=k: self.listen and self.assign(*self.listen, k))
        self.msg = tk.Label(top, text='', font=('Segoe UI', 9), fg=BAD, bg=PANEL, anchor='w')
        self.msg.pack(fill='x', padx=20, pady=(10, 0))
        foot = tk.Frame(top, bg=PANEL)
        foot.pack(fill='x', padx=20, pady=16)
        app._button(foot, _('Restaurar padrão destes'), self.defaults, PANEL2).pack(side='left')
        app._button(foot, _('Fechar'), top.destroy, ACCENT, fg='white').pack(side='right')
        top.bind('<KeyPress>', self.key)
        self.refresh()
        top.update_idletasks()
        x = app.root.winfo_rootx() + (app.root.winfo_width() - top.winfo_width()) // 2
        y = app.root.winfo_rooty() + (app.root.winfo_height() - top.winfo_height()) // 2
        top.geometry('+%d+%d' % (x, y))
        top.grab_set()
        top.focus_force()

    def refresh(self):
        for (i, slot), b in self.slots.items():
            ks = self.app.s['binds'][i]
            if self.listen == (i, slot):
                b.configure(text=_('aperte uma tecla…'), fg=ACCENT2, highlightbackground=ACCENT)
            else:
                b.configure(text=keys.label(ks[slot]) if slot < len(ks) else '—', fg=TEXT if slot < len(ks) else DIM,
                            highlightbackground=LINE)

    def start(self, i, slot):
        self.listen = (i, slot)
        self.msg.configure(text='')
        self.refresh()

    def key(self, e):
        if not self.listen:
            return
        if e.keysym == 'Escape':
            self.listen = None
            self.refresh()
            return
        k = keys.from_event(e)
        if not k:
            self.msg.configure(text=_('Essa tecla não é suportada pelo emulador. Escolha outra.'))
            return
        self.assign(*self.listen, k)

    def assign(self, i, slot, k):
        if k in keys.RESERVED:
            self.msg.configure(text=_('%s é um atalho do emulador (veja "Atalhos do emulador"). Escolha outra.')
                                    % keys.label(k))
            return
        note = self.app.set_bind(i, slot, k)
        self.msg.configure(text=note or '', fg=BAD)
        self.listen = None
        self.refresh()

    def defaults(self):
        for i in self.ids:
            self.app.s['binds'][i] = list(keys.DEFAULT_BINDS[i])
        self.app.save()
        self.app.redraw_controls()
        self.refresh()


# ====================================================================== main window

class Launcher:
    # (key, name, Segoe Fluent Icons glyph)
    PAGES = [('play', _('Jogar'), ''), ('saves', _('Saves'), ''), ('lang', _('Idioma e dublagem'), ''),
             ('gfx', _('Gráficos'), ''), ('ctrl', _('Controles'), ''), ('gest', _('Gestos do jogo'), ''),
             ('mods', _('Mods'), ''), ('cheats', _('Cheats'), ''), ('adv', _('Avançado'), '')]

    def __init__(self, root):
        self.root = root
        self.s = core.load_settings()
        if core.autodetect(self.s):
            core.save_settings(self.s)
        sync_mods(self.s)
        if core.fix_languages(self.s):
            core.save_settings(self.s)
        self.busy = False
        self.imgs = {}
        self.page, self.preset_tiles, self.session = None, {}, None
        self.pad_list = controllers.detect()
        self.kind = pad_kind(self.s, self.pad_list)
        root.title('%s · %s' % (APP_NAME, GAME))
        root.configure(bg=BG)
        root.geometry('1240x760')
        root.minsize(1200, 740)
        try:
            root.iconbitmap(app_ico())
        except Exception:
            pass
        self._style()
        self._build()
        self.show('play')

    # ------------------------------------------------------------ widgets
    def _style(self):
        st = ttk.Style(self.root)
        st.theme_use('clam')
        st.configure('TCombobox', fieldbackground=PANEL2, background=PANEL2, foreground=TEXT, arrowcolor=TEXT,
                     bordercolor=LINE, lightcolor=PANEL2, darkcolor=PANEL2, selectbackground=PANEL2,
                     selectforeground=TEXT, padding=6)
        st.map('TCombobox', fieldbackground=[('readonly', PANEL2)], foreground=[('readonly', TEXT)],
               selectbackground=[('readonly', PANEL2)], selectforeground=[('readonly', TEXT)])
        self.root.option_add('*TCombobox*Listbox.background', PANEL2)
        self.root.option_add('*TCombobox*Listbox.foreground', TEXT)
        self.root.option_add('*TCombobox*Listbox.selectBackground', ACCENT)
        self.root.option_add('*TCombobox*Listbox.font', ('Segoe UI', 10))
        st.configure('Horizontal.TProgressbar', troughcolor=PANEL2, background=ACCENT, bordercolor=PANEL2,
                     lightcolor=ACCENT, darkcolor=ACCENT)
        st.configure('Dark.Vertical.TScrollbar', background=PANEL2, troughcolor=BG, bordercolor=BG, arrowcolor=DIM,
                     lightcolor=PANEL2, darkcolor=PANEL2)
        st.configure('Horizontal.TScale', background=PANEL, troughcolor=PANEL2, bordercolor=LINE,
                     lightcolor=PANEL2, darkcolor=PANEL2)

    def _button(self, parent, text, cmd, bg=PANEL2, fg=TEXT):
        hover = ACCENT2 if bg == ACCENT else LINE
        b = tk.Label(parent, text=text, font=('Segoe UI', 10), fg=fg, bg=bg, padx=14, pady=7, cursor='hand2',
                     highlightbackground=LINE, highlightthickness=1)
        b.bind('<Button-1>', lambda e: cmd())
        b.bind('<Enter>', lambda e: b.configure(bg=hover))
        b.bind('<Leave>', lambda e: b.configure(bg=bg))
        return b

    def _check(self, parent, text, key, bg=PANEL, cmd=None):
        var = tk.BooleanVar(value=bool(self.s[key]))

        def changed():
            self.s[key] = var.get()
            self.save()
            if cmd:
                cmd()
        w = tk.Checkbutton(parent, text=text, variable=var, command=changed, font=('Segoe UI', 10), fg=TEXT,
                           bg=bg, activebackground=bg, activeforeground=TEXT, selectcolor=PANEL2, bd=0,
                           highlightthickness=0, cursor='hand2', anchor='w', justify='left')
        w.var = var
        return w

    def _card(self, parent, title):
        f = tk.Frame(parent, bg=PANEL, highlightbackground=LINE, highlightthickness=1)
        tk.Label(f, text=title, font=('Bahnschrift', 10), fg=DIM, bg=PANEL).pack(anchor='w', padx=16, pady=(14, 8))
        return f

    def _note(self, parent, text, bg=PANEL, wrap=420):
        return tk.Label(parent, text=text, font=('Segoe UI', 9), fg=DIM, bg=bg, justify='left', anchor='w',
                        wraplength=wrap)

    def _combo(self, parent, label, options, key, conv=lambda v: v):
        tk.Label(parent, text=label, font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(anchor='w', padx=16, pady=(4, 2))
        c = ttk.Combobox(parent, values=[a for a, _x in options], state='readonly', font=('Segoe UI', 10))
        cur = next((a for a, v in options if conv(v) == conv(self.s[key])), options[0][0])
        c.set(cur)
        c.pack(fill='x', padx=16, pady=(0, 8))

        def changed(e):
            self.s[key] = dict(options)[c.get()]
            if isinstance(self.s[key], tuple):
                self.s[key] = list(self.s[key])
            self.save()
        c.bind('<<ComboboxSelected>>', changed)
        return c

    def save(self):
        core.save_settings(self.s)
        if getattr(self, 'preset_tiles', None):
            self._mark_presets()

    # ------------------------------------------------------------ layout
    def _build(self):
        side = tk.Frame(self.root, bg=PANEL, width=232)
        side.pack(side='left', fill='y')
        side.pack_propagate(False)
        tk.Frame(self.root, bg=LINE, width=1).pack(side='left', fill='y')
        tk.Label(side, text='Conduit', font=('Bahnschrift SemiBold', 26), fg=TEXT, bg=PANEL).pack(anchor='w', padx=22,
                                                                                               pady=(26, 0))
        tk.Label(side, text='L A U N C H E R', font=('Bahnschrift', 9), fg=ACCENT2, bg=PANEL).pack(anchor='w', padx=24)
        tk.Label(side, text='inFAMOUS Second Son', font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(anchor='w', padx=24,
                                                                                              pady=(2, 0))
        tk.Frame(side, bg=LINE, height=1).pack(fill='x', padx=18, pady=18)
        icons = ICON_FONT if ICON_FONT in tkfont.families(self.root) else 'Segoe MDL2 Assets'
        self.nav = {}
        for key, name, glyph in self.PAGES:
            row = tk.Frame(side, bg=PANEL, cursor='hand2')
            row.pack(fill='x', pady=1)
            mark = tk.Frame(row, bg=PANEL, width=3)
            mark.pack(side='left', fill='y')
            ic = tk.Label(row, text=glyph, font=(icons, 13), fg=DIM, bg=PANEL, width=3, pady=9)
            ic.pack(side='left', padx=(12, 0))
            lb = tk.Label(row, text=name, font=('Segoe UI Semibold', 11), fg=DIM, bg=PANEL, anchor='w')
            lb.pack(side='left', fill='x', expand=True)
            parts = (row, ic, lb)
            for w in parts:
                w.bind('<Button-1>', lambda e, k=key: self.show(k))
                w.bind('<Enter>', lambda e, k=key: self._nav_paint(k, hover=True))
                w.bind('<Leave>', lambda e, k=key: self._nav_paint(k))
            self.nav[key] = (mark, parts)
        bottom = tk.Frame(side, bg=PANEL)
        bottom.pack(side='bottom', fill='x', padx=22, pady=18)
        tk.Label(bottom, text=_('TEMPO DE JOGO'), font=('Bahnschrift', 9), fg=DIM, bg=PANEL).pack(anchor='w')
        self.side_time = tk.Label(bottom, text='', font=('Bahnschrift SemiBold', 18), fg=TEXT, bg=PANEL)
        self.side_time.pack(anchor='w', pady=(0, 10))
        self.side_status = tk.Label(bottom, text='', font=('Segoe UI', 9), fg=DIM, bg=PANEL, justify='left',
                                    anchor='w', wraplength=190)
        self.side_status.pack(anchor='w')
        tk.Label(bottom, text=_('Projeto de fã, não oficial'), font=('Segoe UI', 8), fg='#5d6372', bg=PANEL).pack(
            anchor='w', pady=(8, 0))

        main = tk.Frame(self.root, bg=BG)
        main.pack(side='left', fill='both', expand=True)
        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill='both', expand=True)
        foot = tk.Frame(main, bg=BG)
        foot.pack(fill='x', padx=28, pady=16)
        self.play = tk.Label(foot, text=_('JOGAR'), font=('Bahnschrift SemiBold', 18), fg='white', bg=ACCENT,
                             padx=50, pady=10, cursor='hand2')
        self.play.pack(side='right')
        self.play.bind('<Button-1>', lambda e: self.start())
        self.play.bind('<Enter>', lambda e: self.play.configure(bg=ACCENT2) if not self.busy else None)
        self.play.bind('<Leave>', lambda e: self.play.configure(bg=ACCENT) if not self.busy else None)
        prog = tk.Frame(foot, bg=BG)
        prog.pack(side='left', fill='x', expand=True, padx=(0, 16))
        self.status = tk.Label(prog, text='', font=('Segoe UI', 9), fg=DIM, bg=BG, anchor='w')
        self.status.pack(fill='x')
        self.bar = ttk.Progressbar(prog, mode='determinate', maximum=100)

        self.pages = {}
        for key, _x, _x in self.PAGES:
            f = tk.Frame(self.content, bg=BG)
            getattr(self, '_page_' + key)(f)
            self.pages[key] = f

    def _nav_paint(self, key, hover=False):
        mark, parts = self.nav[key]
        on = key == getattr(self, 'page', None)
        bg = PANEL2 if on or hover else PANEL
        mark.configure(bg=ACCENT if on else bg)
        for w in parts:
            w.configure(bg=bg)
        for w in parts[1:]:
            w.configure(fg=(ACCENT2 if w is parts[1] else TEXT) if on else TEXT if hover else DIM)

    def show(self, key):
        for f in self.pages.values():
            f.pack_forget()
        self.page = key
        for k in self.nav:
            self._nav_paint(k)
        if key == 'saves':
            self.refresh_saves()
        elif key == 'mods':
            sync_mods(self.s)
            self._build_mods()
        self.pages[key].pack(fill='both', expand=True)
        self.refresh()

    # ------------------------------------------------------------ page: play
    # The whole page is the key art; text and tiles are drawn over it, the tiles' glass is in the image.
    TILES = [('game', _('JOGO')), ('lang', _('IDIOMA')), ('gfx', _('GRÁFICOS')), ('ctrl', _('CONTROLES'))]
    TILE_H = 104

    def _page_play(self, p):
        self.hero = tk.Canvas(p, bg=BG, highlightthickness=0)
        self.hero.pack(fill='both', expand=True)
        self.hero.bind('<Configure>', lambda e: self._draw_play())
        self.hero.bind('<Motion>', self._play_hover)
        self.hero.bind('<Leave>', lambda e: self._play_hover(None))
        self.hero.bind('<Button-1>', self._play_click)
        self.tile_at = None

    def _tile_rects(self, w, h):
        gap, n = 12, len(self.TILES)
        tw = (w - 56 - gap * (n - 1)) / n
        return [(int(28 + i * (tw + gap)), h - self.TILE_H - 20, int(28 + i * (tw + gap) + tw), h - 20)
                for i in range(n)]

    def _play_image(self, w, h):
        key = ('play', w, h)
        if key not in self.imgs:
            img = hero_image(w, h)
            # darken the left side for the text and fade the bottom into the window
            gx, gy = Image.new('L', (w, 1)), Image.new('L', (1, h))
            for x in range(w):
                gx.putpixel((x, 0), int(40 + 200 * max(0, 1 - x / (w * 0.72)) ** 1.4))
            for y in range(h):
                gy.putpixel((0, y), int(255 * max(0, (y - h * 0.45) / (h * 0.55)) ** 1.6))
            mask = ImageChops.lighter(gx.resize((w, h)), gy.resize((w, h)))
            img = Image.composite(Image.new('RGB', (w, h), BG), img, mask).convert('RGBA')
            logo = logo_image(330, 140)
            glow = Image.new('RGBA', (logo.width + 40, logo.height + 40), (0, 0, 0, 0))
            glow.paste((0, 0, 0, 190), (20, 20), logo)
            img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14)), (16, 16))
            img.alpha_composite(logo, (36, 36))
            glass = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(glass)
            for x1, y1, x2, y2 in self._tile_rects(w, h):
                d.rounded_rectangle((x1, y1, x2, y2), 12, fill=(21, 23, 29, 218), outline=(42, 46, 57, 255))
            img.alpha_composite(glass)
            self.imgs = {k: v for k, v in self.imgs.items() if not (isinstance(k, tuple) and k[0] == 'play')}
            self.imgs[key] = (ImageTk.PhotoImage(img), 36 + logo.height)
        return self.imgs[key]

    def _play_state(self):
        """Values for the four tiles: {key: (value, sub, ok)}."""
        s = self.s
        info, msg = core.detect(s['folder'])
        text = next(t for t in core.TEXTS if t[0] == s['text'])
        voice = next(v for v in core.VOICES if v[0] == s['voice'])
        lang_ok = core.voice_available(info, s['voice']) and core.text_available(info, s['text'])
        preset = dict((k, n) for k, n, _x, _x in core.PRESETS).get(core.current_preset(s), _('Personalizado'))
        gfx = '%dp%s · %s' % (s['render'][1], _(' · FSR') if s['fsr'] else '',
                              _('tela cheia') if s['fullscreen'] else 'janela')
        pads, kind = self.pad_list, self.kind
        if s['controller']:
            ctrl = pads[0]['name'] if len(pads) == 1 else _('%d controles') % len(pads) if pads else _('Nenhum controle agora')
            if kind == 'playstation':
                sub = _('Touchpad e sensor do próprio controle')
            elif kind == 'xbox':
                sub = _('Ajustes do Xbox: dicas%s') % (_(' e gestos com View') if s['pad_gestures'] else '')
            elif kind == 'other':
                sub = _('Touchpad e movimento no teclado')
            else:
                sub = _('Tipo não identificado: pergunta ao jogar')
        else:
            ctrl, sub = (_('Teclado e mouse'), _('Sem controle')) if s['keyboard'] else (_('Nada ativado!'), '')
        if not emulator.installed():
            game = (_('Emulador não instalado'), _('Clique para baixar o shadPS4'), False)
        else:
            game = (_('Pronto para jogar') if info else _('Jogo não encontrado'),
                    msg if info else _('Clique para escolher a pasta'), bool(info))
        return {
            'game': game,
            'lang': (text[1], _('Vozes: ') + voice[1].split(' — ')[0], lang_ok),
            'gfx': (preset, gfx, True),
            'ctrl': (ctrl, sub, (bool(pads) and kind is not None) or not s['controller']),
        }

    def _draw_play(self):
        c = self.hero
        w, h = max(c.winfo_width(), 200), max(c.winfo_height(), 300)
        photo, y = self._play_image(w, h)
        c.delete('all')
        c.create_image(0, 0, image=photo, anchor='nw')
        x = 40
        y += 34
        slot = (saves.slots() or [None])[0]
        if slot:
            c.create_text(x, y, text=_('CONTINUAR DE ONDE PAROU'), fill=ACCENT2, anchor='nw', font=('Bahnschrift', 10))
            y += 22
            m = c.create_text(x, y, text=slot['mission'], fill=TEXT, anchor='nw', width=min(620, w - 80),
                              font=('Bahnschrift SemiBold', 26))
            y = c.bbox(m)[3] + 12
            px = x
            if slot['karma']:
                t = c.create_text(px + 12, y + 12, text=slot['karma'].upper(), fill='white', anchor='w',
                                  font=('Bahnschrift SemiBold', 9))
                bx = c.bbox(t)
                round_rect(c, px, y, bx[2] + 12, y + 24, 10, fill=karma_color(slot['karma']), outline='')
                c.tag_raise(t)
                px = bx[2] + 24
            if slot['percent'] is not None:
                c.create_rectangle(px, y + 9, px + 180, y + 15, fill=PANEL2, outline='')
                c.create_rectangle(px, y + 9, px + 180 * slot['percent'] / 100, y + 15, fill=ACCENT, outline='')
                c.create_text(px + 192, y + 12, text=_('%d%% concluído') % slot['percent'], fill=TEXT, anchor='w',
                              font=('Segoe UI Semibold', 10))
            y += 36
            when = time.strftime(_('%d/%m às %H:%M'), time.localtime(slot['time']))
            c.create_text(x, y, text=_('%s · salvo em %s · %s de jogo') % (slot['name'], when,
                                                                         short_time(core.play_time())),
                          fill=DIM, anchor='nw', font=('Segoe UI', 10))
        else:
            c.create_text(x, y, text=_('NOVO JOGO'), fill=ACCENT2, anchor='nw', font=('Bahnschrift', 10))
            c.create_text(x, y + 22, text=_('Nenhum save ainda: o jogo começa do início.'), fill=TEXT, anchor='nw',
                          font=('Bahnschrift SemiBold', 20))
        st = self._play_state()
        for (key, title), (x1, y1, x2, y2) in zip(self.TILES, self._tile_rects(w, h)):
            value, sub, ok = st[key]
            hot = self.tile_at == key
            if hot:
                round_rect(c, x1, y1, x2, y2, 12, fill='', outline=ACCENT, width=1)
            c.create_text(x1 + 18, y1 + 16, text=title, fill=ACCENT2 if hot else DIM, anchor='nw',
                          font=('Bahnschrift', 9))
            c.create_oval(x2 - 24, y1 + 18, x2 - 16, y1 + 26, fill=OK if ok else BAD, outline='')
            c.create_text(x1 + 18, y1 + 36, text=value, fill=TEXT, anchor='nw', width=x2 - x1 - 36,
                          font=('Segoe UI Semibold', 12))
            c.create_text(x1 + 18, y1 + 64, text=sub, fill=DIM, anchor='nw', width=x2 - x1 - 36,
                          font=('Segoe UI', 9))

    def _tile_under(self, e):
        if e is None:
            return None
        w, h = self.hero.winfo_width(), self.hero.winfo_height()
        for (key, _x), (x1, y1, x2, y2) in zip(self.TILES, self._tile_rects(w, h)):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                return key
        return None

    def _play_hover(self, e):
        key = self._tile_under(e)
        if key != self.tile_at:
            self.tile_at = key
            self.hero.configure(cursor='hand2' if key else '')
            self._draw_play()

    def _play_click(self, e):
        key = self._tile_under(e)
        if key == 'game':
            self.install_emulator() if not emulator.installed() else self.pick()
        elif key:
            self.show(key)

    # ------------------------------------------------------------ page: saves
    def _page_saves(self, p):
        self._header(p, _('Saves'), _('Antes de cada sessão o launcher guarda um backup dos saves (ficam os últimos %d). '
                                 'Restaurar ou importar também guarda os atuais antes.') % saves.KEEP)
        body = tk.Frame(p, bg=BG)
        body.pack(fill='both', expand=True, padx=28)
        body.columnconfigure(0, weight=11, uniform='c')
        body.columnconfigure(1, weight=9, uniform='c')
        left = self._card(body, _('NO JOGO'))
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        self.slot_box = tk.Frame(left, bg=PANEL)
        self.slot_box.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        right = self._card(body, _('BACKUPS'))
        right.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        acts = tk.Frame(right, bg=PANEL)
        acts.pack(fill='x', padx=16, pady=(0, 8))
        self._button(acts, _('Backup agora'), self.backup_now).pack(side='left')
        self._button(acts, _('Exportar…'), self.export_saves).pack(side='left', padx=6)
        self._button(acts, _('Importar…'), self.import_saves).pack(side='left')
        self.backup_box = tk.Frame(right, bg=PANEL)
        self.backup_box.pack(fill='both', expand=True, padx=12, pady=(4, 12))
        self._button(right, _('Abrir pasta dos backups'), lambda: self._open(saves.BACKUPS)).pack(anchor='w', padx=16,
                                                                                              pady=(0, 14))

    def refresh_saves(self):
        for box in (self.slot_box, self.backup_box):
            for w in box.winfo_children():
                w.destroy()
        rows = saves.slots()
        if not rows:
            self._note(self.slot_box, _('Nenhum save ainda.')).pack(anchor='w', padx=4)
        for r in rows:
            f = tk.Frame(self.slot_box, bg=PANEL2)
            f.pack(fill='x', pady=2)
            tk.Label(f, text=r['name'], font=('Segoe UI Semibold', 9), fg=ACCENT2 if r['auto'] else TEXT, bg=PANEL2,
                     width=12, anchor='w').pack(side='left', padx=(10, 0), pady=6)
            tk.Label(f, text=r['mission'], font=('Segoe UI', 10), fg=TEXT, bg=PANEL2, anchor='w').pack(
                side='left', fill='x', expand=True)
            self._chip_btn(f, _('✎ Editar'), lambda d=r['dir']: SaveEditor(self, d)).pack(side='right', padx=(4, 6))
            tk.Label(f, text=time.strftime('%d/%m %H:%M', time.localtime(r['time'])), font=('Segoe UI', 9),
                     fg=DIM, bg=PANEL2).pack(side='right', padx=6)
            if r['percent'] is not None:
                tk.Label(f, text='%d%%' % r['percent'], font=('Segoe UI Semibold', 9), fg=TEXT, bg=PANEL2,
                         width=4).pack(side='right')
            if r['karma']:
                tk.Label(f, text=r['karma'], font=('Segoe UI Semibold', 8), fg='white', bg=karma_color(r['karma']),
                         padx=6).pack(side='right', padx=6)
        bks = saves.backups()
        if not bks:
            self._note(self.backup_box, _('Nenhum backup ainda. O primeiro é feito quando você abrir o jogo.'),
                       wrap=340).pack(
                anchor='w', padx=4)
        for path, t, lab in bks[:9]:
            f = tk.Frame(self.backup_box, bg=PANEL2)
            f.pack(fill='x', pady=2)
            tk.Label(f, text=time.strftime('%d/%m/%Y  %H:%M', time.localtime(t)), font=('Segoe UI Semibold', 9),
                     fg=TEXT, bg=PANEL2).pack(side='left', padx=10, pady=6)
            if lab:
                tk.Label(f, text=_(lab), font=('Segoe UI', 8), fg=DIM, bg=PANEL2).pack(side='left')
            self._chip_btn(f, _('Restaurar'), lambda p=path, t=t: self.restore_saves(p, t)).pack(side='right', padx=6)
        if len(bks) > 9:
            self._note(self.backup_box, _('+ %d mais antigos na pasta') % (len(bks) - 9)).pack(anchor='w', padx=4,
                                                                                         pady=(4, 0))

    def _saves_locked(self):
        if core.emu_running():
            messagebox.showwarning(TITLE, _('Feche o jogo antes de mexer nos saves.'))
            return True
        return False

    def backup_now(self):
        try:
            p = saves.backup('manual')
            self.status.configure(text=_('Backup feito') if p else _('Nenhum save para guardar'))
        except Exception as e:
            messagebox.showerror(TITLE, str(e))
        self.refresh_saves()

    def restore_saves(self, path, t):
        if self._saves_locked():
            return
        when = time.strftime(_('%d/%m/%Y às %H:%M'), time.localtime(t))
        if not messagebox.askyesno(TITLE, _('Voltar os saves para o backup de %s?\n\nOs saves de agora são guardados '
                                          'num backup antes.') % when):
            return
        try:
            saves.restore(path)
            self.status.configure(text=_('Saves restaurados do backup de %s') % when)
        except Exception as e:
            core.log(traceback.format_exc())
            messagebox.showerror(TITLE, str(e))
        self.refresh_saves()
        self.refresh()

    def export_saves(self):
        if not saves.slots():
            messagebox.showinfo(TITLE, _('Ainda não há saves para exportar.'))
            return
        dest = filedialog.asksaveasfilename(title=_('Exportar saves'), defaultextension='.zip',
                                            filetypes=[(_('Arquivo zip'), '*.zip')],
                                            initialfile=_('%s saves %s.zip') % (TITLE, time.strftime('%Y-%m-%d')))
        if dest:
            try:
                saves.export(os.path.normpath(dest))
                self.status.configure(text=_('Saves exportados para ') + os.path.basename(dest))
            except Exception as e:
                messagebox.showerror(TITLE, str(e))

    def import_saves(self):
        if self._saves_locked():
            return
        src = filedialog.askopenfilename(title=_('Importar saves'), filetypes=[(_('Arquivo zip'), '*.zip')])
        if not src or not messagebox.askyesno(TITLE, _('Trocar os saves pelos de "%s"?\n\nOs saves de agora são '
                                                     'guardados num backup antes.') % os.path.basename(src)):
            return
        try:
            saves.import_zip(os.path.normpath(src))
            self.status.configure(text=_('Saves importados'))
        except Exception as e:
            core.log(traceback.format_exc())
            messagebox.showerror(TITLE, str(e))
        self.refresh_saves()
        self.refresh()

    # ------------------------------------------------------------ page: language
    def _page_lang(self, p):
        self._header(p, _('Idioma e dublagem'), _('Escolha separadamente o idioma das legendas/menus e o das vozes. '
                                             'Os arquivos do jogo não são alterados.'))
        body = tk.Frame(p, bg=BG)
        body.pack(fill='both', expand=True, padx=28)
        body.columnconfigure(0, weight=1, uniform='c')
        body.columnconfigure(1, weight=1, uniform='c')
        left = self._card(body, _('LEGENDAS E MENUS'))
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        self.text_var = tk.StringVar(value=self.s['text'])
        self.text_radios = {}
        grid = tk.Frame(left, bg=PANEL)
        grid.pack(fill='x', padx=12)
        for n, (key, name, _x, _x) in enumerate(core.TEXTS):
            r = self._radio(grid, name, self.text_var, key, self._lang_changed)
            r.grid(row=n // 2, column=n % 2, sticky='w', padx=(0, 16))
            self.text_radios[key] = r
        pack = tk.Frame(left, bg=PANEL)
        pack.pack(fill='x', padx=16, pady=(12, 14))
        self.pack_note = self._note(pack, '', wrap=420)
        self.pack_note.pack(fill='x')
        self._button(pack, _('Importar português do Brasil…'), self.import_pack).pack(anchor='w', pady=(6, 0))
        right = self._card(body, _('VOZES (DUBLAGEM)'))
        right.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        self.voice_var = tk.StringVar(value=self.s['voice'])
        self.voice_radios = {}
        for key, name, _x in core.VOICES:
            r = self._radio(right, name, self.voice_var, key, self._lang_changed)
            r.pack(anchor='w', padx=12, pady=0)
            self.voice_radios[key] = r
        self.lang_sum = tk.Label(p, text='', font=('Segoe UI Semibold', 11), fg=TEXT, bg=BG, anchor='w')
        self.lang_sum.pack(fill='x', padx=30, pady=(14, 0))

    def _radio(self, parent, text, var, value, cmd):
        return tk.Radiobutton(parent, text=text, variable=var, value=value, command=cmd, font=('Segoe UI', 10),
                              fg=TEXT, bg=PANEL, activebackground=PANEL, activeforeground=TEXT, selectcolor=PANEL2,
                              disabledforeground='#555b69', bd=0, highlightthickness=0, cursor='hand2', pady=3)

    def _lang_changed(self):
        self.s['text'] = self.text_var.get()
        self.s['voice'] = self.voice_var.get()
        self.save()
        self.refresh()

    def _header(self, p, title, sub):
        tk.Label(p, text=title, font=('Bahnschrift SemiBold', 22), fg=TEXT, bg=BG).pack(anchor='w', padx=28,
                                                                                      pady=(24, 0))
        tk.Label(p, text=sub, font=('Segoe UI', 10), fg=DIM, bg=BG, justify='left').pack(anchor='w', padx=29,
                                                                                       pady=(2, 14))

    # ------------------------------------------------------------ page: graphics
    def _page_gfx(self, p):
        for w in p.winfo_children():
            w.destroy()
        self._header(p, _('Gráficos'), _('Escolha uma predefinição ou ajuste abaixo. Vale na próxima vez que o jogo abrir.'))
        tiles = tk.Frame(p, bg=BG)
        tiles.pack(fill='x', padx=28, pady=(0, 14))
        self.preset_tiles = {}
        for i, (key, name, desc, vals) in enumerate(core.PRESETS):
            tiles.columnconfigure(i, weight=1, uniform='p')
            t = tk.Frame(tiles, bg=PANEL, highlightthickness=1, highlightbackground=LINE, cursor='hand2')
            t.grid(row=0, column=i, sticky='nsew', padx=(0 if i == 0 else 6, 0 if i == len(core.PRESETS) - 1 else 6))
            a = tk.Label(t, text=name, font=('Bahnschrift SemiBold', 13), fg=TEXT, bg=PANEL, anchor='w')
            a.pack(fill='x', padx=14, pady=(12, 0))
            b = tk.Label(t, text=desc, font=('Segoe UI', 9), fg=DIM, bg=PANEL, anchor='w', justify='left',
                         wraplength=200)
            b.pack(fill='x', padx=14, pady=(2, 12))
            for w in (t, a, b):
                w.bind('<Button-1>', lambda e, k=key: self.apply_preset(k))
            self.preset_tiles[key] = (t, a, b)
        self.preset_note = tk.Label(p, text='', font=('Segoe UI', 9), fg=DIM, bg=BG, anchor='w')
        self.preset_note.pack(fill='x', padx=30, pady=(0, 8))
        self._mark_presets()
        body = tk.Frame(p, bg=BG)
        body.pack(fill='both', expand=True, padx=28)
        body.columnconfigure(0, weight=1, uniform='c')
        body.columnconfigure(1, weight=1, uniform='c')
        left = self._card(body, _('TELA'))
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        self._check(left, _('Tela cheia'), 'fullscreen').pack(anchor='w', padx=12)
        self._note(left, _('Em tela cheia o jogo usa a resolução do monitor. Desligado, abre numa janela.')).pack(
            fill='x', padx=16, pady=(0, 8))
        self._combo(left, _('Tamanho da janela (sem tela cheia)'), core.WINDOW, 'window', tuple)
        self._combo(left, _('Sincronia vertical'), core.PRESENT, 'present')
        self._check(left, _('Mostrar FPS na tela (F10 também liga/desliga)'), 'show_fps').pack(anchor='w', padx=12,
                                                                                           pady=(4, 14))
        right = self._card(body, _('QUALIDADE E DESEMPENHO'))
        right.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        self._combo(right, _('Resolução que o jogo desenha'), core.RENDER, 'render', tuple)
        self._note(right, _('Menor = mais FPS. O emulador estica a imagem até o tamanho da tela.')).pack(
            fill='x', padx=16, pady=(0, 8))
        self._check(right, _('AMD FSR (ampliação com mais nitidez)'), 'fsr').pack(anchor='w', padx=12)
        self._check(right, _('Filtro de nitidez (RCAS)'), 'sharpen').pack(anchor='w', padx=12)
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill='x', padx=16, pady=(2, 8))
        tk.Label(row, text=_('Intensidade'), font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(side='left')
        self.sharp_lbl = tk.Label(row, text='', font=('Segoe UI', 9), fg=TEXT, bg=PANEL, width=5)
        self.sharp_lbl.pack(side='right')
        sc = ttk.Scale(row, from_=0, to=100, orient='horizontal')
        sc.set(max(0, min(100, 100 - self.s['sharpness'] / 20)))
        sc.pack(side='left', fill='x', expand=True, padx=8)

        def sharp(v):
            v = float(v)
            self.s['sharpness'] = int((100 - v) * 20)
            self.sharp_lbl.configure(text='%d%%' % v)
        sc.configure(command=sharp)
        sharp(sc.get())
        sc.bind('<ButtonRelease-1>', lambda e: self.save())
        self._check(right, _('Otimização extra de leitura da GPU (experimental)'), 'perf').pack(anchor='w', padx=12,
                                                                                          pady=(6, 0))
        self._note(right, _('Pode dar mais FPS em lutas pesadas. Se travar ou piorar, desligue.')).pack(
            fill='x', padx=16, pady=(0, 14))

    def apply_preset(self, key):
        self.s.update({k: list(v) if isinstance(v, list) else v for k, v in
                       next(p[3] for p in core.PRESETS if p[0] == key).items()})
        self.save()
        self._page_gfx(self.pages['gfx'])

    def _mark_presets(self):
        cur = core.current_preset(self.s)
        for key, (t, a, b) in self.preset_tiles.items():
            on = key == cur
            bg = PANEL2 if on else PANEL
            t.configure(bg=bg, highlightbackground=ACCENT if on else LINE)
            a.configure(bg=bg, fg=ACCENT2 if on else TEXT)
            b.configure(bg=bg)
        self.preset_note.configure(text='' if cur else _('Personalizado: os ajustes abaixo não batem com nenhuma '
                                                        'predefinição.'))

    # ------------------------------------------------------------ page: controls
    CTRL_TABS = [('pad', _('Gestos no controle')), ('touch', _('Touchpad e movimento no teclado')), ('buttons', _('Botões')),
                 ('options', _('Opções'))]
    # what the player does on the Xbox pad, in the order the game asks for it (keys.PAD_GESTURES + gestures.py)
    PAD_HELP = [
        ('View', _('Tocar o touchpad'), _('Toque rápido = tocar · segurar = apertar (drenar fontes de poder)')),
        ('View + ↑ ↓ ← →', _('Deslizar um dedo'), _('Abrir portas e grades, gestos de deslizar')),
        ('View + LB', 'Dedo 1', _('Encosta um dedo; o analógico esquerdo arrasta (scanner de digital)')),
        ('View + RB', 'Dedo 2', _('Encosta outro dedo; o analógico direito arrasta')),
        ('View + LT', _('Arrastar para cima e segurar'), _('Núcleo móvel: o dedo sobe e fica encostado enquanto segura; RT fica livre')),
        ('View + LB + RB', _('Dois polegares'), _('Os dois dedos apertando juntos')),
        ('View + A', _('Sacudir a lata'), _('"Chacoalhe a lata de spray"')),
        ('View + X  /  View + B', _('Virar o controle de lado'), _('Inclinar para a esquerda / direita')),
        ('View + Y', _('Modo lata de spray'), _('Liga/desliga: controle de lado e o analógico direito mira a tinta')),
    ]

    def _page_ctrl(self, p):
        top = tk.Frame(p, bg=BG)
        top.pack(fill='x', padx=28, pady=(20, 0))
        tk.Label(top, text=_('Controles'), font=('Bahnschrift SemiBold', 22), fg=TEXT, bg=BG).pack(side='left')
        self.ctrl_note = tk.Label(top, text='', font=('Segoe UI', 9), fg=DIM, bg=BG)
        self.ctrl_note.pack(side='right', pady=(10, 0))
        bar = tk.Frame(p, bg=BG)
        bar.pack(fill='x', padx=28, pady=(10, 0))
        tk.Frame(p, bg=LINE, height=1).pack(fill='x', padx=28)
        self.ctrl_tabs, self.ctrl_frames = {}, {}
        for key, name in self.CTRL_TABS:
            t = tk.Label(bar, text=name, font=('Segoe UI Semibold', 10), fg=DIM, bg=BG, padx=14, pady=8,
                         cursor='hand2')
            t.pack(side='left')
            t.bind('<Button-1>', lambda e, k=key: self.ctrl_show(k))
            self.ctrl_tabs[key] = t
        holder = tk.Frame(p, bg=BG)
        holder.pack(fill='both', expand=True)
        for key, _x in self.CTRL_TABS:
            self.ctrl_frames[key] = tk.Frame(holder, bg=BG)
        self.pad = PadView(self.ctrl_frames['buttons'], self)
        self.buttons_note = self._note(self.ctrl_frames['buttons'], '', BG, 900)
        self.buttons_note.pack(fill='x', padx=30, pady=(10, 0))
        self.pad.c.pack(pady=(4, 0))
        self._build_ctrl_options(self.ctrl_frames['options'])
        self.redraw_controls()
        self.ctrl_show('pad' if self.s['controller'] and self.kind in ('xbox', None) else 'touch')

    def ctrl_show(self, key):
        for k, f in self.ctrl_frames.items():
            f.pack_forget()
            self.ctrl_tabs[k].configure(fg=DIM, bg=BG)
        self.ctrl_frames[key].pack(fill='both', expand=True)
        self.ctrl_tabs[key].configure(fg=TEXT, bg=PANEL2)

    def _build_pad_gestures(self, f):
        for w in f.winfo_children():
            w.destroy()
        s = self.s
        box = tk.Frame(f, bg=BG)
        box.pack(fill='both', expand=True, padx=28, pady=14)
        if self.kind in ('playstation', 'other') or not s['controller']:
            tk.Label(box, text=_('Os gestos com View são só para controle do tipo Xbox.'), font=('Segoe UI Semibold', 12),
                     fg=TEXT, bg=BG).pack(anchor='w')
            self._note(box, (_('Controle atual: %s. ') % ', '.join(p['name'] for p in self.pad_list) if self.pad_list
                             else '') + (_('Com DualShock 4 / DualSense o jogo usa o touchpad e o sensor do próprio '
                                         'controle.') if self.kind == 'playstation' else _('Use os atalhos do teclado '
                                         '(aba ao lado).')) + _(' O tipo de controle muda em Opções.'), BG, 760).pack(
                anchor='w', pady=6)
            return
        top = tk.Frame(box, bg=BG)
        top.pack(fill='x')
        self._check(top, _('Gestos no controle, segurando View'), 'pad_gestures', BG,
                    lambda: (self.redraw_controls(), self.refresh())).pack(side='left')
        self._note(top, _('Os atalhos do teclado (aba ao lado) funcionam junto.'), BG).pack(side='right')
        if not s['pad_gestures']:
            self._note(box, _('\nDesligado: View só aperta o touchpad, e o resto fica no teclado.'), BG, 700).pack(
                anchor='w')
            return
        grid = tk.Frame(box, bg=BG)
        grid.pack(fill='x', pady=(10, 0))
        grid.columnconfigure(0, weight=1, uniform='g')
        grid.columnconfigure(1, weight=1, uniform='g')
        for n, (combo, title, sub) in enumerate(self.PAD_HELP):
            card = tk.Frame(grid, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            card.grid(row=n // 2, column=n % 2, sticky='nsew', padx=(0, 6) if n % 2 == 0 else (6, 0), pady=4)
            tk.Label(card, text=combo, font=('Segoe UI Semibold', 9), fg=XBOX_FG, bg=XBOX_BG, width=19, pady=3).pack(
                side='left', padx=(12, 10), pady=10)
            txt = tk.Frame(card, bg=PANEL)
            txt.pack(side='left', fill='x', expand=True, pady=6)
            tk.Label(txt, text=title, font=('Segoe UI Semibold', 10), fg=TEXT, bg=PANEL, anchor='w').pack(anchor='w')
            tk.Label(txt, text=sub, font=('Segoe UI', 8), fg=DIM, bg=PANEL, anchor='w', justify='left',
                     wraplength=330).pack(anchor='w')
        side = tk.Frame(box, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        side.pack(fill='x', pady=(10, 0))
        tk.Label(side, text=_('No modo lata de spray, o controle fica de lado para a'), font=('Segoe UI', 10), fg=TEXT,
                 bg=PANEL).pack(side='left', padx=(14, 8), pady=10)
        var = tk.StringVar(value=s['spray_side'])

        def side_changed():
            s['spray_side'] = var.get()
            self.save()
        for val, name in (('left', _('esquerda')), ('right', _('direita'))):
            self._radio(side, name, var, val, side_changed).pack(side='left', padx=4)
        self._note(side, _('Se o jogo pedir o outro lado, troque aqui.')).pack(side='right', padx=14)
        self._note(box, _('Só funcionam com a janela do jogo na frente. Combinações com View não disparam o botão '
                        'sozinho: View + LB não joga granada.'), BG, 900).pack(anchor='w', pady=(10, 0))

    def redraw_controls(self):
        self.pad.draw()
        self._build_pad_gestures(self.ctrl_frames['pad'])
        if getattr(self, 'gest_body', None):
            self._build_gest()
        self._build_touch(self.ctrl_frames['touch'])
        s = self.s
        if s['keyboard']:
            txt = (_('Clique num botão para trocar a tecla. Verde = botão do Xbox. A câmera no mouse liga com F7; '
                   'F6 (spray) e Delete (touchpad) usam o mouse para outra coisa.'))
        else:
            txt = (_('Verde = botão do Xbox equivalente. Jogando no controle não há nada para configurar aqui; '
                   'para jogar no teclado e mouse, ligue em "Opções".'))
        self.buttons_note.configure(text=txt)

    def _chip_btn(self, parent, text, cmd=None, fixed=False, bg=PANEL):
        b = tk.Label(parent, text=text, font=('Segoe UI Semibold', 9), fg=DIM if fixed else ACCENT2, bg=PANEL2,
                     padx=8, pady=3, cursor='arrow' if fixed else 'hand2', highlightthickness=1,
                     highlightbackground=LINE)
        if cmd:
            b.bind('<Button-1>', lambda e: cmd())
            b.bind('<Enter>', lambda e: b.configure(highlightbackground=ACCENT))
            b.bind('<Leave>', lambda e: b.configure(highlightbackground=LINE))
        return b

    def _build_touch(self, f):
        for w in f.winfo_children():
            w.destroy()
        s = self.s
        if self.kind == 'playstation':
            box = tk.Frame(f, bg=BG)
            box.pack(fill='both', expand=True, padx=28, pady=30)
            tk.Label(box, text=_('O jogo usa o touchpad e o giroscópio do seu controle.'), font=('Segoe UI Semibold', 12),
                     fg=TEXT, bg=BG).pack(anchor='w')
            self._note(box, _('Nada é emulado: deslizar, dois polegares, sacudir e virar a lata de spray funcionam '
                            'direto no DualShock 4 / DualSense. Se for jogar com outro controle, troque o tipo '
                            'de controle em Opções.'), BG, 700).pack(anchor='w', pady=6)
            return
        b = s['binds']
        left = tk.Frame(f, bg=BG)
        left.pack(side='left', fill='y', padx=(28, 0), pady=14)
        art, _x = pad_art.touchpad_art(300)
        self.imgs['touchart'] = ImageTk.PhotoImage(art)
        tk.Label(left, image=self.imgs['touchart'], bg=BG).pack()
        self._note(left, _('O controle do Xbox não tem touchpad nem sensor de movimento. Estes atalhos fazem o '
                         'que o jogo pede com eles. Funcionam junto com o controle.\n\n'
                         'View (Share) do controle também aperta o touchpad.\n\n'
                         'O mouse tem 3 modos, um de cada vez: Delete = touchpad, F6 = giroscópio (spray), '
                         'F7 = câmera. Aperte de novo para desligar.'), BG, 300).pack(anchor='w', pady=(14, 0))

        right = tk.Frame(f, bg=BG)
        right.pack(side='left', fill='both', expand=True, padx=(24, 28), pady=4)

        def section(text):
            tk.Label(right, text=text, font=('Bahnschrift', 10), fg=ACCENT2, bg=BG).pack(anchor='w', pady=(6, 1))

        def row(title, sub, chips):
            r = tk.Frame(right, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            r.pack(fill='x', pady=1)
            txt = tk.Frame(r, bg=PANEL)
            txt.pack(side='left', fill='x', expand=True, padx=12, pady=2)
            tk.Label(txt, text=title, font=('Segoe UI Semibold', 10), fg=TEXT, bg=PANEL, anchor='w').pack(anchor='w')
            tk.Label(txt, text=sub, font=('Segoe UI', 8), fg=DIM, bg=PANEL, anchor='w').pack(anchor='w')
            box = tk.Frame(r, bg=PANEL)
            box.pack(side='right', padx=10)
            for item in chips:
                if isinstance(item, str):
                    tk.Label(box, text=item, font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(side='left', padx=3)
                else:
                    self._chip_btn(box, *item).pack(side='left', padx=2)

        def key(i, prefix=''):
            return (prefix + (' / '.join(keys.label(k) for k in b[i]) or '—'), lambda: self.edit_binding(i))

        def group(ids, title):
            return lambda: BindDialog(self, title, ids)

        section('TOUCHPAD')
        row(_('Apertar o touchpad'), _('Drenar fontes de poder, ver detalhes, empurrar o carro'),
            [key('touchpad_center')] + (['ou', ('View', None, True)] if s['controller'] else []))
        row(_('Dois polegares'), _('Drenar com os dois polegares: segure os dois dedos e aperte o touchpad'),
            [(keys.label(b['touchpad_finger1'][0]) if b['touchpad_finger1'] else '—', None, True), '+',
             (keys.label(b['touchpad_finger2'][0]) if b['touchpad_finger2'] else '—', None, True), '+',
             (keys.label(b['touchpad_center'][0]) if b['touchpad_center'] else 'View', None, True)])
        row(_('Dedo 1 e Dedo 2 (segurar)'), _('Encosta um dedo; o analógico esquerdo/direito arrasta (scanner de digital)'),
            [key('touchpad_finger1', '1: '), key('touchpad_finger2', '2: ')])
        sw = ['touchpad_swipe_up', 'touchpad_swipe_down', 'touchpad_swipe_left', 'touchpad_swipe_right']
        row(_('Deslizar um dedo'), _('Abrir portas e grades'),
            [(' '.join('%s %s' % (a, keys.label(b[i][0]) if b[i] else '—') for a, i in zip('↑↓←→', sw)),
              group(sw, _('Deslizar um dedo')))])
        sw2 = ['touchpad_swipe2_up', 'touchpad_swipe2_down', 'touchpad_swipe2_left', 'touchpad_swipe2_right']
        row(_('Deslizar dois dedos'), _('Gestos com dois dedos'),
            [(' '.join('%s %s' % (a, keys.label(b[i][0]) if b[i] else '—') for a, i in zip('↑↓←→', sw2)),
              group(sw2, _('Deslizar dois dedos')))])
        row(_('Mouse como touchpad'), _('Mover = dedo · clique esquerdo = tocar · clique direito = apertar'),
            [(_('Delete liga/desliga'), None, True)])
        section(_('MOVIMENTO (LATA DE SPRAY)'))
        tilt = ['motion_tilt_left', 'motion_tilt_right']
        row(_('Virar o controle de lado'), _('"Segure o controle de lado" antes de pintar (segurar)'),
            [('← %s   → %s' % tuple(keys.label(b[i][0]) if b[i] else '—' for i in tilt),
              group(tilt, _('Virar o controle de lado')))])
        row(_('Sacudir a lata'), _('"Chacoalhe a lata de spray" (segurar)'), [key('motion_shake')])
        row(_('Mirar o spray'), _('F6: mover o mouse = mover o controle ("Girar" = girar)'),
            [(_('F6 liga/desliga'), None, True), key('mouse_gyro_roll_mode', _('Girar: '))])

    def _build_ctrl_options(self, f):
        body = tk.Frame(f, bg=BG)
        body.pack(fill='both', expand=True, padx=28, pady=16)
        body.columnconfigure(0, weight=1, uniform='c')
        body.columnconfigure(1, weight=1, uniform='c')
        left = self._card(body, _('CONTROLE'))
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        self._check(left, _('Controle ativado'), 'controller', PANEL,
                    lambda: (self.redraw_controls(), self.refresh())).pack(anchor='w', padx=12)
        self._note(left, _('Desligado, o jogo ignora o controle.'), wrap=380).pack(fill='x', padx=36, pady=(0, 6))
        c = self._combo(left, _('Tipo de controle'), core.PAD_MODES, 'pad_mode')
        c.bind('<<ComboboxSelected>>', lambda e: self.root.after(1, self.refresh), add='+')
        self.pad_det = self._note(left, '', wrap=380)
        self.pad_det.pack(fill='x', padx=16, pady=(0, 8))
        self._check(left, _('Botões do Xbox nas dicas do jogo'), 'xbox_prompts', PANEL,
                    lambda: (self.redraw_controls(), self.refresh())).pack(anchor='w', padx=12, pady=(4, 0))
        self._note(left, _('Troca os símbolos do PlayStation por A, B, X, Y, LB, RT… e o touchpad por View. Só vale '
                         'quando o controle for do tipo Xbox.'), wrap=380).pack(fill='x', padx=36, pady=(0, 12))
        right = self._card(body, _('TECLADO E MOUSE'))
        right.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        self._check(right, _('Jogar no teclado e mouse'), 'keyboard', PANEL,
                    lambda: (self.redraw_controls(), self.refresh())).pack(anchor='w', padx=12, pady=(6, 0))
        self._note(right, _('Liga as teclas da aba "Botões" (andar, pular, atirar…). Não precisa para usar só os '
                          'atalhos de touchpad e movimento.'), wrap=380).pack(fill='x', padx=36, pady=(0, 6))
        self._check(right, _('Câmera no mouse (liga com F7 no jogo)'), 'mouse_camera', PANEL,
                    self.redraw_controls).pack(anchor='w', padx=12, pady=(6, 0))
        row = tk.Frame(right, bg=PANEL)
        row.pack(fill='x', padx=36, pady=(2, 8))
        tk.Label(row, text=_('Sensibilidade'), font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(side='left')
        lbl = tk.Label(row, text='', font=('Segoe UI', 9), fg=TEXT, bg=PANEL, width=5)
        lbl.pack(side='right')
        sc = ttk.Scale(row, from_=0.2, to=3.0, orient='horizontal')
        sc.set(self.s['mouse_sens'])
        sc.pack(side='left', fill='x', expand=True, padx=8)

        def ch(v):
            self.s['mouse_sens'] = round(float(v), 2)
            lbl.configure(text='%.1f×' % float(v))
        sc.configure(command=ch)
        ch(sc.get())
        sc.bind('<ButtonRelease-1>', lambda e: self.save())
        foot = tk.Frame(right, bg=PANEL)
        foot.pack(fill='x', padx=16, pady=(4, 14))
        self._button(foot, _('Atalhos do emulador'), self.hotkeys).pack(side='left')
        self._button(foot, _('Restaurar teclas padrão'), self.reset_binds).pack(side='left', padx=8)

    def edit_binding(self, key):
        if key == 'move':
            BindDialog(self, _('Andar (analógico esquerdo)'), PadView.MOVE)
        elif key == 'camera':
            BindDialog(self, _('Câmera (analógico direito) sem o mouse'), PadView.CAM)
        else:
            if key in keys.BUTTONS and not self.s['keyboard']:
                if messagebox.askyesno(TITLE, _('Para trocar as teclas dos botões, ligue "Jogar no teclado e '
                                              'mouse". Ligar agora?')):
                    self.s['keyboard'] = True
                    self.save()
                    self.redraw_controls()
                    self.refresh()
                return
            badge, desc = keys.INPUTS[key]
            BindDialog(self, desc if desc.startswith(badge.split()[0]) else '%s — %s' % (badge, desc), [key])

    def set_bind(self, i, slot, k):
        """Puts key k on input i (slot 0/1); a key used elsewhere moves here. Returns a note."""
        b = self.s['binds']
        note = None
        if k:
            for other, ks in b.items():
                if other != i and k in ks:
                    ks.remove(k)
                    note = _('%s foi tirada de "%s".') % (keys.label(k), keys.INPUTS[other][1])
        cur = [x for x in b[i] if x != k]
        if slot < len(cur):
            if k:
                cur[slot] = k
            else:
                cur.pop(slot)
        elif k:
            cur.append(k)
        b[i] = cur[:2]
        self.save()
        self.redraw_controls()
        return note

    def reset_binds(self):
        if messagebox.askyesno(TITLE, _('Voltar todas as teclas (touchpad, movimento e teclado) para o padrão?')):
            self.s['binds'] = {k: list(v) for k, v in keys.DEFAULT_BINDS.items()}
            self.s['mouse_camera'], self.s['mouse_sens'] = True, 1.0
            self.save()
            self.redraw_controls()

    def hotkeys(self):
        txt = '\n'.join('%s  —  %s' % (' + '.join(keys.label(x.strip()) for x in k.split(',')), d)
                        for k, d in keys.HOTKEYS)
        messagebox.showinfo(_('Atalhos do emulador'), _('Durante o jogo:\n\n') + txt)

    # ------------------------------------------------------------ page: advanced
    def _page_adv(self, p):
        self._header(p, _('Avançado'), _('Biblioteca, atalhos, saves e manutenção.'))
        body = tk.Frame(p, bg=BG)
        body.pack(fill='both', expand=True, padx=28)
        body.columnconfigure(0, weight=1, uniform='c')
        body.columnconfigure(1, weight=1, uniform='c')
        left = self._card(body, _('ATALHOS'))
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        for text, cmd, note in (
                (_('Adicionar à Steam'), self.add_steam, _('Põe o jogo na biblioteca da Steam com capa, abrindo direto '
                                                      'pelo launcher (Steam Input desligado).')),
                (_('Atalho na área de trabalho'), self.desktop, _('Abre o jogo direto, sem passar pelo launcher.'))):
            self._button(left, text, cmd).pack(anchor='w', padx=16, pady=(4, 2))
            self._note(left, note).pack(fill='x', padx=16, pady=(0, 10))
        right = self._card(body, _('SAVES E MANUTENÇÃO'))
        right.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        for text, cmd, note in (
                (_('Abrir pasta dos saves'), lambda: self._open(core.SAVES), 'emu\\user\\home\\1000\\savedata\\CUSA00004'),
                (_('Ver log da última execução'), self.open_log, _('Mande este arquivo se algo der errado.')),
                (_('Limpar cache de shaders'), self.clear_cache, _('Use se a imagem ficar estranha depois de trocar o '
                                                             'emulador. Os primeiros minutos vão engasgar.'))):
            self._button(right, text, cmd).pack(anchor='w', padx=16, pady=(4, 2))
            self._note(right, note).pack(fill='x', padx=16, pady=(0, 10))
        emu = self._card(body, _('EMULADOR (SHADPS4)'))
        emu.grid(row=1, column=0, sticky='nsew', padx=(0, 10), pady=(16, 0))
        self.emu_note = self._note(emu, '')
        self.emu_note.pack(fill='x', padx=16)
        row = tk.Frame(emu, bg=PANEL)
        row.pack(fill='x', padx=16, pady=(8, 14))
        self._button(row, _('Baixar / atualizar emulador'), self.install_emulator).pack(side='left')
        self._button(row, _('Código-fonte'), lambda: os.startfile(emulator.SOURCE)).pack(side='left', padx=8)
        about = self._card(body, _('LAUNCHER'))
        about.grid(row=1, column=1, sticky='nsew', padx=(10, 0), pady=(16, 0))
        row = tk.Frame(about, bg=PANEL)
        row.pack(fill='x', padx=16)
        tk.Label(row, text=_('Idioma do launcher'), font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(side='left')
        names = [n for _x, n in i18n.LANGS]
        cb = ttk.Combobox(row, values=names, state='readonly', font=('Segoe UI', 10), width=22)
        cb.set(dict(i18n.LANGS).get(i18n.current(), names[0]))
        cb.pack(side='left', padx=8)
        cb.bind('<<ComboboxSelected>>', lambda e: self.set_ui_lang(i18n.LANGS[cb.current()][0]))
        row = tk.Frame(about, bg=PANEL)
        row.pack(fill='x', padx=16, pady=(10, 4))
        self._button(row, _('Sobre e créditos'), self.about).pack(side='left')
        self._note(about, _('Projeto de fã, não oficial. Não é afiliado à Sony Interactive Entertainment, à Sucker '
                          'Punch Productions nem à equipe do shadPS4. Nenhum arquivo do jogo vem com o launcher.'),
                   wrap=420).pack(fill='x', padx=16, pady=(4, 14))

    def install_emulator(self):
        if self.busy:
            return
        cur = emulator.installed_version()
        try:
            tag = emulator.latest()[0]
        except Exception as e:
            messagebox.showerror(TITLE, _('Não deu para consultar os releases do shadPS4: %s') % e)
            return
        if emulator.installed() and cur == tag:
            if not messagebox.askyesno(TITLE, _('O shadPS4 %s já é o mais novo. Baixar de novo?') % tag):
                return
        elif not messagebox.askokcancel(TITLE, _('Baixar o shadPS4 %s (cerca de 60 MB) de %s?\n\nEle é software livre '
                                               '(GPL-2.0) e fica na pasta emu.') % (tag, emulator.SOURCE)):
            return
        self.set_busy(True, _('BAIXANDO…'))

        def work():
            try:
                t = emulator.install(lambda d, n: self.progress(100 * d / max(n, 1), _('shadPS4: %d de %d MB')
                                                                 % (d >> 20, n >> 20)))
                self.root.after(0, lambda: (self.set_busy(False), self.status.configure(text=_('shadPS4 %s instalado')
                                                                                             % t), self.refresh()))
            except Exception as e:
                core.log(traceback.format_exc())
                msg = str(e)
                self.root.after(0, lambda: (self.set_busy(False), self.status.configure(text=''),
                                            messagebox.showerror(TITLE, msg)))
        threading.Thread(target=work, daemon=True).start()

    def import_pack(self):
        d = filedialog.askdirectory(title=_('Pasta da versão americana (CUSA00223) ou de um port PT-BR pronto'))
        if not d:
            return
        try:
            kind = packs.import_from(os.path.normpath(d), 'ptbr')
        except RuntimeError:
            messagebox.showerror(TITLE, _('Não achei os arquivos. Escolha a pasta CUSA00223 (com art\\cache\\'
                                        'lang_brazilian_*) ou a de um port com lang_portuguese_* e psarc\\'
                                        'portuguese_*.'))
            return
        except OSError as e:
            messagebox.showerror(TITLE, str(e))
            return
        note = '' if kind == 'port' else (_('\n\nOs textos vieram direto da versão americana, sem adaptação: '
                                          'se algum menu aparecer em inglês, use um port pronto.'))
        messagebox.showinfo(TITLE, _('Português do Brasil importado.') + note)
        self.refresh()

    def set_ui_lang(self, code):
        if code == i18n.current():
            return
        self.s['ui_lang'] = code
        self.save()
        if messagebox.askyesno(TITLE, _('Reiniciar o launcher agora para trocar o idioma?')):
            subprocess.Popen([sys.executable] + ([] if getattr(sys, 'frozen', False) else [os.path.abspath(__file__)]))
            self.root.destroy()

    def about(self):
        messagebox.showinfo('%s %s' % (APP_NAME, APP_VERSION), _('Launcher não oficial para inFAMOUS Second Son no PC, feito por fãs.\n\n'
                                   'inFAMOUS é marca da Sony Interactive Entertainment; o jogo é da Sucker Punch '
                                   'Productions. Você precisa ter a sua própria cópia do jogo.\n\n'
                                   'Emulador: shadPS4 (GPL-2.0) e o build "Infamous" de rayhlancaner-png.\n'
                                   'Cheats: GoldHEN Cheat Repository. Patches: shadps4-emu/ps4_cheats.\n'
                                   'Créditos completos no arquivo CREDITS.md.'))

    # ------------------------------------------------------------ small widgets
    def _switch(self, parent, on, cmd, bg=PANEL, enabled=True):
        """A sliding on/off switch; cmd(new_state)."""
        c = tk.Canvas(parent, width=42, height=22, bg=bg, highlightthickness=0, cursor='hand2' if enabled else '')
        state = {'on': bool(on)}

        def draw():
            c.delete('all')
            v = state['on']
            col = (ACCENT if v else '#3a3f4b') if enabled else '#262a33'
            round_rect(c, 1, 1, 41, 21, 10, fill=col, outline='')
            x = 30 if v else 12
            c.create_oval(x - 7, 4, x + 7, 18, fill='white' if enabled else '#4a505d', outline='')

        def click(e):
            state['on'] = not state['on']
            draw()
            cmd(state['on'])
        draw()
        if enabled:
            c.bind('<Button-1>', click)
        return c

    def _toggle_list(self, key, item, on):
        lst = [x for x in self.s[key] if x != item]
        if on:
            lst.append(item)
        self.s[key] = lst
        self.save()

    # ------------------------------------------------------------ page: game gestures
    # (title, the game's own prompt, drawing, pad gesture outputs, keyboard combos, PlayStation)
    GUIDE = [
        (_('Drenar poder'), _('Mantenha pressionado o touch pad para drenar chaminés, neon, telas ou inimigos '
                         'derrotados.'), 'hold', ['view_hold'], [['touchpad_center']], _('Segurar o touchpad')),
        (_('Dois polegares'), _('Mantenha pressionado o touch pad com ambos os polegares (fontes de concreto, '
                           'núcleos e fontes grandes).'), 'two', ['touchpad_center'],
         [['touchpad_finger1', 'touchpad_finger2', 'touchpad_center']], _('Os dois polegares apertando')),
        (_('Tocar: detalhes'), _('Pressione o touch pad para obter detalhes.'), 'tap', ['view_tap'],
         [['touchpad_center']], _('Apertar o touchpad')),
        (_('Deslizar para abrir'), _('Deslize o dedo no touch pad para abrir a porta (portas, grades, portões).'),
         'swipe', ['touchpad_swipe_up', 'touchpad_swipe_down', 'touchpad_swipe_left', 'touchpad_swipe_right'],
         [['touchpad_swipe_up'], ['touchpad_swipe_down'], ['touchpad_swipe_left'], ['touchpad_swipe_right']],
         _('Deslizar um dedo')),
        (_('Núcleo móvel'), _('Tente explodir o núcleo enquanto o segura para cima (o dedo sobe e fica '
                              'encostado).'), 'dragup', ['drag_lt'],
         [['touchpad_finger1', '!' + _('analógico esq. ↑')]], _('Arrastar de baixo para cima e manter')),
        (_('Scanner de digital'), _('Coloque o dedo no scanner digital (postos de controle do D.U.P.).'), 'finger',
         ['touchpad_finger1'], [['touchpad_finger1']], _('Encostar o dedo e arrastar')),
        (_('Empurrar o carro'), _('Mantenha pressionado o touch pad para mover o carro.'), 'hold', ['view_hold'],
         [['touchpad_center']], _('Segurar o touchpad')),
        (_('Lata em pé: mirar'), _('Segure o controle sem fio com uma mão no sentido vertical e mova para pintar.'),
         'vertical', ['spray'], [['!F6 + mouse']], _('Controle em pé; mover = mirar')),
        (_('Sacudir a lata'), _('Sacuda.'), 'shake', ['motion_shake'], [['motion_shake']], _('Sacudir o controle')),
        (_('Lata de lado'), _('Segure o controle sem fio de lado.'), 'sideways', ['motion_tilt_left', 'motion_tilt_right'],
         [['motion_tilt_left'], ['motion_tilt_right']], _('Virar o controle de lado')),
    ]

    def _pad_text(self, outs):
        if not self.s['pad_gestures']:
            return 'View' if outs[0] in ('view_hold', 'view_tap') else _('desligado')
        labels = {o: lab for o, _x, lab, _x in keys.PAD_GESTURES}
        fixed = {'view_hold': _('View (segurar)'), 'view_tap': _('View (toque)'),
                 'drag_lt': _('View + LT (segurar); RT livre'),
                 'spray': labels['leftjoystick_halfmode'] + _(', analógico dir. mira')}
        texts = [fixed.get(o) or labels.get(o, '—') for o in outs]
        if len(texts) > 1 and all(t.startswith('View + ') for t in texts):
            return 'View + ' + ' / '.join(t[7:] for t in texts)
        return texts[0]

    def _kb_text(self, combos):
        b = self.s['binds']
        out = []
        for combo in combos:
            out.append(' + '.join(i[1:] if i.startswith('!') else (keys.label(b[i][0]) if b.get(i) else '—')
                                  for i in combo))
        return '  '.join(out)

    def _draw_gesture(self, c, kind):
        """Small picture of the touch pad / controller for a gesture, on a 128x78 canvas."""
        fing = dict(fill=ACCENT2, outline='white', width=2)
        arrow = dict(fill=TEXT, width=2, arrow='last', arrowshape=(7, 8, 3))
        if kind in ('hold', 'tap', 'two', 'swipe', 'finger', 'dragup'):
            round_rect(c, 10, 12, 118, 70, 12, fill='#262a34', outline=LINE)
            c.create_rectangle(30, 6, 98, 9, fill=ACCENT, outline='')  # light bar
            if kind == 'two':
                for x in (40, 88):
                    c.create_oval(x - 9, 32, x + 9, 50, **fing)
                c.create_text(64, 41, text='+', fill=TEXT, font=('Segoe UI Semibold', 12))
            elif kind == 'swipe':
                c.create_oval(55, 50, 73, 66, **fing)
                c.create_line(64, 48, 64, 20, **arrow)
            elif kind == 'dragup':
                c.create_oval(56, 58, 72, 70, outline=DIM, width=1, dash=(2, 2))  # where it starts
                c.create_line(64, 56, 64, 30, **arrow)
                c.create_oval(55, 14, 73, 30, **fing)
                c.create_oval(50, 9, 78, 35, outline=ACCENT2, width=3)
                c.create_text(100, 22, text=_('manter'), fill=DIM, font=('Segoe UI', 7))
            elif kind == 'finger':
                c.create_oval(37, 32, 55, 50, **fing)
                c.create_line(58, 41, 84, 41, **arrow)
                c.create_line(46, 30, 46, 18, **arrow)
            else:
                c.create_oval(55, 32, 73, 50, **fing)
                if kind == 'tap':
                    c.create_oval(48, 25, 80, 57, outline=ACCENT2, width=1)
                else:
                    c.create_oval(50, 27, 78, 55, outline=ACCENT2, width=3)
                    c.create_text(100, 62, text=_('segurar'), fill=DIM, font=('Segoe UI', 7))
            return
        # the controller seen from above, as a rounded body
        if kind == 'vertical':
            round_rect(c, 50, 6, 78, 72, 10, fill='#262a34', outline=LINE)
            c.create_oval(58, 14, 70, 26, fill=ACCENT, outline='')
            for i, y in enumerate((30, 40, 50)):
                c.create_line(86, y, 100 + i * 4, y - 6, fill=ACCENT2, width=2)
        elif kind == 'shake':
            round_rect(c, 34, 24, 94, 56, 12, fill='#262a34', outline=LINE)
            c.create_line(64, 20, 64, 4, **arrow)
            c.create_line(64, 60, 64, 76, **arrow)
            for x in (22, 106):
                c.create_line(x, 30, x, 50, fill=ACCENT2, width=2)
        else:  # sideways
            c.create_polygon(30, 48, 82, 20, 98, 46, 46, 74, smooth=True, fill='#262a34', outline=LINE)
            c.create_arc(14, 6, 114, 86, start=20, extent=60, style='arc', outline=ACCENT2, width=2)

    def _page_gest(self, p):
        self._header(p, _('Gestos do jogo'), _('Tudo o que o jogo pede no touchpad e no sensor de movimento, com as frases '
                                          'dele e o que apertar no seu controle e no teclado.'))
        self.gest_body = self._scrollable(p)
        self._build_gest()

    def _scrollable(self, parent):
        """A frame that scrolls with the mouse wheel when its content is taller than the window."""
        holder = tk.Frame(parent, bg=BG)
        holder.pack(fill='both', expand=True, padx=(28, 8))
        c = tk.Canvas(holder, bg=BG, highlightthickness=0)
        bar = ttk.Scrollbar(holder, orient='vertical', command=c.yview, style='Dark.Vertical.TScrollbar')
        inner = tk.Frame(c, bg=BG)
        win = c.create_window(0, 0, window=inner, anchor='nw')
        c.configure(yscrollcommand=bar.set)

        def layout(e=None):
            c.itemconfigure(win, width=c.winfo_width())
            c.configure(scrollregion=(0, 0, 0, inner.winfo_reqheight()))
            if inner.winfo_reqheight() > c.winfo_height():
                bar.pack(side='right', fill='y')
            else:
                bar.pack_forget()
                c.yview_moveto(0)
        c.bind('<Configure>', layout)
        inner.bind('<Configure>', layout)
        wheel = lambda e: c.yview_scroll(-1 if e.delta > 0 else 1, 'units') if bar.winfo_ismapped() else None
        holder.bind('<Enter>', lambda e: self.root.bind_all('<MouseWheel>', wheel))
        holder.bind('<Leave>', lambda e: self.root.unbind_all('<MouseWheel>'))
        c.pack(side='left', fill='both', expand=True)
        return inner

    def _build_gest(self):
        f = self.gest_body
        for w in f.winfo_children():
            w.destroy()
        kind = self.kind
        for i in range(3):
            f.columnconfigure(i, weight=1, uniform='g')
        rows = [('Xbox', XBOX_FG, kind in ('xbox', None) and self.s['controller']),
                (_('Teclado'), ACCENT2, kind != 'playstation'),
                ('PS', '#8fb4ff', kind == 'playstation')]
        for n, (title, prompt, draw, outs, combos, ps) in enumerate(self.GUIDE):
            card = tk.Frame(f, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            card.grid(row=n // 3, column=n % 3, sticky='nsew', padx=(0 if n % 3 == 0 else 5, 0 if n % 3 == 2 else 5),
                      pady=5)
            top = tk.Frame(card, bg=PANEL)
            top.pack(fill='x', padx=10, pady=(10, 4))
            c = tk.Canvas(top, width=128, height=78, bg=PANEL, highlightthickness=0)
            c.pack(side='left')
            self._draw_gesture(c, draw)
            txt = tk.Frame(top, bg=PANEL)
            txt.pack(side='left', fill='both', expand=True, padx=(8, 0))
            tk.Label(txt, text=title, font=('Segoe UI Semibold', 11), fg=TEXT, bg=PANEL, anchor='w').pack(anchor='w')
            tk.Label(txt, text='“%s”' % prompt, font=('Segoe UI', 8, 'italic'), fg=DIM, bg=PANEL, anchor='w',
                     justify='left', wraplength=150).pack(anchor='w')
            for (name, col, active), value in zip(rows, (self._pad_text(outs), self._kb_text(combos), ps)):
                r = tk.Frame(card, bg=PANEL)
                r.pack(fill='x', padx=10, pady=1)
                tk.Label(r, text=name, font=('Segoe UI Semibold', 8), fg=col if active else '#4a505d', bg=PANEL,
                         width=7, anchor='w').pack(side='left')
                tk.Label(r, text=value, font=('Segoe UI Semibold', 9), fg=TEXT if active else '#4a505d',
                         bg=PANEL2 if active else PANEL, padx=6, pady=1).pack(side='left')
            tk.Frame(card, bg=PANEL, height=8).pack()

    # ------------------------------------------------------------ page: mods
    def _page_mods(self, p):
        self._header(p, _('Mods'), _('Ligue e desligue sem mexer nos arquivos do jogo. Vale na próxima vez que o jogo abrir.'))
        self.mods_body = tk.Frame(p, bg=BG)
        self.mods_body.pack(fill='both', expand=True, padx=28)
        self._build_mods()

    def _mod_row(self, parent, title, desc, on, cmd, enabled=True, extra=None):
        r = tk.Frame(parent, bg=PANEL2)
        r.pack(fill='x', pady=2)
        self._switch(r, on, cmd, PANEL2, enabled).pack(side='left', padx=(10, 10), pady=8)
        t = tk.Frame(r, bg=PANEL2)
        t.pack(side='left', fill='x', expand=True, pady=4)
        tk.Label(t, text=title, font=('Segoe UI Semibold', 10), fg=TEXT if enabled else DIM, bg=PANEL2,
                 anchor='w').pack(anchor='w')
        if desc:
            tk.Label(t, text=desc, font=('Segoe UI', 8), fg=DIM, bg=PANEL2, anchor='w', justify='left',
                     wraplength=330).pack(anchor='w')
        if extra:
            extra(r)
        return r

    def _build_mods(self):
        f = self.mods_body
        for w in f.winfo_children():
            w.destroy()
        f.columnconfigure(0, weight=1, uniform='m')
        f.columnconfigure(1, weight=1, uniform='m')
        left = self._card(f, _('PATCHES DO JOGO'))
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 10))
        box = tk.Frame(left, bg=PANEL)
        box.pack(fill='x', padx=12)
        plist = mods.patches()
        if not plist:
            self._note(box, _('Os patches não vêm com o launcher: aperte "Atualizar patches" para baixar.'),
                       wrap=400).pack(anchor='w', padx=4)
        res = [x for x in plist if x['res']]
        for x in plist:
            if not x['res']:
                self._mod_row(box, x['title'], x['desc'], x['name'] in self.s['patches_on'],
                              lambda on, n=x['name']: self._toggle_list('patches_on', n, on))
        if res:
            opts = [(_('Do jogo (1080p)'), '')] + [('%d × %d' % x['res'], x['name']) for x in res]
            cur = next((x['name'] for x in res if x['name'] in self.s['patches_on']), '')
            tk.Label(left, text=_('Resolução que o próprio jogo usa'), font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(
                anchor='w', padx=16, pady=(10, 2))
            cb = ttk.Combobox(left, values=[a for a, _x in opts], state='readonly', font=('Segoe UI', 10))
            cb.set(next(a for a, v in opts if v == cur))
            cb.pack(fill='x', padx=16)

            def res_changed(e):
                pick = dict(opts)[cb.get()]
                self.s['patches_on'] = [n for n in self.s['patches_on'] if n not in {x['name'] for x in res}] + \
                    ([pick] if pick else [])
                self.save()
            cb.bind('<<ComboboxSelected>>', res_changed)
            self._note(left, _('Diferente da resolução em Gráficos (a do emulador): esta muda a do jogo. Acima de 1080p '
                             'pesa bastante.'), wrap=400).pack(fill='x', padx=16, pady=(2, 6))
        foot = tk.Frame(left, bg=PANEL)
        foot.pack(fill='x', padx=16, pady=(4, 14))
        self._button(foot, _('Atualizar patches'), self.update_patches).pack(side='left')
        self._note(foot, _('Fonte: shadps4-emu/ps4_cheats'), wrap=200).pack(side='left', padx=10)

        right = self._card(f, _('MODS DE ARQUIVOS'))
        right.grid(row=0, column=1, sticky='nsew', padx=(10, 0))
        box = tk.Frame(right, bg=PANEL)
        box.pack(fill='x', padx=12)
        kind = self.kind
        ctrl_note = _('Só com controle Xbox (agora: %s)') % {'xbox': _('ativo'), 'playstation': _('desligado, controle '
                                                          'PlayStation'), 'other': _('desligado, outro controle')}.get(
            kind, _('pergunta ao abrir o jogo'))
        self._mod_row(box, _('Botões do Xbox nas dicas'), ctrl_note, self.s['xbox_prompts'],
                      lambda on: (self.s.update(xbox_prompts=on), self.save(), self.redraw_controls()))
        self._mod_row(box, _('Gestos com View no controle'), ctrl_note, self.s['pad_gestures'],
                      lambda on: (self.s.update(pad_gestures=on), self.save(), self.redraw_controls()))
        text = next(t for t in core.TEXTS if t[0] == self.s['text'])
        self._mod_row(box, _('Tradução e dublagem'), _('Agora: %s. Muda em "Idioma e dublagem".') % text[1], True,
                      lambda on: None, enabled=False)
        user = mods.extras()
        tk.Label(right, text=_('SEUS MODS'), font=('Bahnschrift', 9), fg=DIM, bg=PANEL).pack(anchor='w', padx=16,
                                                                                          pady=(10, 2))
        box = tk.Frame(right, bg=PANEL)
        box.pack(fill='x', padx=12)
        packed = {f: r for f, r in mods.zip_mods().items() if r['kind'] != 'files'}
        if not user and not packed:
            self._note(box, _('Nenhum ainda. Arraste um mod em .zip para a pasta mods (botão abaixo): ele é instalado '
                              'sozinho, e sai quando você tira o .zip.'), wrap=400).pack(anchor='w', padx=4)
        kinds = {'dub': _('dublagem e legendas'), 'cheats': _('cheats'), 'patches': _('patches'), 'art': _('artes')}
        for f, r in sorted(packed.items()):
            row = tk.Frame(box, bg=PANEL2)
            row.pack(fill='x', pady=2)
            tk.Label(row, text='\u2714', font=('Segoe UI Symbol', 10), fg=OK, bg=PANEL2).pack(side='left', padx=(14, 10),
                                                                                           pady=8)
            tk.Label(row, text=r['name'], font=('Segoe UI Semibold', 10), fg=TEXT, bg=PANEL2).pack(side='left')
            tk.Label(row, text=' · ' + kinds.get(r['kind'], r['kind']) + ' · ' + f, font=('Segoe UI', 8), fg=DIM,
                     bg=PANEL2).pack(side='left')
        for m in user:
            desc = (m['desc'] + ' · ' if m['desc'] else '') + _('%d arquivo(s)') % len(m['files']) + \
                (' · ' + m['author'] if m['author'] else '')
            self._mod_row(box, m['name'], desc, m['dir'] in self.s['mods_on'],
                          lambda on, d=m['dir']: self._toggle_list('mods_on', d, on),
                          extra=lambda r, d=m['dir']: self._chip_btn(r, _('Remover'), lambda: self.remove_mod(d)).pack(
                              side='right', padx=8))
        foot = tk.Frame(right, bg=PANEL)
        foot.pack(fill='x', padx=16, pady=(8, 14))
        self._button(foot, _('Instalar .zip…'), self.install_mod).pack(side='left')
        self._button(foot, _('Abrir pasta'), lambda: self._open(mods.DROP)).pack(side='left', padx=8)

    def update_patches(self):
        self.status.configure(text=_('Baixando patches…'))

        def work():
            try:
                n = mods.update_patches()
                self.root.after(0, lambda: (self.status.configure(text=_('%d patches disponíveis') % n),
                                            self._build_mods()))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda: (self.status.configure(text=''),
                                            messagebox.showerror(TITLE, _('Não deu para baixar: ') + msg)))
        threading.Thread(target=work, daemon=True).start()

    def install_mod(self):
        src = filedialog.askopenfilename(title=_('Instalar mod'), filetypes=[(_('Mod em .zip'), '*.zip')])
        if not src:
            return
        try:
            mods.add_zip(os.path.normpath(src))
        except OSError as e:
            messagebox.showerror(TITLE, str(e))
            return
        done = sync_mods(self.s)
        bad = [why for f, why in done if why.startswith('erro')]
        if bad:
            messagebox.showerror(TITLE, bad[0])
        else:
            self.status.configure(text=_('Mod "%s" instalado e ligado') % os.path.basename(src))
        self._build_mods()
        self.refresh()

    def remove_mod(self, name):
        if messagebox.askyesno(TITLE, _('Apagar o mod "%s"? A pasta dele (e o .zip, se veio de um) é removida.')
                               % name):
            mods.remove(name)
            self._toggle_list('mods_on', name, False)
            self._build_mods()

    # ------------------------------------------------------------ page: cheats
    def _page_cheats(self, p):
        self._header(p, _('Cheats'), _('Ligue antes de jogar ou com o jogo aberto: com o launcher aberto, muda na hora. '
                                  'Os saves têm backup automático antes de cada sessão.'))
        self.cheat_status = tk.Label(p, text='', font=('Segoe UI Semibold', 10), fg=TEXT, bg=BG, anchor='w')
        self.cheat_status.pack(fill='x', padx=30, pady=(0, 8))
        self.cheat_body = tk.Frame(p, bg=BG)
        self.cheat_body.pack(fill='both', expand=True, padx=28)
        self.cheat_list = None

    def _set_session(self, sess):
        self.session = sess
        if self.page == 'cheats':
            self.refresh_cheats()

    def refresh_cheats(self):
        if self.cheat_list is None:
            self.cheat_list = cheats.load(core.eboot_path(self.s) or '')
        running = self.session is not None
        self.cheat_status.configure(
            text=_('● Jogo aberto: as mudanças entram na hora.') if running else
            _('○ Jogo fechado: os cheats ligados entram quando o jogo abrir.'), fg=OK if running else DIM)
        f = self.cheat_body
        for w in f.winfo_children():
            w.destroy()
        f.columnconfigure(0, weight=1, uniform='c')
        f.columnconfigure(1, weight=1, uniform='c')
        if not self.cheat_list:
            box = tk.Frame(f, bg=BG)
            box.grid(row=0, column=0, columnspan=2, sticky='w')
            self._note(box, _('A lista de cheats não vem com o launcher. Baixe a do GoldHEN Cheat Repository:'), BG,
                       700).pack(anchor='w')
            self._button(box, _('Baixar cheats'), self.download_cheats).pack(anchor='w', pady=8)
        for n, c in enumerate(self.cheat_list):
            card = tk.Frame(f, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            card.grid(row=n // 2, column=n % 2, sticky='nsew', padx=(0, 6) if n % 2 == 0 else (6, 0), pady=4)
            if c['kind'] == 'toggle':
                self._switch(card, c['id'] in self.s['cheats_on'], lambda on, c=c: self.set_cheat(c, on), PANEL,
                             c['ok']).pack(side='left', padx=12, pady=12)
            else:
                b = self._chip_btn(card, _('Aplicar'), (lambda c=c: self.apply_once(c)) if c['ok'] and running else None,
                                   fixed=not (c['ok'] and running))
                b.pack(side='left', padx=(12, 6), pady=12)
            t = tk.Frame(card, bg=PANEL)
            t.pack(side='left', fill='x', expand=True, pady=6)
            tk.Label(t, text=c['name'], font=('Segoe UI Semibold', 10), fg=TEXT if c['ok'] else DIM, bg=PANEL,
                     anchor='w').pack(anchor='w')
            note = c['desc']
            if not c['ok']:
                note = _('Bloqueado: não confere com o seu eboot (feito para outra versão).')
            elif c['kind'] == 'once' and not running:
                note += _(' Abra o jogo e carregue um save para aplicar.')
            tk.Label(t, text=note, font=('Segoe UI', 8), fg=DIM if c['ok'] else BAD, bg=PANEL, anchor='w',
                     justify='left', wraplength=360).pack(anchor='w')
        credits = sorted({c['credits'] for c in self.cheat_list if c['credits']})
        foot = tk.Frame(f, bg=BG)
        foot.grid(row=(len(self.cheat_list) + 1) // 2 + 1, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        self._note(foot, _('Cada cheat é conferido byte a byte com o eboot do seu jogo antes de ser liberado. '
                         'Fonte: GoldHEN Cheat Repository') + (' (%s)' % ', '.join(credits) if credits else '') + '.',
                   BG, 700).pack(side='left')
        self._button(foot, _('Abrir pasta de cheats'), lambda: self._open(cheats.DIR)).pack(side='right')

    def download_cheats(self):
        self.status.configure(text=_('Baixando cheats…'))

        def work():
            try:
                n = cheats.download()
                self.cheat_list = None
                self.root.after(0, lambda: (self.status.configure(text=_('%d arquivo(s) de cheats') % n),
                                            self.refresh_cheats()))
            except Exception as e:
                msg = str(e)
                self.root.after(0, lambda: (self.status.configure(text=''), messagebox.showerror(TITLE, msg)))
        threading.Thread(target=work, daemon=True).start()

    def set_cheat(self, c, on):
        self._toggle_list('cheats_on', c['id'], on)
        if self.session:
            self.session.set_cheat(c, on)
            self.status.configure(text='%s: %s' % (c['name'], _('ligado') if on else _('desligado')))

    def apply_once(self, c):
        if self.session:
            self.session.set_cheat(c, True)
            self.status.configure(text=_('%s: aplicado') % c['name'])

    # ------------------------------------------------------------ state
    def refresh(self):
        info, msg = core.detect(self.s['folder'])
        pads = self.pad_list = controllers.detect()
        kind = pad_kind(self.s, pads)
        if kind != self.kind:
            self.kind = kind
            self.redraw_controls()
        text = next(t for t in core.TEXTS if t[0] == self.s['text'])
        voice = next(v for v in core.VOICES if v[0] == self.s['voice'])
        if self.page == 'play':
            self._draw_play()
        self.side_time.configure(text=short_time(core.play_time()))
        for k, r in self.voice_radios.items():
            r.configure(state='normal' if core.voice_available(info, k) else 'disabled')
        for k, r in self.text_radios.items():
            r.configure(state='normal' if core.text_available(info, k) else 'disabled')
        self.pack_note.configure(text=_('Português do Brasil: ') + (
            'instalado.' if core.pack_ok('ptbr') else _('não incluído. Ele vem da versão americana do jogo '
            '(CUSA00223), que não pode ser distribuída: importe da sua cópia ou de um port já pronto.')))
        self.lang_sum.configure(text=_('Você vai ler em %s e ouvir em %s.') % (text[1], voice[1].split(' — ')[0]))
        names = ', '.join(p['name'] for p in pads)
        kname = {'xbox': _('tipo Xbox'), 'playstation': _('tipo PlayStation'),
                 'other': _('outro tipo')}.get(kind, _('tipo não identificado'))
        self.ctrl_note.configure(text=('%s · %s' % (names, kname)) if pads else _('Nenhum controle conectado agora'))
        self.pad_det.configure(text=(_('Detectado agora: %s (%s).') % (names, kname) if pads else
                                     _('Nenhum controle conectado agora.')) +
                               (_(' Se não der para identificar, o launcher pergunta antes de abrir o jogo.')
                                if self.s['pad_mode'] == 'auto' else ''))
        if self.page == 'cheats':
            self.refresh_cheats()
        v = emulator.installed_version()
        self.emu_note.configure(text=(_('Instalado: %s') % (v or _('versão desconhecida'))) if emulator.installed() else
                                _('Não instalado. O botão abaixo baixa o shadPS4 sozinho, sem abrir nada.'))
        self.side_status.configure(text=('✔ ' if info else '✖ ') + (msg if info else _('Jogo não encontrado')),
                                   fg=OK if info else BAD)

    def pick(self):
        d = filedialog.askdirectory(title=_('Pasta do inFAMOUS Second Son (a que tem eboot.bin)'),
                                    initialdir=self.s['folder'] or core.ROOT)
        if not d:
            return
        d = os.path.normpath(d)
        if not core.detect(d)[0]:
            for sub in [os.path.join(d, x) for x in core.SERIALS] + [os.path.dirname(d)]:
                if core.detect(sub)[0]:
                    d = sub
                    break
        self.s['folder'] = d
        self.save()
        self.refresh()

    def _open(self, p):
        os.makedirs(p, exist_ok=True)
        os.startfile(p)

    def open_log(self):
        for p in (os.path.join(core.EMU_USER, 'log', 'shad_log.txt'), core.LOG):
            if os.path.isfile(p):
                subprocess.Popen(['notepad', p])
                return

    def clear_cache(self):
        d = os.path.join(core.EMU_USER, 'cache')
        if messagebox.askyesno(TITLE, _('Apagar o cache de shaders? O jogo vai recompilar os shaders aos poucos.')):
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(d, exist_ok=True)
            self.status.configure(text=_('Cache de shaders apagado'))

    # ------------------------------------------------------------ actions
    def set_busy(self, busy, text=''):
        self.busy = busy
        self.play.configure(text=text or _('JOGAR'), bg='#5a2a20' if busy else ACCENT, cursor='arrow' if busy else 'hand2')
        if busy:
            self.bar.pack(fill='x', pady=(4, 0))
        else:
            self.bar.pack_forget()

    def progress(self, pct, msg):
        self.root.after(0, lambda: (self.bar.configure(value=pct), self.status.configure(text=msg)))

    def start(self):
        if self.busy:
            return
        if not emulator.installed():
            self.install_emulator()
            return
        if not core.detect(self.s['folder'])[0]:
            messagebox.showwarning(TITLE, _('Escolha primeiro a pasta do jogo.'))
            return
        if not self.s['controller'] and not self.s['keyboard']:
            messagebox.showwarning(TITLE, _('Ative o controle ou o teclado e mouse em "Controles".'))
            return
        if sync_mods(self.s):
            self._build_mods()
        self.pad_list = controllers.detect()
        kind = pad_kind(self.s, self.pad_list)
        if kind is None:
            kind = ask_pad(self.root, self.s, self.pad_list)
            if kind is None:
                return
            self.refresh()
        self.save()
        eff = core.effective(self.s, kind)
        self.set_busy(True, _('PREPARANDO…'))

        def started():
            self.root.after(0, lambda: (self.set_busy(True, _('JOGANDO…')), self.status.configure(text=_('Jogo aberto')),
                                        self.root.iconify()))

        def work():
            try:
                run_game(eff, self.progress, started,
                         lambda sess: self.root.after(0, lambda: self._set_session(sess)))
                self.root.after(0, lambda: (self.set_busy(False), self.status.configure(text=''),
                                            self.root.deiconify(), self.refresh()))
            except Exception as e:
                core.log(traceback.format_exc())
                msg = str(e)
                self.root.after(0, lambda: (self.set_busy(False), self.status.configure(text=''),
                                            self.root.deiconify(), messagebox.showerror(TITLE, msg)))

        threading.Thread(target=work, daemon=True).start()

    def add_steam(self):
        if not messagebox.askokcancel(_('Adicionar à Steam'),
                                      _('O %s vai aparecer na sua biblioteca da Steam, com capa e Steam Input desligado.\n\n'
                                      'A Steam será fechada e aberta de novo. Um atalho antigo com o mesmo nome é '
                                      'substituído.') % GAME):
            return
        self.status.configure(text=_('Adicionando à Steam…'))

        def work():
            try:
                steam.add(GAME, EXE, '--play', core.ART)
                self.root.after(0, lambda: (self.status.configure(text=_('Adicionado à Steam')),
                                            messagebox.showinfo('Steam', _('%s adicionado à Steam.') % GAME)))
            except Exception as e:
                core.log(traceback.format_exc())
                msg = str(e)
                self.root.after(0, lambda: (self.status.configure(text=''), messagebox.showerror('Steam', msg)))

        threading.Thread(target=work, daemon=True).start()

    def desktop(self):
        ps = ("$d=[Environment]::GetFolderPath('Desktop');$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
              "(Join-Path $d '%s.lnk'));$s.TargetPath='%s';$s.Arguments='--play';$s.WorkingDirectory='%s';"
              "$s.IconLocation='%s';$s.Save()" % (GAME, EXE, core.ROOT, app_ico()))
        r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], creationflags=NO_WINDOW,
                           capture_output=True, text=True)
        if r.returncode == 0:
            messagebox.showinfo('Atalho', 'Atalho "%s" criado na área de trabalho.' % GAME)
        else:
            messagebox.showerror('Atalho', r.stderr or 'Não foi possível criar o atalho.')


class SaveEditor:
    """Edits one save slot: karma side, level and value, blast shards; copies or deletes the slot."""

    def __init__(self, app, slot):
        if core.emu_running():
            messagebox.showwarning(TITLE, _('Feche o jogo antes de editar os saves.'))
            return
        self.app, self.slot = app, slot
        info = next((x for x in saves.slots() if x['dir'] == slot), None)
        try:
            v = saveedit.read(slot)
        except OSError as e:
            messagebox.showerror(TITLE, str(e))
            return
        top = self.top = tk.Toplevel(app.root)
        top.title(_('Editar save'))
        top.configure(bg=PANEL)
        top.transient(app.root)
        top.resizable(False, False)
        try:
            top.iconbitmap(app_ico())
        except Exception:
            pass
        tk.Label(top, text='%s · %s' % (info['name'], info['mission']) if info else slot,
                 font=('Bahnschrift SemiBold', 15), fg=TEXT, bg=PANEL).pack(anchor='w', padx=20, pady=(16, 0))
        tk.Label(top, text=_('Um backup dos saves é feito antes de gravar. Feche o jogo antes.'), font=('Segoe UI', 9),
                 fg=DIM, bg=PANEL).pack(anchor='w', padx=20, pady=(0, 10))

        body = tk.Frame(top, bg=PANEL)
        body.pack(fill='x', padx=20)
        tk.Label(body, text=_('LADO DO KARMA'), font=('Bahnschrift', 9), fg=DIM, bg=PANEL).grid(row=0, column=0,
                                                                                           sticky='w')
        self.good = tk.BooleanVar(value=v['good'])
        side = tk.Frame(body, bg=PANEL)
        side.grid(row=1, column=0, columnspan=2, sticky='w', pady=(2, 10))
        for val, name, col in ((True, _('Herói'), HERO_BLUE), (False, 'Infame', ACCENT)):
            tk.Radiobutton(side, text=name, variable=self.good, value=val, command=self._side, font=('Segoe UI', 10),
                           fg=col, bg=PANEL, activebackground=PANEL, activeforeground=col, selectcolor=PANEL2, bd=0,
                           highlightthickness=0, cursor='hand2').pack(side='left', padx=(0, 18))

        tk.Label(body, text=_('NÍVEL DE KARMA'), font=('Bahnschrift', 9), fg=DIM, bg=PANEL).grid(row=2, column=0,
                                                                                            sticky='w')
        self.level = ttk.Combobox(body, state='readonly', font=('Segoe UI', 10), width=30)
        self.level.grid(row=3, column=0, columnspan=2, sticky='w', pady=(2, 10))
        self.level.bind('<<ComboboxSelected>>', lambda e: self._level())

        tk.Label(body, text=_('VALOR DO KARMA'), font=('Bahnschrift', 9), fg=DIM, bg=PANEL).grid(row=4, column=0,
                                                                                            sticky='w')
        row = tk.Frame(body, bg=PANEL)
        row.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(2, 0))
        self.karma = tk.DoubleVar(value=round(v['karma']))
        sc = ttk.Scale(row, from_=-saveedit.KARMA_MAX, to=saveedit.KARMA_MAX, variable=self.karma, length=330,
                       command=lambda x: self.karma_lbl.configure(text='%+d' % float(x)))
        sc.pack(side='left')
        self.karma_lbl = tk.Label(row, text='%+d' % v['karma'], font=('Segoe UI Semibold', 10), fg=TEXT, bg=PANEL,
                                  width=7)
        self.karma_lbl.pack(side='left', padx=8)
        tk.Label(body, text=_('Negativo = infame, positivo = herói. Escolher um nível já ajusta o valor.'),
                 font=('Segoe UI', 8), fg=DIM, bg=PANEL).grid(row=6, column=0, columnspan=2, sticky='w',
                                                               pady=(0, 10))

        tk.Label(body, text=_('FRAGMENTOS DE EXPLOSÃO (EXPERIMENTAL)'), font=('Bahnschrift', 9), fg=DIM,
                 bg=PANEL).grid(row=7, column=0, sticky='w')
        self.shards = tk.Spinbox(body, from_=0, to=9999, width=8, font=('Segoe UI', 10), bg=PANEL2, fg=TEXT,
                                 buttonbackground=PANEL2, insertbackground=TEXT, relief='flat')
        self.shards.delete(0, 'end')
        self.shards.insert(0, str(v['shards']))
        self.shards.grid(row=8, column=0, sticky='w', pady=(2, 0))
        tk.Label(body, text=_('Campo ainda não confirmado no jogo: confira o número no menu de poderes depois.'),
                 font=('Segoe UI', 8), fg=BAD, bg=PANEL).grid(row=9, column=0, columnspan=2, sticky='w', pady=(0, 6))

        slots = tk.Frame(top, bg=PANEL)
        slots.pack(fill='x', padx=20, pady=(8, 0))
        tk.Label(slots, text=_('Copiar este save para'), font=('Segoe UI', 9), fg=DIM, bg=PANEL).pack(side='left')
        names = {x['dir']: '%s (%s)' % (x['name'], x['mission']) for x in saves.slots()}
        targets = ['infamousssUser%d' % i for i in range(10) if 'infamousssUser%d' % i != slot]
        self.targets = {(_('Slot %d — %s') % (int(t[-1]) + 1, names[t].split(' (', 1)[1].rstrip(')')) if t in names
                         else _('Slot %d — vazio') % (int(t[-1]) + 1)): t for t in targets}
        self.target = ttk.Combobox(slots, values=list(self.targets), state='readonly', font=('Segoe UI', 9), width=30)
        self.target.pack(side='left', padx=8)
        app._chip_btn(slots, _('Copiar'), self.copy).pack(side='left')

        foot = tk.Frame(top, bg=PANEL)
        foot.pack(fill='x', padx=20, pady=16)
        app._button(foot, _('Apagar este save'), self.delete, PANEL2, BAD).pack(side='left')
        app._button(foot, _('Salvar'), self.save, ACCENT, 'white').pack(side='right')
        app._button(foot, _('Cancelar'), top.destroy).pack(side='right', padx=8)
        self._side(keep=v['level'])
        top.update_idletasks()
        x = app.root.winfo_rootx() + (app.root.winfo_width() - top.winfo_width()) // 2
        y = app.root.winfo_rooty() + (app.root.winfo_height() - top.winfo_height()) // 2
        top.geometry('+%d+%d' % (x, y))
        top.grab_set()

    def _side(self, keep=None):
        names = saveedit.GOOD if self.good.get() else saveedit.EVIL
        self.level.configure(values=['%d — %s' % (i, _(n)) for i, n in enumerate(names)])
        if keep is not None:
            self.level.current(max(0, min(5, keep)))
        else:
            self.level.current(self.level.current() if self.level.current() >= 0 else 0)
            self._level()

    def _level(self):
        lv = self.level.current()
        k = saveedit.LEVEL_KARMA[lv] * (1 if self.good.get() else -1)
        self.karma.set(k)
        self.karma_lbl.configure(text='%+d' % k)

    def _done(self, msg):
        self.top.destroy()
        self.app.status.configure(text=msg)
        self.app.refresh_saves()
        self.app.refresh()

    def save(self):
        try:
            shards = int(self.shards.get())
        except ValueError:
            messagebox.showerror(TITLE, _('Fragmentos: use um número.'), parent=self.top)
            return
        try:
            saveedit.write(self.slot, self.good.get(), self.level.current(), self.karma.get(), shards)
        except Exception as e:
            core.log(traceback.format_exc())
            messagebox.showerror(TITLE, str(e), parent=self.top)
            return
        self._done(_('Save editado (backup feito antes)'))

    def copy(self):
        t = self.targets.get(self.target.get())
        if not t:
            return
        if not messagebox.askyesno(TITLE, _('Copiar este save para %s? O que estiver lá é substituído (com backup '
                                          'antes).') % self.target.get().split(' — ')[0], parent=self.top):
            return
        try:
            saveedit.copy_slot(self.slot, t)
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self.top)
            return
        self._done(_('Save copiado'))

    def delete(self):
        if not messagebox.askyesno(TITLE, _('Apagar este save? Dá para voltar pelos backups.'), parent=self.top):
            return
        try:
            saveedit.delete_slot(self.slot)
        except Exception as e:
            messagebox.showerror(TITLE, str(e), parent=self.top)
            return
        self._done(_('Save apagado (backup feito antes)'))


class Splash:
    """Small window shown by --play while the game is prepared."""

    def __init__(self, root):
        self.root = root
        root.overrideredirect(True)
        root.configure(bg=BG)
        w, h = 560, 250
        root.geometry('%dx%d+%d+%d' % (w, h, (root.winfo_screenwidth() - w) // 2, (root.winfo_screenheight() - h) // 2))
        root.attributes('-topmost', True)
        img = Image.blend(hero_image(w, h), Image.new('RGB', (w, h), BG), 0.45).convert('RGBA')
        logo = logo_image(320, 130)
        img.alpha_composite(logo, ((w - logo.width) // 2, 34))
        self.img = ImageTk.PhotoImage(img)
        c = tk.Canvas(root, width=w, height=h, highlightthickness=0, bg=BG)
        c.pack()
        c.create_image(0, 0, image=self.img, anchor='nw')
        self.text = c.create_text(w // 2, h - 46, text=_('Preparando…'), fill=TEXT, font=('Segoe UI', 10))
        c.create_rectangle(40, h - 26, w - 40, h - 20, fill=PANEL2, outline='')
        self.barid = c.create_rectangle(40, h - 26, 40, h - 20, fill=ACCENT, outline='')
        self.c, self.w = c, w

    def progress(self, pct, msg):
        def upd():
            self.c.itemconfigure(self.text, text=msg)
            self.c.coords(self.barid, 40, 224, 40 + (self.w - 80) * pct / 100, 230)
        self.root.after(0, upd)


def play_direct():
    s = core.load_settings()
    if core.autodetect(s):
        core.save_settings(s)
    sync_mods(s)
    if core.fix_languages(s):
        core.save_settings(s)
    if not core.detect(s['folder'])[0] or not emulator.installed():
        return False  # the launcher window shows what's missing
    root = tk.Tk()
    root.withdraw()
    pads = controllers.detect()
    kind = pad_kind(s, pads) or ask_pad(root, s, pads)
    if kind is None:
        root.destroy()
        return True
    eff = core.effective(s, kind)
    sp = Splash(root)
    root.deiconify()
    result = {}

    def work():
        try:
            run_game(eff, sp.progress, lambda: root.after(0, root.withdraw))
        except Exception as e:
            core.log(traceback.format_exc())
            result['err'] = str(e)
        root.after(0, root.quit)

    threading.Thread(target=work, daemon=True).start()
    root.mainloop()
    if 'err' in result:
        root.deiconify()
        root.withdraw()
        messagebox.showerror(TITLE, result['err'])
    root.destroy()
    return True


def main():
    if '--play' in sys.argv[1:] and play_direct():
        return
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == '__main__':
    main()

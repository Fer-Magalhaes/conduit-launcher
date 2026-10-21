# inFAMOUS Second Son launcher: finds the game, builds the language/Xbox-prompt mods, writes the
# shadPS4 settings and input bindings, and starts the embedded shadPS4.
# The user's game folder is never written to: shadPS4 gets a view of it under out\run (junctions and
# hard links) with a "-mods" folder next to it, which shadPS4 reads before the game's own files.
import hashlib, json, os, re, shutil, subprocess, sys, time, _winapi

import keys
from i18n import _

if getattr(sys, 'frozen', False):
    ROOT = os.path.dirname(sys.executable)
else:
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMU = os.path.join(ROOT, 'emu')
EMU_EXE = os.path.join(EMU, 'shadPS4.exe')
EMU_USER = os.path.join(EMU, 'user')
SAVES = os.path.join(EMU_USER, 'home', '1000', 'savedata', 'CUSA00004')
OUT = os.path.join(ROOT, 'out')
RUN = os.path.join(OUT, 'run')
GEN = os.path.join(OUT, 'gen')
PACKS = os.path.join(ROOT, 'mods', 'dublagem')
ART = os.path.join(ROOT, 'art')
USER = os.path.join(ROOT, 'user')
SETTINGS = os.path.join(USER, 'settings.json')
LOG = os.path.join(USER, 'last_run.log')
NO_WINDOW = 0x08000000
SERIALS = ('CUSA00004', 'CUSA00223', 'CUSA00064')
NAME = 'inFAMOUS Second Son'

# Game text: (key, name in that language, PS4 system language the game reads, file slot).
# All of these are in the European version (CUSA00004); PT-BR comes from a pack made from the
# user's own US copy (packs.py) and goes into the Portuguese slot.
TEXTS = [
    ('ptbr', 'Português (Brasil)', 7, 'portuguese'),
    ('ptpt', 'Português (Portugal)', 7, 'portuguese'),
    ('en', 'English (US)', 1, 'english'),
    ('enGB', 'English (UK)', 18, 'british'),
    ('es', 'Español', 3, 'spanish'),
    ('fr', 'Français', 2, 'french'),
    ('it', 'Italiano', 5, 'italian'),
    ('de', 'Deutsch', 4, 'german'),
    ('nl', 'Nederlands', 6, 'dutch'),
    ('pl', 'Polski', 16, 'polish'),
    ('ru', 'Русский', 8, 'russian'),
    ('tr', 'Türkçe', 19, 'turkish'),
    ('da', 'Dansk', 14, 'danish'),
    ('fi', 'Suomi', 12, 'finnish'),
    ('no', 'Norsk', 15, 'norwegian'),
    ('sv', 'Svenska', 13, 'swedish'),
]
# Text slots without voice files of their own: the game plays these voices with them
VOICE_SLOT = {'british': 'english', 'danish': 'english', 'finnish': 'english', 'norwegian': 'english',
              'swedish': 'english'}
# Voices: (key, name, game file prefix or None for a pack only). PT-PT uses its pack when there is one,
# else the game's own Portuguese files.
VOICES = [
    ('ptbr', 'Português (Brasil)', None),
    ('ptpt', 'Português (Portugal)', 'portuguese'),
    ('english', 'English', 'english'),
    ('spanish', 'Español', 'spanish'),
    ('french', 'Français', 'french'),
    ('italian', 'Italiano', 'italian'),
    ('german', 'Deutsch', 'german'),
    ('dutch', 'Nederlands', 'dutch'),
    ('polish', 'Polski', 'polish'),
    ('russian', 'Русский', 'russian'),
    ('turkish', 'Türkçe', 'turkish'),
]
RENDER = [(_('720p — mais leve (recomendado)'), (1280, 720)), ('900p', (1600, 900)), (_('1080p — igual ao PS4'), (1920, 1080))]
WINDOW = [('1280 × 720', (1280, 720)), ('1600 × 900', (1600, 900)), ('1920 × 1080', (1920, 1080)),
          ('2560 × 1440', (2560, 1440))]
PRESENT = [(_('Mailbox — sem cortes, baixa latência'), 'Mailbox'), (_('VSync — trava no Hz do monitor'), 'Fifo'),
           (_('Sem VSync — pode cortar a imagem'), 'Immediate')]

# graphics presets: (key, name, one-line description, settings)
PRESETS = [
    ('performance', _('Desempenho'), _('Mais FPS: 720p ampliado com FSR'),
     {'render': [1280, 720], 'fsr': True, 'sharpen': True, 'sharpness': 250, 'present': 'Mailbox', 'perf': True}),
    ('balanced', _('Equilibrado'), _('900p com FSR, bom meio-termo'),
     {'render': [1600, 900], 'fsr': True, 'sharpen': True, 'sharpness': 250, 'present': 'Mailbox', 'perf': False}),
    ('quality', _('Qualidade'), _('1080p nativo, imagem mais limpa'),
     {'render': [1920, 1080], 'fsr': False, 'sharpen': True, 'sharpness': 250, 'present': 'Mailbox', 'perf': False}),
    ('ps4', _('Como no PS4'), _('1080p com VSync, sem filtros'),
     {'render': [1920, 1080], 'fsr': False, 'sharpen': False, 'sharpness': 250, 'present': 'Fifo', 'perf': False}),
]


def current_preset(s):
    for key, _, _, vals in PRESETS:
        if all(s[k] == v for k, v in vals.items()):
            return key
    return None


def play_time():
    """Seconds played, from the embedded emulator plus the old shadPS4 setup the saves came from."""
    total = 0
    for p in (os.path.join(EMU_USER, 'play_time.txt'), os.path.join(os.environ.get('APPDATA', ''), 'shadPS4',
                                                                     'play_time.txt')):
        try:
            for line in open(p, encoding='utf-8', errors='replace'):
                parts = line.split()
                if len(parts) >= 2 and parts[0] in SERIALS:
                    h, m, sec = (int(x) for x in parts[1].split(':'))
                    total += h * 3600 + m * 60 + sec
        except (OSError, ValueError):
            pass
    return total


DEFAULTS = {
    'folder': '', 'text': 'ptbr', 'voice': 'ptbr', 'xbox_prompts': True,
    'controller': True, 'native_touch': False, 'pad_gestures': True, 'spray_side': 'left', 'keyboard': False, 'mouse_camera': True, 'mouse_sens': 1.0,
    'binds': None, 'binds_version': 0, 'fullscreen': True, 'render': [1280, 720], 'window': [1280, 720], 'fsr': False,
    'sharpen': True, 'sharpness': 250, 'present': 'Mailbox', 'show_fps': False, 'perf': False,
    'pad_mode': 'auto', 'mods_on': [], 'patches_on': [], 'cheats_on': [],
}

# controller kinds the launcher adapts to (controllers.py detects them)
PAD_MODES = [(_('Detectar sozinho'), 'auto'), (_('Xbox / XInput (8BitDo, etc.)'), 'xbox'),
             (_('PlayStation (DualShock 4 / DualSense)'), 'playstation'), (_('Outro controle ou só teclado'), 'other')]


def effective(s, kind):
    """Settings for this session: the Xbox-only changes (button prompts, View gestures, touch pad
    emulation on the pad) apply only with an Xbox-type pad; a PlayStation pad uses its own touch pad
    and motion sensor."""
    e = dict(s)
    if kind != 'xbox':
        e['xbox_prompts'] = False
        e['pad_gestures'] = False
    e['native_touch'] = kind == 'playstation'
    e['pad_kind'] = kind
    return e


def log(msg):
    os.makedirs(USER, exist_ok=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('[%H:%M:%S] ') + msg + '\n')


def load_settings():
    try:
        s = json.load(open(SETTINGS, encoding='utf-8'))
    except (OSError, ValueError):
        s = {}
    s = dict(DEFAULTS, **s)
    if s['binds_version'] != keys.BINDS_VERSION:
        # the first version moved the touch/motion keys this setup always used; start over
        s['binds'], s['binds_version'], s['keyboard'] = None, keys.BINDS_VERSION, False
    binds = dict(keys.DEFAULT_BINDS)
    binds.update(s['binds'] or {})
    s['binds'] = {k: list(v) for k, v in binds.items() if k in keys.DEFAULT_BINDS}
    return s


def save_settings(s):
    os.makedirs(USER, exist_ok=True)
    tmp = SETTINGS + '.tmp'
    json.dump(s, open(tmp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    os.replace(tmp, SETTINGS)


# ---------------------------------------------------------------- detection

def read_sfo(path):
    """PARAM.SFO -> dict of its string/int values."""
    b = open(path, 'rb').read()
    import struct
    _, _, kt, dt, n = struct.unpack('<IIIII', b[:20])
    out = {}
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack('<HHIII', b[20 + i * 16:36 + i * 16])
        k = b[kt + ko:b.index(b'\0', kt + ko)].decode()
        v = b[dt + do:dt + do + ln]
        out[k] = struct.unpack('<I', v[:4])[0] if fmt == 0x404 else v.rstrip(b'\0').decode('utf-8', 'replace')
    return out


def patch_dir(folder):
    for suffix in ('-UPDATE', '-patch'):
        p = folder + suffix
        if os.path.isdir(p):
            return p
    return None


def detect(folder):
    """Returns (info dict or None, message)."""
    if not folder or not os.path.isdir(folder):
        return None, _('Escolha a pasta do jogo (a que tem eboot.bin dentro).')
    if not os.path.isfile(os.path.join(folder, 'eboot.bin')):
        return None, _('Esta pasta não tem o eboot.bin do jogo.')
    sfo = {}
    for base in filter(None, (patch_dir(folder), folder)):
        p = os.path.join(base, 'sce_sys', 'param.sfo')
        if os.path.isfile(p):
            sfo = read_sfo(p)
            break
    serial = sfo.get('TITLE_ID', '')
    if serial and serial not in SERIALS:
        return None, _('Este não é o inFAMOUS Second Son (%s).') % serial
    cache = os.path.join(folder, 'art', 'cache')
    if not os.path.isfile(os.path.join(cache, 'lang_english_text.xpps')):
        return None, _('Faltam os arquivos do jogo (art\\cache).')
    info = {'folder': folder, 'serial': serial or 'CUSA00004', 'version': sfo.get('APP_VER', '?'),
            'patch': patch_dir(folder), 'cache': cache}
    msg = '%s · v%s' % (info['serial'], info['version'])
    if info['patch']:
        msg += _(' · com atualização')
    return info, msg


def autodetect(s):
    if detect(s['folder'])[0]:
        return False
    cands = [os.path.join(ROOT, 'jogo'), os.path.join(os.path.dirname(ROOT), 'InfamousSecondSon', 'CUSA00004')]
    for base in (os.path.join(ROOT, 'jogo'), os.path.dirname(ROOT)):
        try:
            for e in os.scandir(base):
                if e.is_dir():
                    cands += [e.path] + [os.path.join(e.path, x) for x in SERIALS]
        except OSError:
            pass
    for c in cands:
        if detect(c)[0]:
            s['folder'] = os.path.normpath(c)
            return True
    return False


def fix_languages(s):
    """Picks a language the game folder really has when the chosen one is missing (a new install has no
    Brazilian Portuguese pack until the user imports it). Returns True when it changed something."""
    info = detect(s['folder'])[0]
    if not info:
        return False
    changed = False
    if not text_available(info, s['text']):
        s['text'], changed = 'ptpt' if s['text'] == 'ptbr' else 'en', True
    if not voice_available(info, s['voice']):
        s['voice'], changed = 'ptpt' if s['voice'] == 'ptbr' else 'english', True
    return changed


def pack_ok(lang):
    d = os.path.join(PACKS, lang)
    return all(os.path.isfile(os.path.join(d, f)) for f in
               ['lang_text.xpps', 'lang_text_p.xpps', 'lang_audio.xpps', 'lang_audio_p.xpps'] +
               ['psarc/%s.psarc' % x for x in ('a', 'a_p', 'b', 'b_p')])


def voice_available(info, voice):
    if pack_ok(voice):
        return True
    prefix = dict((k, src) for k, _, src in VOICES)[voice]
    return bool(info and prefix) and os.path.isfile(os.path.join(info['cache'], 'lang_%s_audio.xpps' % prefix))


def text_available(info, key):
    if pack_ok(key):
        return True
    slot = next(t[3] for t in TEXTS if t[0] == key)
    return key != 'ptbr' and bool(info) and os.path.isfile(os.path.join(info['cache'], 'lang_%s_text.xpps' % slot))


def saves_count():
    try:
        return len([e for e in os.scandir(SAVES) if e.is_dir()])
    except OSError:
        return 0


# ---------------------------------------------------------------- file helpers

def _is_link(p):
    return os.path.islink(p) or os.path.isjunction(p)


def safe_remove(p):
    """Deletes a prepared tree without ever following a junction into the user's files."""
    if not os.path.lexists(p):
        return
    if _is_link(p):
        try:
            os.rmdir(p)
        except OSError:
            os.unlink(p)
    elif os.path.isdir(p):
        for e in os.scandir(p):
            safe_remove(e.path)
        os.rmdir(p)
    else:
        try:
            os.chmod(p, 0o666)
        except OSError:
            pass
        os.unlink(p)


def link_file(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def view(src, dst):
    """dst becomes a real folder whose subfolders are junctions to src's and files hard links."""
    os.mkdir(dst)
    for e in os.scandir(src):
        d = os.path.join(dst, e.name)
        if e.is_dir():
            _winapi.CreateJunction(os.path.abspath(e.path), d)
        else:
            link_file(e.path, d)


def _stamp(p):
    st = os.stat(p)
    return '%s|%d|%d' % (os.path.normcase(os.path.abspath(p)), st.st_size, int(st.st_mtime))


def _gen(name, sources, make):
    """Cached generated file under out\\gen: rebuilt when a source changes."""
    os.makedirs(GEN, exist_ok=True)
    dst = os.path.join(GEN, name)
    tag = dst + '.src'
    want = hashlib.md5('\n'.join(_stamp(p) for p in sources).encode() + XBOX_VERSION).hexdigest()
    if os.path.isfile(dst) and os.path.isfile(tag) and open(tag).read() == want:
        return dst
    data = make()
    open(dst + '.tmp', 'wb').write(data)
    os.replace(dst + '.tmp', dst)
    open(tag, 'w').write(want)
    return dst


# ---------------------------------------------------------------- language and Xbox prompts

# Button glyphs in the game's text (private-use characters) -> Xbox names of the same byte length.
XBOX_VERSION = b'xbox-1'
XBOX_GLYPHS = {
    '': b'[B]', '': b'[X]', '': b'[Y]', '': b'[A]',
    '': b'LB ', '': b'LT ', '': b'RB ', '': b'RT ',
    '': b'LS ', '': b'RS ', '': b'[A]', '': b'[B]',
}
XBOX_WORDS = {  # the touch pad button is View/Back on an Xbox pad (same byte length)
    'ptbr': [('do touch pad', 'View (Share)')],
    'ptpt': [('do painel tátil', 'View (Partilhar)'), ('do Painel Tátil', 'View (Partilhar)')],
    'en': [('Touch Pad Button', 'View/Back Button')],
    'enGB': [('Touch Pad Button', 'View/Back Button')],
}


def xbox_text(data, lang):
    for g, rep in XBOX_GLYPHS.items():
        data = data.replace(g.encode(), rep)
    for a, b in XBOX_WORDS.get(lang, []):
        a, b = a.encode(), b.encode()
        assert len(a) == len(b)
        data = data.replace(a, b)
    return data


def _with_identity(src, slot_file):
    """The 16 bytes at 0x78 name the language slot a .xpps belongs to: a file moved to another
    slot gets that slot's value, as the PT-BR port did."""
    def make():
        b = bytearray(open(src, 'rb').read())
        b[0x78:0x88] = open(slot_file, 'rb').read(0x88)[0x78:0x88]
        return bytes(b)
    return make


def language_files(info, s):
    """{relative path inside the game: replacement file} for the chosen text, voice and prompts."""
    text = next(t for t in TEXTS if t[0] == s['text'])
    slot = text[3]
    cache = info['cache']
    files = {}

    def slot_ref(kind):
        return os.path.join(cache, 'lang_%s_%s.xpps' % (slot, kind))

    def identity(p):
        return open(p, 'rb').read(0x88)[0x78:0x88]

    # text: the pack (with this slot's identity) or the game's own file, plus the Xbox prompts
    for kind in ('text', 'text_p'):
        rel = 'art/cache/lang_%s_%s.xpps' % (slot, kind)
        ref = slot_ref(kind)
        src = os.path.join(PACKS, s['text'], 'lang_%s.xpps' % kind) if pack_ok(s['text']) else ref
        fix = identity(src) != identity(ref)
        if s['xbox_prompts'] or fix:
            def make(src=src, ref=ref, fix=fix):
                data = _with_identity(src, ref)() if fix else open(src, 'rb').read()
                return xbox_text(data, s['text']) if s['xbox_prompts'] else data
            files[rel] = _gen('%s_%s%s.xpps' % (s['text'], kind, '_xbox' if s['xbox_prompts'] else ''),
                              [src, ref], make)
        elif src != ref:
            files[rel] = src

    # voice: a pack, or another language's files from the game moved into the slot the game plays
    slot = VOICE_SLOT.get(slot, slot)
    v = s['voice']
    if pack_ok(v):
        base = os.path.join(PACKS, v)
        audio = {k: os.path.join(base, 'lang_%s.xpps' % k) for k in ('audio', 'audio_p')}
        psarc = {k: os.path.join(base, 'psarc', '%s.psarc' % k) for k in ('a', 'a_p', 'b', 'b_p')}
    else:
        v = dict((k, src) for k, _, src in VOICES)[v]
        if v == slot:
            return files  # the game's own voice files for this slot
        audio = {k: os.path.join(cache, 'lang_%s_%s.xpps' % (v, k)) for k in ('audio', 'audio_p')}
        psarc = {k: os.path.join(cache, 'psarc', '%s_%s.psarc' % (v, k)) for k in ('a', 'a_p', 'b', 'b_p')}
    for k, src in audio.items():
        ref = slot_ref(k)
        files['art/cache/lang_%s_%s.xpps' % (slot, k)] = src if identity(src) == identity(ref) else             _gen('%s_%s_as_%s.xpps' % (s['voice'], k, slot), [src, ref], _with_identity(src, ref))
    for k, src in psarc.items():
        files['art/cache/psarc/%s_%s.psarc' % (slot, k)] = src
    return files


# ---------------------------------------------------------------- shadPS4 settings and input

def _merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _merge(a[k], v)
        else:
            a[k] = v
    return a


def write_emu_config(s, console_language):
    p = os.path.join(EMU_USER, 'config.json')
    try:
        cfg = json.load(open(p, encoding='utf-8'))
    except (OSError, ValueError):
        cfg = {}
    rw, rh = s['render']
    ww, wh = s['window']
    _merge(cfg, {
        'General': {'console_language': console_language, 'discord_rpc_enabled': False, 'show_splash': False,
                    'show_fps_counter': bool(s['show_fps']), 'install_dirs': [], 'connected_to_network': False},
        'GPU': {'full_screen': bool(s['fullscreen']), 'full_screen_mode': 'Fullscreen (Borderless)',
                'internal_screen_width': rw, 'internal_screen_height': rh, 'window_width': ww,
                'window_height': wh, 'fsr_enabled': bool(s['fsr']), 'rcas_enabled': bool(s['sharpen']),
                'rcas_attenuation': int(s['sharpness']), 'present_mode': s['present']},
        'Input': {'use_unified_input_config': False, 'background_controller_input': False,
                  'motion_controls_enabled': True,
                  'cursor_state': 1, 'cursor_hide_timeout': 3},
        'Log': {'sync': False},
    })
    os.makedirs(EMU_USER, exist_ok=True)
    json.dump(cfg, open(p + '.tmp', 'w', encoding='utf-8'), indent=2)
    os.replace(p + '.tmp', p)
    # a per-game file would override these settings
    for name in ('CUSA00004.json', 'CUSA00223.json', 'CUSA00064.json'):
        g = os.path.join(EMU_USER, 'custom_configs', name)
        if os.path.isfile(g):
            os.replace(g, g + '.off')


def write_inputs(s, serial):
    d = os.path.join(EMU_USER, 'input_config')
    os.makedirs(d, exist_ok=True)
    text = keys.input_ini(s)
    for name in {serial, 'CUSA00004', 'default'}:
        open(os.path.join(d, name + '.ini'), 'w', encoding='utf-8').write(text)
    open(os.path.join(d, 'global.ini'), 'w', encoding='utf-8').write(keys.global_ini(s))


# ---------------------------------------------------------------- prepare and run

def prepare(s, progress=lambda pct, msg: None):
    info, msg = detect(s['folder'])
    if not info:
        raise RuntimeError(msg)
    log('jogo: %s (%s)' % (info['folder'], msg))
    text = next(t for t in TEXTS if t[0] == s['text'])
    if not text_available(info, s['text']):
        raise RuntimeError(_('Os arquivos de %s não foram encontrados. Importe a dublagem em "Idioma e dublagem".')
                           % text[1])
    if not voice_available(info, s['voice']):
        raise RuntimeError(_('A dublagem escolhida não foi encontrada. Escolha outra em "Idioma e dublagem".'))
    log('controle: %s (botões do Xbox %s, gestos %s, touchpad do próprio controle %s)' % (
        s.get('pad_kind'), s['xbox_prompts'], s['pad_gestures'], s['native_touch']))

    progress(10, _('Preparando idioma e botões…'))
    import mods
    files = language_files(info, s)
    extra = mods.extra_files(s['mods_on'])
    for rel in sorted(set(files) & set(extra)):
        log('mod %s substitui o arquivo de idioma/botões %s' % (os.path.relpath(extra[rel], ROOT), rel))
    files.update(extra)
    log('mods: ' + ', '.join('%s <- %s' % (k, os.path.relpath(v, ROOT)) for k, v in sorted(files.items())))

    progress(60, _('Montando os arquivos do jogo…'))
    serial_dir = os.path.basename(os.path.normpath(info['folder']))
    if os.path.lexists(RUN):
        safe_remove(RUN)
    os.makedirs(RUN)
    game = os.path.join(RUN, serial_dir)
    view(info['folder'], game)
    if info['patch']:
        view(info['patch'], game + '-patch')
    if files:
        for rel, src in files.items():
            link_file(src, os.path.join(game + '-mods', *rel.split('/')))

    progress(85, _('Aplicando configurações…'))
    write_emu_config(s, text[2])
    write_inputs(s, info['serial'])
    progress(100, _('Pronto'))
    return os.path.join(game, 'eboot.bin')


def eboot_path(s):
    """The game's own eboot.bin (the update's when it has one), for checking cheats."""
    info = detect(s['folder'])[0]
    if not info:
        return None
    for base in filter(None, (info['patch'], info['folder'])):
        p = os.path.join(base, 'eboot.bin')
        if os.path.isfile(p):
            return p
    return None


def _clean_env(perf):
    """The packaged launcher points Windows' DLL search at its own _internal folder, and child
    processes inherit it."""
    import ctypes
    ctypes.windll.kernel32.SetDllDirectoryW(None)
    env = dict(os.environ)
    internal = os.path.normcase(getattr(sys, '_MEIPASS', '') or '\0')
    env['PATH'] = os.pathsep.join(p for p in env.get('PATH', '').split(os.pathsep)
                                  if not os.path.normcase(p).startswith(internal))
    for k in ('TCL_LIBRARY', 'TK_LIBRARY', '_MEIPASS2', '_PYI_APPLICATION_HOME_DIR', '_PYI_PARENT_PROCESS_LEVEL'):
        env.pop(k, None)
    # third-party Vulkan layers (Steam/Fossilize, RTSS, OBS, Epic) hang the game's loading
    env.update({'DISABLE_VK_LAYER_VALVE_steam_fossilize_1': '1', 'DISABLE_VK_LAYER_VALVE_steam_overlay_1': '1',
                'DISABLE_RTSS_LAYER': '1', 'DISABLE_VULKAN_OBS_CAPTURE': '1',
                'EOS_OVERLAY_DISABLE_VULKAN_WIN64': '1'})
    if perf:
        env.update({'SHAD_READBACK_WINDOW_KB': '2048', 'SHAD_HOT_WINDOW_SECS': '10', 'SHAD_AHEAD_MAX': '32'})
    return env


def emu_running():
    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq shadPS4.exe', '/NH'], capture_output=True, text=True,
                       creationflags=NO_WINDOW)
    return 'shadps4.exe' in r.stdout.lower()


def launch(eboot, s, cheats_on=()):
    """Starts shadPS4 with the chosen patches; returns a cheats.Session."""
    import cheats, mods
    args = [EMU_EXE, '--game', eboot, '--fullscreen', 'true' if s['fullscreen'] else 'false']
    patch = mods.write_patch_file(s['patches_on'])
    if patch:
        args += ['--patch', patch]
    log('launch: ' + ' '.join(args))
    return cheats.Session(args, EMU, _clean_env(s['perf']), cheats_on)


def wait(session):
    """Waits for the game, including a shadPS4 that relaunches itself."""
    code = session.wait()
    while emu_running():
        time.sleep(2)
    return code


def xinput_pads():
    """Connected XInput pads (Xbox, 8BitDo...)."""
    import ctypes
    try:
        x = ctypes.windll.xinput1_4
    except OSError:
        return []
    state = ctypes.create_string_buffer(16)
    return [i for i in range(4) if x.XInputGetState(i, state) == 0]

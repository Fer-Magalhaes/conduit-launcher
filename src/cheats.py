# Cheats (GoldHEN .json in mods\cheats) and the running game session.
# Cheats are written into the game's memory by the embedded shadPS4 through its IPC channel
# (SHADPS4_ENABLE_IPC): the ones switched on before the game starts are queued and applied when
# the eboot loads, and switching one later takes effect right away.
# Each cheat is checked against the game's own eboot.bin first: its "off" bytes must be the bytes
# at that address, so a cheat made for another version is never written.
import glob, json, os, struct, subprocess, threading

import core
from i18n import _

DIR = os.path.join(core.ROOT, 'mods', 'cheats')
BASE = 0x400000  # some cheat files give addresses with the PS4 load base added

# Portuguese names for the cheats this game's files have (others keep their own name)
NAMES = {
    'godmode': (_('Invencível'), _('Delsin não toma dano.')),
    'infinite energy': (_('Energia infinita'), _('Os poderes nunca acabam.')),
    'infinite bombs / rockets': (_('Bombas e mísseis infinitos'), _('O ataque pesado (granada, míssil) não gasta.')),
    'infinite skillpoints / shards': (_('Fragmentos infinitos'), _('Fragmentos de explosão ficam em 999 para '
                                                             'comprar melhorias.')),
    'max level true hero': (_('Karma máximo: Herói Verdadeiro'), _('Uma vez: leva o karma ao topo do lado herói.')),
    'max level infamous': (_('Karma máximo: Infame'), _('Uma vez: leva o karma ao topo do lado infame.')),
    'inf finisher': (_('Golpe final de karma sempre pronto'), _('Uma vez: enche a barra do golpe final '
                                                          '(Karma Bomb).')),
}
REPO = 'GoldHEN/GoldHEN_Cheat_Repository'
REPO_URL = 'https://github.com/' + REPO


def download():
    """Fetches this game's cheat files from the GoldHEN cheat repository. Returns how many."""
    import urllib.request
    ua = {'User-Agent': 'Conduit-Launcher'}
    tree = json.load(urllib.request.urlopen(urllib.request.Request(
        'https://api.github.com/repos/%s/git/trees/HEAD?recursive=1' % REPO, headers=ua), timeout=30))
    files = [t['path'] for t in tree.get('tree', []) if t['path'].startswith('json/')
             and os.path.basename(t['path']).startswith(core.SERIALS)]
    os.makedirs(DIR, exist_ok=True)
    for p in files:
        data = urllib.request.urlopen(urllib.request.Request(
            'https://raw.githubusercontent.com/%s/HEAD/%s' % (REPO, p), headers=ua), timeout=30).read()
        json.loads(data.decode('utf-8-sig'))  # refuse anything that isn't a cheat file
        open(os.path.join(DIR, os.path.basename(p)), 'wb').write(data)
    return len(files)


class Eboot:
    """Reads bytes of a PS4 eboot.bin (SELF with plain segments, or ELF) by virtual address."""

    def __init__(self, path):
        self.b = open(path, 'rb').read()
        b, base = self.b, 0
        blocks = {}
        if b[:4] == b'\x4f\x15\x3d\x1d':
            n = struct.unpack('<H', b[0x18:0x1a])[0]
            for i in range(n):
                fl, off, fs, ms = struct.unpack('<QQQQ', b[0x20 + i * 32:0x40 + i * 32])
                if fl & 0x800:
                    blocks[(fl >> 20) & 0xfff] = (off, fl)
            base = 0x20 + n * 0x20
        elif b[:4] != b'\x7fELF':
            raise ValueError('eboot desconhecido')
        phoff, = struct.unpack('<Q', b[base + 0x20:base + 0x28])
        phn, = struct.unpack('<H', b[base + 0x38:base + 0x3a])
        self.segs = []  # (vaddr, filesz, memsz, file offset or None)
        for i in range(phn):
            t, _, o, va, _, fs, ms, _ = struct.unpack('<IIQQQQQQ', b[base + phoff + i * 56:base + phoff + i * 56 + 56])
            if t != 1:
                continue
            if blocks:
                o, fl = blocks.get(i, (None, 0))
                if fl & 8:  # compressed segment: can't be read
                    o = None
            else:
                o = base + o
            self.segs.append((va, fs, ms, o))

    def read(self, va, n):
        """bytes, b'' when the address is in memory past the file (zero-filled), None when unmapped."""
        for v, fs, ms, o in self.segs:
            ms = (ms + 0x3fff) & ~0x3fff  # segments are mapped in whole 16 KiB pages
            if v <= va and va + n <= v + ms:
                if va + n <= v + fs:
                    return self.b[o + va - v:o + va - v + n] if o is not None else None
                return b'' if va >= v + fs else None
        return None


def _hex(s):
    return bytes.fromhex(s.replace(' ', ''))


def _resolve(eboot, mem):
    """'relative' or 'absolute' address style that matches this eboot, or None."""
    for style, va in (('relative', int(mem['offset'], 16)), ('absolute', int(mem['offset'], 16) - BASE)):
        if va < 0:
            continue
        off = _hex(mem['off'])
        got = eboot.read(va, len(off))
        if got == off or (got == b'' and not any(off)) or (got == b'' and mem['on'] == mem['off']):
            return style
    return None


def load(eboot_path):
    """[{id, name, desc, kind ('toggle'|'once'), memory: [(offset, on, off, relative)], ok, source}]"""
    try:
        eboot = Eboot(eboot_path)
    except (OSError, ValueError):
        eboot = None
    out, seen = [], set()
    for path in sorted(glob.glob(os.path.join(DIR, '*.json'))):
        try:
            d = json.load(open(path, encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        for m in d.get('mods', []):
            raw = m.get('name', '').strip()
            base = raw.lower().split(' (')[0]
            if base in seen:
                continue
            mem, ok = [], eboot is not None
            for e in m.get('memory', []):
                style = _resolve(eboot, e) if eboot else None
                ok = ok and style is not None
                mem.append((e['offset'], e['on'], e['off'], style != 'absolute'))
            seen.add(base)
            name, desc = NAMES.get(base, (raw, ''))
            out.append({'id': base, 'name': name, 'desc': desc, 'kind': 'toggle' if m.get('type') == 'checkbox'
                        else 'once', 'memory': mem, 'ok': ok, 'source': os.path.basename(path),
                        'credits': ', '.join(d.get('credits', []))})
    return out


# ---------------------------------------------------------------- running game (IPC)

class Session:
    """The running shadPS4. Keeps the IPC pipe so cheats can be switched while playing."""

    def __init__(self, args, cwd, env, cheats_on):
        self.args, self.cwd, self.env = args, cwd, dict(env, SHADPS4_ENABLE_IPC='true')
        self.lock = threading.Lock()
        self.proc, self.restarting = None, False
        self._start(cheats_on)

    def _start(self, cheats_on):
        self.proc = subprocess.Popen(self.args, cwd=self.cwd, env=self.env, stdin=subprocess.PIPE,
                                     stderr=subprocess.PIPE, creationflags=core.NO_WINDOW)
        self.ready = threading.Event()
        self.pending = list(cheats_on)
        threading.Thread(target=self._read, args=(self.proc,), daemon=True).start()

    def _send(self, *lines):
        with self.lock:
            try:
                self.proc.stdin.write(''.join('%s\n' % str(x).replace('\n', '\\n') for x in lines).encode())
                self.proc.stdin.flush()
                return True
            except (OSError, ValueError):
                return False

    def _patch(self, cheat, on):
        for offset, von, voff, relative in cheat['memory']:
            self._send('PATCH_MEMORY', cheat['name'], offset, von if on else voff, '', '', int(relative), 0, 0, 0)
        core.log('cheat %s: %s' % ('ligado' if on else 'desligado', cheat['name']))

    def _read(self, proc):
        restart = None
        for raw in proc.stderr:
            line = raw.decode('utf-8', 'replace').rstrip('\r\n')
            if line == ';#IPC_END':
                for c in self.pending:
                    self._patch(c, True)
                self._send('RUN', 'START')
                self.ready.set()
            elif line == ';RESTART':
                restart = []
            elif restart is not None and line.startswith(';'):
                restart.append(line[1:])
                if len(restart) == int(restart[0]) + 1:
                    self._relaunch(restart[1:])
                    return

    def _relaunch(self, args):
        core.log('shadPS4 pediu para reiniciar: ' + ' '.join(args))
        self.restarting = True
        old = self.proc
        old.kill()
        old.wait()
        self.args = [self.args[0]] + args  # the restart arguments don't include the executable
        self._start(self.pending)
        self.restarting = False

    def set_cheat(self, cheat, on):
        """Switches a cheat; a one-time cheat only runs while the game is loaded."""
        if cheat['kind'] == 'once':
            if on and self.ready.is_set():
                self._patch(cheat, True)
            return
        if on and cheat not in self.pending and cheat['kind'] == 'toggle':
            self.pending.append(cheat)
        elif not on and cheat in self.pending:
            self.pending.remove(cheat)
        if self.ready.is_set():
            self._patch(cheat, on)

    def wait(self):
        while True:
            p = self.proc
            code = p.wait()
            while self.restarting:
                threading.Event().wait(0.2)
            if p is self.proc:  # not replaced by a restart
                return code

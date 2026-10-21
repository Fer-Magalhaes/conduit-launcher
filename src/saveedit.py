# Save editor. dis.dat is plain (no encryption, no checksum). Known fields, found by comparing the
# 12 slots against what the game shows for them:
#   0x04 float  karma now (negative = evil)        0x10 u32  side: 1 hero, 0 evil
#   0x08 float  lowest karma reached               0x14 u32  karma level 0..5
#   0x0c float  highest karma reached              0x24 u32  blast shards to spend (not yet confirmed)
# Every change backs the saves up first (saves.backup) and also updates the slot's param.sfo
# subtitle, which is what the game's load menu and the launcher show.
import os, re, shutil, struct

import core
import saves
from i18n import _

GOOD = ['Vândalo', 'Protetor', 'Guardião', 'Campeão', 'Exemplo', 'Herói Verdadeiro']
EVIL = ['Vândalo', 'Marginal', 'Criminoso', 'Bioterrorista', 'Mais Procurado', 'Infame']
# karma value used when a level is picked: the slots show level 2 hero at 879, level 5 evil at -4300
LEVEL_KARMA = [0, 100, 875, 1750, 3000, 4350]
KARMA_MAX = 5000


def _path(slot):
    return os.path.join(core.SAVES, slot, 'dis.dat')


def read(slot):
    b = open(_path(slot), 'rb').read(0x40)
    karma, low, high = struct.unpack('<fff', b[4:16])
    good, level = struct.unpack('<II', b[0x10:0x18])
    shards, = struct.unpack('<I', b[0x24:0x28])
    return {'karma': karma, 'low': low, 'high': high, 'good': bool(good), 'level': level, 'shards': shards}


def level_name(good, level):
    return (GOOD if good else EVIL)[max(0, min(5, level))]


def _check_free():
    if core.emu_running():
        raise RuntimeError(_('Feche o jogo antes de editar os saves.'))


def write(slot, good, level, karma, shards):
    _check_free()
    saves.backup('antes de editar')
    p = _path(slot)
    b = bytearray(open(p, 'rb').read())
    old_karma, low, high = struct.unpack('<fff', b[4:16])
    karma = max(-KARMA_MAX, min(KARMA_MAX, float(karma)))
    struct.pack_into('<fff', b, 4, karma, min(low, karma), max(high, karma))
    struct.pack_into('<II', b, 0x10, int(bool(good)), max(0, min(5, int(level))))
    struct.pack_into('<I', b, 0x24, max(0, min(9999, int(shards))))
    open(p + '.tmp', 'wb').write(b)
    os.replace(p + '.tmp', p)
    _set_subtitle_karma(slot, level_name(good, level))
    core.log('save %s editado: karma %.0f, %s, fragmentos %d' % (slot, karma, level_name(good, level), shards))


def copy_slot(src, dst):
    _check_free()
    saves.backup('antes de copiar slot')
    d = os.path.join(core.SAVES, dst)
    tmp = d + '.tmp'
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(os.path.join(core.SAVES, src), tmp)
    sfo = os.path.join(tmp, 'sce_sys', 'param.sfo')
    if os.path.isfile(sfo):
        _sfo_set(sfo, 'SAVEDATA_DIRECTORY', dst)
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.replace(tmp, d)


def delete_slot(slot):
    _check_free()
    saves.backup('antes de apagar slot')
    shutil.rmtree(os.path.join(core.SAVES, slot))


# ---------------------------------------------------------------- param.sfo strings

def _sfo_set(path, key, value):
    """Rewrites a string entry in place, within its reserved size."""
    b = bytearray(open(path, 'rb').read())
    _, _, kt, dt, n = struct.unpack('<IIIII', b[:20])
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack('<HHIII', b[20 + i * 16:36 + i * 16])
        k = b[kt + ko:b.index(b'\0', kt + ko)].decode()
        if k != key or fmt == 0x404:
            continue
        data = value.encode('utf-8')[:mx - 1]
        b[dt + do:dt + do + mx] = data + b'\0' * (mx - len(data))
        struct.pack_into('<I', b, 20 + i * 16 + 4, len(data) + 1)
        open(path, 'wb').write(b)
        return True
    return False


def _set_subtitle_karma(slot, name):
    sfo = os.path.join(core.SAVES, slot, 'sce_sys', 'param.sfo')
    try:
        sub = core.read_sfo(sfo).get('SUBTITLE', '')
    except (OSError, ValueError):
        return
    new, n = re.subn(r'\(([^()]*)\)(\s*-\s*\d+%)', '(%s)\\2' % name.replace('\\', ''), sub)
    if n:
        _sfo_set(sfo, 'SUBTITLE', new)


def free_slots():
    have = {s['dir'] for s in saves.slots()}
    return [n for n in ['infamousssUser%d' % i for i in range(10)] if n not in have]

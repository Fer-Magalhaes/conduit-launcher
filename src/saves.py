# Save slots (read from each slot's param.sfo), automatic backups before every session, and
# export/import as .zip.
import hashlib, os, re, shutil, time, zipfile

import core
from i18n import _

BACKUPS = os.path.join(core.USER, 'backups')
KEEP = 20


def slots():
    """[{dir, name, mission, karma, percent, auto, time}] newest first."""
    out = []
    try:
        entries = [e for e in os.scandir(core.SAVES) if e.is_dir()]
    except OSError:
        return out
    for e in entries:
        sfo = os.path.join(e.path, 'sce_sys', 'param.sfo')
        try:
            sub = core.read_sfo(sfo).get('SUBTITLE', '')
        except (OSError, ValueError, IndexError):
            sub = ''
        auto = sub.startswith('(')
        sub = re.sub(r'^\([^)]*\)\s*', '', sub)
        m = re.match(r'(.*?)\s*\(([^)]*)\)\s*-\s*(\d+)%', sub)
        mission, karma, pct = (m.group(1), m.group(2), int(m.group(3))) if m else (sub or e.name, '', None)
        mt = max((os.path.getmtime(os.path.join(dp, f)) for dp, _, fn in os.walk(e.path) for f in fn), default=0)
        n = re.search(r'(\d+)$', e.name)
        num = int(n.group(1)) + 1 if n else ''
        out.append({'dir': e.name, 'mission': mission, 'karma': karma, 'percent': pct, 'auto': auto, 'time': mt,
                    'name': '%s %s' % (_('Automático') if 'auto' in e.name.lower() else _('Slot'), num)})
    out.sort(key=lambda x: (-x['time'], x['dir']))
    return out


def _fingerprint():
    h = hashlib.md5()
    for dp, _, fn in sorted(os.walk(core.SAVES)):
        for f in sorted(fn):
            p = os.path.join(dp, f)
            st = os.stat(p)
            h.update(('%s|%d|%d' % (os.path.relpath(p, core.SAVES), st.st_size, int(st.st_mtime))).encode())
    return h.hexdigest()


def _zip(dest):
    tmp = dest + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for dp, _, fn in os.walk(core.SAVES):
            for f in fn:
                p = os.path.join(dp, f)
                z.write(p, os.path.relpath(p, core.SAVES))
        z.comment = _fingerprint().encode()
    os.replace(tmp, dest)
    return dest


def backups():
    """[(path, time, label)] newest first."""
    try:
        files = [os.path.join(BACKUPS, f) for f in os.listdir(BACKUPS) if f.endswith('.zip')]
    except OSError:
        return []
    out = []
    for p in files:
        m = re.match(r'saves-(\d{8}-\d{6})(?:-(.*))?\.zip$', os.path.basename(p))
        if m:
            t = time.mktime(time.strptime(m.group(1), '%Y%m%d-%H%M%S'))
            out.append((p, t, (m.group(2) or '').replace('-', ' ')))
    return sorted(out, key=lambda x: -x[1])


def backup(label=''):
    """Zips the saves into user\\backups unless the newest backup already has them. Returns the path."""
    if not slots():
        return None
    fp = _fingerprint()
    old = backups()
    if old and not label:
        try:
            if zipfile.ZipFile(old[0][0]).comment.decode() == fp:
                return old[0][0]
        except (OSError, zipfile.BadZipFile):
            pass
    os.makedirs(BACKUPS, exist_ok=True)
    name = 'saves-%s%s.zip' % (time.strftime('%Y%m%d-%H%M%S'), '-' + label.replace(' ', '-') if label else '')
    path = _zip(os.path.join(BACKUPS, name))
    for p, _, lab in backups()[KEEP:]:
        if not lab:  # labelled ones (before a restore/import) are kept
            os.unlink(p)
    return path


def export(dest):
    return _zip(dest)


def _check(zpath):
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
    tops = {n.replace('\\', '/').split('/')[0] for n in names}
    if not any(n.replace('\\', '/').endswith('sce_sys/param.sfo') for n in names) or \
            any(t in ('..', '') or ':' in t for t in tops):
        raise RuntimeError(_('Este .zip não tem saves do inFAMOUS Second Son.'))


def restore(zpath, label='antes de restaurar'):
    """Replaces the saves with a .zip (backup or exported); the current saves are backed up first."""
    _check(zpath)
    backup(label)
    tmp = core.SAVES + '.new'
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(tmp)
    old = core.SAVES + '.old'
    shutil.rmtree(old, ignore_errors=True)
    if os.path.isdir(core.SAVES):
        os.replace(core.SAVES, old)
    os.makedirs(os.path.dirname(core.SAVES), exist_ok=True)
    os.replace(tmp, core.SAVES)
    shutil.rmtree(old, ignore_errors=True)


def import_zip(zpath):
    restore(zpath, 'antes de importar')

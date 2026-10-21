# Mods the launcher can switch on and off:
#   game patches  shadPS4 patch XML in mods\patches (code changes: skip intro, no motion blur...);
#                 the chosen ones go into one generated file passed with --patch
#   file mods     folders in mods\extras, each a copy of the game's own paths (art\cache\...) with an
#                 optional mod.json {"name", "description", "author"}; linked into the "-mods" overlay
#   .zip mods     dropped in the mods folder: installed and removed by themselves (sync_zips)
import json, os, shutil, urllib.request, zipfile
import xml.etree.ElementTree as ET

import core
from i18n import _

PATCHES = os.path.join(core.ROOT, 'mods', 'patches')
EXTRAS = os.path.join(core.ROOT, 'mods', 'extras')
PATCH_URL = 'https://raw.githubusercontent.com/shadps4-emu/ps4_cheats/main/PATCHES/InfamousSecondSon.xml'
META = ('mod.json', 'preview.png', 'leia-me.txt', 'readme.txt', 'README.md')

# English patch name -> (Portuguese name, description); resolution patches form one choice
PT = {
    'Skip intro movie': (_('Pular o vídeo de abertura'), _('Vai direto para o carregamento ao abrir o jogo. As cenas da '
                                                       'história continuam.')),
    'Disable motion blur': (_('Sem desfoque de movimento'), _('Imagem mais nítida ao girar a câmera e um pouco mais '
                                                         'de FPS.')),
    'Disable depth of field': (_('Sem profundidade de campo'), _('O fundo não fica borrado nas cenas e na mira.')),
    'Disable depth blur': (_('Sem desfoque de distância'), _('Prédios ao longe ficam nítidos.')),
}
RES_PREFIX = 'Render resolution '


def _patch_files():
    try:
        return sorted(os.path.join(PATCHES, f) for f in os.listdir(PATCHES) if f.lower().endswith('.xml'))
    except OSError:
        return []


def patches():
    """[{name, title, desc, note, author, res (w, h) or None}] for this game."""
    out, seen = [], set()
    for path in _patch_files():
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError):
            continue
        ids = {e.text for e in root.iter('ID')}
        if not ids & set(core.SERIALS):
            continue
        for m in root.iter('Metadata'):
            name = m.get('Name', '')
            if not name or name in seen:
                continue
            seen.add(name)
            res = None
            if name.startswith(RES_PREFIX):
                try:
                    res = tuple(int(x) for x in name[len(RES_PREFIX):].split('x'))
                except ValueError:
                    pass
            title, desc = PT.get(name, ('%d × %d' % res if res else name, ''))
            out.append({'name': name, 'title': title, 'desc': desc, 'note': m.get('Note', ''),
                        'author': m.get('Author', ''), 'res': res})
    return out


def write_patch_file(names):
    """One patch XML with the chosen patches enabled; returns its path, or None."""
    if not names:
        return None
    out = ET.Element('Patch')
    tid = ET.SubElement(out, 'TitleID')
    for s in core.SERIALS:
        ET.SubElement(tid, 'ID').text = s
    used = set()
    for path in _patch_files():
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError):
            continue
        for m in root.iter('Metadata'):
            if m.get('Name') in names and m.get('Name') not in used:
                used.add(m.get('Name'))
                m.set('isEnabled', 'true')
                out.append(m)
    if not used:
        return None
    os.makedirs(core.GEN, exist_ok=True)
    dst = os.path.join(core.GEN, 'patches.xml')
    ET.ElementTree(out).write(dst, encoding='utf-8', xml_declaration=True)
    core.log('patches: ' + ', '.join(sorted(used)))
    return dst


def update_patches():
    """Downloads the newest patch file for this game. Returns the number of patches in it."""
    req = urllib.request.Request(PATCH_URL, headers={'User-Agent': 'Conduit-Launcher'})
    data = urllib.request.urlopen(req, timeout=20).read()
    ET.fromstring(data)  # refuse anything that isn't XML
    os.makedirs(PATCHES, exist_ok=True)
    dst = os.path.join(PATCHES, 'InfamousSecondSon.xml')
    open(dst + '.tmp', 'wb').write(data)
    os.replace(dst + '.tmp', dst)
    return len(patches())


# ---------------------------------------------------------------- file mods

def extras():
    """[{dir, name, desc, author, files: [relative paths]}]"""
    out = []
    try:
        entries = sorted(os.scandir(EXTRAS), key=lambda e: e.name.lower())
    except OSError:
        return out
    for e in entries:
        if not e.is_dir():
            continue
        try:
            info = json.load(open(os.path.join(e.path, 'mod.json'), encoding='utf-8-sig'))
        except (OSError, ValueError):
            info = {}
        files = []
        for dp, _, fn in os.walk(e.path):
            for f in fn:
                rel = os.path.relpath(os.path.join(dp, f), e.path).replace('\\', '/')
                if rel not in META:
                    files.append(rel)
        out.append({'dir': e.name, 'name': info.get('name') or e.name, 'desc': info.get('description', ''),
                    'author': info.get('author', ''), 'files': sorted(files)})
    return out


def extra_files(enabled):
    """{relative game path: file} for the enabled file mods (later folders win on conflicts)."""
    files = {}
    for m in extras():
        if m['dir'] in enabled:
            for rel in m['files']:
                files[rel] = os.path.join(EXTRAS, m['dir'], *rel.split('/'))
    return files


# ---------------------------------------------------------------- drop-in .zip mods
# Any .zip put in the mods folder is installed by itself the next time the launcher opens or a game
# starts, and uninstalled when the .zip is taken out. What it is comes from its contents (or the
# "type" in its mod.json): a language pack, cheats, patches, artwork, or files for the game.

DROP = os.path.join(core.ROOT, 'mods')
STATE = os.path.join(core.USER, 'mods_zips.json')
ART_FILES = {'hero.png', 'logo.png', 'cover.png', 'wide.png', 'icon.png'}


def _stamp(path):
    st = os.stat(path)
    return '%d|%d' % (st.st_size, int(st.st_mtime))


def _kind(names, info):
    if info.get('type') in ('dub', 'cheats', 'patches', 'art', 'files'):
        return info['type']
    base = {n.split('/')[-1].lower() for n in names}
    if any(b.startswith(('lang_brazilian_', 'lang_portuguese_')) or b in ('lang_text.xpps', 'lang_audio.xpps')
           for b in base):
        return 'dub'
    if base <= ART_FILES | {'credits.txt', 'mod.json'}:
        return 'art'
    if all(b.endswith('.json') for b in base - {'mod.json'}):
        return 'cheats'
    if all(b.endswith('.xml') for b in base - {'mod.json'}):
        return 'patches'
    return 'files'


def _uninstall(rec):
    import packs
    if rec['kind'] == 'dub':
        packs.remove(rec['target'])
    elif rec['kind'] == 'files':
        shutil.rmtree(os.path.join(EXTRAS, rec['target']), ignore_errors=True)
    else:
        for f in rec.get('files', []):
            try:
                os.remove(f)
            except OSError:
                pass


def _install(path, s):
    import packs
    name = os.path.splitext(os.path.basename(path))[0]
    tmp = os.path.join(core.OUT, 'zip_' + name)
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if not n.endswith('/')]
        if not names:
            raise RuntimeError(_('O .zip está vazio.'))
        info = {}
        meta = [n for n in names if n.split('/')[-1].lower() == 'mod.json']
        if meta:
            try:
                info = json.loads(z.read(meta[0]).decode('utf-8-sig'))
            except ValueError:
                pass
        z.extractall(tmp)
    kind = _kind(names, info)
    rec = {'kind': kind, 'name': info.get('name') or name, 'files': []}
    files = [os.path.join(dp, f) for dp, _x, fn in os.walk(tmp) for f in fn]
    if kind == 'dub':
        lang = info.get('lang', 'ptbr')
        if any(os.path.basename(f) == 'lang_text.xpps' for f in files):  # already in the launcher's layout
            root = os.path.dirname(next(f for f in files if os.path.basename(f) == 'lang_text.xpps'))
            packs.remove(lang)
            shutil.copytree(root, os.path.join(core.PACKS, lang),
                            ignore=shutil.ignore_patterns('mod.json', '*.txt', '*.md'))
        else:
            packs.import_from(tmp, lang)
        rec['target'] = lang
    elif kind == 'files':
        top = {os.path.relpath(f, tmp).split(os.sep)[0] for f in files}
        src = os.path.join(tmp, top.pop()) if len(top) == 1 and not os.path.isfile(os.path.join(tmp, *top)) else tmp
        dst = os.path.join(EXTRAS, name)
        shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(EXTRAS, exist_ok=True)
        shutil.copytree(src, dst)
        rec['target'] = name
        if name not in s['mods_on']:
            s['mods_on'] = s['mods_on'] + [name]
    else:
        dest = {'cheats': os.path.join(DROP, 'cheats'), 'patches': PATCHES, 'art': core.ART}[kind]
        os.makedirs(dest, exist_ok=True)
        for f in files:
            if os.path.basename(f).lower() == 'mod.json':
                continue
            out = os.path.join(dest, os.path.basename(f))
            shutil.copy2(f, out)
            rec['files'].append(out)
    shutil.rmtree(tmp, ignore_errors=True)
    return rec


def sync_zips(s):
    """Installs new or changed .zip files in the mods folder and removes what was installed from
    ones that are gone. Returns a list of (zip name, what happened)."""
    try:
        state = json.load(open(STATE, encoding='utf-8'))
    except (OSError, ValueError):
        state = {}
    try:
        zips = {f: os.path.join(DROP, f) for f in os.listdir(DROP) if f.lower().endswith('.zip')}
    except OSError:
        zips = {}
    done = []
    for f in list(state):
        if f not in zips:
            _uninstall(state.pop(f))
            done.append((f, 'removido'))
    for f, path in sorted(zips.items()):
        stamp = _stamp(path)
        if state.get(f, {}).get('stamp') == stamp:
            continue
        if f in state:
            _uninstall(state.pop(f))
        try:
            rec = _install(path, s)
        except (OSError, RuntimeError, zipfile.BadZipFile) as e:
            core.log('mod %s: falhou: %s' % (f, e))
            done.append((f, 'erro: %s' % e))
            continue
        rec['stamp'] = stamp
        state[f] = rec
        core.log('mod %s instalado (%s)' % (f, rec['kind']))
        done.append((f, rec['kind']))
    if done:
        os.makedirs(core.USER, exist_ok=True)
        json.dump(state, open(STATE, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    return done


def zip_mods():
    """{zip name: record} of what is installed from the mods folder."""
    try:
        return json.load(open(STATE, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def add_zip(path):
    """Copies a .zip into the mods folder (the next sync installs it)."""
    os.makedirs(DROP, exist_ok=True)
    shutil.copy2(path, os.path.join(DROP, os.path.basename(path)))


def remove(name):
    """Removes a file mod folder, and its .zip when it came from one."""
    for f, rec in zip_mods().items():
        if rec['kind'] == 'files' and rec['target'] == name:
            try:
                os.remove(os.path.join(DROP, f))
            except OSError:
                pass
    shutil.rmtree(os.path.join(EXTRAS, name), ignore_errors=True)

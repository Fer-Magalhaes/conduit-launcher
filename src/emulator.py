# Downloads the shadPS4 build the launcher runs (the "Infamous" fork, GPL-2.0) from its GitHub releases
# into emu\. Nothing of the emulator is shipped with the launcher.
# emu\user\ is created so shadPS4 keeps its settings, saves and shader cache there (portable mode).
import json, os, urllib.request

import core

REPO = 'rayhlancaner-png/shadPS4-Infamous-FixBuild'
SOURCE = 'https://github.com/' + REPO
API = 'https://api.github.com/repos/%s/releases/latest' % REPO
ASSET = 'shadPS4.exe'
VERSION = os.path.join(core.EMU, 'version.txt')
UA = {'User-Agent': 'Conduit-Launcher'}


def installed():
    return os.path.isfile(core.EMU_EXE)


def installed_version():
    try:
        return open(VERSION, encoding='utf-8').read().strip() or None
    except OSError:
        return None


def latest():
    """(tag, download url, size in bytes) of the newest release."""
    req = urllib.request.Request(API, headers=dict(UA, Accept='application/vnd.github+json'))
    rel = json.load(urllib.request.urlopen(req, timeout=20))
    for a in rel.get('assets', []):
        if a.get('name') == ASSET:
            return rel['tag_name'], a['browser_download_url'], a['size']
    raise RuntimeError('No %s in the latest release of %s' % (ASSET, REPO))


def install(progress=lambda done, total: None):
    """Downloads the newest shadPS4.exe. Returns the release tag."""
    tag, url, size = latest()
    os.makedirs(os.path.join(core.EMU, 'user'), exist_ok=True)
    part = core.EMU_EXE + '.part'
    req = urllib.request.Request(url, headers=UA)
    done = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(part, 'wb') as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            progress(done, size)
    with open(part, 'rb') as f:
        ok = f.read(2) == b'MZ'
    if done != size or not ok:
        os.remove(part)
        raise RuntimeError('Download incomplete (%d of %d bytes)' % (done, size))
    os.replace(part, core.EMU_EXE)
    open(VERSION, 'w', encoding='utf-8').write(tag)
    core.log('shadPS4 %s installed from %s' % (tag, SOURCE))
    return tag

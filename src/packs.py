# Language packs in mods\dublagem\<ptbr|ptpt>: lang_text.xpps, lang_text_p.xpps, lang_audio.xpps,
# lang_audio_p.xpps and psarc\a.psarc, a_p, b, b_p. They are made from the user's own game files and
# never shipped. core.language_files fixes each file's slot identity when it goes into the game.
import os, shutil

import core

TEXT = ('text', 'text_p')
AUDIO = ('audio', 'audio_p')
PSARC = ('a', 'a_p', 'b', 'b_p')


def _find(folder, names):
    """{wanted name: full path} searching folder and below (first match wins)."""
    found = {}
    for dp, _, fn in os.walk(folder):
        low = {f.lower(): f for f in fn}
        for n in names:
            if n not in found and n.lower() in low:
                found[n] = os.path.join(dp, low[n.lower()])
    return found


def _copy(pairs, lang):
    dst = os.path.join(core.PACKS, lang)
    tmp = dst + '.tmp'
    shutil.rmtree(tmp, ignore_errors=True)
    for src, rel in pairs:
        out = os.path.join(tmp, *rel.split('/'))
        core.link_file(src, out)
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    os.replace(tmp, dst)
    return dst


def import_from(folder, lang='ptbr'):
    """Builds the pack from either a US copy of the game (CUSA00223: lang_brazilian_* and
    psarc\\brazilian_*) or a ready port for the European version (lang_portuguese_* and
    psarc\\portuguese_*). Returns which kind was found."""
    for prefix, kind in (('brazilian', 'us'), ('portuguese', 'port')):
        names = ['lang_%s_%s.xpps' % (prefix, k) for k in TEXT + AUDIO] + \
                ['%s_%s.psarc' % (prefix, k) for k in PSARC]
        found = _find(folder, names)
        if len(found) == len(names):
            pairs = [(found['lang_%s_%s.xpps' % (prefix, k)], 'lang_%s.xpps' % k) for k in TEXT + AUDIO]
            pairs += [(found['%s_%s.psarc' % (prefix, k)], 'psarc/%s.psarc' % k) for k in PSARC]
            _copy(pairs, lang)
            core.log('pacote %s importado de %s (%s)' % (lang, folder, kind))
            return kind
    raise RuntimeError('missing')


def remove(lang):
    shutil.rmtree(os.path.join(core.PACKS, lang), ignore_errors=True)

# PS4 inputs the launcher can bind, the default layout, key capture and the shadPS4 input
# config (user\input_config\<serial>.ini, syntax "output = input", plus global.ini).
# The touch pad and motion parts emulate what an Xbox pad lacks; the button part is only for
# playing on keyboard and mouse.
from i18n import _

BINDS_VERSION = 2
# keys the gestures helper holds to move finger 1 (View + LT: from the bottom of the pad to the top);
# bound to the left stick, which drags finger 1 while it is down
DRAG_UP_KEY, DRAG_DOWN_KEY = 'kp8', 'kp2'
# held by the helper during that drag only: with it, View + LT stop pressing the touch pad and aiming.
# (A combo with LT alone would always win over View: shadPS4 counts a trigger as held even at rest.)
DRAG_BLOCK_KEY = 'kp5'

# id: (button label, what it does in Second Son)
INPUTS = {
    'cross': ('✕', _('Pular')),
    'circle': ('○', _('Esquivar / abaixar')),
    'square': ('□', _('Corpo a corpo')),
    'triangle': ('△', _('Interagir / algemar')),
    'l1': ('L1', _('Granada')),
    'r1': ('R1', _('Tiro pesado')),
    'l2': ('L2', _('Mirar')),
    'r2': ('R2', _('Atirar / pintar')),
    'l3': ('L3', _('Karma (L3+R3)')),
    'r3': ('R3', _('Karma (L3+R3)')),
    'options': ('OPTIONS', _('Menu / pausa')),
    'pad_up': ('↑', _('Direcional cima')),
    'pad_down': ('↓', _('Direcional baixo')),
    'pad_left': ('←', _('Direcional esquerda')),
    'pad_right': ('→', _('Direcional direita')),
    'axis_left_y_minus': ('L ↑', _('Andar para frente')),
    'axis_left_y_plus': ('L ↓', _('Andar para trás')),
    'axis_left_x_minus': ('L ←', _('Andar para a esquerda')),
    'axis_left_x_plus': ('L →', _('Andar para a direita')),
    'axis_right_y_minus': ('R ↑', _('Câmera para cima')),
    'axis_right_y_plus': ('R ↓', _('Câmera para baixo')),
    'axis_right_x_minus': ('R ←', _('Câmera para a esquerda')),
    'axis_right_x_plus': ('R →', _('Câmera para a direita')),
    # touch pad
    'touchpad_center': ('TOUCHPAD', _('Apertar o touchpad')),
    'touchpad_finger1': ('Dedo 1', _('Dedo 1 (lado esquerdo, analógico esq. move)')),
    'touchpad_finger2': ('Dedo 2', _('Dedo 2 (lado direito, analógico dir. move)')),
    'touchpad_swipe_up': (_('Deslizar ↑'), _('Deslizar um dedo para cima')),
    'touchpad_swipe_down': (_('Deslizar ↓'), _('Deslizar um dedo para baixo')),
    'touchpad_swipe_left': (_('Deslizar ←'), _('Deslizar um dedo para a esquerda')),
    'touchpad_swipe_right': (_('Deslizar →'), _('Deslizar um dedo para a direita')),
    'touchpad_swipe2_up': (_('2 dedos ↑'), _('Deslizar dois dedos para cima')),
    'touchpad_swipe2_down': (_('2 dedos ↓'), _('Deslizar dois dedos para baixo')),
    'touchpad_swipe2_left': (_('2 dedos ←'), _('Deslizar dois dedos para a esquerda')),
    'touchpad_swipe2_right': (_('2 dedos →'), _('Deslizar dois dedos para a direita')),
    # motion
    'motion_tilt_left': (_('Inclinar ←'), _('Virar o controle de lado (esquerda)')),
    'motion_tilt_right': (_('Inclinar →'), _('Virar o controle de lado (direita)')),
    'motion_shake': (_('Sacudir'), _('Sacudir a lata de spray')),
    'mouse_gyro_roll_mode': (_('Girar'), _('Mouse gira o controle (segurar)')),
}
XBOX = {'cross': 'A', 'circle': 'B', 'square': 'X', 'triangle': 'Y', 'l1': 'LB', 'r1': 'RB', 'l2': 'LT', 'r2': 'RT',
        'l3': 'LS', 'r3': 'RS', 'options': 'Menu', 'touchpad_center': 'View', 'pad_up': '↑', 'pad_down': '↓',
        'pad_left': '←', 'pad_right': '→'}
BUTTONS = ['cross', 'circle', 'square', 'triangle', 'l1', 'r1', 'l2', 'r2', 'l3', 'r3', 'options', 'pad_up',
           'pad_down', 'pad_left', 'pad_right', 'axis_left_y_minus', 'axis_left_y_plus', 'axis_left_x_minus',
           'axis_left_x_plus', 'axis_right_y_minus', 'axis_right_y_plus', 'axis_right_x_minus',
           'axis_right_x_plus']
TOUCH = ['touchpad_center', 'touchpad_finger1', 'touchpad_finger2', 'touchpad_swipe_up', 'touchpad_swipe_down',
         'touchpad_swipe_left', 'touchpad_swipe_right', 'touchpad_swipe2_up', 'touchpad_swipe2_down',
         'touchpad_swipe2_left', 'touchpad_swipe2_right', 'mouse_gyro_roll_mode']
MOTION = ['motion_tilt_left', 'motion_tilt_right', 'motion_shake']  # these go in global.ini

# Touch and motion keys are the ones this setup always used; the button keys are for keyboard play.
DEFAULT_BINDS = {
    'touchpad_center': ['f'], 'touchpad_finger1': ['9'], 'touchpad_finger2': ['0'],
    'touchpad_swipe_up': ['1'], 'touchpad_swipe_down': ['2'], 'touchpad_swipe_left': ['3'],
    'touchpad_swipe_right': ['4'], 'touchpad_swipe2_up': ['5'], 'touchpad_swipe2_down': ['6'],
    'touchpad_swipe2_left': ['7'], 'touchpad_swipe2_right': ['8'], 'mouse_gyro_roll_mode': [],
    'motion_tilt_left': ['g'], 'motion_tilt_right': ['h'], 'motion_shake': ['t'],
    'cross': ['space'], 'circle': ['lctrl'], 'square': ['v', 'middlebutton'], 'triangle': ['e'],
    'l1': ['q', 'sidebuttonback'], 'r1': ['r', 'sidebuttonforward'], 'l2': ['rightbutton'], 'r2': ['leftbutton'],
    'l3': ['lshift'], 'r3': ['c'], 'options': ['enter'],
    'pad_up': ['up'], 'pad_down': ['down'], 'pad_left': ['left'], 'pad_right': ['right'],
    'axis_left_y_minus': ['w'], 'axis_left_y_plus': ['s'], 'axis_left_x_minus': ['a'], 'axis_left_x_plus': ['d'],
    'axis_right_y_minus': ['i'], 'axis_right_y_plus': ['k'], 'axis_right_x_minus': ['j'], 'axis_right_x_plus': ['l'],
}

# keys the emulator itself uses (global.ini)
HOTKEYS = [('delete', _('Mouse vira touchpad (liga/desliga)')), ('f6', _('Mouse vira giroscópio, para o spray (liga/desliga)')),
           ('f7', _('Mouse vira câmera (liga/desliga)')), ('f8', _('Recarrega os controles')), ('f9', _('Pausa')),
           ('f10', _('Mostra o FPS')), ('f11', _('Tela cheia')), ('f12', _('Captura de quadro')),
           ('lctrl, lshift, end', _('Fecha o jogo')), ('kpplus', 'Volume +'), ('kpminus', 'Volume −')]
RESERVED = {'kp8', 'kp2', 'kp5', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12', 'delete', 'kpplus', 'kpminus',
            'escape'}
GLOBAL_INI = '''# Atalhos do emulador (gerado pelo launcher do inFAMOUS Second Son)
hotkey_add_virtual_user = f5
hotkey_capture_frame = f12
hotkey_emulator_settings = f3
hotkey_fullscreen = f11
hotkey_pause = f9
hotkey_quit = lctrl, lshift, end
hotkey_reload_inputs = f8
hotkey_remove_virtual_user = f4
hotkey_screenshot_with_overlays = lalt, f12
hotkey_show_fps = f10
hotkey_toggle_friends = f2
hotkey_toggle_mouse_to_gyro = f6
hotkey_toggle_mouse_to_joystick = f7
hotkey_toggle_mouse_to_touchpad = delete
hotkey_volume_down = kpminus
hotkey_volume_up = kpplus
'''

CONTROLLER = '''# Controle
cross = cross
circle = circle
square = square
triangle = triangle
l1 = l1
r1 = r1
l2 = l2
r2 = r2
l3 = l3
r3 = r3
options = options
pad_up = pad_up
pad_down = pad_down
pad_left = pad_left
pad_right = pad_right
axis_left_x = axis_left_x
axis_left_y = axis_left_y
axis_right_x = axis_right_x
axis_right_y = axis_right_y
analog_deadzone = leftjoystick, 2, 127
analog_deadzone = rightjoystick, 2, 127
'''


def _lines(s, ids):
    out = []
    for i in ids:
        for k in s['binds'].get(i, []):
            out.append('%s = %s' % (i, k))
    return out


# Gestures on the controller with View held (combos use up their buttons, so View + LB doesn't
# also throw a grenade). View alone is bound natively; gestures.py adds the second thumb and spray mode.
PAD_GESTURES = [
    ('touchpad_center', 'back, l1, r1', 'View + LB + RB', _('Dois polegares (apertar)')),
    ('touchpad_finger1', 'back, l1', 'View + LB', _('Dedo 1, o analógico esquerdo arrasta')),
    ('touchpad_finger2', 'back, r1', 'View + RB', _('Dedo 2, o analógico direito arrasta')),
    ('leftjoystick_halfmode', 'back, l2, kp5', 'View + LT', _('Arrastar para cima e segurar: núcleo móvel (RT fica livre)')),
    ('touchpad_swipe_up', 'back, pad_up', 'View + ↑', _('Deslizar para cima')),
    ('touchpad_swipe_down', 'back, pad_down', 'View + ↓', _('Deslizar para baixo')),
    ('touchpad_swipe_left', 'back, pad_left', 'View + ←', _('Deslizar para a esquerda')),
    ('touchpad_swipe_right', 'back, pad_right', 'View + →', _('Deslizar para a direita')),
    ('motion_shake', 'back, cross', 'View + A', _('Sacudir a lata')),
    ('motion_tilt_left', 'back, square', 'View + X', _('Inclinar para a esquerda')),
    ('motion_tilt_right', 'back, circle', 'View + B', _('Inclinar para a direita')),
    ('leftjoystick_halfmode', 'back, triangle', 'View + Y', _('Modo lata de spray (liga/desliga)')),
]


def input_ini(s):
    lines = ['# Gerado pelo launcher do inFAMOUS Second Son. Mude pela página Controles do launcher.', '']
    if s['controller']:
        lines.append(CONTROLLER)
        if not s['native_touch'] and s['pad_gestures']:
            lines.append('# View/Share aperta o touchpad; com outro botão vira gesto (o launcher cuida do segundo '
                         'polegar e do modo spray)')
            lines += ['touchpad_center = back'] + ['%s = %s' % (out, combo) for out, combo, _, _ in PAD_GESTURES] + ['axis_left_y_minus = ' + DRAG_UP_KEY, 'axis_left_y_plus = ' + DRAG_DOWN_KEY, '']
        elif not s['native_touch']:
            lines += ['# View/Share do controle aperta o touchpad', 'touchpad_center = back', '']
    if not s['native_touch']:
        lines += ['# Touchpad no teclado: segure 9 ou 0 e mova o analógico para arrastar um dedo;',
                  '# 9 + 0 + F = apertar com os dois polegares. Delete: o mouse vira o touchpad.']
        lines += _lines(s, TOUCH) + ['']
    if s['keyboard']:
        lines.append('# Teclado e mouse (F7 liga o mouse na câmera)')
        ids = [i for i in BUTTONS if not (s['mouse_camera'] and i.startswith('axis_right'))]
        lines += _lines(s, ids)
        if s['mouse_camera']:
            lines += ['mouse_to_joystick = right', 'mouse_movement_params = 0.5, %.2f, 0.125' % float(s['mouse_sens'])]
        lines.append('')
    lines.append('override_controller_color = false, 0, 0, 255')
    return '\n'.join(lines) + '\n'


def global_ini(s):
    text = GLOBAL_INI
    if not s['native_touch']:
        text += '# Movimento: virar o controle de lado e sacudir a lata de spray (F6: mouse vira giroscópio)\n'
        text += '\n'.join(_lines(s, MOTION)) + '\n'
    return text


# ---------------------------------------------------------------- key capture (tkinter events)

MOUSE = [('leftbutton', _('Mouse esquerdo')), ('rightbutton', _('Mouse direito')), ('middlebutton', _('Botão do meio')),
         ('sidebuttonback', _('Lateral de trás')), ('sidebuttonforward', _('Lateral da frente')),
         ('mousewheelup', _('Roda para cima')), ('mousewheeldown', _('Roda para baixo'))]

_VK = {0x20: 'space', 0x0D: 'enter', 0x09: 'tab', 0x08: 'backspace', 0x1B: 'escape', 0x25: 'left', 0x26: 'up',
       0x27: 'right', 0x28: 'down', 0x2D: 'insert', 0x2E: 'delete', 0x24: 'home', 0x23: 'end', 0x21: 'pgup',
       0x22: 'pgdown', 0x14: 'capslock', 0x6A: 'kpasterisk', 0x6B: 'kpplus', 0x6D: 'kpminus', 0x6E: 'kpperiod',
       0x6F: 'kpslash', 0x91: 'scrolllock', 0x13: 'pausebreak'}
_SYM = {'Shift_L': 'lshift', 'Shift_R': 'rshift', 'Control_L': 'lctrl', 'Control_R': 'rctrl', 'Alt_L': 'lalt',
        'Alt_R': 'ralt', 'Win_L': 'lwin', 'Win_R': 'rwin', 'comma': 'comma', 'period': 'period', 'slash': 'slash',
        'semicolon': 'semicolon', 'apostrophe': 'apostrophe', 'quoteright': 'apostrophe', 'minus': 'minus',
        'equal': 'equals', 'bracketleft': 'lbracket', 'bracketright': 'rbracket', 'backslash': 'backslash',
        'grave': 'grave', 'quoteleft': 'grave'}


def from_event(e):
    """tkinter KeyPress event -> shadPS4 key name, or None."""
    if e.keysym in _SYM:
        return _SYM[e.keysym]
    vk = e.keycode
    if 0x41 <= vk <= 0x5A:
        return chr(vk).lower()
    if 0x30 <= vk <= 0x39:
        return chr(vk)
    if 0x70 <= vk <= 0x7B:
        return 'f%d' % (vk - 0x6F)
    if 0x60 <= vk <= 0x69:
        return 'kp%d' % (vk - 0x60)
    return _VK.get(vk)


_NAMES = {'leftbutton': _('Mouse esq.'), 'rightbutton': _('Mouse dir.'), 'middlebutton': _('Mouse meio'),
          'sidebuttonback': 'Mouse 4', 'sidebuttonforward': 'Mouse 5', 'mousewheelup': _('Roda ↑'),
          'mousewheeldown': _('Roda ↓')}
_NAMES.update({'space': _('Espaço'), 'enter': 'Enter', 'tab': 'Tab', 'backspace': 'Backspace', 'lshift': _('Shift esq.'),
               'rshift': _('Shift dir.'), 'lctrl': _('Ctrl esq.'), 'rctrl': _('Ctrl dir.'), 'lalt': 'Alt', 'ralt': 'Alt Gr',
               'up': _('Seta ↑'), 'down': _('Seta ↓'), 'left': _('Seta ←'), 'right': _('Seta →'), 'pgup': 'Page Up',
               'pgdown': 'Page Down', 'capslock': 'Caps Lock', 'insert': 'Insert', 'home': 'Home', 'end': 'End',
               'comma': ',', 'period': '.', 'slash': '/', 'semicolon': ';', 'apostrophe': "'", 'minus': '-',
               'equals': '=', 'lbracket': '[', 'rbracket': ']', 'backslash': '\\', 'grave': '`', 'delete': 'Delete',
               'kpasterisk': 'Num *', 'kpperiod': 'Num ,', 'kpslash': 'Num /', 'lwin': 'Win', 'rwin': 'Win',
               'kpplus': 'Num +', 'kpminus': 'Num −'})


def label(k):
    if k in _NAMES:
        return _NAMES[k]
    if k.startswith('kp') and k[2:].isdigit():
        return 'Num ' + k[2:]
    return k.upper()

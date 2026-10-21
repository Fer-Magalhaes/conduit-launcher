# Touch pad and motion gestures on an Xbox pad, with View as the "touch" button.
# Most gestures are plain combos in the shadPS4 input config (keys.pad_gesture_lines); the ones a
# combo can't express are done here: a combo fires one output and uses up its buttons, and
# shadPS4 only takes motion from the mouse. This thread reads the pad (XInput) and presses the
# launcher's own touch/motion keys, and moves the mouse, only while the game window is in front.
#   View alone ............ bound in the input config itself (touchpad_center = back)
#   View + LT ............. finger 1 down at the bottom of the pad, dragged to the top and kept there
#                           (mobile cores); RT stays free
#   View + LB + RB ........ both thumbs: the combo clicks with one finger, this adds the second finger
#   View + Y .............. spray can mode on/off: controller held sideways, right stick aims the can
import ctypes, threading, time
from ctypes import wintypes

import keys

BACK, LB, RB, A, B, X, Y = 0x0020, 0x0100, 0x0200, 0x1000, 0x2000, 0x4000, 0x8000
DPAD = 0x000F
AIM_SPEED = 14.0  # mouse pixels per poll at full stick

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class _GAMEPAD(ctypes.Structure):
    _fields_ = [('buttons', wintypes.WORD), ('lt', ctypes.c_ubyte), ('rt', ctypes.c_ubyte),
                ('lx', ctypes.c_short), ('ly', ctypes.c_short), ('rx', ctypes.c_short), ('ry', ctypes.c_short)]


class _STATE(ctypes.Structure):
    _fields_ = [('packet', wintypes.DWORD), ('pad', _GAMEPAD)]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD), ('dwFlags', wintypes.DWORD),
                ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wintypes.LONG), ('dy', wintypes.LONG), ('mouseData', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD), ('dwExtraInfo', ctypes.c_size_t)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [('ki', _KEYBDINPUT), ('mi', _MOUSEINPUT), ('pad', ctypes.c_byte * 32)]


class _INPUT(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('u', _INPUTUNION)]


_VK = {'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'backspace': 0x08, 'lshift': 0xA0, 'rshift': 0xA1,
       'lctrl': 0xA2, 'rctrl': 0xA3, 'lalt': 0xA4, 'ralt': 0xA5, 'up': 0x26, 'down': 0x28, 'left': 0x25,
       'right': 0x27, 'insert': 0x2D, 'home': 0x24, 'end': 0x23, 'pgup': 0x21, 'pgdown': 0x22, 'capslock': 0x14,
       'comma': 0xBC, 'period': 0xBE, 'minus': 0xBD, 'equals': 0xBB, 'semicolon': 0xBA, 'slash': 0xBF,
       'f6': 0x75}
_EXTENDED = {0x25, 0x26, 0x27, 0x28, 0x2D, 0x24, 0x23, 0x21, 0x22, 0xA3, 0xA5}


def vk_of(name):
    if not name:
        return None
    if len(name) == 1 and name.isalnum():
        return ord(name.upper())
    if name.startswith('kp') and name[2:].isdigit():
        return 0x60 + int(name[2:])
    if name.startswith('f') and name[1:].isdigit():
        return 0x6F + int(name[1:])
    return _VK.get(name)


def _send(*inputs):
    arr = (_INPUT * len(inputs))(*inputs)
    user32.SendInput(len(inputs), arr, ctypes.sizeof(_INPUT))


def _key(vk, down):
    scan = user32.MapVirtualKeyW(vk, 0)
    flags = 0x0008 | (0 if down else 0x0002) | (0x0001 if vk in _EXTENDED else 0)  # SCANCODE, KEYUP, EXTENDED
    i = _INPUT(type=1)
    i.u.ki = _KEYBDINPUT(0, scan, flags, 0, 0)
    _send(i)


def _mouse(dx, dy):
    i = _INPUT(type=0)
    i.u.mi = _MOUSEINPUT(int(dx), int(dy), 0, 0x0001, 0, 0)
    _send(i)


def _foreground_is(exe_name):
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    try:
        buf = ctypes.create_unicode_buffer(520)
        n = wintypes.DWORD(520)
        ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
        return bool(ok) and buf.value.lower().endswith('\\' + exe_name.lower())
    finally:
        kernel32.CloseHandle(h)


class Gestures:
    def __init__(self, s, log=lambda m: None):
        b = s['binds']
        first = lambda i: vk_of(b.get(i, [None])[0] if b.get(i) else None)
        self.vk_finger2 = first('touchpad_finger2')
        self.vk_finger1 = first('touchpad_finger1')
        self.vk_up = vk_of(keys.DRAG_UP_KEY)
        self.vk_down = vk_of(keys.DRAG_DOWN_KEY)
        self.vk_block = vk_of(keys.DRAG_BLOCK_KEY)
        self.dragging = False
        self.vk_tilt = first('motion_tilt_right' if s.get('spray_side') == 'right' else 'motion_tilt_left')
        self.log = log
        self.held = set()
        self.spray = False
        self.stop_ev = threading.Event()
        try:
            self.xinput = ctypes.windll.xinput1_4
        except OSError:
            self.xinput = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        if self.xinput:
            self.thread.start()

    # ------------------------------------------------------------ key state
    def _hold(self, vk, on):
        if vk is None:
            return
        if on and vk not in self.held:
            _key(vk, True)
            self.held.add(vk)
        elif not on and vk in self.held:
            _key(vk, False)
            self.held.discard(vk)

    def _tap(self, vk):
        if vk is not None:
            _key(vk, True)
            time.sleep(0.09)
            _key(vk, False)

    def _release_all(self):
        for vk in list(self.held):
            self._hold(vk, False)
        self.dragging = False

    def _set_spray(self, on):
        if on == self.spray:
            return
        self.spray = on
        self._tap(_VK['f6'])  # the emulator's mouse-to-gyro toggle
        self._hold(self.vk_tilt, on)
        self.log('modo spray ' + ('ligado' if on else 'desligado'))

    # ------------------------------------------------------------ loop
    def _read(self, state):
        for i in range(4):
            if self.xinput.XInputGetState(i, ctypes.byref(state)) == 0:
                return state.pad
        return None

    def _run(self):
        state = _STATE()
        prev = 0
        while not self.stop_ev.is_set():
            time.sleep(0.008)
            if not _foreground_is('shadPS4.exe'):
                if self.held or self.spray:
                    self._release_all()
                    if self.spray:
                        self.spray = False
                        self.log('modo spray desligado (janela do jogo saiu da frente)')
                prev = 0
                continue
            pad = self._read(state)
            if pad is None:
                continue
            btn = pad.buttons
            view = bool(btn & BACK)
            pressed = btn & ~prev

            # View + LT: finger 1 goes down (shadPS4 puts it in the middle), straight to the bottom,
            # then to the top, and stays there while held
            drag = view and pad.lt > 60
            if drag and not self.dragging:
                self._hold(self.vk_block, True)
                time.sleep(0.02)
                self._hold(self.vk_finger1, True)
                self._hold(self.vk_down, True)
                time.sleep(0.12)
                self._hold(self.vk_down, False)
                self._hold(self.vk_up, True)
                self.dragging = True
                self.log('View + LT: dedo 1 arrastado para cima')
            elif not drag and self.dragging:
                self._hold(self.vk_up, False)
                time.sleep(0.03)
                self._hold(self.vk_finger1, False)
                self._hold(self.vk_block, False)
                self.dragging = False

            # View + LB + RB: second finger for "both thumbs"
            self._hold(self.vk_finger2, view and btn & LB and btn & RB)

            # View + Y: spray can mode
            if view and pressed & Y:
                self._set_spray(not self.spray)
            if self.spray:
                rx, ry = pad.rx, pad.ry
                if abs(rx) > 7000 or abs(ry) > 7000:
                    _mouse(rx / 32767 * AIM_SPEED, -ry / 32767 * AIM_SPEED)
            prev = btn
        self._release_all()
        if self.spray:
            self.spray = False

    def stop(self):
        self.stop_ev.set()
        if self.thread.is_alive():
            self.thread.join(1)

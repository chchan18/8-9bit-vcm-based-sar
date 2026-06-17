#!/usr/bin/env python3
"""Type ASCII text into an X11 window using XTest.

This helper is intentionally tiny and only supports the characters needed
for CIW bridge recovery commands.
"""

import argparse
import ctypes
import ctypes.util
import time


SHIFT_L = 0xFFE1
RETURN = 0xFF0D
ESCAPE = 0xFF1B

SHIFTED = {
    '"': "'",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    ":": ";",
}


def keysym_for_char(ch):
    if ch == "\x1b":
        return ESCAPE, False
    if ch == "\n":
        return RETURN, False
    if "A" <= ch <= "Z":
        return ord(ch.lower()), True
    if ch in SHIFTED:
        return ord(SHIFTED[ch]), True
    return ord(ch), False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("window", help="X11 window id, for example 0x3200006")
    parser.add_argument("text", nargs="?", default="", help="text to type; use \\n for Return")
    parser.add_argument("--file", help="read text to type from a file")
    parser.add_argument("--delay", type=float, default=0.02)
    args = parser.parse_args()

    x11_path = ctypes.util.find_library("X11")
    xtst_path = ctypes.util.find_library("Xtst")
    if not x11_path or not xtst_path:
        raise SystemExit("X11/Xtst libraries not found")

    x11 = ctypes.cdll.LoadLibrary(x11_path)
    xtst = ctypes.cdll.LoadLibrary(xtst_path)
    x11.XOpenDisplay.restype = ctypes.c_void_p
    display = x11.XOpenDisplay(None)
    if not display:
        raise SystemExit("Could not open X display")

    window = int(args.window, 0)
    shift_code = x11.XKeysymToKeycode(display, SHIFT_L)

    x11.XRaiseWindow(display, window)
    x11.XSetInputFocus(display, window, 2, 0)
    x11.XFlush(display)
    time.sleep(0.2)

    if args.file:
        with open(args.file, "r") as handle:
            text = handle.read()
    else:
        text = args.text.replace("\\n", "\n").replace("\\e", "\x1b")
    for ch in text:
        keysym, need_shift = keysym_for_char(ch)
        keycode = x11.XKeysymToKeycode(display, keysym)
        if not keycode:
            raise SystemExit("No keycode for {!r} keysym={}".format(ch, keysym))
        if need_shift:
            xtst.XTestFakeKeyEvent(display, shift_code, True, 0)
        xtst.XTestFakeKeyEvent(display, keycode, True, 0)
        xtst.XTestFakeKeyEvent(display, keycode, False, 0)
        if need_shift:
            xtst.XTestFakeKeyEvent(display, shift_code, False, 0)
        x11.XFlush(display)
        time.sleep(args.delay)

    x11.XFlush(display)
    x11.XCloseDisplay(display)


if __name__ == "__main__":
    main()

import ctypes
from ctypes.wintypes import *
import os
import sys
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import threading
import time
import subprocess
from pathlib import Path

# Hello firend, are you lost? Welcome to cursed clipboard PNG optimizer. This is fucked and doesn't fully work.
# The PNG data that gets put back in to the clipboard is pastable in to image editors, but not for example: a discord chat. (Which is what I initially wanted to reduce file send size lol)
"""
pip requirements:
pystray
six
pillow

external requirements:
optipng (can install via winget)
"""
# Fuckery begin:

stop_thread = False
stop_clipboard_thread = False
current_clipboard_data = "a"
compressed_clipboard_data = "b"

# main thread here
def worker():
    systrayIcon.run_detached()
    clipboard_thread.start()
    while not stop_thread:
        time.sleep(1)
    systrayIcon.stop()
    sys.exit()

# monitors clipboard for PNG image data.
def clipboard_monitor():
    global current_clipboard_data
    global compressed_clipboard_data
    while not stop_clipboard_thread:
        time.sleep(1)
        if current_clipboard_data == compressed_clipboard_data:
            print("Clipboard contents are already compressed, skipping.")
            try:
                open_clipboard()
                current_clipboard_data = get_png()
                close_clipboard()
            except:
                print("Clipboard data is not a png.")
                close_clipboard()
            # keep checking if our thing is already optimized.
        else:
            try:
                open_clipboard()
                print("Clipboard is open...")
                current_clipboard_data = get_png()
                systrayIcon.notify('Found png data in clipboard. Optimizing.')
                with open("clipboard.png", "wb") as file:
                    file.write(current_clipboard_data)
                    # can't convert from memory, sadge. Gotta write files. Maybe ImageMagick would work if I could figure out how to put PythonMagick in to my project lel.
                empty_clipboard()
                optimize_png()
                with open("clipboard_optimized.png", "rb") as compressed_file:
                    compressed_clipboard_data = compressed_file.read()
                current_clipboard_data = compressed_clipboard_data
                set_png()
                # Funi but works.
                systrayIcon.notify('Image optimized and copied to clipboard.')
                close_clipboard()
                print("Clipboard is closed.")
            except:
                print("Clipboard data is not a png.")
                close_clipboard()

# Exit application
def exit_icon():
    global stop_thread
    global stop_clipboard_thread
    stop_clipboard_thread = True
    stop_thread = True

# image generator code (for tray icon)
def create_image(width, height, color1, color2):
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 2, 0, width, height // 2),
        fill=color2)
    dc.rectangle(
        (0, height // 2, width // 2, height),
        fill=color2)

    return image

# Create the system tray icon bingus with a orange and white checker icon xd
systrayIcon = Icon('clopy', create_image(64, 64, 'orange', 'white'), menu=Menu(
    MenuItem(
        'Exit',
        exit_icon
        )
    )
)

# call on optipng to optimize the .pn
def optimize_png():
    global compressed_clipboard_data
    try:
        subprocess.run(
            ["optipng", "--clobber", "-o", "2", "clipboard.png", "--out", "clipboard_optimized.png"],
            shell=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print("Failed to optimize image:", e.stderr.decode('utf-8'))
        return False

# Cursed fuckery do not touch.
class clopyWin32ClipboardError(Exception):
    pass

class clopyWin32MemoryError(Exception):
    pass

def clipboard_error(error_msg: str) -> None:
    close_clipboard()
    raise clopyWin32ClipboardError(error_msg)

def memory_error(error_msg: str) -> None:
    close_clipboard()
    raise clopyWin32MemoryError(error_msg)

def global_alloc(flags: int, size: int) -> int:
    h_mem = kernel32.GlobalAlloc(flags, size)
    if (h_mem is None):
        memory_error("Unable to allocate memory.")
    else:
        return h_mem

def global_lock(h_mem: int) -> int:
    lp_mem = kernel32.GlobalLock(h_mem)
    if (lp_mem is None):
        memory_error("Unable to lock global memory object.")
    else:
        return lp_mem

def global_unlock(h_mem: int) -> int:
    kernel32.GlobalUnlock(h_mem)

def get_clipboard_data(format: int) -> int:
    h_mem = user32.GetClipboardData(format)
    if (h_mem is None):
        clipboard_error("Unable to access clipboard data.")
    else:
        return h_mem

def set_clipboard_data(format: int, h_mem: int) -> int:
    h_data = user32.SetClipboardData(format, h_mem)
    if (h_data is None):
        clipboard_error("Unable to set clipboard data.")
    else:
        return h_data

def open_clipboard() -> int:
    return user32.OpenClipboard(None)
    
def close_clipboard() -> int:
    return user32.CloseClipboard()
    
def empty_clipboard() -> int:
    return user32.EmptyClipboard()

def get_png() -> str:
    png_format = 0
    PNG = user32.RegisterClipboardFormatW(ctypes.c_wchar_p('PNG'))
    image_png = user32.RegisterClipboardFormatW(
        ctypes.c_wchar_p('image/png'))
    if user32.IsClipboardFormatAvailable(PNG):
        png_format = PNG
    elif user32.IsClipboardFormatAvailable(image_png):
        png_format = image_png
    else:
        clipboard_error("clipboard image not available in 'PNG' or 'image/png' format")

    h_mem = get_clipboard_data(png_format)
    lp_mem = global_lock(h_mem)
    size = kernel32.GlobalSize(lp_mem)
    data = bytes((ctypes.c_char * size).from_address(lp_mem))
    global_unlock(h_mem)

    return data

def set_png():
    current_dir = os.getcwd()
    try:
        subprocess.Popen(
            ["powershell", "Set-Clipboard", "-LiteralPath", current_dir+"\clipboard_optimized.png"],
            stdout=sys.stdout
        )
        return True
    except subprocess.CalledProcessError as e:
        print("Failed copy:", e.stderr.decode('utf-8'))
        return False

GMEM_MOVABLE = 2
INT_P = ctypes.POINTER(ctypes.c_int)

CF_UNICODETEXT = 13
CF_HDROP = 15
CF_BITMAP = 2   # hbitmap
CF_DIB = 8   # DIB and BITMAP are interconvertable as from windows clipboard
CF_DIBV5 = 17

# bitmap compression types
BI_RGB = 0
BI_RLE8 = 1
BI_RLE4 = 2
BI_BITFIELDS = 3
BI_JPEG = 4
BI_PNG = 5
BI_ALPHABITFIELDS = 6
 
format_dict = {
    1: 'CF_TEXT',
    2: 'CF_BITMAP',
    3: 'CF_METAFILEPICT',
    4: 'CF_SYLK',
    5: 'CF_DIF',
    6: 'CF_TIFF',
    7: 'CF_OEMTEXT',
    8: 'CF_DIB',
    9: 'CF_PALETTE',
    10: 'CF_PENDATA',
    11: 'CF_RIFF',
    12: 'CF_WAVE',
    13: 'CF_UNICODETEXT',
    14: 'CF_ENHMETAFILE',
    15: 'CF_HDROP',
    16: 'CF_LOCALE',
    17: 'CF_DIBV5',
}

class BITMAPFILEHEADER(ctypes.Structure):
    _pack_ = 1  # structure field byte alignment
    _fields_ = [
        ('bfType', WORD),  # file type ("BM")
        ('bfSize', DWORD),  # file size in bytes
        ('bfReserved1', WORD),  # must be zero
        ('bfReserved2', WORD),  # must be zero
        ('bfOffBits', DWORD),  # byte offset to the pixel array
    ]

sizeof_BITMAPFILEHEADER = ctypes.sizeof(BITMAPFILEHEADER)

class BITMAPINFOHEADER(ctypes.Structure):
    _pack_ = 1  # structure field byte alignment
    _fields_ = [
        ('biSize', DWORD),
        ('biWidth', LONG),
        ('biHeight', LONG),
        ('biPLanes', WORD),
        ('biBitCount', WORD),
        ('biCompression', DWORD),
        ('biSizeImage', DWORD),
        ('biXPelsPerMeter', LONG),
        ('biYPelsPerMeter', LONG),
        ('biClrUsed', DWORD),
        ('biClrImportant', DWORD)
    ]

sizeof_BITMAPINFOHEADER = ctypes.sizeof(BITMAPINFOHEADER)

class BITMAPV4HEADER(ctypes.Structure):
    _pack_ = 1  # structure field byte alignment
    _fields_ = [
        ('bV4Size', DWORD),
        ('bV4Width', LONG),
        ('bV4Height', LONG),
        ('bV4PLanes', WORD),
        ('bV4BitCount', WORD),
        ('bV4Compression', DWORD),
        ('bV4SizeImage', DWORD),
        ('bV4XPelsPerMeter', LONG),
        ('bV4YPelsPerMeter', LONG),
        ('bV4ClrUsed', DWORD),
        ('bV4ClrImportant', DWORD),
        ('bV4RedMask', DWORD),
        ('bV4GreenMask', DWORD),
        ('bV4BlueMask', DWORD),
        ('bV4AlphaMask', DWORD),
        ('bV4CSTypes', DWORD),
        ('bV4RedEndpointX', LONG),
        ('bV4RedEndpointY', LONG),
        ('bV4RedEndpointZ', LONG),
        ('bV4GreenEndpointX', LONG),
        ('bV4GreenEndpointY', LONG),
        ('bV4GreenEndpointZ', LONG),
        ('bV4BlueEndpointX', LONG),
        ('bV4BlueEndpointY', LONG),
        ('bV4BlueEndpointZ', LONG),
        ('bV4GammaRed', DWORD),
        ('bV4GammaGreen', DWORD),
        ('bV4GammaBlue', DWORD)
    ]

sizeof_BITMAPV4HEADER = ctypes.sizeof(BITMAPV4HEADER)

class BITMAPV5HEADER(ctypes.Structure):
    _pack_ = 1  # structure field byte alignment
    _fields_ = [
        ('bV5Size', DWORD),
        ('bV5Width', LONG),
        ('bV5Height', LONG),
        ('bV5PLanes', WORD),
        ('bV5BitCount', WORD),
        ('bV5Compression', DWORD),
        ('bV5SizeImage', DWORD),
        ('bV5XPelsPerMeter', LONG),
        ('bV5YPelsPerMeter', LONG),
        ('bV5ClrUsed', DWORD),
        ('bV5ClrImportant', DWORD),
        ('bV5RedMask', DWORD),
        ('bV5GreenMask', DWORD),
        ('bV5BlueMask', DWORD),
        ('bV5AlphaMask', DWORD),
        ('bV5CSTypes', DWORD),
        ('bV5RedEndpointX', LONG),
        ('bV5RedEndpointY', LONG),
        ('bV5RedEndpointZ', LONG),
        ('bV5GreenEndpointX', LONG),
        ('bV5GreenEndpointY', LONG),
        ('bV5GreenEndpointZ', LONG),
        ('bV5BlueEndpointX', LONG),
        ('bV5BlueEndpointY', LONG),
        ('bV5BlueEndpointZ', LONG),
        ('bV5GammaRed', DWORD),
        ('bV5GammaGreen', DWORD),
        ('bV5GammaBlue', DWORD),
        ('bV5Intent', DWORD),
        ('bV5ProfileData', DWORD),
        ('bV5ProfileSize', DWORD),
        ('bV5Reserved', DWORD)
    ]

sizeof_BITMAPV5HEADER = ctypes.sizeof(BITMAPV5HEADER)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

user32.OpenClipboard.argtypes = HWND,
user32.OpenClipboard.restype = BOOL
user32.GetClipboardData.argtypes = UINT,
user32.GetClipboardData.restype = HANDLE
user32.SetClipboardData.argtypes = UINT, HANDLE
user32.SetClipboardData.restype = HANDLE
user32.CloseClipboard.argtypes = None
user32.CloseClipboard.restype = BOOL
user32.IsClipboardFormatAvailable.argtypes = UINT,
user32.IsClipboardFormatAvailable.restype = BOOL
user32.CountClipboardFormats.argtypes = None
user32.CountClipboardFormats.restype = UINT
user32.EnumClipboardFormats.argtypes = UINT,
user32.EnumClipboardFormats.restype = UINT
user32.GetClipboardFormatNameA.argtypes = UINT, LPSTR, UINT
user32.GetClipboardFormatNameA.restype = UINT
user32.RegisterClipboardFormatA.argtypes = LPCSTR,
user32.RegisterClipboardFormatA.restype = UINT
user32.RegisterClipboardFormatW.argtypes = LPCWSTR,
user32.RegisterClipboardFormatW.restype = UINT
user32.RegisterClipboardFormatW.argtypes = LPCWSTR,
user32.RegisterClipboardFormatW.restype = UINT
user32.EmptyClipboard.argtypes = None
user32.EmptyClipboard.restype = BOOL

kernel32.GlobalAlloc.argtypes = UINT, ctypes.c_size_t
kernel32.GlobalAlloc.restype = HGLOBAL
kernel32.GlobalSize.argtypes = HGLOBAL,
kernel32.GlobalSize.restype = UINT
kernel32.GlobalLock.argtypes = HGLOBAL,
kernel32.GlobalLock.restype = LPVOID
kernel32.GlobalUnlock.argtypes = HGLOBAL,
kernel32.GlobalUnlock.restype = BOOL

shell32.DragQueryFile.argtypes = HANDLE, UINT, ctypes.c_void_p, UINT
shell32.DragQueryFile.restype = UINT

# End of cursed fuckery, proceed. :3

clipboard_thread = threading.Thread(target=clipboard_monitor)
thread = threading.Thread(target=worker)
thread.start()
# Program start.
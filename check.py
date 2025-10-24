import ctypes
from ctypes import util

path = util.find_library("ApplicationServices")
if not path:
    print("Could not locate ApplicationServices framework")
    raise SystemExit(1)

quartz = ctypes.cdll.LoadLibrary(path)
quartz.AXIsProcessTrusted.restype = ctypes.c_bool
quartz.AXIsProcessTrusted.argtypes = []
print("Accessibility trusted:", quartz.AXIsProcessTrusted())

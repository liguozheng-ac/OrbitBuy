"""在宿主系统读取实际权限，不把 Windows st_mode 当作 POSIX 权限。"""
import os


def assert_private_file(path):
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600
        return
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    api.GetFileSecurityW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                                     wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
    api.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = (
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD))
    kernel.LocalFree.argtypes = (ctypes.c_void_p,)
    size = wintypes.DWORD()
    api.GetFileSecurityW(str(path), 4, None, 0, ctypes.byref(size))
    descriptor = ctypes.create_string_buffer(size.value)
    assert api.GetFileSecurityW(str(path), 4, descriptor, size.value, ctypes.byref(size))
    text = wintypes.LPWSTR()
    assert api.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 4, ctypes.byref(text), None)
    try:
        sddl = text.value
        assert sddl.startswith("D:P")
        assert set(sddl[3:].split(")(")) == {"(A;;FA;;;SY", "A;;FA;;;OW)"}, sddl
    finally:
        kernel.LocalFree(text)

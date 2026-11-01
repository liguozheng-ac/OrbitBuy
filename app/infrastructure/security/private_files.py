"""私有评测文件：POSIX 0600，Windows 使用受保护的 owner/SYSTEM DACL。"""
from __future__ import annotations

import os
from pathlib import Path


def secure_private_file(path: Path) -> None:
    if os.name != "nt":
        os.chmod(path, 0o600)
        return
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    descriptor = ctypes.c_void_p()
    api.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD))
    api.SetFileSecurityW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p)
    kernel.LocalFree.argtypes = (ctypes.c_void_p,)
    # OW 为当前文件 owner，SY 为 SYSTEM。禁止继承宽泛的父目录读权限。
    if not api.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        "D:P(A;;FA;;;SY)(A;;FA;;;OW)", 1, ctypes.byref(descriptor), None
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not api.SetFileSecurityW(str(path), 0x4 | 0x80000000, descriptor):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.LocalFree(descriptor)


def create_private_file(path: Path) -> None:
    """创建空文件后立即收紧权限，写敏感内容前失败即停止。"""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    secure_private_file(path)

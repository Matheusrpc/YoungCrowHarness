"""Run native tests with current-user ownership and an inherited private fixture ACL.

Windows hosted runners create objects owned by Administrators by default. This
process-only fixture setup models the supported profile without changing the
product's permission checks, existing files, accounts or machine policy.
"""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import runpy
import sys
import tempfile
import uuid


def main():
    if os.name != 'nt' or len(sys.argv) < 2:
        raise SystemExit('Windows test command required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    security = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                           wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    security.SetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    security.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    token = wintypes.HANDLE()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 0x0080 | 0x0008, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())

    def info(kind):
        size = wintypes.DWORD()
        security.GetTokenInformation(token, kind, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not security.GetTokenInformation(token, kind, buffer, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer

    def set_owner(pointer):
        if not security.SetTokenInformation(token, 4, ctypes.byref(pointer), ctypes.sizeof(pointer)):
            raise ctypes.WinError(ctypes.get_last_error())

    original = None
    try:
        user, owner = info(1), info(4)  # TOKEN_USER / TOKEN_OWNER start with a SID pointer.
        user_sid = ctypes.cast(user, ctypes.POINTER(ctypes.c_void_p))[0]
        original = ctypes.c_void_p(ctypes.cast(owner, ctypes.POINTER(ctypes.c_void_p))[0])
        changed = not security.EqualSid(user_sid, original)
        set_owner(ctypes.c_void_p(user_sid))
        verified = info(4)
        if not security.EqualSid(user_sid, ctypes.cast(verified, ctypes.POINTER(ctypes.c_void_p))[0]):
            raise RuntimeError('fixture owner was not set')
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        import adoption_fs as fs
        base = fs.checked_path(Path(os.environ.get('RUNNER_TEMP', tempfile.gettempdir())) / ('yc-' + uuid.uuid4().hex[:8]))
        fs.private_dir(base)
        fs.inspect_permissions(base, role='snapshot')
        os.environ.update(TEMP=str(base), TMP=str(base))
        tempfile.tempdir = str(base)
        print(f'Windows fixture: current user owner verified; adjusted={changed}; private parent verified', flush=True)
        command = sys.argv[1:]
        if command[0] == '-m':
            sys.argv = command[1:]
            runpy.run_module(sys.argv[0], run_name='__main__', alter_sys=True)
        else:
            sys.argv = command
            runpy.run_path(command[0], run_name='__main__')
    finally:
        try:
            if original is not None:
                set_owner(original)
        finally:
            kernel.CloseHandle(token)


if __name__ == '__main__':
    main()

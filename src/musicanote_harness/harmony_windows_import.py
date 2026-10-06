"""Opt-in Windows-only music21 OS-label lookup, isolated to a fresh worker.

Do not patch platform.system/uname, installed files, registry, ACL or WMI.
Replace only music21.common.misc.getPlatform with the SAME bytecode whose
private platform.system dependency returns the OS label already established
by sys.platform and os.name. A pinned misc.py guards against library drift.
"""
from contextlib import contextmanager
import hashlib
import importlib.abc
import importlib.machinery
import os
from pathlib import Path
import sys
from types import FunctionType, SimpleNamespace

VERSION = 'isolated-music21-windows-label-0.1.0'
MISC_SHA = '3d3ebec7d339132eb555f45fb8ec4e0518248cf34bfbb38b28b32f2636be778e'
TARGET = 'music21.common.misc'


def bind_windows_label(fn):
    """Default Windows getPlatform behavior, without an architecture probe."""
    if (not isinstance(fn, FunctionType) or fn.__name__ != 'getPlatform' or
            'platform' not in fn.__code__.co_names or 'platform' not in fn.__globals__):
        raise ValueError('unrecognized_music21_platform_function')
    result = FunctionType(fn.__code__, fn.__globals__ | {
        'platform': SimpleNamespace(system=lambda: 'Windows')}, fn.__name__,
        fn.__defaults__, fn.__closure__)
    result.__kwdefaults__ = fn.__kwdefaults__
    result.__annotations__ = dict(fn.__annotations__)
    return result


class MiscLoader:
    def __init__(self, loader, receipt):
        self.loader, self.receipt = loader, receipt

    def create_module(self, spec):
        create = getattr(self.loader, 'create_module', None)
        return create(spec) if create is not None else None

    def exec_module(self, module):
        self.loader.exec_module(module)
        actual = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        self.receipt['observed_misc_sha256'] = actual
        if actual != MISC_SHA:
            self.receipt['reason'] = 'library_source_changed_original_lookup_retained'
            return
        module.getPlatform = bind_windows_label(module.getPlatform)
        self.receipt.update(applied=True, reason='same_windows_label_no_wmi_architecture_query',
            bytecode_preserved=True, global_platform_module_modified=False)


class MiscFinder(importlib.abc.MetaPathFinder):
    def __init__(self, receipt):
        self.receipt = receipt

    def find_spec(self, fullname, path=None, target=None):
        if fullname != TARGET:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or spec.loader is None:
            raise ImportError('music21_misc_loader_unavailable')
        spec.loader = MiscLoader(spec.loader, self.receipt)
        return spec


@contextmanager
def isolated_windows_label(enabled):
    receipt = dict(version=VERSION, requested=bool(enabled), applied=False,
        sys_platform=sys.platform, os_name=os.name, installed_files_modified=False)
    finder = None
    if not enabled:
        receipt['reason'] = 'disabled'
    elif sys.platform != 'win32' or os.name != 'nt':
        receipt['reason'] = 'not_native_windows_original_lookup_retained'
    elif TARGET in sys.modules:
        raise ValueError('isolated_label_requires_fresh_music21_import')
    else:
        finder = MiscFinder(receipt)
        sys.meta_path.insert(0, finder)
    try:
        yield receipt
    finally:
        if finder is not None:
            sys.meta_path.remove(finder)
        # A successful binding remains ONLY in the fresh child process. The
        # original global platform object and installation were never changed.

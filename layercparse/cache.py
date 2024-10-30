# Caches pickled python objects to disk
# If the source file is newer than the cache file, the cache is considered invalid

import os, shutil
from typing import Callable, Protocol

import pickle

from .internal import *
from . import workspace

cachedir = ".parsecache"

use_cache = True

def getcachedir() -> str:
    return os.path.join(workspace.rootPath, "build", cachedir)

def clearcache():
    if not workspace.rootPath:
        return
    cachepath = getcachedir()
    if os.path.exists(cachepath):
        shutil.rmtree(cachepath)

def relpath(srcpath: str) -> str:
    return (os.path.relpath(srcpath, workspace.rootPath)
            if workspace.rootPath and srcpath.startswith(workspace.rootPath) else
            os.path.relpath(srcpath, "/",)
            if os.path.isabs(srcpath) else
            srcpath)

def getcachepath(srcpath: str, suffix: str = "") -> str:
    if not workspace.rootPath:
        return ""
    return os.path.join(getcachedir(), relpath(srcpath) + suffix)

# Returns true if the object is in the cache
def is_cached(srcpath: str,
              dependencies: list[str] | None = None,
              suffix: str = "",
              cachepath: str = "") -> bool:
    if not cachepath:
        cachepath = getcachepath(srcpath, suffix)
    if not cachepath:
        return False
    try:
        cachestat = os.stat(cachepath)
        if not dependencies:
            srcstat = os.stat(srcpath)
            return (srcstat.st_mtime - cachestat.st_mtime) <= 1
        for dep in dependencies:
            depstat = os.stat(dep)
            if (depstat.st_mtime - cachestat.st_mtime) > 1:
                return False
        return True
    except FileNotFoundError:
        return False

# Returns the object from the cache if it exists and is up to date
def get(srcpath: str,
        dependencies: list[str] | None = None,
        suffix: str = "",
        cachepath: str = "") -> object | None:
    if not cachepath:
        cachepath = getcachepath(srcpath, suffix)
    if not is_cached(srcpath, dependencies, suffix=suffix, cachepath=cachepath):
        return None
    try:
        with open(cachepath, "rb") as f:
            return pickle.load(f)
    except (FileNotFoundError, pickle.UnpicklingError):
        return None

# Pickles the object to the cache
def put(obj: object, srcpath: str, suffix: str = "", cachepath: str = "") -> object:
    if not cachepath:
        cachepath = getcachepath(srcpath, suffix)
    if not cachepath:
        return obj
    os.makedirs(os.path.dirname(cachepath), exist_ok=True)
    with open(cachepath, "wb") as f:
        pickle.dump(obj, f)
    return obj

# Decorator that wraps a function or instance method with caching
def cached(fileFn: Callable[..., str] | None = None,
           depsFn: Callable[..., list[str] | None] | None = None,
           suffixFn: Callable[..., str] | None = None):
    if not fileFn:
        raise ValueError("fileFn is required")
    if not depsFn:
        depsFn = lambda *args, **kwargs: None
    if not suffixFn:
        suffixFn = lambda *args, **kwargs: ""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not use_cache:
                return func(*args, **kwargs)
            key = fileFn(*args, **kwargs)
            deps = depsFn(*args, **kwargs)
            suffix = suffixFn(*args, **kwargs)
            if (obj := get(key, dependencies=deps, suffix=suffix)) is not None:
                return obj
            return put(func(*args, **kwargs), key, suffix=suffix)
        return wrapper
    return decorator

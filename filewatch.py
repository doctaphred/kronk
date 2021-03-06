import time
from importlib import reload
from pathlib import Path
from threading import Thread, Lock


def _watch(callback, path, interval):
    path = Path(path)
    last_modified = path.stat().st_mtime_ns
    while True:
        stat = path.stat()
        if stat.st_mtime_ns != last_modified:
            callback(stat)
            last_modified = stat.st_mtime_ns
        time.sleep(interval)


def watch(callback, path, interval=0.5):
    """Invoke callback whenever the given file has been modified.

    This operation polls the filesystem, so a minimum interval between
    polls must be given, and should be as large as possible to avoid
    excessive overhead.

    Note that the resolution of modification time varies by OS and
    filesystem: on HFS+, it is 1 second. The minimum effective setting
    for interval is therefore resolution / 2, or 0.5 seconds on HFS+.

    The callback is given a single argument: the stat_result object
    object returned by Path(path).stat().

    This function would preferably be implemented via filesystem event
    notifications, but those are platform-dependent and sound boring to
    code. Consider the watchdog library if you need that functionality.

    Args:
        callback: called every time the specified file is modified.
        path: a path to a file (string or pathlib.Path).
        interval: the minimum interval between filesystem polls, in
            seconds.
    Side effects:
        Starts a daemon thread which may invoke the given callback.
    """
    Thread(target=_watch, args=(callback, path, interval), daemon=True).start()


def catch(func, *args, **kwargs):
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        result = None
        ex = e
    else:
        ex = None
    return result, ex


def autoreload(module, interval=0.5, verbose=True, retry=2):
    """Reload module whenever its source file is modified.

    Polls the file every interval seconds in a separate thread.

    See watch.
    """
    file = module.__file__

    def info(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)

    if retry is None:
        def callback(_):
            reload(module)
    else:
        def callback(_):
            while True:
                info('Reloading', file)
                try:
                    reload(module)
                except Exception as e:
                    info('Error reloading {}:'.format(file))
                    info('{e.__class__}: {e}'.format(e=e))
                    info('Retrying in', retry, 'seconds...')
                    time.sleep(retry)
                else:
                    return

    watch(callback, file, interval=interval)


class FreshFile:
    """Each call to FreshFile.read returns the file's current contents.

    Polls the file every interval seconds in a separate thread.

    See watch.
    """

    def __init__(self, path, interval=0.5):
        self.path = path
        self._lock = Lock()
        self.refresh()
        watch(lambda _: self.unfreshen(), path, interval=interval)

    @property
    def fresh(self):
        return self._fresh

    def refresh(self):
        """Re-read file from disk."""
        with self._lock:
            with open(self.path) as f:
                self._contents = f.read()
            self._fresh = True

    def unfreshen(self):
        with self._lock:
            self._fresh = False

    def read(self):
        """Return the current contents of the file."""
        if not self._fresh:
            self.refresh()
        return self._contents


if __name__ == '__main__':
    import sys
    path = sys.argv[1]

    def time_delta_printer():
        stat = yield
        last_modified = stat.st_mtime
        print(path, 'first modified at', last_modified)
        while True:
            stat = yield
            modified = stat.st_mtime
            print(path, 'modified after', modified - last_modified, 's')
            last_modified = modified

    printer_coroutine = time_delta_printer()
    next(printer_coroutine)  # Advance the coroutine to the first yield

    watch(printer_coroutine.send, path)
    print('Watching', path)
    print('Press enter to stop')
    input()

    # $ python3 filewatch.py test.txt
    # Watching test.txt
    # Press enter to stop
    # test.txt first modified at 1453569373.0
    # test.txt modified after 1.0 s
    # test.txt modified after 1.0 s
    # test.txt modified after 3.0 s
    # test.txt modified after 1.0 s
    # test.txt modified after 2.0 s

# BSD 3-Clause License; see https://github.com/jpivarski/awkward-1.0/blob/master/LICENSE

"""
Defines Futures and Executors for Uproot Sources.

These are distinct from Python's built-in Futures and Executors because each
Thread in the thread pools are associated with one Resource, such as an open
file handle.
"""

from __future__ import absolute_import

import sys
import time
import threading

try:
    import queue
except ImportError:
    import Queue as queue

import uproot4._util


class Future(object):
    """
    Abstract base class for Futures, which have the same interface as Python
    Futures.
    """


class Executor(object):
    """
    Abstract base class for Executors, which have the same interface as Python
    Executors.
    """


class TrivialFuture(Future):
    """
    A Future that is filled as soon as it is created.
    """

    def __init__(self, result):
        """
        Creates a TrivialFuture preloaded with a `result`.
        """
        self._result = result

    def cancel(self):
        return False

    def cancelled(self):
        return False

    def running(self):
        return False

    def done(self):
        return True

    def result(self, timeout=None):
        return self._result

    def exception(self, timeout=None):
        return None

    def add_done_callback(self, fn):
        return fn(self)


class ResourceExecutor(Executor):
    """
    An Executor that doesn't manage any Threads, but does manage Resources,
    such as file handles (as a context manager).
    """

    def __init__(self, resource):
        """
        Args:
            resource (Resource): Something to pass `__enter__` and `__exit__`
                to when entering and exiting the scope of a context block.
        """
        self._resource = resource

    @property
    def num_workers(self):
        """
        Always returns 0, which indicates the lack of background workers.
        """
        return 0

    def __enter__(self):
        """
        Passes `__enter__` to the Resource.
        """
        self._resource.__enter__()

    def __exit__(self, exception_type, exception_value, traceback):
        """
        Passes `__exit__` to the Resource.
        """
        self._resource.__exit__(exception_type, exception_value, traceback)

    def submit(self, fn, *args, **kwargs):
        """
        Immediately evaluate the function `fn` with `resource` as a first
        argument, before `args` and `kwargs`.
        """
        return TrivialFuture(fn(self._resource, *args, **kwargs))

    def map(self, func, *iterables):
        """
        Like Python's Executor.
        """
        for x in iterables:
            yield func(self._resource, x)

    def shutdown(self, wait=True):
        """
        Manually calls `__exit__`.
        """
        self.__exit__()


class TaskFuture(Future):
    """
    A Future that waits for a `result` to be filled (by an Executor or one of
    its Threads).

    Contains one `threading.Event` to block `result` until ready.
    """

    def __init__(self, task, *args, **kwargs):
        """
        Args:
            task (None or callable): An object that determines when the
                `result` will be ready, but its meaning is interpreted by the
                controlling Executor or Thread.
            args (tuple): Arguments to pass to the `task` as a callable,
                after the Resource.
            kwargs (dict): Keyword arguments to pass to the `task` as a
                callable.
        """
        self._task = task
        self._args = args
        self._kwargs = kwargs
        self._finished = threading.Event()
        self._result = None
        self._excinfo = None

    def cancel(self):
        raise NotImplementedError

    def cancelled(self):
        raise NotImplementedError

    def running(self):
        raise NotImplementedError

    def done(self):
        raise NotImplementedError

    def result(self, timeout=None):
        """
        Wait for the `threading.Event` to be set, and then either return the
        `result` or raise the exception that occurred on the filling Thread.
        """
        self._finished.wait(timeout=timeout)
        if self._excinfo is None:
            return self._result
        else:
            cls, err, trc = self._excinfo
            if uproot4._util.py2:
                exec("raise cls, err, trc")
            else:
                raise err.with_traceback(trc)

    def exception(self, timeout=None):
        raise NotImplementedError

    def add_done_callback(self, fn):
        raise NotImplementedError


class ThreadResourceWorker(threading.Thread):
    """
    A Python Thread that controls one Resource and watches a `work_queue` for
    Futures to evaluate (as callables).
    """

    def __init__(self, resource, work_queue):
        """
        Args:
            resource (Resource): First argument passed to each Future's `task`
                callable.
            work_queue (queue.Queue): FIFO for work.

        This Thread pulls items from the `work_queue` or waits for it to be
        filled.

        If it receives a None from the `work_queue`, it shuts down.
        """
        super(ThreadResourceWorker, self).__init__()
        self.daemon = True
        self._resource = resource
        self._work_queue = work_queue

    @property
    def resource(self):
        """
        First argument passed to each Future's `task` callable.
        """
        return self._resource

    @property
    def work_queue(self):
        """
        FIFO for work.
        """
        return self._work_queue

    def run(self):
        """
        Listens to the `work_queue`, processing each Future it recieves.

        If it finds a None on the `work_queue`, the Thread shuts down.
        """
        while True:
            future = self._work_queue.get()
            if future is None:
                break

            assert isinstance(future, TaskFuture)
            try:
                future._result = future._task(
                    self._resource, *future._args, **future._kwargs
                )
            except Exception:
                future._excinfo = sys.exc_info()
            future._finished.set()


class ThreadResourceExecutor(Executor):
    """
    An Executor that manages Threads as well as Resources, such as file handles
    (one Resource per Thread).

    All Threads are shut down and Resources are released when exiting a context
    block.
    """

    def __init__(self, resources):
        """
        Args:
            resources (iterable of Resource): Resources, such as file handles,
                to manage; spawns one Thread per Resource.
        """
        self._work_queue = queue.Queue()
        self._workers = [ThreadResourceWorker(x, self._work_queue) for x in resources]
        for thread in self._workers:
            thread.start()

    @property
    def num_workers(self):
        """
        The number of Threads in this thread pool.
        """
        return len(self._workers)

    @property
    def workers(self):
        """
        The Threads in this thread pool.
        """
        return self._workers

    def __enter__(self):
        """
        Passes `__enter__` to the Resources attached to each worker.
        """
        for thread in self._workers:
            thread.resource.__enter__()

    def __exit__(self, exception_type, exception_value, traceback):
        """
        Passes `__exit__` to the Resources attached to each worker and shuts
        down the Threads in the thread pool.
        """
        self.shutdown()
        for thread in self._workers:
            thread.resource.__exit__(exception_type, exception_value, traceback)

    def submit(self, fn, *args, **kwargs):
        """
        Submits a function to be evaluated by a Thread in the thread pool.

        The Resource associated with that Thread is passed as the first argument
        to the callable `fn`.
        """
        task = TaskFuture(fn, *args, **kwargs)
        self._work_queue.put(task)
        return task

    def map(self, func, *iterables):
        """
        Like Python's Executor.
        """
        futures = [self.submit(func, x) for x in iterables]
        for future in futures:
            yield future.result()

    def shutdown(self, wait=True):
        """
        Puts None on the `work_queue` until all Threads get the message and
        shut down.
        """
        while any(thread.is_alive() for thread in self._workers):
            for x in range(len(self._workers)):
                self._work_queue.put(None)
            time.sleep(0.001)

#!/usr/bin/env python3
"""Run the benchmark test suite without requiring pytest."""

import contextlib
import importlib
import inspect
import re
import sys
import traceback
from pathlib import Path


class Skipped(Exception):
    pass


class _FakeRaises:
    def __init__(self, expected, match=None):
        self.expected = expected
        self.match = match

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            raise AssertionError(f"expected {self.expected.__name__} but no exception was raised")
        if not issubclass(exc_type, self.expected):
            return False
        if self.match is not None and re.search(self.match, str(exc_value)) is None:
            raise AssertionError(
                f"exception message {str(exc_value)!r} does not match {self.match!r}"
            )
        return True


class _FakeMark:
    @staticmethod
    def parametrize(argnames, argvalues):
        names = [n.strip() for n in argnames.split(",")]

        def decorator(func):
            def wrapper(*args, **kwargs):
                results = []
                for values in argvalues:
                    if len(names) == 1:
                        call_args = {names[0]: values}
                    else:
                        call_args = dict(zip(names, values))
                    results.append(func(**call_args))
                return results

            wrapper.__name__ = func.__name__
            return wrapper

        return decorator

    @staticmethod
    def skip(reason=""):
        def decorator(func):
            def wrapper(*args, **kwargs):
                raise AssertionError(f"skipped: {reason}")

            wrapper.__name__ = func.__name__
            return wrapper

        return decorator


class _FakePytest:
    raises = _FakeRaises
    mark = _FakeMark

    @staticmethod
    def skip(reason=""):
        raise Skipped(reason)

    @staticmethod
    def importorskip(name):
        try:
            return importlib.import_module(name)
        except ImportError as exc:
            raise Skipped(f"could not import {name}: {exc}") from exc


def _run_all_tests():
    sys.modules["pytest"] = _FakePytest()

    tests_dir = Path(__file__).resolve().parents[1] / "tests"
    failures = 0
    skipped = 0
    total = 0

    for path in sorted(tests_dir.glob("test_*.py")):
        module_name = f"async_vla_benchmark.tests.{path.stem}"
        try:
            module = __import__(module_name, fromlist=["*"])
        except Exception as exc:
            print(f"IMPORT FAIL {path.stem}: {exc}")
            failures += 1
            continue

        for name in dir(module):
            if not name.startswith("test_"):
                continue
            func = getattr(module, name)
            if not callable(func):
                continue
            total += 1
            try:
                func()
                print(f"PASS {module_name}.{name}")
            except Skipped as exc:
                skipped += 1
                print(f"SKIP {module_name}.{name}: {exc}")
            except Exception as exc:
                failures += 1
                print(f"FAIL {module_name}.{name}: {exc}")
                traceback.print_exc()

    passed = total - failures - skipped
    print(f"\n{passed} passed, {failures} failed, {skipped} skipped out of {total}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all_tests())

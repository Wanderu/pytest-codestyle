import py.io
import pycodestyle
import pytest


def pytest_addoption(parser):
    default_max_line_length = pycodestyle.MAX_LINE_LENGTH
    default_ignore = pycodestyle.DEFAULT_IGNORE.split(',')

    group = parser.getgroup('codestyle')
    group.addoption('--codestyle', action='store_true',
                    default=False, help='run pycodestyle')

    parser.addini('codestyle_max_line_length', default=pycodestyle.MAX_LINE_LENGTH,
                  help=f"set maximum allowed line length (default: {default_max_line_length})")
    parser.addini('codestyle_select', type='linelist',
                  help='select errors and warnings (default: [])')
    parser.addini('codestyle_ignore', type='linelist',
                  help=f"skip errors and warnings (default: [{' '.join(default_ignore)}])")
    parser.addini('codestyle_show_source', type="bool", default=True,
                  help='show source code for each error (default: True)')


def pytest_collect_file(parent, path):
    config = parent.config
    if config.option.codestyle and path.ext == '.py':
        return Item(path, parent)


class Item(pytest.Item, pytest.File):
    CACHE_KEY = 'codestyle/mtimes'

    def __init__(self, path, parent):
        super().__init__(path, parent)

    def setup(self):
        old_mtime = self.config.cache.get(self.CACHE_KEY, {}).get(str(self.fspath), -1)
        mtime = self.fspath.mtime()
        if old_mtime == mtime:
            pytest.skip('previously passed pycodestyle checks')

    def runtest(self):
        # http://pycodestyle.pycqa.org/en/latest/api.html#pycodestyle.Checker
        # http://pycodestyle.pycqa.org/en/latest/advanced.html
        checker = pycodestyle.Checker(
                        filename=self.fspath,
                        max_line_length=int(self.config.getini('codestyle_max_line_length')),
                        select=self.config.getini('codestyle_select'),
                        ignore=self.config.getini('codestyle_ignore'),
                        show_source=self.config.getini('codestyle_show_source')
                    )
        file_errors, out, err = py.io.StdCapture.call(checker.check_all)
        if file_errors > 0:
            raise CodeStyleError(out)
        else:
            # update cache
            # http://pythonhosted.org/pytest-cache/api.html
            cache = self.config.cache.get(self.CACHE_KEY, {})
            cache[str(self.fspath)] = self.fspath.mtime()
            self.config.cache.set(self.CACHE_KEY, cache)

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(CodeStyleError):
            return excinfo.value.args[0]
        else:
            return super().repr_failure(excinfo)

    def reportinfo(self):
        # https://github.com/pytest-dev/pytest/blob/4678cbeb913385f00cc21b79662459a8c9fafa87/_pytest/main.py#L550
        # https://github.com/pytest-dev/pytest/blob/4678cbeb913385f00cc21b79662459a8c9fafa87/_pytest/doctest.py#L149
        return self.fspath, None, 'pycodestyle-check'


class CodeStyleError(Exception):
    """custom exception for error reporting."""

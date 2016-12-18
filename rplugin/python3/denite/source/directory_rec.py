# ============================================================================
# FILE: directory_rec.py
# AUTHOR: Shougo Matsushita <Shougo.Matsu at gmail.com>
#         okamos <himinato.k at gmail.com>
# License: MIT license
# ============================================================================

from .base import Base
from denite.process import Process
from os.path import relpath, isabs, join
from copy import copy


class Source(Base):

    def __init__(self, vim):
        super().__init__(vim)

        self.name = 'directory_rec'
        self.kind = 'directory'
        self.vars = {
            'command': [],
            'min_cache_files': 10000,
        }
        self.__cache = {}

    def on_init(self, context):
        context['__proc'] = None
        directory = context['args'][0] if len(
            context['args']) > 0 else self.vim.call('getcwd')
        context['__directory'] = self.vim.call('expand', directory)

    def on_close(self, context):
        if context['__proc']:
            context['__proc'].kill()
            context['__proc'] = None

    def gather_candidates(self, context):
        if context['__proc']:
            return self.__async_gather_candidates(context, 0.5)

        if context['is_redraw']:
            self.__cache = {}

        directory = context['__directory']

        if directory in self.__cache:
            return self.__cache[directory]

        command = copy(self.vars['command'])
        if not self.vars['command']:
            if context['is_windows']:
                return []

            command = [
                'find', '-L', context['__directory'],
                '-path', '*/.git/*', '-prune', '-o',
                '-type', 'l', '-print', '-o', '-type', 'd', '-print']
        else:
            command.append(directory)
        context['__proc'] = Process(command, context, directory)
        context['__current_candidates'] = []
        return self.__async_gather_candidates(context, 2.0)

    def __async_gather_candidates(self, context, timeout):
        outs, errs = context['__proc'].communicate(timeout=timeout)
        context['is_async'] = not context['__proc'].eof()
        if context['__proc'].eof():
            context['__proc'] = None
        if not outs:
            return []
        if isabs(outs[0]):
            candidates = [{'word': relpath(x, start=context['__directory']),
                           'action__path': x}
                          for x in outs
                          if x != '' and x != context['__directory']]
        else:
            candidates = [{'word': x, 'action__path':
                           join(context['__directory'], x)}
                          for x in outs if x != '' and x != '.']
        context['__current_candidates'] += candidates
        if len(context['__current_candidates']) >= \
                self.vars['min_cache_files']:
            self.__cache[context['__directory']] = \
                context['__current_candidates']
        return candidates

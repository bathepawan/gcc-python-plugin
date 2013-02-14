#   Copyright 2012 David Malcolm <dmalcolm@redhat.com>
#   Copyright 2012 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

import os
import sys

from configbuilder import ConfigBuilder, CheckFor

class GccPythonPluginConfigBuilder(ConfigBuilder):
    def __init__(self, argv):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--gcc')
        parser.add_argument('--plugindir')
        args, argv = parser.parse_known_args(argv)
        ConfigBuilder.__init__(self, argv)
        self.gcc = args.gcc
        self.plugindir = args.plugindir
        self.extra_compilation_args = []

    def main(self):
        prefix = 'GCC_PYTHON_PLUGIN_CONFIG_'
        if self.plugindir:
            plugindir = self.plugindir
        else:
            plugindir = self.capture_shell_output('locating plugin directory for %s' % self.gcc,
                                            '%s --print-file-name=plugin' % self.gcc).strip()
        extraargs = ['-I%s' % os.path.join(plugindir, 'include')]
        self.test_for_mandatory_c_header('gcc-plugin.h', extraargs)

        self.test_whether_built_with_cplusplus()

        self.test_c_compilation(initmsg='checking whether plugin.def defines PLUGIN_FINISH_DECL',
                              src='''
#include <gcc-plugin.h>

int i[PLUGIN_FINISH_DECL];
''',
                              extraargs=extraargs,
                              description='Does plugin.def define PLUGIN_FINISH_DECL?',
                              defn=prefix+'has_PLUGIN_FINISH_DECL')
        self.write_outcome()
        self.write_EXTRA_CFLAGS()

    def test_whether_built_with_cplusplus(self):
        """
        Determine if the GCC was built with C++ or C
        """
        # According to http://gcc.gnu.org/ml/gcc/2012-03/msg00411.html
        # we should look in $(gcc -print-file-name=plugin)/include/auto-host.h
        # where we'll see either:
        #
        # Old 4.6, built with C:
        #   /* Define if building with C++. */
        #   #ifndef USED_FOR_TARGET
        #   /* #undef ENABLE_BUILD_WITH_CXX */
        #   #endif
        #
        # New 4.7, built with C++:
        #   /* Define if building with C++. */
        #   #ifndef USED_FOR_TARGET
        #   #define ENABLE_BUILD_WITH_CXX 1
        #   #endif
        #
        # 4.8, built with C++ doesn't have this (always built with C++)
        with CheckFor('Checking whether %s was built with C or C++' % self.gcc,
                      True) as check:
            def with_cplusplus():
                check.okmsg = 'C++'
                self.extra_compilation_args += ['-x', 'c++']
            def with_c():
                check.okmsg = 'C'
            auto_host_h = os.path.join(self.plugindir, 'include', 'auto-host.h')
            with open(auto_host_h, 'r') as f:
                content = f.read()
            if '/* #undef ENABLE_BUILD_WITH_CXX */' in content:
                with_c()
            elif '#define ENABLE_BUILD_WITH_CXX 1' in content:
                with_cplusplus()
            else:
                # Not found, assume C++:
                with_cplusplus()

    def write_EXTRA_CFLAGS(self):
        filename = 'autogenerated-EXTRA_CFLAGS.txt'
        sys.stdout.write('writing %s\n' % filename)
        with open(filename, 'w') as f:
            f.write(' '.join(self.extra_compilation_args))

ch = GccPythonPluginConfigBuilder(sys.argv)
ch.main()


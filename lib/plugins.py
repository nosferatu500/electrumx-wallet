#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2015 Thomas Voegtlin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import traceback
import sys
import os
import imp
import pkgutil

from util import *
from i18n import _
from util import print_error, profiler


class Plugins:

    @profiler
    def __init__(self, config, is_local, gui_name):
        if is_local:
            find = imp.find_module('plugins')
            plugins = imp.load_module('electrum_plugins', *find)
            self.pathname = find[1]
        else:
            plugins = __import__('electrum_plugins')
            self.pathname = None

        self.plugins = {}
        self.descriptions = plugins.descriptions
        for item in self.descriptions:
            name = item['name']
            if gui_name not in item.get('available_for', []):
                continue
            x = item.get('registers_wallet_type')
            if x:
                self.register_wallet_type(config, name, x)
            if config.get('use_' + name):
                self.load_plugin(config, name)

    def print_error(self, *msg):
        print_error("[%s]" % self.__class__.__name__, *msg)

    def get(self, name):
        return self.plugins.get(name)

    def count(self):
        return len(self.plugins)

    def load_plugin(self, config, name):
        full_name = 'electrum_plugins.' + name
        try:
            if self.pathname:  # local
                path = os.path.join(self.pathname, name + '.py')
                p = imp.load_source(full_name, path)
            else:
                p = __import__(full_name, fromlist=['electrum_plugins'])
            plugin = p.Plugin(config, name)
            self.plugins[name] = plugin
            self.print_error("loaded", name)
            return plugin
        except Exception:
            print_msg(_("Error: cannot initialize plugin"), name)
            traceback.print_exc(file=sys.stdout)
            return None

    def toggle_enabled(self, config, name):
        p = self.get(name)
        config.set_key('use_' + name, p is None, True)
        if p:
            self.plugins.pop(name)
            p.close()
            self.print_error("closed", name)
            return None
        return self.load_plugin(config, name)

    def is_available(self, name, w):
        for d in self.descriptions:
            if d.get('name') == name:
                break
        else:
            return False
        deps = d.get('requires', [])
        for dep, s in deps:
            try:
                __import__(dep)
            except ImportError:
                return False
        wallet_types = d.get('requires_wallet_type')
        if wallet_types:
            if w.wallet_type not in wallet_types:
                return False
        return True

    def wallet_plugin_loader(self, config, name):
        if self.plugins.get(name) is None:
            self.load_plugin(config, name)
        return self.plugins[name]
 
    def register_wallet_type(self, config, name, x):
        import wallet
        x += (lambda: self.wallet_plugin_loader(config, name),)
        wallet.wallet_types.append(x)

hook_names = set()
hooks = {}

def hook(func):
    hook_names.add(func.func_name)
    return func

def run_hook(name, *args):
    return _run_hook(name, False, *args)

def always_hook(name, *args):
    return _run_hook(name, True, *args)

def _run_hook(name, always, *args):
    results = []
    f_list = hooks.get(name, [])
    for p, f in f_list:
        if name == 'load_wallet':
            p.wallet = args[0]
        if name == 'init_qt':
            gui = args[0]
            p.window = gui.main_window
        if always or p.is_enabled():
            try:
                r = f(*args)
            except Exception:
                print_error("Plugin error")
                traceback.print_exc(file=sys.stdout)
                r = False
            if r:
                results.append(r)
        if name == 'close_wallet':
            p.wallet = None

    if results:
        assert len(results) == 1, results
        return results[0]


class BasePlugin:

    def __init__(self, config, name):
        self.name = name
        self.config = config
        self.wallet = None
        # add self to hooks
        for k in dir(self):
            if k in hook_names:
                l = hooks.get(k, [])
                l.append((self, getattr(self, k)))
                hooks[k] = l

    def close(self):
        # remove self from hooks
        for k in dir(self):
            if k in hook_names:
                l = hooks.get(k, [])
                l.remove((self, getattr(self, k)))
                hooks[k] = l

    def print_error(self, *msg):
        print_error("[%s]"%self.name, *msg)

    def requires_settings(self):
        return False

    @hook
    def load_wallet(self, wallet, window): pass

    @hook
    def close_wallet(self): pass

    #def init(self): pass

    def is_enabled(self):
        return self.is_available() and self.config.get('use_'+self.name) is True

    def is_available(self):
        return True

    def settings_dialog(self):
        pass

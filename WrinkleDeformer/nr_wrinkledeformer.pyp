# Copyright (C) 2014  Niklas Rosenstein
# All rights rights.

__author__ = 'Niklas Rosenstein <rosensteinniklas(at)gmail.com>'
__version__ = '1.0'

# ~~~~~~~~~~~~ localimport bootstrap ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# see https://gist.github.com/NiklasRosenstein/f5690d8f36bbdc8e5556
import os, sys, glob
class localimport(object):
    _modulecache = []
    _eggs = staticmethod(lambda x: glob.glob(os.path.join(x, '*.egg')))
    def __init__(self, libpath, autoeggs=False, foreclosed=False, path=os.path):
        if not path.isabs(libpath):
            libpath = path.join(path.dirname(path.abspath(__file__)), libpath)
        self.libpath = libpath; self.autoeggs = autoeggs; self.fclosed = foreclosed
    def __enter__(self):
        self._path, self._mpath = list(sys.path), list(sys.meta_path)
        self._mods = frozenset(sys.modules.keys())
        sys.path.append(self.libpath)
        sys.path.extend(self._eggs(self.libpath) if self.autoeggs else [])
    def __exit__(self, *args):
        sys.path[:] = self._path; sys.meta_path[:] = self._mpath
        for key in sys.modules.keys():
            if key not in self._mods and self._islocal(sys.modules[key]):
                localimport._modulecache.append(sys.modules.pop(key))
    def _islocal(self, mod):
        if self.fclosed: return True
        filename = getattr(mod, '__file__', None)
        if filename:
            try: s = os.path.relpath(filename, self.libpath)
            except ValueError: return False
            else: return s == os.curdir or not s.startswith(os.pardir)
        else: return False
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import os
import sys
import c4d
import logging

with localimport('lib'):
    import res; res.init(__file__, __res__)
    import knife

@apply
def logger():
    formatter = logging.Formatter('[%(name)s - %(levelname)s]: %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.Logger('WrinkleDeformer ' + __version__)
    logger.addHandler(handler)
    return logger

class WrinkleDeformer(c4d.plugins.ObjectData):

    PluginId = 1033765
    PluginName = res.string('WRINKLEDEFORMER_NAME')
    PluginDescription = "Onr_wrinkledeformer"
    PluginInfo = c4d.OBJECT_MODIFIER
    PluginIcon = res.bitmap('res', 'icon.png')

    @classmethod
    def register(cls):
        return c4d.plugins.RegisterObjectPlugin(
            cls.PluginId, cls.PluginName, cls, cls.PluginDescription,
            cls.PluginInfo, cls.PluginIcon)

    # c4d.plugins.ObjectData

    def ModifyObject(self, op, doc, pobj, pobj_mg, op_mg, lod, flags, thread):

        # Just make sure we don't operate on invalid data which
        # would cause an exception.
        if not pobj.IsInstanceOf(c4d.Opoint):
            logger.warn('Good thing we program safe. Got a non-point '
                'object in ModifyObject()')
            return True

        seed = op[res.NR_WRINKLEDEFORMER_SEED]
        iterations = op[res.NR_WRINKLEDEFORMER_ITERATIONS]

        text = res.string('WRINKLEDEFORMER_ACTIONTEXT', pobj.GetName())
        c4d.StatusSetText(text)
        c4d.StatusSetSpin()
        try:
            knife.randomize_cuts(pobj, iterations, seed)
        finally:
            c4d.StatusClear()
        return True

    # c4d.plugins.NodeData

    def Init(self, op):
        self.InitAttr(op, int, [res.NR_WRINKLEDEFORMER_SEED])
        self.InitAttr(op, int, [res.NR_WRINKLEDEFORMER_ITERATIONS])

        op[res.NR_WRINKLEDEFORMER_SEED] = 42892
        op[res.NR_WRINKLEDEFORMER_ITERATIONS] = 7
        return True

def main():
    if WrinkleDeformer.register():
        logger.info('registered')

if __name__ == "__main__":
    main()

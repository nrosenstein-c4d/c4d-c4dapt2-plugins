# Copyright (C) 2014  Niklas Rosenstein
# All rights rights.

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
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

import os, sys
import c4d, math, random
import logging
with localimport('library'):
    import res; res.init(__file__, __res__)

singleton = lambda x: x()

@singleton
def logger():
    logger = logging.Logger('PaperCut v' + __version__)
    formatter = logging.Formatter('[%(name)s - %(levelname)s]: %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class KnifeSession(object):
    """
    This class represents a session to apply commands using the
    knife tool on a Cinema 4D Point or Polygon Object.
    """

    def __init__(self, obj, options=None):
        super(KnifeSession, self).__init__()
        if not isinstance(obj, c4d.PointObject):
            raise TypeError('expected PointObject instance')
        self.obj = obj
        self.options = c4d.BaseContainer()
        if options: self.options.MergeContainer(options)

    def __setitem__(self, id_, value):
        self.options[id_] = value

    def __getitem__(self, id_):
        return self.options[id_]

    def cut(self, p1, n1, p2, n2):
        """
        Cut the object in the session with the specified input points
        and their direction. The normals should usually point into the
        same direction for "Line" cuts.

        ``n1.Cross(n2)`` builds the normal of the cutting plane. The
        coordinates must be given in world space.
        """

        data = self.options
        data.SetVector(c4d.MDATA_KNIFE_P1, p1)
        data.SetVector(c4d.MDATA_KNIFE_V1, n1)
        data.SetVector(c4d.MDATA_KNIFE_P2, p2)
        data.SetVector(c4d.MDATA_KNIFE_V2, n2)

        mode = c4d.MODELINGCOMMANDMODE_ALL
        flags = c4d.MODELINGCOMMANDFLAGS_0
        c4d.utils.SendModelingCommand(c4d.MCOMMAND_KNIFE, [self.obj],
            bc=data, mode=mode, doc=self.obj.GetDocument(), flags=flags)

    def randomize(self, iterations, seed):
        """
        Applies *iteration* cuts using randomly generated values based
        on the specified *seed* value.
        """

        rgen = random.Random(seed)
        rand = lambda: rgen.random() * 2 - 1
        rvgen = lambda: c4d.Vector(rand(), rand(), rand()).GetNormalized()

        mg = self.obj.GetMg()
        rad = self.obj.GetRad().GetLength()
        cuts = []

        for i in xrange(iterations):
            p1 = rvgen() * rad
            p2 = -p1
            p1 = mg * p1
            p2 = mg * p2

            n1 = rvgen()
            n2 = (p2 - p1).GetNormalized()
            p1 -= n1 * rad
            p2 -= n1 * rad

            off = n1.Cross(n2) * rad * rgen.random()
            p1 += off
            p2 += off

            cuts.append((p1, n1, p2, n2))
            self.cut(p1, n1, p2, n2)
        return cuts

class PaperCut(c4d.plugins.ObjectData):

    PluginId = 1033765
    PluginName = "PaperCut"
    PluginDescription = "Onrpapercutdeformer"
    PluginInfo = c4d.OBJECT_MODIFIER
    PluginIcon = res.bitmap('res', 'icon.png')

    @classmethod
    def register(cls):
        return c4d.plugins.RegisterObjectPlugin(
            cls.PluginId, cls.PluginName, cls, cls.PluginDescription,
            cls.PluginInfo, cls.PluginIcon)

    # c4d.plugins.ObjectData

    def CheckDirty(self, op, doc):
        op.SetDirty(c4d.DIRTYFLAGS_DATA)

    def ModifyObject(self, op, doc, pobj, pobj_mg, op_mg, lod, flags, thread):

        # Just make sure we don't operate on invalid data which
        # would cause an exception.
        if not pobj.IsInstanceOf(c4d.Opoint):
            logger.warn('Good thing we program safe. Got a non-point '
                'object in ModifyObject()')
            return True

        seed = op[res.NR_PAPERCUTDEFORMER_SEED]
        iterations = op[res.NR_PAPERCUTDEFORMER_ITERATIONS]

        session = KnifeSession(pobj)
        session.randomize(iterations, seed)
        return True

    # c4d.plugins.NodeData

    def Init(self, op):
        self.InitAttr(op, int, [res.NR_PAPERCUTDEFORMER_SEED])
        self.InitAttr(op, int, [res.NR_PAPERCUTDEFORMER_ITERATIONS])

        op[res.NR_PAPERCUTDEFORMER_SEED] = 42892
        op[res.NR_PAPERCUTDEFORMER_ITERATIONS] = 7
        return True

def main():
    print res.string('FOO', 'Peter', 'Sunny')
    print res.tup('FOO', 'Peter', 'Sunny')
    if PaperCut.register():
        logger.info('registered')

if __name__ == "__main__":
    main()


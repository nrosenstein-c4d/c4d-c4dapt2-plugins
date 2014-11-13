# Copyright (C) 2014  Niklas Rosenstein
# All rights rights.
#
# todo:
# - use the data from restriction tags
# - the StretchData should store the position locally

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0'

import os, sys
import c4d
import logging

singleton = lambda x: x()

class res:
    def __getitem__(self, name):
        value = getattr(self, name)
        return value, c4d.plugins.GeLoadString(value)
    def __call__(self, name):
        return c4d.plugins.GeLoadString(getattr(self, name))
    def file(self, *parts):
        return os.path.join(os.path.dirname(__file__), 'res', *parts)

    NR_STRETCHDEFORMER_INNER_RADIUS         = 1000
    NR_STRETCHDEFORMER_OUTER_RADIUS         = 1001
    NR_STRETCHDEFORMER_BTN_INITIALIZE       = 1002
    NR_STRETCHDEFORMER_BTN_FREE             = 1003
    NR_STRETCHDEFORMER_COMPRESS_STRENGTH    = 1004
    NR_STRETCHDEFORMER_FALLOFF_SPLINE       = 1005
    NR_STRETCHDEFORMER_COMPRESS_SPLINE      = 1006
    NR_STRETCHDEFORMER_COMPRESS_MAXDISTANCE = 1007
    Onrstretchdeformer                      = 1033758
res = res()

@singleton
def logger():
    logger = logging.Logger('StretchDeformer ' + __version__)
    formatter = logging.Formatter('[%(name)s - %(levelname)s]: %(message)s')
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def closest_point_to_line(a, b, p, clamp):
    # We could simply use
    #   n = (b - a).GetNormalized()
    #   return p + (a - p) - ((a - p) * n) * n
    # But it will not easily yield `t` from this formula:
    #   p = a + t * (b - a)
    # Which we need to figure if the value must be clamped.

    ab = (b - a)
    ab2 = ab.x ** 2 + ab.y ** 2 + ab.z ** 2
    if ab2 < 1e-6:
        return a

    ap = (p - a)
    ap_ab = ap.x * ab.x + ap.y * ab.y + ap.z * ab.z
    t = ap_ab / ab2
    if clamp:
        if t < 0.0: return a
        elif t > 1.0: return b

    return a + ab * t

def draw_line_sphere(bd, off, rad):
    """
    Draws a sphere constructed of three circles into the viewport.

    :param bd: The Cinema 4D BaseDraw object
    :param off: A Vector for the offset of the sphere.
    :param rad: A Vector defining the dimensions of the sphere.
    """

    def rotate(mat):
        """
        Rotates the components of a matrix, replace v1 with v2, v2
        with v3 and v3 with v1.
        """

        temp = mat.v1
        mat.v1 = mat.v2
        mat.v2 = mat.v3
        mat.v3 = temp

    mat = c4d.Matrix(off, c4d.Vector(rad.x, 0, 0),
        c4d.Vector(0, rad.y, 0), c4d.Vector(0, 0, rad.z))
    bd.DrawCircle(mat)
    rotate(mat)
    bd.DrawCircle(mat)
    rotate(mat)
    bd.DrawCircle(mat)

class Weight(object):
    """
    This helper class calculates linear weight for a value from
    a minimum and maximum value. If the value is equal or in
    between the minimum and maximum value, the resulting weight
    will be in range [0;1]. Optionally, the weight can be clamped
    to this range.
    """

    def __init__(self, minvalue, maxvalue, clamp, spline=None, default=1.0):
        super(Weight, self).__init__()
        self.minvalue = float(minvalue)

        divisor = float(maxvalue - minvalue)
        if abs(divisor) < 1e-6:
            self.multiplier = None
        else:
            self.multiplier = 1.0 / divisor

        self.clamp = clamp
        self.spline = spline
        self.default = float(default)

    def __call__(self, value):
        if self.multiplier is None:
            weight = self.default
        else:
            weight = (value - self.minvalue) * self.multiplier
            if self.clamp:
                if weight < 0: weight = 0.0
                elif weight > 1.0: weight = 1.0
        if self.spline:
            weight = self.spline.GetPoint(weight).y
        return weight

class StretchData(object):
    """
    This class contains data for calculating the stretch of an object
    for the Stretch Deformer, and also implements various helpers for
    doing the calculations.
    """

    @classmethod
    def from_hyperfile(cls, hf, disklevel):
        data = cls.__new__(cls)
        if not data.read(hf, disklevel):
            return None
        return data

    @classmethod
    def as_copy(cls, instance):
        data = cls.__new__(cls)
        instance.copy_to(data)
        return data

    def __init__(self, pos):
        super(StretchData, self).__init__()
        self.pos = pos

    def copy_to(self, other):
        other.pos = c4d.Vector(self.pos)

    def write(self, hf):
        if not hf.WriteVector(self.pos):
            return False
        return True

    def read(self, hf, disklevel):
        self.pos = c4d.Vector()

        pos = hf.ReadVector()
        if pos is None:
            return False
        self.pos = pos

        return True

class StretchDeformer(c4d.plugins.ObjectData):

    PluginId = 1033758
    PluginName = "Stretch"
    PluginDescription = "Onrstretchdeformer"
    PluginInfo = c4d.OBJECT_MODIFIER
    PluginIcon = None

    # These sets contain the IDs of the parameters that should be
    # disabled when the deformer is initialized/not initialized,
    # respectively.
    DisableDef = {
        'initialized': frozenset([
            res.NR_STRETCHDEFORMER_BTN_INITIALIZE,
            ]),
        'not-innitialized': frozenset([
            res.NR_STRETCHDEFORMER_BTN_FREE,
            res.NR_STRETCHDEFORMER_COMPRESS_STRENGTH,
            res.NR_STRETCHDEFORMER_FALLOFF_SPLINE,
            res.NR_STRETCHDEFORMER_COMPRESS_SPLINE,
            ]),
        }

    # Actions that should be performed when a description command
    # is received, optionally wrapped in a undo step. This is handled
    # in the Message() method.
    CommandActions = {
        res.NR_STRETCHDEFORMER_BTN_INITIALIZE: {
            'name': 'do_initialize',
            'init-undo': True,
            },
        res.NR_STRETCHDEFORMER_BTN_FREE: {
            'name': 'do_free',
            'init-undo': True,
            },
        }

    # This is the default value for the weight spline.
    @singleton
    def DefaultFalloffSpline():
        spline = c4d.SplineData()
        spline.MakeLinearSplineLinear(2)
        spline.Mirror()
        return spline

    # This is the default value for the stretch spline.
    @singleton
    def DefaultCompressSpline():
        spline = c4d.SplineData()
        spline.MakeUserSpline("1.0 - sin(x * PI)", 5)
        return spline

    @classmethod
    def register(cls):
        return c4d.plugins.RegisterObjectPlugin(
            cls.PluginId, cls.PluginName, cls, cls.PluginDescription,
            cls.PluginInfo, cls.PluginIcon)

    def __init__(self):
        super(StretchDeformer, self).__init__()
        self.data = None

    def do_initialize(self, op):
        if self.is_initialized():
            logger.warning('%s already initialized', op.GetName())
            return

        pos = op.GetMg().off
        self.data = StretchData(pos)
        op.SetDirty(c4d.DIRTYFLAGS_DATA)

    def do_free(self, op):
        if not self.is_initialized():
            logger.warning('nothing to free for %s', op.GetName())
            return

        self.data = None
        op.SetDirty(c4d.DIRTYFLAGS_DATA)

    def is_initialized(self):
        return self.data is not None

    # c4d.plugins.ObjectData

    def Draw(self, op, drawpass, bd, bh):
        if drawpass != c4d.DRAWPASS_OBJECT:
            return c4d.DRAWRESULT_SKIP

        # Set the matrix and color for future draw operations.
        mg = op.GetMg()
        bd.SetMatrix_Matrix(op, mg)
        bd.SetPen(c4d.GetViewColor(c4d.VIEWCOLOR_MODIFIER))

        # Get the inner and outer radius of the deformer and draw
        # line-cirlces into the viewport.
        inner_radius = op[res.NR_STRETCHDEFORMER_INNER_RADIUS]
        outer_radius = op[res.NR_STRETCHDEFORMER_OUTER_RADIUS]
        draw_line_sphere(bd, c4d.Vector(), c4d.Vector(inner_radius))
        draw_line_sphere(bd, c4d.Vector(), c4d.Vector(outer_radius))

        # Draw a line and a small dot to the origin of the Stretch
        # Deformer, if it is initialized.
        if self.is_initialized():
            origin = (~mg) * self.data.pos
            bd.DrawLine(c4d.Vector(), origin, 0)
            bd.DrawHandle(origin, c4d.DRAWHANDLE_BIG, 0)

        # Everything worked out fine.
        return c4d.DRAWRESULT_OK

    def ModifyObject(self, op, doc, pobj, pobj_mg, op_mg, lod, flags, thread):
        """
        This method is called to apply to let the deformer apply its
        deformations to the PolygonObject *pobj*.
        """

        # The documentation states that the 'pobj' parameter is a
        # BaseObject instance, it does not explicitly state that only
        # PointObjects are passed. That is usually, the case, but
        # we want to be sure ...
        if not pobj.CheckType(c4d.Opoint):
            logger.info('ModifyObject() got non-PointObject (%s). Good thing is: '
                'we write safe code!', pobj.GetName())
            return True

        # We don't do anything if the deformer was not initialized.
        # Still, its not an error so we return True.
        if not self.is_initialized():
            return True

        # Get the parameters from the deformer. Just in case we get
        # None instead of a SplineData object, we use the default one.
        inner_radius = op[res.NR_STRETCHDEFORMER_INNER_RADIUS]
        outer_radius = op[res.NR_STRETCHDEFORMER_OUTER_RADIUS]
        strength = op[res.NR_STRETCHDEFORMER_COMPRESS_STRENGTH]
        maxdistance = abs(op[res.NR_STRETCHDEFORMER_COMPRESS_MAXDISTANCE])
        falloff = op[res.NR_STRETCHDEFORMER_FALLOFF_SPLINE]
        if not falloff:
            falloff = StretchDeformer.DefaultFalloffSpline
        compress = op[res.NR_STRETCHDEFORMER_COMPRESS_SPLINE]
        if not compress:
            compress = StretchDeformer.DefaultCompressSpline

        # Extract the StretchData for quicker access and additional
        # data/calculators we will need.
        origin = self.data.pos
        shift = op_mg.off - origin
        if maxdistance < 1e-6:
            compress_strength = 1.0
        else:
            compress_strength = shift.GetLength() / maxdistance

        # For speed reasons, we pre-calculate the inverse-matrix
        # of the Point Object and use a calcuator for the weight
        # that is designed for that job.
        pobj_img = ~pobj_mg
        getfalloff = Weight(inner_radius, outer_radius, True, falloff)
        getcompress = Weight(0, shift.GetLength(), True, compress)

        # Get the points of the object that is to be deformed
        # and process them to reflect the modified state.
        points = pobj.GetAllPoints()
        new_points = []
        for point in points:

            # Compute the world position of the point.
            point = pobj_mg * point

            # Calculate the amount the current point should be
            # moved into the direction of the deformer.
            falloff = getfalloff((origin - point).GetLength())
            point += shift * falloff

            # Compute the closest point on the line between the
            # origin deformation position and its new position.
            closest = closest_point_to_line(origin, op_mg.off, point, True)

            # Based on the distance from the origin, we calculate the
            # "compression", the amount about which the real point
            # is moved towards the closest point on the line.
            compress = (1.0 - getcompress((closest - origin).GetLength()))

            # Move the point into the direction of the closest point
            # based on the calculated compress weight.
            if falloff > 0:
                final_compress = compress * strength * compress_strength
                if final_compress > 1.0:
                    final_compress = 1.0
                point += (closest - point) * final_compress

            # Make the point relative to the Point Object again and
            # add the point to the list of new points.
            new_points.append(pobj_img * point)

        # Update the points of the object.
        pobj.SetAllPoints(new_points)
        return True

    # c4d.plugins.NodeData

    def Init(self, op):
        # Initialize the data-types of the parameters.
        self.InitAttr(op, float, [res.NR_STRETCHDEFORMER_INNER_RADIUS])
        self.InitAttr(op, float, [res.NR_STRETCHDEFORMER_OUTER_RADIUS])
        self.InitAttr(op, c4d.SplineData, [res.NR_STRETCHDEFORMER_FALLOFF_SPLINE])
        self.InitAttr(op, c4d.SplineData, [res.NR_STRETCHDEFORMER_COMPRESS_SPLINE])
        self.InitAttr(op, float, [res.NR_STRETCHDEFORMER_COMPRESS_STRENGTH])
        self.InitAttr(op, float, [res.NR_STRETCHDEFORMER_COMPRESS_MAXDISTANCE])

        # Initialize the actual values.
        op[res.NR_STRETCHDEFORMER_INNER_RADIUS] = 100
        op[res.NR_STRETCHDEFORMER_OUTER_RADIUS] = 200
        op[res.NR_STRETCHDEFORMER_FALLOFF_SPLINE] = StretchDeformer.DefaultFalloffSpline
        op[res.NR_STRETCHDEFORMER_COMPRESS_SPLINE] = StretchDeformer.DefaultCompressSpline
        op[res.NR_STRETCHDEFORMER_COMPRESS_STRENGTH] = 1.0
        op[res.NR_STRETCHDEFORMER_COMPRESS_MAXDISTANCE] = 200
        return True

    def CopyTo(self, other, op, other_op, flags, atrans):
        """
        Copy the data from this ObjectData to ``other``, an instance
        of the same class. This is called, for instance, when copying
        a node, allowing it to copy any internal data.
        """

        if self.is_initialized():
            other.data = StretchData.as_copy(self.data)
        else:
            other.data = None

        return True

    def Write(self, op, hf):
        hf.WriteBool(self.is_initialized())
        if self.is_initialized():
            self.data.write(hf)
        return True

    def Read(self, op, hf, disklevel):
        has_data = hf.ReadBool()
        if has_data is None:
            return False

        data = StretchData.from_hyperfile(hf, disklevel)
        if data is None:
            return False
        self.data = data

        return True

    def Message(self, op, kind, data):
        if kind == c4d.MSG_DESCRIPTION_COMMAND:
            # Get the ID of the parameter for which the command was
            # sent and retreive the sctiony that should be executed
            # for it.
            paramid = data['id'][0].id
            action = StretchDeformer.CommandActions.get(paramid)

            if action:
                method = getattr(self, action['name'])
                init_undo = action.get('init-undo', False)
                undo_type = action.get('undo-type', c4d.UNDOTYPE_CHANGE)

                # Start an undo if that is desired.
                if init_undo:
                    doc = op.GetDocument()
                    doc.StartUndo()
                    doc.AddUndo(undo_type, op)

                try:
                    method(op)
                finally:
                    # Make sure to close the undo.
                    if init_undo:
                        doc.EndUndo()

        return True

    def GetDEnabling(self, node, descid, data, flags, itemdesc):
        paramid = descid[0].id
        if paramid in StretchDeformer.DisableDef['initialized']:
            return not self.is_initialized()
        elif paramid in StretchDeformer.DisableDef['not-innitialized']:
            return self.is_initialized()
        else:
            # Let the parent-class decide.
            return super(StretchDeformer, self).GetDEnabling(
                node, descid, data, flags, itemdesc)

def main():
    if StretchDeformer.register():
        logger.info('registered')

if __name__ == "__main__":
    main()

# Copyright (C) 2014  Niklas Rosenstein
# All rights rights.
'''
This module implements invoking the Knife Modeling Command from
Cinema 4D on a Polygon Object.
'''

__all__ = ['Session', 'cut']


import c4d
import random


class Session(object):
    '''
    If you're doing multiple cuts on an object, you should prefer to
    use this class instead of :meth:`cut` over and over again.

    :param obj: The :class:`c4d.PolygonObject`
    '''

    def __init__(self, obj):
        super(Session, self).__init__()
        if not isinstance(obj, c4d.PolygonObject):
            raise TypeError('expected c4d.PolygonObject for parameter `obj`')
        self.obj = obj
        self.data = c4d.BaseContainer()

    def __repr__(self):
        return 'knife.Session(obj={%s})' % self.obj.GetName()

    def cut(self, p1, p2, n1, n2):
        '''
        Executes the Knife Modeling Command, cutting the object the
        Session was initialized with the part plane spanned by *p1*,
        *p2*, *n1* and *n2*. The normals specify the direction in which
        the plane expands, respectively.
        '''

        data = self.data
        data.SetVector(c4d.MDATA_KNIFE_P1, p1)
        data.SetVector(c4d.MDATA_KNIFE_P2, p2)
        data.SetVector(c4d.MDATA_KNIFE_V1, n1)
        data.SetVector(c4d.MDATA_KNIFE_V2, n2)
        return c4d.utils.SendModelingCommand(
            c4d.MCOMMAND_KNIFE, [self.obj], bc=data,
            doc=self.obj.GetDocument())

    def randomize(self, n, seed):
        '''
        Create *n* random cuts on the object.
        '''

        mat = self.obj.GetMg()
        rad = self.obj.GetRad()

        # The "sphere_radius" is the amount that we need to move
        # the cutting plane away from the object to ensure that it
        # cuts the object as a whole.
        sphere_radius = rad.GetLengthSquared()

        # Create a random number generator and a function to
        # generate random numbers in range [-1;1].
        r = random.Random(seed)
        rand11 = lambda: r.random() * 2.0 - 1.0

        # Do "n" iterations and perform a cut each time.
        for __ in xrange(n):

            # We choose a random point that lies inside the geometry
            # of the Polygon Object (based on the result of GetRad()).
            midpoint = c4d.Vector(
                rand11() * rad.x,
                rand11() * rad.y,
                rand11() * rad.z)

            # Create a matrix that has a completely random alignment.
            rotation = get_random_rotation(r)

            # Determine the direction in which we need to shift the
            # cutting plane.
            direction = (rotation.v1 + rotation.v2) * 0.5

            # Offset the rotation matrix respectively into the direction
            # and multiply with the actual object's matrix.
            rotation.off = direction * -sphere_radius
            rotation = mat * rotation

            # Determine the plane based on the matrix.
            n1 = rotation.v1
            n2 = rotation.v2
            p1 = n1 + rotation.off
            p2 = n2 + rotation.off

            # Do the actual cut.
            self.cut(p1, p2, n1, n2)


def cut(obj, p1, p2, p3):
    '''
    See :meth:`Session.cut`.

    :param obj: The :class:`c4d.PolygonObject`
    '''

    return Session(obj).cut(p1, p2, p3)


def get_random_rotation(r=random):
    '''
    Creates a :class:`c4d.Matrix` that has a completely random
    rotation based on the random number generator *r*.
    '''

    rand11 = lambda: r.random() * 2.0 - 1.0
    randv1 = lambda: c4d.Vector(rand11(), rand11(), rand11())

    m = c4d.Matrix(v1=randv1(), v2=randv1())
    m.v3 = m.v1.Cross(m.v2)
    m.v2 = m.v1.Cross(m.v3)
    m.Normalize()
    return m

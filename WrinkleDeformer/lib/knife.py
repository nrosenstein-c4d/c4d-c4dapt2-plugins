# Copyright (C) 2014  Niklas Rosenstein
# All rights rights.

__all__ = ['Session', 'cut']

import c4d
import random

def cut(obj, p1, p2, v1, v2):
    data = c4d.BaseContainer()
    data.SetVector(c4d.MDATA_KNIFE_P1, p1)
    data.SetVector(c4d.MDATA_KNIFE_P2, p2)
    data.SetVector(c4d.MDATA_KNIFE_V1, v1)
    data.SetVector(c4d.MDATA_KNIFE_V2, v2)
    c4d.utils.SendModelingCommand(
        c4d.MCOMMAND_KNIFE, [obj], bc=data, doc=obj.GetDocument())

def randomize_cuts(dest, iterations, seed):
    # Create a random generator with the specified seed.
    r = random.Random(seed)

    # Read the matrix, mid-point and size from the target
    # object.
    mat = dest.GetMg()
    mid = dest.GetMp()
    rad = dest.GetRad()

    # We need to offset the cutting plane so that it is surely
    # not inside of the target object.
    offset_distance = rad.GetLength() * 4

    # Helper function to get a random value in range -1..1
    rand11 = lambda: r.random() * 2 - 1

    # Helper function to get a Vector with all three components
    # in the range of -1..1.
    randv = lambda: c4d.Vector(rand11(), rand11(), rand11())
    for __ in xrange(iterations):
        # Step 1) Choose a random point inside the bounding box
        # of the destination object. We do this by multiplying
        # each component of the `rad` vector with a random value
        # between -1 and 1.
        off = mid + rad ^ randv()

        # Step 2) Choose a random cutting plane spanned by two
        # vectors.  We use the cross-product to ensure they are
        # perpendicular.
        v1 = randv()
        v2 = v1.Cross(randv())

        # Step 3): Move the cutting plane offset away from the
        # object into the right direction (so the plane is still
        # cutting through the object).
        direction = (v1 + v2) * 0.5
        off -= direction * offset_distance

        # Step 4) Multiply with the target object's global matrix
        # to adjust to its offset and rotation. The direction
        # vectors should not be offset, so we use the no-offset
        # matrix.
        rot = c4d.Matrix(off, v1, v2, v2.Cross(v1))
        rot = rot.GetNormalized() * mat

        # Cut the object.
        cut(dest, rot.off, rot.off, rot.v1, rot.v2)

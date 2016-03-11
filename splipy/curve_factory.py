# -*- coding: utf-8 -*-

"""Handy utilities for creating curves."""

from math import pi, cos, sin, sqrt, ceil
from splipy import Curve, BSplineBasis
from splipy.utils import flip_and_move_plane_geometry
import numpy as np
import copy

__all__ = ['Boundary', 'line', 'polygon', 'n_gon', 'circle', 'circle_segment',
           'interpolate', 'least_square_fit', 'cubic_curve']

class Boundary:
    """Enumeration representing different boundary conditions used in
    :func:`interpolate`."""

    FREE = 1
    """The curve will be smooth at the second and second-to-last unique knot."""

    NATURAL = 2
    """The curve will have zero second derivatives at the endpoints."""

    HERMITE = 3
    """Specify the derivatives at the knots."""

    PERIODIC = 4
    """The curve will be periodic at the endpoints."""

    TANGENT = 5
    """Specify the tangents at the endpoints."""

    TANGENTNATURAL = 6
    """Use `TANGENT` for the start and `NATURAL` for the end."""


def line(a, b, relative=False):
    """Create a line between two points.

    :param point-like a: Start point
    :param point-like b: End point
    :param bool relative: Whether *b* is relative to *a*
    :return: Linear curve from *a* to *b*
    :rtype: Curve
    """
    if relative:
        b = tuple(ai + bi for ai, bi in zip(a, b))
    return Curve(controlpoints=[a, b])


def polygon(*points, **keywords):
    """polygon(points...)

    Create a linear interpolation between input points.

    :param [point-like] points: The points to interpolate
    :param bool relative: If controlpoints are interpreted as relative to the 
        previous one
    :return: Linear curve through the input points
    :rtype: Curve
    """
    if len(points) == 1:
        points = points[0]

    # establish knot vector based on eucledian length between points
    knot = [0, 0]
    prevPt = points[0]
    for pt in points[1:]:
        dist = 0
        for (x0, x1) in zip(prevPt, pt):  # loop over (x,y) and maybe z-coordinate
            dist += (x1 - x0)**2
        knot.append(knot[-1] + sqrt(dist))
        prevPt = pt
    knot.append(knot[-1])

    relative = keywords.get('relative', False)
    if relative:
        points = list(points)
        for i in range(1, len(points)):
            points[i] = [x0 + x1 for (x0,x1) in zip(points[i-1], points[i])]

    return Curve(BSplineBasis(2, knot), points)


def n_gon(n=5, r=1, center=(0,0,0), normal=(0,0,1)):
    """n_gon([n=5], [r=1])

    Create a regular polygon of *n* equal sides centered at the origin.

    :param int n: Number of sides and vertices
    :param float r: Radius
    :param point-like center: local origin
    :param vector-like normal: local normal
    :return: A linear, periodic, 2D curve
    :rtype: Curve
    :raises ValueError: If radius is not positive
    :raises ValueError: If *n* < 3
    """
    if r <= 0:
        raise ValueError('radius needs to be positive')
    if n < 3:
        raise ValueError('regular polygons need at least 3 sides')

    cp = []
    dt = 2 * pi / n
    knot = [-1]
    for i in range(n):
        cp.append([r * cos(i * dt), r * sin(i * dt)])
        knot.append(i)
    knot += [n, n+1]
    basis = BSplineBasis(2, knot, 0)

    result =  Curve(basis, cp)
    return flip_and_move_plane_geometry(result, center, normal)

def circle(r=1, center=(0,0,0), normal=(0,0,1), type='p2C0'):
    """circle([r=1])

    Create a circle.

    :param float r: Radius
    :param point-like center: local origin
    :param vector-like normal: local normal
    :param string type: The type of parametrization ('p2C0' or 'p4C1')
    :return: A periodic, quadratic rational curve
    :rtype: Curve
    :raises ValueError: If radius is not positive
    """
    if r <= 0:
        raise ValueError('radius needs to be positive')

    if type == 'p2C0' or type == 'C0p2':
        w = 1.0 / sqrt(2)
        controlpoints = [[1, 0, 1],
                         [w, w, w],
                         [0, 1, 1],
                         [-w, w, w],
                         [-1, 0, 1],
                         [-w, -w, w],
                         [0, -1, 1],
                         [w, -w, w]]
        knot = np.array([-1, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5]) / 4.0 * 2 * pi

        result = Curve(BSplineBasis(3, knot, 0), controlpoints, True)
    elif type == 'p4C1' or type == 'C1p4':
        w = 2*sqrt(2)/3
        a = 1.0/2/sqrt(2)
        b = 1.0/6 * (4*sqrt(2)-1)
        controlpoints = [[ 1,-a, 1],
                         [ 1, a, 1],
                         [ b, b, w],
                         [ a, 1, 1],
                         [-a, 1, 1],
                         [-b, b, w],
                         [-1, a, 1],
                         [-1,-a, 1],
                         [-b,-b, w],
                         [-a,-1, 1],
                         [ a,-1, 1],
                         [ b,-b, w]]
        knot = np.array([ -1, -1, 0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5]) / 4.0 * 2 * pi
        result = Curve(BSplineBasis(5, knot, 1), controlpoints, True)
    else:
        raise ValueError('Unkown type: %s' %(type))

    result *= r
    return flip_and_move_plane_geometry(result, center, normal)

def circle_segment(theta, r=1, center=(0,0,0), normal=(0,0,1)):
    """circle_segment(theta, [r=1])

    Create a circle segment starting paralell to the rotated x-axis.

    :param float theta: Angle in radians
    :param float r: Radius
    :return: A quadratic rational curve
    :rtype: Curve
    :raises ValueError: If radiusis not positive
    :raises ValueError: If theta is not in the range *[-2pi, 2pi]*
    """
    # error test input
    if abs(theta) > 2 * pi:
        raise ValueError('theta needs to be in range [-2pi,2pi]')
    if r <= 0:
        raise ValueError('radius needs to be positive')
    if theta == 2*pi:
        return circle(r, center, normal)

    # build knot vector
    knot_spans = int(ceil(theta / (2 * pi / 3)))
    knot = [0]
    for i in range(knot_spans + 1):
        knot += [i] * 2
    knot += [knot_spans]  # knot vector [0,0,0,1,1,2,2,..,n,n,n]
    knot = np.array(knot) / float(knot[-1]) * theta  # set parametic space to [0,theta]

    n = (knot_spans - 1) * 2 + 3  # number of control points needed
    cp = []
    t = 0  # current angle
    dt = float(theta) / knot_spans / 2  # angle step

    # build control points
    for i in range(n):
        w = 1 - (i % 2) * (1 - cos(dt))  # weights = 1 and cos(dt) every other i
        x = r * cos(t)
        y = r * sin(t)
        cp += [[x, y, w]]
        t += dt

    result = Curve(BSplineBasis(3, knot), cp, True)
    return flip_and_move_plane_geometry(result, center, normal)

def interpolate(x, basis, t=None):
    """interpolate(x, basis, [t=None])

    Perform general spline interpolation on a provided basis.

    :param matrix-like x: Matrix *X[i,j]* of interpolation points *xi* with
        components *j*
    :param BSplineBasis basis: Basis on which to interpolate
    :param array-like t: parametric values at interpolation points; defaults to
        Greville points if not provided
    :return: Interpolated curve
    :rtype: Curve
    """
    # wrap x into a numpy matrix
    x = np.matrix(x)

    # evaluate all basis functions in the interpolation points
    if t is None:
        t = basis.greville()
    N = basis.evaluate(t)

    # solve interpolation problem
    controlpoints = np.linalg.solve(N, x)

    return Curve(basis, controlpoints)

def least_square_fit(x, basis, t):
    """Perform a least-square fit of a point cloud onto a spline basis

    :param matrix-like x: Matrix *X[i,j]* of interpolation points *xi* with
        components *j*. The number of points must be equal to or larger than
        the number of basis functions in *basis*
    :param BSplineBasis basis: Basis on which to interpolate
    :param array-like t: parametric values at evaluation points
    :return: Approximated curve
    :rtype: Curve
    """
    # wrap x into a numpy matrix
    x = np.matrix(x)

    # evaluate all basis functions at evaluation points
    N = basis.evaluate(t)

    # solve interpolation problem
    controlpoints,_,_,_ = np.linalg.lstsq(N, x)

    return Curve(basis, controlpoints)


def cubic_curve(x, boundary=Boundary.FREE, t=None, tangents=None):
    """cubic_curve(x, [boundary=Boundary.FREE], [t=None], [tangents=None])

    Perform cubic spline interpolation on a provided basis.

    The valid boundary conditions are enumerated in :class:`Boundary`. The
    meaning of the `tangents` parameter depends on the specified boundary
    condition:

    - `TANGENT`: two points,
    - `TANGENTNATURAL`: one point,
    - `HERMITE`: *n* points

    :param matrix-like x: Matrix *X[i,j]* of interpolation points *x_i* with
        components *j*
    :param int boundary: Any value from :class:`Boundary`.
    :param array-like t: parametric values at interpolation points, defaults
        to Euclidean distance between evaluation points
    :param matrix-like tangents: Tangent information according to the boundary
        conditions.
    :return: Interpolated curve
    :rtype: Curve
    """
    n = len(x)
    if t is None:
        t = [0.0]
        for (x0,x1) in zip(x[:-1,:], x[1:,:]):
            # eucledian distance between two consecutive points 
            dist = np.linalg.norm(np.array(x1)-np.array(x0))
            t.append(t[-1]+dist)

    # modify knot vector for chosen boundary conditions
    knot = [t[0]]*3 + list(t) + [t[-1]]*3
    if boundary == Boundary.FREE:
        del knot[-5]
        del knot[4]
    elif boundary == Boundary.HERMITE:
        knot = sorted(knot + t[1:-1])

    # create the interpolation basis and interpolation matrix on this
    if boundary == Boundary.PERIODIC:
        knot[0]  = t[-3] - t[-1]
        knot[1]  = t[-2] - t[-1]
        knot[-2] = t[-1] + t[1]
        knot[-1] = t[-1] + t[2]
        basis = BSplineBasis(4, knot, 1)
    else:
        basis = BSplineBasis(4, knot)
    N = basis(t)  # left-hand-side matrix

    # add derivative boundary conditions if applicable
    if boundary in [Boundary.TANGENT, Boundary.HERMITE, Boundary.TANGENTNATURAL]:
        if boundary == Boundary.TANGENT:
            dn = basis([t[0], t[-1]], d=1)
            N  = np.resize(N, (N.shape[0]+2, N.shape[1]))
            x  = np.resize(x, (x.shape[0]+2, x.shape[1]))
        elif boundary == Boundary.TANGENTNATURAL:
            dn = basis(t[0], d=1)
            N  = np.resize(N, (N.shape[0]+1, N.shape[1]))
            x  = np.resize(x, (x.shape[0]+1, x.shape[1]))
        elif boundary == Boundary.HERMITE:
            dn = getBasis(t, d=1)
            N  = np.resize(N, (N.shape[0]+n, N.shape[1]))
            x  = np.resize(x, (x.shape[0]+n, x.shape[1]))
        x[n:,:] = tangents
        N[n:,:] = dn

    # add double derivative boundary conditions if applicable
    if boundary in [Boundary.NATURAL, Boundary.TANGENTNATURAL]:
        if boundary == Boundary.NATURAL:
            ddn  = basis([t[0], t[-1]], d=2)
            new  = 2
        elif boundary == Boundary.TANGENTNATURAL:
            ddn  = basis(t[-1], d=2)
            new  = 1
        N  = np.resize(N, (N.shape[0]+new, N.shape[1]))
        x  = np.resize(x, (x.shape[0]+new, x.shape[1]))
        N[-new:,:] = ddn
        x[-new:,:] = 0

    # solve system to get controlpoints
    cp = np.linalg.solve(N,x)

    # wrap it all into a curve and return
    return Curve(basis, cp)

def bezier(pts, quadratic=False, relative=False):
    """Generate a cubic or quadratic bezier curve from a set of control points

    :param [array-like] pts: list of control-points. In addition to a starting
        point we need three points per bezier interval for cubic splines and
        two points for quadratic splines
    :param bool quadratic: True if a quadratic spline is to be returned, False
        if a cubic spline is to be returned
    :param bool relative: If controlpoints are interpreted as relative to the 
        previous one
    :return: Bezier curve
    :rtype: Curve
    
    """
    if quadratic:
        p = 3
    else:
        p = 4
    # compute number of intervals
    n = int((len(pts)-1)/(p-1))
    # generate uniform knot vector of repeated integers
    knot = range(n+1) * (p-1) + [0, n]
    knot.sort()
    if relative:
        pts = copy.deepcopy(pts)
        for i in range(1, len(pts)):
            pts[i] = [x0 + x1 for (x0,x1) in zip(pts[i-1], pts[i])]
    return Curve(BSplineBasis(p, knot), pts)

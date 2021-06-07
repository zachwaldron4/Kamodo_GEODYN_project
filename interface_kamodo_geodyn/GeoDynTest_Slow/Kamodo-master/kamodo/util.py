"""
Copyright © 2017 United States Government as represented by the Administrator, National Aeronautics and Space Administration.  
No Copyright is claimed in the United States under Title 17, U.S. Code.  All Other Rights Reserved.
"""
import logging
import os
import tempfile
import sys
import numpy.f2py  # just to check it presents
from numpy.distutils.exec_command import exec_command


import sympy
from collections import OrderedDict, defaultdict
import collections
import functools
from sympy import sympify as parse_expr
from sympy.utilities.autowrap import ufuncify
import functools
from decorator import decorator, decorate
from sympy import symbols, Symbol
from sympy.core.function import UndefinedFunction
from inspect import getargspec, getfullargspec
import inspect
from sympy.physics import units
from sympy.physics import units as sympy_units
from sympy.physics.units.systems.si import dimsys_SI
import numpy as np
from sympy import latex, Eq
from sympy.parsing.latex import parse_latex
import pandas as pd
from scipy.integrate import solve_ivp
from sympy.physics.units.util import _get_conversion_matrix_for_expr

from sympy.core.compatibility import reduce, Iterable, ordered
from sympy import Add, Mul, Pow, Tuple, sympify, default_sort_key
from sympy.physics.units.quantities import Quantity
from sympy.physics.units import Dimension
from sympy import nsimplify
from sympy import Function

import urllib.request, json
import requests

import base64
import types
import forge

from sympy.physics.units import UnitSystem
from sympy.physics.units import Dimension




def get_unit_quantity(name, base, scale_factor, abbrev=None, unit_system='SI'):
    '''Define a unit in terms of a base unit'''
    unit = units.Quantity(name, abbrev=abbrev)
    base_unit = getattr(sympy_units, base)

    try:
        # sympy >= 1.5 raises the following warning:
        #   Use unit_system.set_quantity_dimension or
        # <unit>.set_global_relative_scale_factor
        unit.set_global_relative_scale_factor(scale_factor, base_unit)
    except AttributeError:
        unit.set_dimension(base_unit.dimension)
        unit.set_scale_factor(scale_factor * base_unit, unit_system=unit_system)

    return unit


unit_subs = dict(
    nT=get_unit_quantity('nanotesla', 'tesla', .000000001, 'nT', 'SI'),
    R_E=get_unit_quantity('earth radii', 'm', 6.371e6, 'R_E', 'SI'),
    R_S=get_unit_quantity('solar radii', 'm', 6.957e8, 'R_S', 'SI'),
    erg=get_unit_quantity('erg', 'J', .0000001, 'erg', 'SI'),
    nPa=get_unit_quantity('nanopascals', 'pascal', .000000001, 'nPa', 'SI'),
    cc=sympy_units.cm**3,
    AU=get_unit_quantity('astronomical unit', 'm', 1.496e+11, 'AU', 'SI'),
    arcsec=get_unit_quantity('arc seconds', 'degrees', 1./3600, '\"', 'SI'),
    )

sympy_units.erg = unit_subs['erg']

prefix_dict = sympy_units.prefixes.PREFIXES  #built-in dictionary of Prefix instances
#test_unit_subs={}  #dictionary to replace subs in kamodo.get_unit_quantities()
unit_list = ['m', 's', 'g', 'A', 'K', 'radian', 'sr', 'cd', 'mole', 'eV', 'Pa', 'F', 'N',
             'V', 'Hz', 'C', 'W', 'Wb', 'H', 'S', 'Bq', 'Gy', 'erg', 'T']

#list of SI units included in sympy (likely not complete)

for item in unit_list:
    unit_item = getattr(sympy_units, item)
    unit_subs[item] = unit_item
    for key in prefix_dict.keys():
        unit_subs[key+item] = get_unit_quantity(str(prefix_dict[key].name)+
                                                str(unit_item.name), str(unit_item.name),
                                                float(prefix_dict[key].scale_factor),
                                                abbrev=key+item)

reserved_names = dir(sympy)


def get_kamodo_unit_system():
    """Same as SI but supports anglular frequency"""

    radian = sympy.physics.units.radian
    degree = sympy.physics.units.degree
    si_unit_system = UnitSystem.get_unit_system('SI')
    si_dimension_system = si_unit_system.get_dimension_system()

    angle = Dimension('angle', 'A')

    kamodo_dims = si_dimension_system.extend(
        new_base_dims=(angle,),
        new_derived_dims=[Dimension('angular_velocity')],
        new_dim_deps={Symbol('angular_velocity'): {Symbol('angle'): 1, Symbol('time'): -1}})

    kamodo_units = si_unit_system.extend(
        (radian,),
        (radian, degree),
        dimension_system=kamodo_dims)

    return kamodo_units


kamodo_unit_system = get_kamodo_unit_system()

def get_ufunc(expr, variable_map):
    """Numerically optimize expression"""

    expr = sympify(expr, locals=variable_map)
    func = ufuncify(expr.free_symbols, expr)
    formula = 'f{} = {}'.format(tuple(expr.free_symbols), expr)
    return func, formula


def compile_fortran(source, module_name, extra_args='', folder='./'):
    """compile fortran source code"""
    with tempfile.NamedTemporaryFile('w', suffix='.f90') as fortran_file:
        fortran_file.write(source)
        fortran_file.flush()

        args = ' -c -m {} {} {}'.format(module_name, fortran_file.name, extra_args)
        command = 'cd "{}" && "{}" -c "import numpy.f2py as f2py;f2py.main()" {}'.format(
            folder, sys.executable, args)
        status, output = exec_command(command)
        return status, output, command


def substr_replace(name, name_maps):
    """replaces all substrings in name with those given by name_maps"""
    for old, new in name_maps:
        name = name.replace(old, new)
    return name


# This should be in yaml
def beautify_latex(expr):
    """convert string to latex-compatible expression"""
    return substr_replace(expr, [
        ('**', '^'),
        ('plus', '+'),
        ('minus', '-'),
        ('comma', ','),
        ('LEFT', '\\left ('),
        ('RIGHT', '\\right )'),
        ('integral', '\\int'),
        ('rvert', '\\rvert'),
        ('lvert', '\\lvert'),
    ])


def arg_to_latex(arg):
    return beautify_latex(latex(Symbol(arg)))


def decorator_wrapper(f, *args, **kwargs):
    """Wrapper needed by decorator.decorate to pass through args, kwargs"""
    return f(*args, **kwargs)


def kamodofy(
        _func=None,
        units='',
        arg_units=None,
        data=None,
        update=None,
        equation=None,
        citation=None,
        hidden_args=[],
        **kwargs):
    """Adds meta and data attributes to functions for compatibility with Komodo

    meta: a dictionary containing {units: <str>}
    data:
        if supplied, set f.data = data
        if not supplied, set f.data = f(), assuming it can be called with no arguments.
            If f cannot be called with no arguments, set f.data = None
    """

    def decorator_kamodofy(f):
        f.meta = dict(
            units=units,
            arg_units=arg_units,
            citation=citation,
            equation=equation,
            hidden_args=hidden_args)

        if citation is not None:
            if f.__doc__ is not None:
                f.__doc__ = f.__doc__ + '\n\ncitation: {}'.format(citation)
            else:
                f.__doc__ = 'citation: {}'.format(citation)
        f.update = update
        if data is None:
            try:
                f.data = f(**kwargs)
            except:
                f.data = None
        else:
            f.data = data

        if equation is not None:
            latex_str = equation.strip("$")
            f._repr_latex_ = lambda: latex_str
        # f._repr_latex_ = lambda : "${}$".format(latex(parse_latex(latex_str)))
        else:
            f_ = symbols(f.__name__, cls=UndefinedFunction)
            lhs = f_.__call__(*symbols(getfullargspec(f).args))
            # lambda_ = symbols('lambda', cls=UndefinedFunction)
            lambda_ = Function('lambda')
            latex_eq = latex(Eq(lhs, lambda_(*lhs.args)))
            f._repr_latex_ = lambda: "${}$".format(latex(latex_eq))

        return decorate(f, decorator_wrapper)  # preserves signature

    if _func is None:
        return decorator_kamodofy
    else:
        return decorator_kamodofy(_func)



def sort_symbols(symbols):
    symbols_ = list(symbols)
    symbols_.sort(key=str)
    return tuple(symbols_)


def valid_args(f, kwargs):
    '''Extract arguments from kwargs that appear in f'''
    valid = OrderedDict()
    if type(f) == np.vectorize:
        for a in inspect.getfullargspec(f.pyfunc).args:
            if a in kwargs:
                valid[a] = kwargs[a]
        return valid
    else:
        for a in getfullargspec(f).args:
            if a in kwargs:
                valid[a] = kwargs[a]
        return valid


def eval_func(func, kwargs):
    '''Evaluate function over valid argument'''
    try:
        return func(**valid_args(func, kwargs))
    except TypeError as m:
        raise TypeError(str(m) + str(list(valid_args(func, kwargs).keys())))


def get_defaults(func):
    sig = inspect.signature(func)
    defaults = {}
    for k, v in sig.parameters.items():
        if v.default is not inspect._empty:
            defaults[k] = v.default

    return defaults


def cast_0_dim(a, to):
    if a.ndim == 0:
        return a * np.ones(to.shape)
    else:
        return a


def simulate(state_funcs, **kwargs):
    """Iterate over functions.

    state_funcs(OrderedDict)
        key: the variable to update
        value: the function that updates the variable

    Any remaining kwargs are passed to the state functions.

    The order of the keys in state_funcs determines which variables get updated first.
    """

    verbose = kwargs.get('verbose', False)
    steps = kwargs.get('steps', 1)

    state_dict = kwargs.copy()
    yield OrderedDict([(k, state_dict.get(k, None)) for k in state_funcs])
    for i in range(steps):
        result = []
        for arg, f in list(state_funcs.items()):
            try:
                result.append((arg, eval_func(f, state_dict)))
            except TypeError as m:
                raise TypeError('{}:'.format(arg) + str(m))
            state_dict.update(OrderedDict(result))
        yield OrderedDict(result)


def pad_nan(array):
    if len(array.shape) == 1:
        # print('padding array {}'.format(array.shape))
        return np.pad(array.astype(float), (0, 1),
                      mode='constant', constant_values=np.nan).T
    elif len(array.shape) == 2:
        # print('padding array {}'.format(array.shape))
        return np.pad(array.astype(float), ((0, 1), (0, 0)),
                      mode='constant', constant_values=np.nan)
    else:
        raise NotImplementedError('cannot pad shape {}'.format(array.shape))


def concat_solution(gen, variable):
    """combine solutions of a function generator
    iterates through a function generator and extracts defaults for each function
    these solutions are then padded with nans and stacked

    stacking is vertically for N-d, horizontally for 1-d
    """
    result = []
    params = defaultdict(list)
    for f in gen:
        for k, v in list(get_defaults(f).items()):
            params[k].append(pad_nan(v))
        params[variable].append(pad_nan(f.data))

    for k, v in list(params.items()):
        if len(v[0].shape) == 1:
            params[k] = np.hstack(v)
        else:
            params[k] = np.vstack(v)
    return params


existing_plot_types = pd.DataFrame({
    ('1', 'N', 'N'): ['1-d line', ''],
    ('1', 'N', 'Nx2'): ['2-d line', ''],
    ('1', 'N', 'Nx3'): ['3-d line', ''],
    ('3', 'N, N, N', 'N'): ['3-d colored line', ''],
    ('1', 'Nx2', 'Nx2'): ['2-d vector field', ''],
    ('1', 'Nx3', 'Nx3'): ['3-d vector field', ''],
    ('2', 'N, M', 'NxM'): ['2-d contour', 'indexing'],
    ('2', 'NxM, NxM', 'NxM'): ['2-d contour (skew/carpet)', 'indexing'],
    ('3', 'NxM, NxM, NxM', '1'): ['Parametric Surface', ''],
    ('3', 'NxM, NxM, NxM', 'NxM'): ['Coloured Parametric Surface', ''],
    ('3', 'L, M, 1', 'LxM'): ['Map-to-plane', 'indexing*'],
    ('3', '1, M, N', 'MxN'): ['Map-to-plane', 'indexing*'],
    ('3', 'L, 1, N', 'LxN'): ['Map-to-plane', 'indexing*']
}).T
existing_plot_types.index.set_names(['nargs', 'arg shapes', 'out shape'], inplace=True)
existing_plot_types.columns = ['Plot Type', 'notes']

# manually generate the appropriate function signature
grid_wrapper_def_A = r"""def wrapped({signature}):
    coordinates = np.meshgrid({arg_str}, indexing = 'xy', sparse = False, copy = False)
    points = np.column_stack([c.ravel() for c in coordinates])
    out_shape = [-1] + list(coordinates[0].shape)
    return np.squeeze({fname}(points).reshape(out_shape, order = 'A'))
    """

grid_wrapper_def_C = r"""def wrapped({signature}):
    coordinates = np.meshgrid({arg_str}, indexing = 'ij', sparse = False, copy = False)
    points = np.column_stack([c.ravel() for c in coordinates])
    out_shape = list(coordinates[0].shape) + [-1]
    return np.squeeze({fname}(points).reshape(out_shape, order = 'C'))
    """


def gridify(_func=None, order='A', **defaults):
    """Given a function of shape (n,dim) and arguments of shape (L), (M), calls f with points L*M"""

    def decorator_gridify(f):

        arg_str = ', '.join([k for k in defaults])

        signature = ''
        for k, v in defaults.items():
            signature = signature + "{} = {},".format(k, k)

        scope = {**defaults}
        scope['np'] = np
        scope[f.__name__] = f

        if order == 'A':
            exec(grid_wrapper_def_A.format(signature=signature, arg_str=arg_str, fname=f.__name__), scope)
        elif order == 'C':
            exec(grid_wrapper_def_C.format(signature=signature, arg_str=arg_str, fname=f.__name__), scope)
        wrapped = scope['wrapped']
        wrapped.__name__ = f.__name__
        wrapped.__doc__ = f.__doc__

        return decorate(wrapped, decorator_wrapper)

    if _func is None:
        return decorator_gridify
    else:
        return decorator_gridify(_func)


def pointlike(_func=None, signature=None, otypes=[np.float], squeeze=None):
    """Transforms a single-argument function to one that accepts m points of dimension n"""

    def decorator_pointlike(func):
        def argument_wrapper(f, *args, **kwargs):
            """Wrapper needed by decorator.decorate to pass through args, kwargs"""
            if type(args[0]) != np.array:
                args = [np.array(x) for x in args]
            for i, x in enumerate(args):
                if len(x.shape) == 1:
                    args[i] = np.expand_dims(x, axis=0)
            if squeeze is not None:
                try:
                    return np.vectorize(f, otypes=otypes, signature=signature)(*args, **kwargs).squeeze(squeeze)
                except:
                    return np.vectorize(f, otypes=otypes, signature=signature)(*args, **kwargs)
            else:
                return np.vectorize(f, otypes=otypes, signature=signature)(*args, **kwargs)

        if not hasattr(func, '__name__'):
            func.__name__ = 'pointlike'

        return decorate(func, argument_wrapper)

    if _func is None:
        return decorator_pointlike
    else:
        return decorator_pointlike(_func)


def event(func, terminal=True, direction=0):
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)

    wrapped.terminal = terminal
    wrapped.direction = direction
    return wrapped


def solve(fprime=None, seeds=None, varname=None, interval=None,
          dense_output=True,  # generate a callable solution
          events=None,  # stop when event is triggered
          vectorized=True,
          npoints=50,
          directions=(-1, 1),
          verbose=False,
          ):
    """Decorator that solves initial value problem for a given function

    Can be used to generate streamlines, streaklines, fieldlines, etc
    """

    if len(seeds.shape) > 1:
        pass
    else:
        seeds = np.expand_dims(seeds, axis=0)

    t_eval = np.linspace(*interval, npoints)
    nseeds = len(seeds)

    def decorator_solve(f):
        solutions = []
        t = []

        fprime_ = {}
        for d in directions:
            fprime_[d] = lambda s, y: d * f(y.T)

        for i, seed in enumerate(seeds):
            for d in directions:
                result = solve_ivp(fprime_[d], interval, seed,
                                   dense_output=dense_output,
                                   events=events,
                                   vectorized=vectorized,
                                   t_eval=t_eval)
                solutions.append(result['sol'])
                interval_bounded = result['t']
                seed_numbers = np.ones(len(interval_bounded)) * i  # *len(directions) + 1*(d > 0)
                integrals = interval_bounded[::d] * d * 1j
                if d < 0:
                    t.extend(list(seed_numbers + integrals))
                else:
                    t.extend(list(seed_numbers + integrals)[1:])

        t = np.hstack(t)

        def solution(s=t):
            s = np.array(s)
            if len(s.shape) == 0:
                s = np.expand_dims(s, axis=0)

            isolution = np.floor(s.real).astype(int) * len(directions) + (s.imag > 0)

            results = []
            seed_number = []
            integral = []
            for soln, imag_ in zip(isolution, s.imag):
                seed_number.append(np.floor(soln / len(directions)))
                integral.append(imag_)
                try:
                    if np.isnan(abs(soln + imag_)):
                        results.append(np.ones(isolution.shape[-1]) * np.nan)
                    else:
                        results.append(solutions[soln](np.abs(imag_)))
                except:
                    results.append(np.ones(isolution.shape[-1]) * np.nan)
            index_ = pd.MultiIndex.from_arrays([seed_number, integral],
                                               names=['seed', 'integral'])
            return pd.DataFrame(np.vstack(results), index=index_).drop_duplicates()

        solution.__name__ = varname

        return decorate(solution, decorator_wrapper)  # preserves signature

    if fprime is None:
        return decorator_solve
    else:
        return decorator_solve(fprime)


def convert_unit_to(expr, target_units, unit_system=kamodo_unit_system, raise_errors=True):
    """
    Same as sympy.convert_to but accepts equations and allows functions of units to pass

    Convert ``expr`` to the same expression with all of its units and quantities
    represented as factors of ``target_units``, whenever the dimension is compatible.

    ``target_units`` may be a single unit/quantity, or a collection of
    units/quantities.

    Examples
    ========

    >>> from sympy.physics.units import speed_of_light, meter, gram, second, day
    >>> from sympy.physics.units import mile, newton, kilogram, atomic_mass_constant
    >>> from sympy.physics.units import kilometer, centimeter
    >>> from sympy.physics.units import gravitational_constant, hbar
    >>> from sympy.physics.units import convert_to
    >>> convert_to(mile, kilometer)
    25146*kilometer/15625
    >>> convert_to(mile, kilometer).n()
    1.609344*kilometer
    >>> convert_to(speed_of_light, meter/second)
    299792458*meter/second
    >>> convert_to(day, second)
    86400*second
    >>> 3*newton
    3*newton
    >>> convert_to(3*newton, kilogram*meter/second**2)
    3*kilogram*meter/second**2
    >>> convert_to(atomic_mass_constant, gram)
    1.660539060e-24*gram

    Conversion to multiple units:

    >>> convert_to(speed_of_light, [meter, second])
    299792458*meter/second
    >>> convert_to(3*newton, [centimeter, gram, second])
    300000*centimeter*gram/second**2

    Conversion to Planck units:

    >>> from sympy.physics.units import gravitational_constant, hbar
    >>> convert_to(atomic_mass_constant, [gravitational_constant, speed_of_light, hbar]).n()
    7.62963085040767e-20*gravitational_constant**(-0.5)*hbar**0.5*speed_of_light**0.5

    """


    from sympy.physics.units import UnitSystem
    unit_system = UnitSystem.get_unit_system(unit_system)

    if not isinstance(target_units, (Iterable, Tuple)):
        target_units = [target_units]


    if hasattr(expr, 'rhs'):
        return Eq(convert_unit_to(expr.lhs, target_units, unit_system),
            convert_unit_to(expr.rhs, target_units, unit_system))
    # if type(type(expr)) is UndefinedFunction:
    if is_function(expr):
        # print('undefined input expr:{}'.format(expr))
        return nsimplify(expr, rational=True)

    if isinstance(expr, Add):
        return Add.fromiter(convert_unit_to(i, target_units, unit_system) for i in expr.args)

    expr = sympify(expr)

    if not isinstance(expr, Quantity) and expr.has(Quantity):
        try:
            expr = expr.replace(
                lambda x: isinstance(x, Quantity),
                lambda x: x.convert_to(target_units, unit_system))
        except OSError:
            raise OSError('problem converting {} to {}\n{}'.format(
                expr, target_units, unit_system))

    def get_total_scale_factor(expr):
        if isinstance(expr, Mul):
            return reduce(lambda x, y: x * y, [get_total_scale_factor(i) for i in expr.args])
        elif isinstance(expr, Pow):
            return get_total_scale_factor(expr.base) ** expr.exp
        elif isinstance(expr, Quantity):
            return unit_system.get_quantity_scale_factor(expr)
        return expr

    if expr == target_units:
        return expr

    depmat = _get_conversion_matrix_for_expr(expr, target_units, unit_system)
    if depmat is None:
        if raise_errors:
            raise NameError('cannot convert {} to {} {}'.format(expr, target_units, unit_system))
        return nsimplify(expr, rational=True)

    expr_scale_factor = get_total_scale_factor(expr)
    result = expr_scale_factor * Mul.fromiter(
        (1/get_total_scale_factor(u) * u) ** p for u, p in zip(target_units, depmat))
    return nsimplify(result, rational=True)


def get_expr_unit(expr, unit_registry, verbose=False):
    '''Get units from an expression'''
    if is_function(expr):
        for func in unit_registry:
            if type(expr) == type(func):
                # b(a) = b(x)
                if verbose:
                    print('get_expr_unit: found match {} for {}'.format(func, expr))
                # {f(x): f(cm), f(cm): kg}
                func_units = unit_registry[func]
                if func_units in unit_registry:
                    return unit_registry[func_units]
                return func_units
        if verbose:
            print('get_expr_unit: no match found for {}'.format(expr))

    if isinstance(expr, Mul):
        results = []
        for arg in expr.args:
            result = get_expr_unit(arg, unit_registry, verbose)
            if result is not None:
                results.append(result)
        if len(results) > 0:
            return Mul.fromiter(results)
        else:
            return None

    if len(unit_registry) > 0:
        expr_unit = expr.subs(
            unit_registry, simultaneous=False).subs(
                unit_registry, simultaneous=False)
    else:
        expr_unit = expr

    if len(expr_unit.free_symbols) > 0:
        return None

    if isinstance(expr_unit, Add):
        # use the first term
        arg_0 = expr_unit.args[0]
        convert_unit_to(expr_unit, arg_0, kamodo_unit_system)
        result = arg_0
    else:
        result = expr_unit

    # if len(result.free_symbols) > 0:
    #     return None

    return get_base_unit(result)


def get_arg_units(expr, unit_registry, arg_units=None):
    """retrieves units of expression arguments
    """
    if arg_units is None:
        arg_units = dict()

    if expr in unit_registry:
        # unit_registry: {f(cm,km): kg}
        if is_function(unit_registry[expr]):
            for arg_, arg_unit in zip(expr.args, unit_registry[expr].args):
                arg_units[arg_] = arg_unit
        return arg_units

    # 2*a(x)
    for arg in expr.args:
        arg_units = get_arg_units(arg, unit_registry, arg_units)
    return arg_units

def replace_args(expr, from_map, to_map):
    # func_symbol = type(expr)
    arg_map = dict()
    for arg in expr.free_symbols:
        if (arg in from_map) & (arg in to_map):
            from_unit = from_map[arg]
            to_unit = to_map[arg]
            try:
                assert get_dimensions(from_unit) == get_dimensions(to_unit)
                arg_map[arg] = convert_unit_to(
                    arg*to_unit,
                    from_unit,
                    kamodo_unit_system)/from_unit
            except:
                raise NameError('cannot convert from {} to {}'.format(from_unit, to_unit))
    return expr.subs(arg_map)

def unify_args(expr, unit_registry, to_symbol, verbose):
    """replaces arguments in an expression"""
    expr_units = get_arg_units(expr, unit_registry)
    to_units = get_arg_units(to_symbol, unit_registry)
    if verbose:
        print('unify_args: {} arg units {}'.format(expr, expr_units))
        print('unify_args: to arg units', to_units)
    expr = replace_args(expr, expr_units, to_units)
    if verbose:
        print('unify_args: converted expression:', expr)
    return expr

def unify(expr, unit_registry, to_symbol=None, verbose=False):
    """adds unit conversion factors to composed functions"""
    if verbose:
        print('unify: to_symbol:', to_symbol)
    if hasattr(expr, 'rhs'):
        return Eq(expr.lhs, unify(
            expr.rhs,
            unit_registry,
            to_symbol=expr.lhs,
            verbose=verbose))
    if isinstance(expr, Add):
        if verbose:
            print('unify: Adding expression: {} -> {}'.format(
                expr, get_expr_unit(to_symbol, unit_registry, verbose)))
        return Add.fromiter([unify(arg, unit_registry, to_symbol, verbose) for arg in expr.args])

    expr_unit = get_expr_unit(expr, unit_registry, verbose)

    if verbose:
        print('unify: {} unit {}'.format(expr, expr_unit))
        print('unify: {} symbols {}'.format(expr, expr.free_symbols))
        print('unify: {} symbols {}'.format(to_symbol, to_symbol.free_symbols))
    try:
        assert expr.free_symbols.issubset(to_symbol.free_symbols)
    except:
        raise NameError("{} arguments not in {}".format(
            expr.free_symbols, to_symbol.free_symbols))

    if is_function(expr):
        if verbose:
            print('unify: function expression: {}'.format(expr))
        if to_symbol is not None:
            if verbose:
                print('\nunify: to_symbol args: {}'.format(to_symbol.args))
                print('unify: to_symbol free symbols: {}'.format(to_symbol.free_symbols))
                print('unify: expr args: {}'.format(expr.args))
                print('unify: expr free symbols: {}'.format(expr.free_symbols))

            for k, v in unit_registry.items():
                if isinstance(expr, type(k)):
                    if len(k.free_symbols) > 0:
                        if verbose:
                            print('unify: found matching {} -> {}'.format(expr, k))
                        arg_units = get_arg_units(k, unit_registry)
                        if verbose:
                            print('unify: func units:', arg_units)
                            print('unify: {}->{}'.format(expr.args, k.args))
                        expr_units = {}
                        for arg, sym in zip(expr.args, k.args):
                            to_unit = arg_units.get(sym)
                            from_unit = get_expr_unit(arg, unit_registry)
                            if (from_unit is not None) and (to_unit is not None):
                                expr_units[arg] = convert_unit_to(
                                    arg*from_unit,
                                    to_unit,
                                    kamodo_unit_system)/to_unit
                        expr = expr.subs(expr_units)

                        if verbose:
                            print('unify: replaced args', expr)

    expr = unify_args(expr, unit_registry, to_symbol, verbose)

    if (to_symbol is not None) & (expr_unit is not None):
        to_unit = get_expr_unit(to_symbol, unit_registry, verbose)
        if verbose:
            print('unify: to_unit {}'.format(to_unit))
        expr_dimensions = get_dimensions(expr_unit)
        to_dimensions = get_dimensions(to_unit)
        if expr_dimensions.compare(to_dimensions) == 0:
            if verbose:
                print('unify: {} [{}] -> to_symbol: {}[{}]'.format(
                    expr, expr_unit, to_symbol, to_unit))
            expr = convert_unit_to(
                expr*expr_unit,
                to_unit,
                kamodo_unit_system)/to_unit
        else:
            if verbose:
                print('unify: registry:')
                for k, v in unit_registry.items():
                    print('unify:\t{} -> {}'.format(k, v))
                print('compare:{}'.format(expr_dimensions.compare(to_dimensions)))
                error_msg = 'cannot convert {} [{}] {} to {}[{}] {}'.format(
                expr, expr_unit, expr_dimensions,
                to_symbol, to_unit, to_dimensions)
                print(error_msg)
            raise NameError(error_msg)

    return expr

def get_abbrev(unit):
    """get the abbreviation for a mixed unit"""
    if hasattr(unit, 'abbrev'):
        return unit.abbrev
    if isinstance(unit, Mul):
        return Mul.fromiter([get_abbrev(arg) for arg in unit.args])
    if isinstance(unit, Pow):
        base, exp = unit.as_base_exp()
        return Pow(get_abbrev(base), exp)
    return unit


def base_dimensions(d):
    dependencies = dimsys_SI.get_dimensional_dependencies(d)
    return Mul.fromiter(Pow(Dimension(base), exp_) for base, exp_ in dependencies.items())

def get_dimensions(unit):
    """get the set of basis units"""
    if hasattr(unit, 'dimension'):
        base_dims = base_dimensions(unit.dimension)
        if len(base_dims.args) == 1:
            return base_dims.args[0]
        else:
            return Mul.fromiter([arg.args[0] for arg in base_dimensions(unit.dimension).args])
    if isinstance(unit, Mul):
        terms = [get_dimensions(arg) for arg in unit.args]
        return Mul.fromiter(terms)
    if isinstance(unit, Pow):
        base, exp = unit.as_base_exp()
        return Pow(get_dimensions(base), exp)
    return 1


def get_base_unit(expr):
    if hasattr(expr, 'dimension'):
        return expr
    if isinstance(expr, Mul):
        results = []
        for arg in expr.args:
            result = get_base_unit(arg)
            if result is not None:
                results.append(result)
        if len(results) > 0:
            return Mul.fromiter(results)
        else:
            return None
    if isinstance(expr, Pow):
        base, exp = expr.as_base_exp()
        return Pow(get_base_unit(base), exp)
    if isinstance(expr, Add):
        results = [get_dimensions(arg) for arg in expr.args]
        arg0_dimensions = results[0]
        for r in results:
            try:
                assert arg0_dimensions == r
            except:
                print(results)
                raise
        return get_base_unit(expr.args[0])
    return None

def is_function(expr):
    """returns True if expr is a function

    examples:
        f(x): True
        symbols('f', cls=UndefinedFunction): True
        x: False
    """
    if isinstance(expr, UndefinedFunction):
        return True
    return isinstance(type(expr), UndefinedFunction)


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
    
class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyArrayEncoder, self).default(obj)

def full_classname(o):
    module = o.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return o.__class__.__name__
    return module + '.' + o.__class__.__name__

def serialize(obj):
    if isinstance(obj, (np.ndarray, np.generic)):
        if isinstance(obj, np.ndarray):
            return {
                # '__ndarray__': base64.b64encode(obj.tobytes()),
                '__ndarray__': obj.tolist(),
                'dtype': obj.dtype.str,
                'shape': obj.shape,
            }
        elif isinstance(obj, (np.bool_, np.number)):
            return {
                # '__npgeneric__': base64.b64encode(obj.tobytes()),
                '__ndarray__': obj.tolist(),
                'dtype': obj.dtype.str,
            }
    if isinstance(obj, pd.DataFrame):
        return {
            '__pddataframe__': obj.values.tolist(),
            '__index__': serialize(obj.index),
            'dtype': full_classname(obj),
        }
    if isinstance(obj, pd.Index):
        if isinstance(obj, pd.DatetimeIndex):
            return {
                '__datetime__': [_ for _ in map(pd.datetime.isoformat, obj)],
                'dtype': full_classname(obj),
            }
        else:
            return {
                '__index__': obj.tolist(),
                'dtype': full_classname(obj),
            }
    if isinstance(obj, pd.Series):
        return {
            '__pdseries__': obj.values.tolist(),
            '__index__': serialize(obj.index),
            'dtype': full_classname(obj),
        }
    if isinstance(obj, set):
        return {'__set__': list(obj)}
    if isinstance(obj, tuple):
        return {'__tuple__': list(obj)}
    if isinstance(obj, complex):
        return {'__complex__': obj.__repr__()}

    if isinstance(obj, types.GeneratorType):
        return {'__lambdagen__': [{
            'params':{k:serialize(v) for k, v in get_defaults(func).items()},
            'result':serialize(func())} for func in obj]}

    if isinstance(obj, int):
        return obj

    # Let the base class default method raise the TypeError
    raise TypeError('Unable to serialise object of type {}'.format(type(obj)))

def lambdagen(obj):
    """create a generator of lambda functions"""
    for func_ in obj['__lambdagen__']:
        signature = []
        for arg, arg_default in func_['params'].items():
            signature.append(forge.arg(
                arg,
                default=deserialize(arg_default)))
        @forge.sign(*signature)
        def func(*args, **kwargs):
            """API function"""
            return deserialize(func_['result'])

        yield kamodofy(func)
    
def deserialize(obj):
    # convert obj into numpy, pandas
    if isinstance(obj, dict):
        if '__ndarray__' in obj:
            # return np.frombuffer(
            #     base64.b64decode(obj['__ndarray__']),
            #     dtype=np.dtype(obj['dtype'])
            # ).reshape(obj['shape'])
            return np.array(obj['__ndarray__'])
        if '__npgeneric__' in obj:
            # return np.frombuffer(
            #     base64.b64decode(obj['__npgeneric__']),
            #     dtype=np.dtype(obj['dtype'])
            # )[0]
            return np.array(obj['__npgeneric__'])
        if '__pddataframe__' in obj:
            return pd.DataFrame(
                obj['__pddataframe__'],
                index=deserialize(obj['__index__']))
        if '__pdseries__' in obj:
            return pd.Series(
                obj['__pdseries__'],
                index=deserialize(obj['__index__']))
        if '__datetime__' in obj:
            return pd.to_datetime(obj['__datetime__'])
        if '__index__' in obj:
            return pd.Index(obj['__index__'])
        if '__set__' in obj:
            return set(obj['__set__'])
        if '__tuple__' in obj:
            return tuple(obj['__tuple__'])
        if '__complex__' in obj:
            return complex(obj['__complex__'])
        if '__lambdagen__' in obj:
            return lambdagen(obj)

    return obj

# over-write the load(s)/dump(s) functions
def load(*args, **kwargs):
    kwargs['object_hook'] = deserialize
    return json.load(*args, **kwargs)


def loads(*args, **kwargs):
    kwargs['object_hook'] = deserialize
    return json.loads(*args, **kwargs)


def dump(*args, **kwargs):
    kwargs['default'] = serialize
    return json.dump(*args, **kwargs)


def dumps(*args, **kwargs):
    kwargs['default'] = serialize
    return json.dumps(*args, **kwargs)

def get_undefined_funcs(expr):
    """retrieve an expression's undefined functions"""
    return expr.atoms(sympy.function.AppliedUndef)

def sign_defaults(symbol, expr, composition):
    '''gets defaults from an expression using composition'''
    defaults={}
    for f_ in get_undefined_funcs(expr):
        # includes {h(f(g)), f(g)}
        if str(f_) in composition:
            # ignores h(f(g))
            f_defaults = get_defaults(composition[str(f_)])
            # flatten defaults
            for arg, arg_default in f_defaults.items():
                defaults[arg] = arg_default

    arg_signatures = []
    # defaults have to go last, which may conflict with user's ordering
    for arg in symbol.args:
        str_arg = str(arg)
        if str_arg in defaults:
            arg_default=defaults[str(arg)]
            arg_signatures.append(forge.arg(str_arg, default=arg_default))
        else:
            arg_signatures.append(forge.arg(str_arg))

    # will raise an error if defaults are not last
    signature = forge.sign(*arg_signatures)
    return signature

class LambdaGenerator(object):
    def __init__(self, lambda_generator):
        """supports simple expressions for manipulating lambda generators"""
        self._lambda_generator = lambda_generator

    def __add__(self, other):
        if isinstance(other, LambdaGenerator):
            for func, gunc in zip(self._lambda_generator, other._lambda_generator):
                yield lambda: func()+gunc()
        else:
            for func in self._lambda_generator:
                yield lambda: func()+other
    def __sub__(self, other):
        if isinstance(other, LambdaGenerator):
            for func, gunc in zip(self._lambda_generator, other._lambda_generator):
                yield lambda: func()-gunc()
        else:
            for func in self._lambda_generator:
                yield lambda: func()-other
    def __mul__(self, other):
        if isinstance(other, LambdaGenerator):
            for func, gunc in zip(self._lambda_generator, other._lambda_generator):
                # what do we do with defaults?
                yield lambda: func()*gunc()
        else:
            for func in self._lambda_generator:
                yield lambda: func()*other
    def __truediv__(self, other):
        if isinstance(other, LambdaGenerator):
            for func, gunc in zip(self._lambda_generator, other._lambda_generator):
                # what do we do with defaults?
                yield lambda: func().__truediv__(gunc())
        else:
            for func in self._lambda_generator:
                yield lambda: func().__truediv__(other)
    def __floordiv__(self, other):
        if isinstance(other, LambdaGenerator):
            for func, gunc in zip(self._lambda_generator, other._lambda_generator):
                # what do we do with defaults?
                yield lambda: func().__floordiv__(gunc())
        else:
            for func in self._lambda_generator:
                yield lambda: func().__floordiv__(other)
    def __pow__(self, other):
        if isinstance(other, LambdaGenerator):
            for func, gunc in zip(self._lambda_generator, other._lambda_generator):
                yield lambda: func().__pow__(gunc())
        else:
            for func in self._lambda_generator:
                yield lambda: func().__pow__(other)


def get_bbox(fig):
    t0 = fig['data'][0]
    xmin = np.nanmin(t0['x'])
    xmax = np.nanmax(t0['x'])
    ymin = np.nanmin(t0['y'])
    ymax = np.nanmax(t0['y'])
    zmin = np.nanmin(t0['z'])
    zmax = np.nanmax(t0['z'])
    for t in fig['data']:
        xmin = min(xmin, np.nanmin(t['x']))
        xmax = max(xmax, np.nanmax(t['x']))
        ymin = min(ymin, np.nanmin(t['y']))
        ymax = max(ymax, np.nanmax(t['y']))
        zmin = min(zmin, np.nanmin(t['z']))
        zmax = max(zmax, np.nanmax(t['z']))
    return xmin, xmax, ymin, ymax, zmin, zmax

def set_aspect(fig):
    """sets aspect ratio of the scene based on bounding box of traces"""
    fig.layout.scene.aspectmode='manual'
    xmin, xmax, ymin, ymax, zmin, zmax = get_bbox(fig)
    fig.layout.scene.aspectratio=dict(x=xmax-xmin, y=ymax-ymin,z=zmax-zmin)
    return fig




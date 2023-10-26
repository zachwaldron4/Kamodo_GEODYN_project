# -*- coding: utf-8 -*-
"""
Created on Fri Jun 18 11:55:58 2021
@author: rringuet

Instead of writing individual wrappers for each model, this file is used to
do anything model-specific, such as importing the right readers.


Help on coordinate systems:
    The resource information on SpacePy's coordinate conversion function is
        sparse at best, so the below information has been collected via other
        resources and our own testing of the function. The data concerning the
        spherical coordinate systems are collected into a table format for
        easier perusal.
    For cartesian coordinates, all of the input values should be in earth radii (R_E)
        in order (x, y, z) to work properly.
    For spherical coordinates, all of the input values should be in order
        (longitude, latitude, altitude or radius). The longitude and latitude
        values should be in degrees, altitude values in kilometers, and radius
        values in earth radii (R_E) from the Earth's center. All latitude values
        should fall between -90 and 90 degrees. The longitude range differs
        between the coordinate systems and is given for each in the table below.

SpacePy
Abbrev.   Full Name                       Lon. range     vertical variable
--------------------------------------------------------------------------
GDZ    Geodetic (WGS 84)                  (-180, 180)    Altitude (km)
GEO    Geographic                         (-180, 180)    Radius (R_E)
GSM    Geocentric Solar Magnetospheric    (-180, 180)    Radius (R_E)
GSE    Geocentric Solar Ecliptic          (-180, 180)    Radius (R_E)
SM     Solar Magnetic                     (-180, 180)    Radius (R_E)
GEI    Geocentric Equatorial Inertial     (-180, 180)    Radius (R_E)
      (also ECI = Earth-Centered Inertial)
MAG    Geomagnetic                        (-180, 180)    Radius (R_E)
SPH    Spherical                            (0, 360)     Radius (R_E)
RLL    Radius, Latitude, Longitude        (-180, 180)    Radius (R_E)

For descriptions of most of the coordinate systems, see
https://sscweb.gsfc.nasa.gov/users_guide/Appendix_C.shtml and it's reference,
"Geophysical Coordinate Transformations", C.T. Russell, Cosmic Electrodynamics,
Vol. 2, pp. 184 - 196, 1971.
"""
from glob import glob
from numpy import unique
from os.path import basename
import numpy as np


model_dict = {0: 'CTIPe', 1: 'GITM', 2: 'IRI', 3: 'SWMF_IE', 4: 'TIEGCM',
              5: 'OpenGGCM_GM', 6: 'AMGeO'}


def convert_model_string(model_int):
    '''Converts numerical model reference to string.

    Input:
        model_int: An integer or string representing the model.
    Output:
        If model_int is an integer, the string corresponding to that model is
            returned. If model_int is not an integer, model_int is returned
            unchanged.
    '''

    if isinstance(model_int, int):
        return model_dict[model_int]
    else:
        return model_int


def Choose_Model(model):
    '''Returns module specific to the model requested.

    Input:
        model: A string or integer corresponding to the desired model. If the
            string is empty, print statements are executed.
    Output: The module associated with the model reader for the desired model.
        If model is an empty string, None is returned.
    '''
    # UPDATE THIS AS MORE MODELS ARE ADDED

    if model == '':  # Give a list of possible values
        print(f"Possible models are: {model_dict}")
        print('Integers or strings allowed.')
        return

    model = convert_model_string(model)  # convert to string

    if model == 'CTIPe':
        import kamodo_ccmc.readers.ctipe_4D as module
        return module

    elif model == 'IRI':
        import kamodo_ccmc.readers.iri_4D as module
        return module

    elif model == 'GITM':
        import kamodo_ccmc.readers.gitm_4Dcdf as module
        return module

    elif model == 'SWMF_IE':
        import kamodo_ccmc.readers.swmfie_4Dcdf as module
        return module

    elif model == 'TIEGCM':
        import kamodo_ccmc.readers.tiegcm_4D as module
        return module

    elif model == 'OpenGGCM_GM':
        import kamodo_ccmc.readers.openggcm_gm_4Dcdf_xarray as module
        return module

    elif model == 'AMGeO':
        import kamodo_ccmc.readers.amgeo_4D as module
        return module

    else:
        raise AttributeError('Model not yet added.')


def FileSearch(model, file_dir, call_type='normal'):
    '''Returns list of model data files for each model based on the name pattern.

    Inputs:
        model: A string or integer corresponding to the desired model.
        file_dir: A string indicated the full file path to the directory desired.
        call_type: A string (default='normal'). If call_type is 'normal', the
            normal time range is used in the file search logic, typically one day.
            If call_type is another string, then a smaller time range is used,
            typically one hour.
    Outputs: If the model output only produces one file per day, or the reader
        knows of the different filenames, then a string is returned. Otherwise,
        an array of filename patterns is returned.'''

    # UPDATE THIS AS NEW MODELS ARE ADDED

    if isinstance(model, int):
        model = model_dict[model]  # convert to string

    if model == 'CTIPe':
        files = sorted(glob(file_dir+'*.nc'))  # look for wrapped and original data
        file_patterns = unique([file_dir+basename(f)[:10] for f in files
                                if 'CTIPe' not in basename(f)])
        return file_patterns

    elif model == 'IRI':
        return file_dir+'IRI.3D.*.nc'

    elif model == 'GITM':  # whole day version of filesearch
        files = sorted(glob(file_dir+'*'))  # next line returns list of prefixes
        if call_type == 'normal':  # give prefix for full day files
            file_patterns = unique([file_dir+'*'+basename(f)[7:13] for f in files
                                    if 'GITM'  not in basename(f)   and 
                                       '.nc'   not in basename(f)   and
                                       'files' not in basename(f) ])   # Zach modified for gitm2 case
        else:  # give prefix for hourly files
            file_patterns = unique([file_dir+'*'+basename(f)[7:16] for f in files
                                    if '.nc'   not in basename(f)  and
                                       'GITM'  not in basename(f)  and
                                       'files' not in basename(f) ])   # Zach modified for gitm2 case
        return file_patterns

    elif model == 'SWMF_IE':
        files = sorted(glob(file_dir+'i_e*'))  # next line returns list of prefixes
        if call_type == 'normal':  # give prefix for full day files
            file_patterns = unique([file_dir+basename(f)[:11] for f in files
                                    if '.nc' not in basename(f)])
        else:  # give prefix for hourly files
            file_patterns = unique([file_dir+basename(f)[:14] for f in files
                                    if '.nc' not in basename(f)])
        return file_patterns

    elif model == 'TIEGCM':
        # print('Please remove all pxxx.nc files if present.')
        return file_dir+'*.nc'

    elif model == 'OpenGGCM_GM':
        files = sorted(glob(file_dir+'*.nc'))
        file_patterns = unique([file_dir + basename(f).split('3df_')[0] + '3df_' +
                                f.split('3df_')[1][:13] for f in files])
        return file_patterns

    elif model == 'AMGeO':
        files = sorted(glob(file_dir+'*.h5'))
        file_patterns = unique([file_dir + basename(f).split('.h5')[0][:-1]
                                for f in files])
        return file_patterns

    else:
        raise AttributeError('Model not yet added.')


def Model_Reader(model):
    '''Returns model reader for requested model. Model agnostic.
    Input: model: A string or integer associated with the desired model.

    Output: The MODEL Kamodo class object in the desired model reader.
    '''

    module = Choose_Model(model)
    return module.MODEL()  # imports Kamodo


def Model_Variables(model, return_dict=False):
    '''Returns model variables for requested model. Model agnostic.

    Inputs:
        model: A string or integer associated with the desired model.
        return_dict: A boolean (default=False). If False, the full variable dictionary
            associated with the model is printed to the screen and None is returned.
            If True, the full variable dictionary is returned without any printed statements.
        Output: None or the variable dictionary. (See return_dict description.)
    '''

    # choose the model-specific function to retrieve the variables
    module = Choose_Model(model)
    variable_dict = module.model_varnames
    var_dict = {value[0]: value[1:] for key, value in variable_dict.items()}

    # retrieve and print model specific and standardized variable names
    if return_dict:
        return var_dict
    else:
        print('\nThe model accepts the standardized variable names listed below.')
        print('-----------------------------------------------------------------------------------')
        for key, value in sorted(var_dict.items()):
            print(f"{key} : '{value}'")
        print()
        return


def File_Variables(model, file_dir, return_dict=False):
    '''Print list of variables in model data output stored in file_dir.

    Inputs:
        model: A string or integer associated with the desired model.
        file_dir: A string giving the full file path for the chosen directory.
        return_dict: A boolean (default=False). If False, the variable dictionary
            associated with the files in the given directory is printed to the screen
            and None is returned. If True, the same variable dictionary is returned
            without any printed statements.
        Output: None or the variable dictionary. (See return_dict description.)
    '''

    reader = Model_Reader(model)
    file_patterns = FileSearch(model, file_dir)
    file_variables = {}
    # collect file variables in a nested dictionary
    if isinstance(file_patterns, list) or isinstance(file_patterns, np.ndarray):
        for file_pattern in file_patterns:
            
#             print('zach-- file_pattern', file_pattern)
            kamodo_object = reader(file_pattern, fulltime=False, variables_requested='all')
            file_variables[file_pattern] = {key: value for key, value
                                            in sorted(kamodo_object.var_dict.items())}

    else:  # reader requires full filenames, not a file pattern
        files = sorted(glob(file_patterns))  # find full filenames for given pattern
        for file in files:
            kamodo_object = reader(file, fulltime=False, variables_requested='all')
            file_variables[file] = {key: value for key, value
                                    in sorted(kamodo_object.var_dict.items())}

    # either return or print nested_dictionary
    if return_dict:
        return file_variables
    else:
        # print file pattern standardized variable names
        for file_key in file_variables.keys():
            print(f'\nThe file {file_key} contains the following standardized variable names:')
            print('-----------------------------------------------------------------------------------')
            for key, value in file_variables[file_key].items():
                print(f"{key} : '{value}'")
            print()
        return


def File_Times(model, file_dir, print_output=True):
    '''Return/print time ranges available in the data in the given dir. Also
    performs file conversions if the expected converted files are not found for
    the files or file naming patterns detected. If the model_times.csv file is
    not found in the given directory, it is created. If new files or file naming
    patterns are detected that are not in the model_times.csv file in the given
    directory, the file is updated.

    Inputs:
        model: A string or integer associated with the desired model.
        file_dir: A string giving the full file path for the chosen directory.
        print_output: A boolean (default=True). If True, the time information associated
            with each file or file naming pattern is printed to the screen. If
            False, no print statements are executed.
    Output: A dictionary containing a date string as the keys and a list of the
        time information for each file name or file naming pattern. The list
        contains the the file name or file naming pattern, the beginning and
        end times in UTC in string and timestamp format, followed by the smallest
        time resolution in seconds detected in the data.
    '''

    # get time ranges from data
    from kamodo_ccmc.flythrough.SF_utilities import check_timescsv
    file_patterns = FileSearch(model, file_dir)
    times_dict = check_timescsv(file_patterns, model)

    # print time ranges for given file groups: file_pattern, beg time, end time
    if print_output:
        print('File pattern: UTC time ranges')
        print('------------------------------------------')
        for key in times_dict.keys():
            print(f"{times_dict[key][0]} : {times_dict[key][1:]}")

    return times_dict


def Var_3D(model):
    '''Return list of model variables that are three-dimensional. Model agnostic.

    Input: model: A string or integer indicating the desired model.
    Output: A list of the standardized variable names associated with the model
        that have three dimensions (typically time + 2D spatial).
    '''

    # choose the model-specific function to retrieve the 3D variable list
    variable_dict = Model_Variables(model, return_dict=True)
    return [value[0] for key, value in variable_dict.items() if len(value[4]) == 3]


def Var_ilev(model):
    '''Return list of possible ilev coordinate names for model given.

    Input: model: A string or integer indicating the desired model.
    Output: A list of the pressure level coordinate names associated with the model.
    '''

    variable_dict = Model_Variables(model, return_dict=True)
    ilev_list = list(unique([value[4][-1] for key, value in variable_dict.items()
                     if len(value[4]) == 4 and 'ilev' in value[4][-1]]))
    return ilev_list


def Var_units(model, variable_list):
    '''Determines the proper units for the given variables.

    Inputs:
        model: A string or integer indicating the desired model.
        variable_list: A list of strings for the desired standardized variable
            names.
    Output: A dictionary of the standardized variable names as keys with the
        corresponding units as the values.
    '''

    variable_dict = Model_Variables(model, return_dict=True)
    return {key: value[-1] for key, value in variable_dict.items() if key in
            variable_list}


def convert_variablenames(model, variable_list):
    '''Given list of integers for variable names, convert to names for given model.

    Inputs:
        model: A string or integer indicating the desired model.
        variable_list: A list of strings or integers for the desired
            standardized variable names.
    Output: A list of the desired standardized variable names.
    '''

    if isinstance(variable_list[0], int):
        variable_dict = Model_Variables(model, return_dict=True)
        tmp_var = [value[0] for key, value in variable_dict.items()
                   if value[2] in variable_list]
        variable_list = tmp_var
    return variable_list


def convert_coordnames(coord_type, coord_grid):
    '''Convert integers to strings for coordinate names and grid types.

    Inputs:
        coord_type: An integer or string corresponding to the desired coordinate
            system.
        coord_grid: An integer or string corresponding to the desired coordinate
            grid type (e.g. 0 for cartesian or 1 for spherical.)
    Outputs: Two strings representing the coordinate system and grid type.
    '''

    if isinstance(coord_type, int) and isinstance(coord_grid, int):
        spacepy_dict = {0: 'GDZ', 1: 'GEO', 2: 'GSM', 3: 'GSE', 4: 'SM',
                        5: 'GEI', 6: 'MAG', 7: 'SPH', 8: 'RLL'}
        coord_type = spacepy_dict[coord_type]
        if coord_grid == 0:
            coord_grid = 'car'
        elif coord_grid == 1:
            coord_grid = 'sph'
    return coord_type, coord_grid


def coord_units(coord_type, coord_grid):
    '''Determines the proper coordinate units given the coordinate system and type.

    Inputs:
        coord_type: An integer or string corresponding to the desired coordinate
            system.
        coord_grid: An integer or string corresponding to the desired coordinate
            grid type (e.g. 0 for cartesian or 1 for spherical.)
    Outputs: A dictionary with key, value pairs giving the proper units for each
        coordinate grid component (e.g. c1, c2, c3 in R_E for cartesian).
    '''

    if coord_grid == 'car':
        if coord_type in ['GDZ', 'SPH', 'RLL']:
            print(f'There is no cartesian version in the {coord_type} coordinate system.')
            return
        return {'utc_time': 's', 'net_idx': '', 'c1': 'R_E', 'c2': 'R_E',
                'c3': 'R_E'}
    elif coord_grid == 'sph':
        if coord_type == 'GDZ':
            return {'utc_time': 's', 'net_idx': '', 'c1': 'deg', 'c2': 'deg',
                    'c3': 'km'}
        else:
            return {'utc_time': 's', 'net_idx': '', 'c1': 'deg', 'c2': 'deg',
                    'c3': 'R_E'}


def coord_names(coord_type, coord_grid):
    '''Determines the proper coordinate component names for a given coordinate
    system and grid type.

    Inputs:
        coord_type: An integer or string corresponding to the desired coordinate
            system.
        coord_grid: An integer or string corresponding to the desired coordinate
            grid type (e.g. 0 for cartesian or 1 for spherical.)
    Outputs: A dictionary with key, value pairs giving the proper coordinate
        component names for each coordinate grid component (e.g. c1, c2, c3
        associated with Longitude, Latitude, and Radius for most spherical systems).
    '''

    if coord_grid == 'car':
        return {'c1': 'X_'+coord_type, 'c2': 'Y_'+coord_type, 'c3': 'Z_'+coord_type}
    elif coord_grid == 'sph' and coord_type == 'GDZ':
        return {'c1': 'Longitude', 'c2': 'Latitude', 'c3': 'Altitude'}
    elif coord_grid == 'sph' and coord_type != 'GDZ':
        return {'c1': 'Longitude', 'c2': 'Latitude', 'c3': 'Radius'}





# # -*- coding: utf-8 -*-
# """
# Created on Fri Jun 18 11:55:58 2021
# @author: rringuet

# Instead of writing individual wrappers for each model, this file is used to
# do anything model-specific, such as importing the right readers.


# Help on coordinate systems:
#     The resource information on SpacePy's coordinate conversion function is
#         sparse at best, so the below information has been collected via other
#         resources and our own testing of the function. The data concerning the
#         spherical coordinate systems are collected into a table format for
#         easier perusal.
#     For cartesian coordinates, all of the input values should be in earth radii (R_E)
#         in order (x, y, z) to work properly.
#     For spherical coordinates, all of the input values should be in order
#         (longitude, latitude, altitude or radius). The longitude and latitude
#         values should be in degrees, altitude values in kilometers, and radius
#         values in earth radii (R_E) from the Earth's center. All latitude values
#         should fall between -90 and 90 degrees. The longitude range differs
#         between the coordinate systems and is given for each in the table below.

# SpacePy
# Abbrev.   Full Name                       Lon. range     vertical variable
# --------------------------------------------------------------------------
# GDZ    Geodetic (WGS 84)                  (-180, 180)    Altitude (km)
# GEO    Geographic                         (-180, 180)    Radius (R_E)
# GSM    Geocentric Solar Magnetospheric    (-180, 180)    Radius (R_E)
# GSE    Geocentric Solar Ecliptic          (-180, 180)    Radius (R_E)
# SM     Solar Magnetic                     (-180, 180)    Radius (R_E)
# GEI    Geocentric Equatorial Inertial     (-180, 180)    Radius (R_E)
#       (also ECI = Earth-Centered Inertial)
# MAG    Geomagnetic                        (-180, 180)    Radius (R_E)
# SPH    Spherical                            (0, 360)     Radius (R_E)
# RLL    Radius, Latitude, Longitude        (-180, 180)    Radius (R_E)

# For descriptions of most of the coordinate systems, see
# https://sscweb.gsfc.nasa.gov/users_guide/Appendix_C.shtml and it's reference,
# "Geophysical Coordinate Transformations", C.T. Russell, Cosmic Electrodynamics,
# Vol. 2, pp. 184 - 196, 1971.
# """
# from glob import glob
# from numpy import unique
# from os.path import basename
# import numpy as np


# model_dict = {0: 'CTIPe', 1: 'GITM', 2: 'IRI', 3: 'SWMF_IE', 4: 'TIEGCM',
#               5: 'OpenGGCM_GM', 6: 'AmGEO'}


# def convert_model_string(model_int):
#     '''Converts numerical model reference to string.

#     Input:
#         model_int: An integer or string representing the model.
#     Output:
#         If model_int is an integer, the string corresponding to that model is
#             returned. If model_int is not an integer, model_int is returned
#             unchanged.
#     '''

#     if isinstance(model_int, int):
#         return model_dict[model_int]
#     else:
#         return model_int


# def Choose_Model(model):
#     '''Returns module specific to the model requested.

#     Input:
#         model: A string or integer corresponding to the desired model. If the
#             string is empty, print statements are executed.
#     Output: The module associated with the model reader for the desired model.
#         If model is an empty string, None is returned.
#     '''
#     # UPDATE THIS AS MORE MODELS ARE ADDED

#     if model == '':  # Give a list of possible values
#         print(f"Possible models are: {model_dict}")
#         print('Integers or strings allowed.')
#         return

#     model = convert_model_string(model)  # convert to string

#     if model == 'CTIPe':
#         import kamodo_ccmc.readers.ctipe_4D as module
#         return module

#     elif model == 'IRI':
#         import kamodo_ccmc.readers.iri_4D as module
#         return module

#     elif model == 'GITM':
#         import kamodo_ccmc.readers.gitm_4Dcdf as module
#         return module

#     elif model == 'SWMF_IE':
#         import kamodo_ccmc.readers.swmfie_4Dcdf as module
#         return module

#     elif model == 'TIEGCM':
#         import kamodo_ccmc.readers.tiegcm_4D as module
#         return module

#     elif model == 'OpenGGCM_GM':
#         import kamodo_ccmc.readers.openggcm_gm_4Dcdf_xarray as module
#         return module

#     elif model == 'AmGEO':
#         import kamodo_ccmc.readers.amgeo_4D as module
#         return module

#     else:
#         raise AttributeError('Model not yet added.')


# def FileSearch(model, file_dir, call_type='normal'):
#     '''Returns list of model data files for each model based on the name pattern.

#     Inputs:
#         model: A string or integer corresponding to the desired model.
#         file_dir: A string indicated the full file path to the directory desired.
#         call_type: A string (default='normal'). If call_type is 'normal', the
#             normal time range is used in the file search logic, typically one day.
#             If call_type is another string, then a smaller time range is used,
#             typically one hour.
#     Outputs: If the model output only produces one file per day, or the reader
#         knows of the different filenames, then a string is returned. Otherwise,
#         an array of filename patterns is returned.'''

#     # UPDATE THIS AS NEW MODELS ARE ADDED

#     if isinstance(model, int):
#         model = model_dict[model]  # convert to string

#     if model == 'CTIPe':
#         files = sorted(glob(file_dir+'*.nc'))  # look for wrapped and original data
#         file_patterns = unique([file_dir+basename(f)[:10] for f in files
#                                 if 'CTIPe' not in basename(f)])
#         return file_patterns

#     elif model == 'IRI':
#         return file_dir+'IRI.3D.*.nc'

#     elif model == 'GITM':  # whole day version of filesearch
#         files = sorted(glob(file_dir+'*'))  # next line returns list of prefixes
#         if call_type == 'normal':  # give prefix for full day files
#             file_patterns = unique([file_dir+'*'+basename(f)[7:13] for f in files
#                                     if 'GITM' not in basename(f) and '.nc'
#                                     not in basename(f)])
#         else:  # give prefix for hourly files
#             file_patterns = unique([file_dir+'*'+basename(f)[7:16] for f in files
#                                     if '.nc' not in basename(f) and 'GITM'
#                                     not in basename(f)])
#         return file_patterns

#     elif model == 'SWMF_IE':
#         files = sorted(glob(file_dir+'i_e*'))  # next line returns list of prefixes
#         if call_type == 'normal':  # give prefix for full day files
#             file_patterns = unique([file_dir+basename(f)[:11] for f in files
#                                     if '.nc' not in basename(f)])
#         else:  # give prefix for hourly files
#             file_patterns = unique([file_dir+basename(f)[:14] for f in files
#                                     if '.nc' not in basename(f)])
#         return file_patterns

#     elif model == 'TIEGCM':
#         #### GEODYN EDIT: remove comment
# #         print('Please remove all pxxx.nc files if present.')
#         return file_dir+'*.nc'

#     elif model == 'OpenGGCM_GM':
#         files = sorted(glob(file_dir+'*.nc'))
#         file_patterns = unique([file_dir + basename(f).split('3df_')[0] + '3df_' +
#                                 f.split('3df_')[1][:13] for f in files])
#         return file_patterns

#     elif model == 'AmGEO':
#         return file_dir+'*N.h5'

#     else:
#         raise AttributeError('Model not yet added.')


# def Model_Reader(model):
#     '''Returns model reader for requested model. Model agnostic.
#     Input: model: A string or integer associated with the desired model.

#     Output: The MODEL Kamodo class object in the desired model reader.
#     '''

#     module = Choose_Model(model)
#     return module.MODEL()  # imports Kamodo


# def Model_Variables(model, return_dict=False):
#     '''Returns model variables for requested model. Model agnostic.

#     Inputs:
#         model: A string or integer associated with the desired model.
#         return_dict: A boolean (default=False). If False, the full variable dictionary
#             associated with the model is printed to the screen and None is returned.
#             If True, the full variable dictionary is returned without any printed statements.
#         Output: None or the variable dictionary. (See return_dict description.)
#     '''

#     # choose the model-specific function to retrieve the variables
#     module = Choose_Model(model)
#     variable_dict = module.model_varnames
#     var_dict = {value[0]: value[1:] for key, value in variable_dict.items()}

#     # retrieve and print model specific and standardized variable names
#     if return_dict:
#         return var_dict
#     else:
#         print('\nThe model accepts the standardized variable names listed below.')
#         print('-----------------------------------------------------------------------------------')
#         for key, value in sorted(var_dict.items()):
#             print(f"{key} : '{value}'")
#         print()
#         return


# def File_Variables(model, file_dir, return_dict=False):
#     '''Print list of variables in model data output stored in file_dir.

#     Inputs:
#         model: A string or integer associated with the desired model.
#         file_dir: A string giving the full file path for the chosen directory.
#         return_dict: A boolean (default=False). If False, the variable dictionary
#             associated with the files in the given directory is printed to the screen
#             and None is returned. If True, the same variable dictionary is returned
#             without any printed statements.
#         Output: None or the variable dictionary. (See return_dict description.)
#     '''

#     reader = Model_Reader(model)
#     file_patterns = FileSearch(model, file_dir)
#     file_variables = {}
#     # collect file variables in a nested dictionary
#     if isinstance(file_patterns, list) or isinstance(file_patterns, np.ndarray):
#         for file_pattern in file_patterns:
#             kamodo_object = reader(file_pattern, fulltime=False, variables_requested='all')
#             file_variables[file_pattern] = {key: value for key, value
#                                             in sorted(kamodo_object.var_dict.items())}

#     else:  # reader requires full filenames, not a file pattern
#         files = sorted(glob(file_patterns))  # find full filenames for given pattern
#         for file in files:
#             kamodo_object = reader(file, fulltime=False, variables_requested='all')
#             file_variables[file] = {key: value for key, value
#                                     in sorted(kamodo_object.var_dict.items())}

#     # either return or print nested_dictionary
#     if return_dict:
#         return file_variables
#     else:
#         # print file pattern standardized variable names
#         for file_key in file_variables.keys():
#             print(f'\nThe file {file_key} contains the following standardized variable names:')
#             print('-----------------------------------------------------------------------------------')
#             for key, value in file_variables[file_key].items():
#                 print(f"{key} : '{value}'")
#             print()
#         return


# def File_Times(model, file_dir, print_output=True):
#     '''Return/print time ranges available in the data in the given dir. Also
#     performs file conversions if the expected converted files are not found for
#     the files or file naming patterns detected. If the model_times.csv file is
#     not found in the given directory, it is created. If new files or file naming
#     patterns are detected that are not in the model_times.csv file in the given
#     directory, the file is updated.

#     Inputs:
#         model: A string or integer associated with the desired model.
#         file_dir: A string giving the full file path for the chosen directory.
#         print_output: A boolean (default=True). If True, the time information associated
#             with each file or file naming pattern is printed to the screen. If
#             False, no print statements are executed.
#     Output: A dictionary containing a date string as the keys and a list of the
#         time information for each file name or file naming pattern. The list
#         contains the the file name or file naming pattern, the beginning and
#         end times in UTC in string and timestamp format, followed by the smallest
#         time resolution in seconds detected in the data.
#     '''

#     # get time ranges from data
#     from kamodo_ccmc.flythrough.SF_utilities import check_timescsv
#     file_patterns = FileSearch(model, file_dir)
#     times_dict = check_timescsv(file_patterns, model)

#     # print time ranges for given file groups: file_pattern, beg time, end time
#     if print_output:
#         print('File pattern: UTC time ranges')
#         print('------------------------------------------')
#         for key in times_dict.keys():
#             print(f"{times_dict[key][0]} : {times_dict[key][1:]}")

#     return times_dict


# def Var_3D(model):
#     '''Return list of model variables that are three-dimensional. Model agnostic.

#     Input: model: A string or integer indicating the desired model.
#     Output: A list of the standardized variable names associated with the model
#         that have three dimensions (typically time + 2D spatial).
#     '''

#     # choose the model-specific function to retrieve the 3D variable list
#     variable_dict = Model_Variables(model, return_dict=True)
#     return [value[0] for key, value in variable_dict.items() if len(value[4]) == 3]


# def Var_ilev(model):
#     '''Return list of possible ilev coordinate names for model given.

#     Input: model: A string or integer indicating the desired model.
#     Output: A list of the pressure level coordinate names associated with the model.
#     '''

#     variable_dict = Model_Variables(model, return_dict=True)
#     ilev_list = list(unique([value[4][-1] for key, value in variable_dict.items()
#                      if len(value[4]) == 4 and 'ilev' in value[4][-1]]))
#     return ilev_list


# def Var_units(model, variable_list):
#     '''Determines the proper units for the given variables.

#     Inputs:
#         model: A string or integer indicating the desired model.
#         variable_list: A list of strings for the desired standardized variable
#             names.
#     Output: A dictionary of the standardized variable names as keys with the
#         corresponding units as the values.
#     '''

#     variable_dict = Model_Variables(model, return_dict=True)
#     return {key: value[-1] for key, value in variable_dict.items() if key in
#             variable_list}


# def convert_variablenames(model, variable_list):
#     '''Given list of integers for variable names, convert to names for given model.

#     Inputs:
#         model: A string or integer indicating the desired model.
#         variable_list: A list of strings or integers for the desired
#             standardized variable names.
#     Output: A list of the desired standardized variable names.
#     '''

#     if isinstance(variable_list[0], int):
#         variable_dict = Model_Variables(model, return_dict=True)
#         tmp_var = [value[0] for key, value in variable_dict.items()
#                    if value[2] in variable_list]
#         variable_list = tmp_var
#     return variable_list


# def convert_coordnames(coord_type, coord_grid):
#     '''Convert integers to strings for coordinate names and grid types.

#     Inputs:
#         coord_type: An integer or string corresponding to the desired coordinate
#             system.
#         coord_grid: An integer or string corresponding to the desired coordinate
#             grid type (e.g. 0 for cartesian or 1 for spherical.)
#     Outputs: Two strings representing the coordinate system and grid type.
#     '''

#     if isinstance(coord_type, int) and isinstance(coord_grid, int):
#         spacepy_dict = {0: 'GDZ', 1: 'GEO', 2: 'GSM', 3: 'GSE', 4: 'SM',
#                         5: 'GEI', 6: 'MAG', 7: 'SPH', 8: 'RLL'}
#         coord_type = spacepy_dict[coord_type]
#         if coord_grid == 0:
#             coord_grid = 'car'
#         elif coord_grid == 1:
#             coord_grid = 'sph'
#     return coord_type, coord_grid


# def coord_units(coord_type, coord_grid):
#     '''Determines the proper coordinate units given the coordinate system and type.

#     Inputs:
#         coord_type: An integer or string corresponding to the desired coordinate
#             system.
#         coord_grid: An integer or string corresponding to the desired coordinate
#             grid type (e.g. 0 for cartesian or 1 for spherical.)
#     Outputs: A dictionary with key, value pairs giving the proper units for each
#         coordinate grid component (e.g. c1, c2, c3 in R_E for cartesian).
#     '''

#     if coord_grid == 'car':
#         if coord_type in ['GDZ', 'SPH', 'RLL']:
#             print(f'There is no cartesian version in the {coord_type} coordinate system.')
#             return
#         return {'utc_time': 's', 'net_idx': '', 'c1': 'R_E', 'c2': 'R_E',
#                 'c3': 'R_E'}
#     elif coord_grid == 'sph':
#         if coord_type == 'GDZ':
#             return {'utc_time': 's', 'net_idx': '', 'c1': 'deg', 'c2': 'deg',
#                     'c3': 'km'}
#         else:
#             return {'utc_time': 's', 'net_idx': '', 'c1': 'deg', 'c2': 'deg',
#                     'c3': 'R_E'}


# def coord_names(coord_type, coord_grid):
#     '''Determines the proper coordinate component names for a given coordinate
#     system and grid type.

#     Inputs:
#         coord_type: An integer or string corresponding to the desired coordinate
#             system.
#         coord_grid: An integer or string corresponding to the desired coordinate
#             grid type (e.g. 0 for cartesian or 1 for spherical.)
#     Outputs: A dictionary with key, value pairs giving the proper coordinate
#         component names for each coordinate grid component (e.g. c1, c2, c3
#         associated with Longitude, Latitude, and Radius for most spherical systems).
#     '''

#     if coord_grid == 'car':
#         return {'c1': 'X_'+coord_type, 'c2': 'Y_'+coord_type, 'c3': 'Z_'+coord_type}
#     elif coord_grid == 'sph' and coord_type == 'GDZ':
#         return {'c1': 'Longitude', 'c2': 'Latitude', 'c3': 'Altitude'}
#     elif coord_grid == 'sph' and coord_type != 'GDZ':
#         return {'c1': 'Longitude', 'c2': 'Latitude', 'c3': 'Radius'}

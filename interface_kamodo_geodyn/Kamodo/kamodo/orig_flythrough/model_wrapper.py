# -*- coding: utf-8 -*-
"""
Created on Fri Jun 18 11:55:58 2021

@author: rringuet

Instead of writing individual wrappers for each model, this file is used to
do anything model-specific, such as importing the right readers.
"""
from glob import glob
from numpy import unique
from os.path import basename


model_dict = {0:'CTIPe', 1:'GITM', 2:'IRI', 3:'SWMF_IE', 4:'TIEGCM'}

def convert_model_string(model_int):
    '''Converts numerical model reference to string.'''
    
    if isinstance(model_int,int): 
        return model_dict[model_int]
    else:
        return model_int


def Choose_Model(model):
    '''Returns module specific to the model requested.'''
    #UPDATE THIS AS MORE MODELS ARE ADDED

    if model == '':  #Give a list of possible values
        print(f"Possible models are: {model_dict}")
        print('Integers or strings allowed.')
        return
    
    model = convert_model_string(model)  #convert to string
    
    if model=='CTIPe':
        import kamodo.readers.ctipe_4D as module
        return module
    
    elif model=='IRI':
        import kamodo.readers.iri_4D as module
        return module
    
    elif model=='GITM':
        import kamodo.readers.gitm_4Dcdf as module
        return module
    
    elif model=='SWMF_IE':
        import kamodo.readers.swmfie_4Dcdf as module
        return module
    
    elif model=='TIEGCM':
        import kamodo.orig_readers.tiegcm_4D as module
        return module
    
    else:
        raise AttributeError('Model not yet added.')    


def FileSearch(model, file_dir, call_type='normal'):
    '''Returns list of model data files for each model based on the name pattern.
    If only one file per day, or reader knows of the different filenames, then return string.
    Else, return an array of filename patterns.'''
    #UPDATE THIS AS NEW MODELS ARE ADDED
    
    if isinstance(model,int): model = model_dict[model]  #convert to string
    
    if model=='CTIPe':
        files = glob(file_dir+'*.nc')  #look for wrapped and original data
        file_patterns = unique([file_dir+basename(f)[:10] for f in files \
                                            if 'CTIPe' not in basename(f)])
        return file_patterns  
    
    elif model=='IRI':
        return file_dir+'IRI.3D.*.nc'
    
    elif model=='GITM':  #whole day version of filesearch
        files = glob(file_dir+'*')  #next line returns list of prefixes: e.g. 3DALL_t20150315
        if call_type=='normal': #give prefix for full day files
            file_patterns = unique([file_dir+'*'+basename(f)[7:13] for f in files\
                                    if 'GITM' not in basename(f) and '.nc' not in basename(f)])
        else:  #give prefix for hourly files
            file_patterns = unique([file_dir+'*'+basename(f)[7:16] for f in files \
                                    if '.nc' not in basename(f) and 'GITM' not in basename(f)])
        return file_patterns     
    
    elif model=='SWMF_IE':
        files = glob(file_dir+'i_e*')  #next line returns list of prefixes: e.g. i_e20150315
        if call_type=='normal': #give prefix for full day files
            file_patterns = unique([file_dir+basename(f)[:11] for f in files\
                                            if '.nc' not in basename(f)])
        else:  #give prefix for hourly files
            file_patterns = unique([file_dir+basename(f)[:14] for f in files\
                                            if '.nc' not in basename(f)])
        return file_patterns        

    elif model=='TIEGCM':
        return file_dir+'s*.nc'
    
    else:
        raise AttributeError('Model not yet added.')
        

def Model_Reader(model):
    '''Returns model reader for requested model. Model agnostic.'''
    
    module = Choose_Model(model)
    return module.MODEL()  #imports Kamodo
        

def Model_Variables(model, return_dict=False):
    '''Returns model variables for requested model. Model agnostic.'''
    
    #choose the model-specific function to retrieve the variables
    module = Choose_Model(model)
    variable_dict = module.model_varnames
    var_dict = {value[0]:value[1:] for key, value in variable_dict.items()}
        
    #retrieve and print model specific and standardized variable names
    if return_dict: 
        return var_dict
    else:
        print('\nThe model accepts the standardized variable names listed below.')
        #print('Units for the chosen variables are printed during the satellite flythrough if available.')
        print('-----------------------------------------------------------------------------------')
        for key, value in var_dict.items(): print(f"{key} : '{value}'")
        print()
        return    
    
    
def Var_3D(model):
    '''Return list of model variables that are three-dimensional. Model agnostic.'''
    
    #choose the model-specific function to retrieve the 3D variable list
    variable_dict = Model_Variables(model, return_dict=True)    
    return [value[0] for key, value in variable_dict.items() if len(value[4])==3]

def Var_ilev(model):
    '''Return list of possible ilev coordinate names for model given.'''

    variable_dict = Model_Variables(model, return_dict=True)   
    ilev_list = list(unique([value[4][-1] for key, value in variable_dict.items() \
                                if len(value[4])==4 and 'ilev' in value[4][-1]]))
    return ilev_list

def Var_units(model, variable_list):
    '''Returns dictionary of key, value = varname, units.'''

    variable_dict = Model_Variables(model, return_dict=True)  
    return {key:value[-1] for key, value in variable_dict.items() if key in variable_list}    

def convert_variablenames(model, variable_list):
    '''Given list of integers for variable names, convert to names for given model.'''

    if isinstance(variable_list[0], int):
        variable_dict = Model_Variables(model, return_dict=True)          
        tmp_var = [value[0] for key, value in variable_dict.items()\
                               if value[2] in variable_list]
        variable_list = tmp_var
    return variable_list
    
def convert_coordnames(coord_type, coord_grid):
    '''convert integers to strings for coordinate names and grid types.'''
    
    if isinstance(coord_type, int) and isinstance(coord_grid, int):
        spacepy_dict = {0:'GDZ',1:'GEO',2:'GSM',3:'GSE',4:'SM',5:'GEI',6:'MAG',
                        7:'SPH',8:'RLL'}
        coord_type = spacepy_dict[coord_type]
        if coord_grid==0:
            coord_grid = 'car'
        elif coord_grid==1:
            coord_grid = 'sph'
    return coord_type, coord_grid
    
def coord_units(coord_type, coord_grid):
    '''return proper units given coordinate system'''
    
    if coord_grid=='car':
        if coord_type in ['GDZ','SPH','RLL']:
            print(f'There is no cartesian version in the {coord_type} coordinate system.')
            return
        return {'utc_time':'s','net_idx':'','c1':'R_E','c2':'R_E','c3':'R_E'}
    elif coord_grid=='sph':
        if coord_type=='GDZ':
            return {'utc_time':'s','net_idx':'','c1':'deg','c2':'deg','c3':'km'}
        else:
            return {'utc_time':'s','net_idx':'','c1':'deg','c2':'deg','c3':'R_E'}
        
def coord_names(coord_type, coord_grid):
    '''given type and grid of coordinates, return dicitonary of coordinate names.'''
    
    if coord_grid=='car':
        return {'c1':'X_'+coord_type, 'c2':'Y_'+coord_type, 'c3':'Z_'+coord_type}
    elif coord_grid=='sph' and coord_type=='GDZ':
        return {'c1':'Longitude', 'c2':'Latitude', 'c3':'Altitude'}
    elif coord_grid=='sph' and coord_type!='GDZ':
        return {'c1':'Longitude', 'c2':'Latitude', 'c3':'Radius'}
import pandas as pd
import numpy  as np
#### Computer/ Command Line functions
import os
import os.path
import shutil
import linecache
import logging
import sys

#### Import the Pygeodyn Modules
## level 3
from pygeodyn.control import RunController
from pygeodyn.read    import PygeodynReader


class InheritControl(RunController):
    """Class that enable satellite to inherit the RunController Class"""
    def __init__(self):
        RunController.__init__(self)
        pass


# class Satellite_ICESat2(PygeodynController, PygeodynReader ):
class ICESat2(RunController):#,  PygeodynReader):
    """Inherited class for the ICESat-2 Satellite's run configuration.
    
    Level 2 in the Pygeodyn Infrastructure but it inherits the methods in Level
    3.  Class with satellite specific confiuguration for running Pygeodyn with
    ICESat2.  This class hosts all major modifications to the methods in the
    RunController and PygeodynReader that allow the running of the ICESat2
    satellite through Pygeodyn.  The setup here is originally for PCE trajectory
    analysis.


    Parameters
    ----------
        Inherit PygeodynController : Class
            Used to control and run the GEODYN with Python
        Inherit PygeodynReader : Class
            Used to read and reformat the GEODYN output with Python

    
    Returns
    -------
        Object
            Returns an object with methods that have been re-written to
            accomodate the Icesat2 satellite, its data, and its default
            configuration on AWS.
            
    """

    def __init__(self):
        # Initialize the ICESat2 class to contain the methods from RunController
        InheritControl.__init__(self)
        # Call the control path pointer to establish attributed paths
        self.ctrlStage1_setup_path_pointers()

        #=====================================================================

        # Universal ICESat2 Properties 
        # COSPAR ID number
        self.satellite_id = '1807001'
        
        #=====================================================================
        ## Use the Global Files for the timeperiod of interest
        epoch_str = self.params['epoch_start'].split('.')[0]
        epoch_dt = pd.to_datetime(epoch_str, format='%y%m%d %H%M%S')
        if epoch_dt.year<2020:
            #### Atmospheric Gravity file name
            self.filename_atmograv  = 'ATGRAV.glo-3HR_20160101-PRESENT'\
                                                +'_9999_AOD1B_0006.0090'
            #### Planetary Ephemeris file name
            self.filename_ephem     = 'ephem1430.data_2025'
            #### Gravity field file name
            self.filename_gravfield = 'eigen-6c.gfc_20080101_do_200_fix.grv'

        #=====================================================================
        ### Run-type Options
        list_run_types = ["PCE_vs_OrbitFit",
                          "OrbitPropagation"] 
        # Fill in the appropriate settings based on the run_type.
        if self.run_type == "PCE_vs_OrbitFit":
            self.tracking_data_type = 'PCE'
            self.cards_to_remove = [ 'ACCEL9','ORBTVU', 'RESID', 'CON9PA',]

            if epoch_dt.year<2020:
                #### G2B file name
                self.filename_g2b                 = 'g2b_pce_fullset_nomaneuver'  
                #### PCE Ascii textfile name
                self.StateVector_epochs_datafile  = self.dir_input\
                                                    +'/PCE_ascii.txt'
        #
        elif self.run_type == "OrbitPropagation":
                self.filename_g2b = False
                self.StateVector_epochs_datafile  = self.dir_input\
                                                    +'/PCE_ascii.txt'
        else:
            print("Run Settings Error: User input bad option as run_type.")
            print("    bad input:           ",self.run_type)
            print("    available run types: ",list_run_types)
            sys.exit(0)

        #=====================================================================
        

#         self.path_to_binaryrvgs     = '/data/data_geodyn/inputs/icesat2/pre_processing/traj_files_rvg'
#         self.StateVector_epochs_datafile = '/data/data_geodyn/inputs/icesat2/setups/PCE_ascii.txt'
        

        
        
        
        
        
    
    
    def clean_iisset_file(self):
        '''
        Overwrite the setup file with the icesat2 specific run parameters.

        To make major changes to this function (i.e. implemement a NON-PCE based run of ICESat2)
            construct a new class to inherit this one, and overwrite this method in that class. 
        
        This function does the following:
            - copies setup file to a temporoary file
            - Adds the GLOBAL TITLE Cards (3 strings at top)
            - Removes all instances of the GPS satellites
            - Deletes specified cards in the cards_to_remove list
            - Modifies the cards in card_strings dict
            - Includes the time dependent DRAG options in the card_drag_strings dict
            - Adds cards that are wanted that are not in the file.

            * this

        '''
        logger = logging.getLogger(self.execlog_filename)
        logger.info(f"Cleaning iiset file")

        #### --------------------------------------------------------------------
        #### Initialize our variables from user input
        (path_to_setupfiles, 
        setup_file_arc, 
        SAT_ID, 
        den_model_setupval) = ( self.dir_input,  
                                self.setup_file_arc, 
                                self.satellite_id, 
                                self.iisset_den)
              
        #### OPEN THE LOG FILE TO APPEND THE SETUP PARAMETERS TO
        log_file = open(self.log_file, 'a')

        ORIG_iisset_file = self.filename_iisset 
        iisset_file      = 'cleaned_setup'+'_'  + self.arcdate_for_files
        log_file.write(f"    Original iisset file            {self.filename_iisset} \n")
        log_file.write('\n')
        
        
        #### --------------------------------------------------------------------
        ##### COPY THE FILE SO THAT YOU DON'T OVERWRITE THE ORIGINAL
        ####    We copy to a temporary file "cleaned_setup_file"
                    
        shutil.copyfile(ORIG_iisset_file, self.dir_tmp_arc +'/'+iisset_file+'.bz2')
        
        os.chdir(self.dir_tmp_arc)
        os.system('bunzip2 -v '+ '*.bz2')
        os.chdir(self.path_pygeodyn)
        
        iisset_file = self.dir_tmp_arc+'/' +'cleaned_setup'+'_'  + self.arcdate_for_files
        
        
      
    
      
        #### --------------------------------------------------------------------
        #### identify the cards we do not want in the setup file according to user request
        cards_to_remove = self.params['cards_to_remove']
        # 
        ###  The below cards must be removed despite any modifications 
        ###  the user requests for the working of the PCE data run type
        cards_to_remove.append('SATPAR') 
        cards_to_remove.append('EPOCH') 
        cards_to_remove.append('ELEMS1') 
        cards_to_remove.append('ELEMS2') 
        cards_to_remove.append('OLOAD') 
        cards_to_remove.append('DRAG   0 0') 
        cards_to_remove.append('XEPHEM') 
        cards_to_remove.append('REFRAC') 
        cards_to_remove.append('GPSMOD') 
        cards_to_remove.append('OFFSET') 
        cards_to_remove.append('OFFADJ') 
        cards_to_remove.append('ANTPHC') 
        cards_to_remove.append('ANTPH2') 
        cards_to_remove.append('CGMASS') 
        cards_to_remove.append('MBIAS')
        
        cards_to_remove.append('SIGMA          51')   ### 51 is the TWO-WAY-RANGE datatype (not PCE)
        cards_to_remove.append('SIGMA          85')   ### 85 is the DOUBLY DIFFERENCED ONE -WAY RANGES (not PCE)
        cards_to_remove.append('SELECT         51') 
        cards_to_remove.append('SELECT         85') 

        
        


        #### --------------------------------------------------------------------
        ##### Grab the EPOCH start and end times
        EPOCH_lines = []
        with open(iisset_file, 'r') as f:
            for line_no, line_text in enumerate(f):
                if 'EPOCH         ' in line_text:
                    EPOCH_lines.append(line_no) 

        #### --------------------------------------------------------------------
        ##### Identify and save the EPOCH start and end times
        for i,val in enumerate(EPOCH_lines):
            satpar_line = linecache.getline(iisset_file,val) # Check the above SATPAR line get the correct satellite ID (i.e. NOT GPS)

            ##### only do this for the main satellite, so look for the correct SATID in the SATPAR card above EPOCH
            if SAT_ID in satpar_line:
                epoch_start = linecache.getline(iisset_file,val + 1)[20:40].strip() #181013210000.0000000
                epoch_start_YYMMDD = linecache.getline(iisset_file,val + 1)[20:26].strip()       # 181013
                epoch_start_HHMM = linecache.getline(iisset_file,val + 1)[26:30].strip()         # 2100
                epoch_start_SS_SSSSSSS = linecache.getline(iisset_file,val + 1)[30:40].strip()   # 00.0000000     

                epoch_end   = linecache.getline(iisset_file,val + 1)[60:80].strip() #1810160300 00.000
                epoch_end_YYMMDD = linecache.getline(iisset_file,val + 1)[60:66].strip()       # 181016
                epoch_end_HHMM = linecache.getline(iisset_file,val + 1)[66:70].strip()         # 210000.0000000
                epoch_end_SS_SSSSSSS = linecache.getline(iisset_file,val + 1)[70:80].strip()   # 00.0000000     
#         print('original epoch strt',epoch_start)
#         print('original epoch end',epoch_end)
#         print(self.arcnumber)
        
        
        if  self.params['epoch_start'] == None :  # if no options given 
            pass  ## use the defaults from the setup file (parsed above)
        else:
            
            epoch_start            = self.params['epoch_start'][self.arcnumber]
            epoch_start_YYMMDD     = epoch_start[:6].strip() 
            epoch_start_HHMM       = epoch_start[7:11].strip()
            epoch_start_SS_SSSSSSS = epoch_start[11:21].strip()
            epoch_start            = epoch_start_YYMMDD+epoch_start_HHMM+epoch_start_SS_SSSSSSS
                 
                
        if  self.params['epoch_end'] == None :
            pass
        else:
            epoch_end            = self.params['epoch_end'][self.arcnumber]
            epoch_end_YYMMDD     = epoch_end[:6].strip() 
            epoch_end_HHMM       = epoch_end[7:11].strip()
            epoch_end_SS_SSSSSSS = epoch_end[11:21].strip()
            epoch_end            = epoch_end_YYMMDD+epoch_end_HHMM+epoch_end_SS_SSSSSSS

        #### --------------------------------------------------------------------
        #### Use pandas datetime and time delta to make adjustments to the dates on the ATGRAV and DRAG cards
        #### --------------------------------------------------------------------
        epoch_start_dt = pd.to_datetime( epoch_start_YYMMDD+epoch_start_HHMM, format='%y%m%d%H%M%S')
        epoch_end_dt = pd.to_datetime( epoch_end_YYMMDD+epoch_end_HHMM, format='%y%m%d%H%M%S')

        
        #### RE-SAVE THE DATE in datetime format for easy printing
        self.epoch_start_dt = epoch_start_dt
        self.epoch_end_dt   = epoch_end_dt

        
        dt_2days = pd.Series(pd.to_timedelta(48,'h'))
        dt_1days = pd.Series(pd.to_timedelta(24,'h'))
        
        dt_epoch_start_minus2days = (epoch_start_dt - dt_2days).dt.strftime('%y%m%d%H%M%S.0000000').values[0]
        dt_epoch_end_plus1days    = (epoch_end_dt + dt_1days).dt.strftime('%y%m%d%H%M%S.000').values[0]

                            
        
        ##### -------------------------------------------------------------------------------------------
        ##### -------------------------------------------------------------------------------------------
        ##### -------------------------------------------------------------------------------------------
        ###       FIND THE X,Y,Z,Xdot,Ydot,Zdot for this epoch start in the PCE data.
        ##### -------------------------------------------------------------------------------------------
#         os.system('bunzip2'+' '+self.StateVector_epochs_datafile+'.bz2')
        
        epoch_start_dt_STR = str(epoch_start_dt)
        date_in_file_flag = False
        
#         print("Epoch Start: "  , epoch_start_dt_STR)
#         print("Epoch End:   "  , epoch_end_dt)

        with open(self.StateVector_epochs_datafile, 'r') as f:
            for line_no, line_text in enumerate(f):
                
                if epoch_start_dt_STR in line_text:
                    date_in_file_flag= True
#                     print('    ','xyzline',line_no,line_text)

                    break
           
        if date_in_file_flag == False:
            change_elems_flag = False
            print(epoch_start_dt_STR,'not found in file.  Leaving ELEMS as is.')
#             print('Check that the start date:',epoch_start_dt_STR)
#             print('    is within the PCE date range saved in the file')
#             print('       ',self.StateVector_epochs_datafile)
#                     os.system('bzip2'+' '+'/data/data_geodyn/inputs/icesat2/setups/StateVector_epochs.txt')
#             sys.exit()

        else:
            change_elems_flag = True
            xyzline = pd.read_csv(self.StateVector_epochs_datafile, 
                        skiprows = line_no, 
                        nrows=1,           
                        sep = '\s+',
                        dtype=str,
                        names = [
                            'Date',
                            'MJDSECs', 
                            'RSECS', #(fractional secs)
                            'GPS offset', # (UTC - GPS offset (secs))
                            'X',
                            'Y',
                            'Z',
                            'X_dot',
                            'Y_dot',
                            'Z_dot',
                            'YYMMDDhhmmss',
                                ],)

            X     =  xyzline['X'].values[0].ljust(20)     #'  -745933.8926940708'
            Y     =  xyzline['Y'].values[0].ljust(20)     #'  -4864983.834066438'
            Z     =  xyzline['Z'].values[0].ljust(20)     #'    4769954.60524261'
            X_dot =  xyzline['X_dot'].values[0].ljust(20) #'  457.44564954037634'
            Y_dot =  xyzline['Y_dot'].values[0].ljust(20) #'   5302.381564886811'
            Z_dot =  xyzline['Z_dot'].values[0].ljust(20) #'    5463.55571622269'

            ##### -------------------------------------------------------------------------------------------
            #### --------------------------------------------------------------------------------------------

        
        ####   INPUT THE OPTIONS ON THE SPECIFIC CARDS YOU WANT TO CHANGE
        ##### Putting in the options is one of the hardest parts of using GEODYN
        #####    They require VERY specific inputs depending on the run type.  
        card_strings = {}
        
        
            #####  ORBFIL KEY ------ Requests output of trajectory file(s) on specified unit(s) 
            #####                           on the last iteration of the run.
            #####
            #####   columns      Orbit output option
            #####    7           Coordinate system of output
            #####                      0 - True of date (default)
            #####                      1 - True of reference date 
            #####                   ** 2 - Mean of year 2000    
            #####    8           Switch indicating whether trajectory file is for a single 
            #####                  satellite or a set of satellites.
            #####                   ** 0 - Single satellite 0 0
            #####                      1 - Set of satellites. This option has meaning 
            #####                            only when used in conjunction with sets of 
            #####                            satellites (See EPOCH and SLAVE option cards
            #####                            for more details ). If satellite ID in columns
            #####                            18-24 is a master satellite , then the trajectory
            #####                          for all satellites in the set will be output.
            #####  9-11           Mandatory unit number for trajectory file. All trajectory 
            #####                  files within an arc must have unique unit numbers. 
            #####                  The suggested unit number starts at 130.
            #####  18-25        Satellite ID. This field must contain a valid ID.
            #####  25-44        START date and time for trajectory output (YYMMDDHHMMSS.SS).
            #####  45-59        STOP  date and time for trajectory output (YYMMDDHHMMSS.SS).
            #####  60-72        Time interval between successive trajectory outputs.
            
            
        txt = self.arc_length
        chars = [s for s in [char for char in txt] if s.isdigit()]
        int_arc_length = int(''.join(chars))

            
        if int_arc_length == 24:
#             dt_end_minusmins = (epoch_end_dt - pd.Series(pd.to_timedelta(20,'m'))).dt.strftime('%y%m%d%H%M%S.0000000').values[0]
#             dt_start_plusmins  = (epoch_start_dt + pd.Series(pd.to_timedelta(20,'m'))).dt.strftime('%y%m%d%H%M%S.0000000').values[0] 
            
            # #### ADD A TEMPORARY HASDM RUN OPTION:  july 10, 2022 
            if self.den_model == 'hasdm_oc':
                dt_end_minusmins = (epoch_end_dt - pd.Series(pd.to_timedelta(20,'m'))).dt.strftime('%y%m%d%H%M%S.0000000').values[0]
                dt_start_plusmins  = (epoch_start_dt + pd.Series(pd.to_timedelta(20,'m'))).dt.strftime('%y%m%d%H%M%S.0000000').values[0] 
            else:
                dt_end_minusmins = (epoch_end_dt - pd.Series(pd.to_timedelta(1,'m'))).dt.strftime('%y%m%d%H%M%S.0000000').values[0]
                dt_start_plusmins  = (epoch_start_dt + pd.Series(pd.to_timedelta(1,'m'))).dt.strftime('%y%m%d%H%M%S.0000000').values[0]       

        elif int_arc_length < 24:
            dt_end_minusmins = (epoch_end_dt - pd.Series(pd.to_timedelta(1,'m'))).dt.strftime('%y%m%d%H%M%S.0000000').values[0]
            dt_start_plusmins  = (epoch_start_dt + pd.Series(pd.to_timedelta(1,'m'))).dt.strftime('%y%m%d%H%M%S.0000000').values[0]       


        card_strings['SELECT         01']  =  'SELECT         01                       '+dt_start_plusmins+dt_end_minusmins   
        card_strings['SELECT         02']  =  'SELECT         02                       '+dt_start_plusmins+dt_end_minusmins   
        card_strings['SELECT         03']  =  'SELECT         03                       '+dt_start_plusmins+dt_end_minusmins   

        card_strings['ORBFIL'] =  'ORBFIL20131'+'      '   \
                                      + SAT_ID + '     '   \
                                      + str(dt_start_plusmins)[:-6] +'  '       \
                                      + str(dt_end_minusmins)[:15]  +'        ' \
                                      + '120'   # time interval between successive outputs
        
        print('     SELECT data data from:       ',str(dt_start_plusmins),str(dt_end_minusmins))
        print('     ORBFIL will print data from: ',str(dt_start_plusmins)[:-6],str(dt_end_minusmins)[:15])
#         card_strings['ORBFIL'] =  'ORBFIL20131      '+SAT_ID+'     '+str(dt_start_plusmins)[:-6]+'  '+str(dt_end_minusmins)[:15]+'         60'
        
#         card_strings['OBSVU']  =  'OBSVU 2'  # print residuals on last iteration only
        card_strings['OBSVU']  =  'OBSVU 5'  # NO residuals requested for any arc

        ##### --------------------------------------------------------------------
            ####   PRNTVU KEY ------ Used to control the IIS and IIE printed content 
            ####                             Be warned that if you include a bunch, the file 
            ####                             will be huge, and the run time will increase 
            ####                             (printing to ascii is slow)
            ####    columns      IIS output option
            ####      9          Simple list of GEODYN -IIS setup. Interpretive
            ####     10          Interpretive list of GEODYN -IIS setup.
            ####     11          Observation block \ion report.
            ####     12          Gravity model coefficients. Global  
            ####     13          Global parameter values and sigmas.                             
            ####     14          Arc parameter values and sigmas.
            ####     15          Sea surface topography. Ocean
            ####     16          Ocean Tide Model.  
            ####    columns      IIE output option
            ####     18          Simple list of GEODYN -IIS setup.
            ####     19          Values of estimated E-biases.
            ####     20          E-matrix labels in Summary Page.
            ####     21          Adjusted station baselines  
            ####     22          Correlations for adjusted parameters.                             
            ####     23          Shadow crossing. 
            ####-----------------------------------------------------------------------------------------------
            ##### ORBTVU KEY ------ Controls the printing of ASCII 
            #####                           orbit info to a separate file.
            ####   columns       Orbit output option
            #####    7           Frequency of trajectory output.
            #####                    0 - vwd btwn times in cols 25-59 and at 
            #####                          intvl specfd in columns 60-72.
            #####                  **1 - vwd btwn times in cols 25-59 at 
            #####                          data points only.
            #####                    2 - vwd btwn times in cols 25-59 at data
            #####                          points and at the intvl in columns 60-72.
            #####    8           Coordinate system of output
            #####                  **0 - True of date
            #####                    1 - True of ref date 
            #####                    2 - Mean of year 2000
            #####    9           Trajectory type indicator.
            #####                  **0 - Cartesian ephemeris 
            #####                    1 - Keplerian ephemeris 
            #####                    2 - Both Cartesian and Keplerian ephemerides.
            #####    1           Iterations on which trajectory will be printed.
            #####                    0 - First arc iter of first global iter 
            #####                  **1 - Last arc iter of last global iter 
            #####                    2 - Both first first and last last 
            #####                    3 - All iterations
#       card_strings['PRNTVU'] =  'PRNTVU55212222    22122'  # original
        card_strings['PRNTVU'] =  'PRNTVU5521111211 121122'  # suppress some IIS/IIE outputs.

        card_strings['ATMDEN'] =  'ATMDEN  '+ den_model_setupval
        card_strings['ATGRAV']  =  'ATGRAV9090              '+dt_epoch_start_minus2days +''+dt_epoch_end_plus1days[:-1]   
        card_strings['I64G2E']  =  'I64G2E         25'  # using 30 like in st-SLR run maxed out the memory usage
        card_strings['SIGMA           1']  =  'SIGMA           1               1.0                 1.0'    
        card_strings['SIGMA           2']  =  'SIGMA           2               1.0                 1.0'    
        card_strings['SIGMA           3']  =  'SIGMA           3               1.0                 1.0'   
#         card_strings['SIGMA          51']  =  'SIGMA          51               10.0D+25             0.10'  
#         card_strings['SIGMA          85']  =  'SIGMA          85               0.010000            0.010000'  
        
        ### Fix the coordinate system... PCE Data was in J2000
        card_strings['REFSYS']  = 'REFSYS193310        '+epoch_start+ '0'
#         print('TEST FIND EPOCH-- epoch_start:', epoch_start)
        card_strings['EPOCH']   = 'EPOCH               '+epoch_start+epoch_start+epoch_end
        card_strings['SATPAR']  = 'SATPAR   139     '+SAT_ID+'          9.53000000       1514.000'
        
        if change_elems_flag == True:
            card_strings['ELEMS1']  = 'ELEMS11             '+X+''+Y+''+Z+''   
            card_strings['ELEMS2']  = 'ELEMS2              '+X_dot+''+Y_dot+''+Z_dot+''
                
        #### Suppress the printing of the flux model
        card_strings['FLUX  1']  =  'FLUX  0'
        card_strings['STEP']  =  'STEP             '+SAT_ID+'           '+str(int(self.geodyn_StepSize))+'.' 

        
        
        #### --------------------------------------------------------------------
        ####    Search through the file to see if any of the cards we WANT are NOT in the file
        #### --------------------------------------------------------------------
        ##### read in all lines of the file and save them
        with open(iisset_file, "r") as f:
            lines_all = f.readlines()                
        ##### card flags to see if certain cards are present in the file
        card_flag = {}
        for card in card_strings:
            ### Set the default flag to be False,  if the card is in the file, flip the flag to True
            card_flag[card] = False
            for line in lines_all:
                if card in line:
                    card_flag[card] = True

        #### --------------------------------------------------------------------
        ####    Edit the cards that exist in the file that we want to modify
        #### --------------------------------------------------------------------
        ###### Re-write the file line-by-line and EDIT the cards that need to be modified    
        lines_replace = {}
        with open(iisset_file, "r") as f:
            lines = f.readlines()
            for line_num, line in enumerate(lines):
                for card in card_strings:
                    if card in line:
                        lines_replace[line_num] = card_strings[card]
        with open(iisset_file, "r") as f:
            lines_all = f.readlines()
        with open(iisset_file, "w") as f:
            for line_num, line in enumerate(lines_all):
                if line_num in lines_replace:
#                     print('replacing line',lines_replace[line_num])
                    f.write(lines_replace[line_num]+'\n')
                else:
                     f.write(line)

        #####  IF we are using CD adjustement drag options, then set the drag cards according to the run settings
        #####  If we are NOT using CD adjustment, remove DRAG times from the file
        ####   INPUT THE DRAG OPTIONS  for time dependent drag
        card_drag_strings={}
        card_drag_strings['CONDRG']  =  'CONDRG  1        '+SAT_ID+'     '                   \
                                                + str(epoch_start[:-5])+str(epoch_end[:-5])  \
                                                + '         0.50000  28800.'
                                             #     '         0.50000  28800.'

        
        CD_VALUE = str(self.params['cd_value'])
        print('   Using a CD value of ', CD_VALUE)

        if self.params['cd_adjustment_boolean'] == True:  ### Allow CD to ADJUST, i.e. multiple DRAG cards with times
           
            hours_between_cd_adj = self.params['hours_between_cd_adj']
            if self.params['total_hours_in_run']==hours_between_cd_adj:   # The 24 hour case
                num_of_cd_adj = (self.params['total_hours_in_run']/self.params['hours_between_cd_adj'])
            else:    
                num_of_cd_adj = (self.params['total_hours_in_run']/self.params['hours_between_cd_adj']) #- 1
            add_hours_dt = pd.Series(pd.to_timedelta(hours_between_cd_adj,'h'))
            
            drag_dates = []
            for i_cd in np.arange(0, num_of_cd_adj):
                factor = i_cd+1
                drag_dates.append( (epoch_start_dt+add_hours_dt*factor).dt.strftime('%y%m%d%H%M%S').values[0])
                
            for i_cd in np.arange(0, num_of_cd_adj):
                i_cd = int(i_cd)
                print('     drag_date ', i_cd ,' ',  pd.to_datetime( drag_dates[i_cd], format='%y%m%d%H%M%S'))

                card_drag_strings[i_cd] =  'DRAG             '+ SAT_ID+' '            \
                                                              + CD_VALUE+'0000000D+00'\
                                                              + '     '+drag_dates[i_cd][:10] \
                                                              + ' 0.00    0.100D+02'
#                 card_drag_strings[i_cd] =  'DRAG             '+SAT_ID+' 2.2000000000000D+00'+drag_dates[i_cd][:10]+' 0.00    0.100D+02'

        else:
            cards_to_remove.append('CONDRG')

            
            #### --------------------------------------------------------------------
        ####   INPUT THE DRAG OPTIONS  for time dependent drag
#         card_drag_strings={}
#         card_drag_strings['CONDRG']  =  'CONDRG  1        '+SAT_ID+'     '+str(epoch_start[:-5])+str(epoch_end[:-5])+'         0.50000  28800.'

        #### for adding time dependent drag estimations.  We need to do a few things:
        ###       Find the drag card that is already in the file:
        ###       Add CONDRAG before all drag cards
        ###       Add DRAG cards with TIME periods after the first drag card
        if self.params['cd_adjustment_boolean'] == True:
            with open(iisset_file, "r") as f:
                lines_all = f.readlines()                
            with open(iisset_file, "w") as f:
                for line in lines_all:
                    if 'DRAG   0 0       '+SAT_ID+' 2.3000000000000E+00' in line:  #this finds the DRAG line.  
                        f.write(card_drag_strings['CONDRG'] + ' \n')
                        f.write('DRAG             '+SAT_ID+' '+CD_VALUE+'0000000E+00'+ ' \n')
                        for i_cd in np.arange(0, num_of_cd_adj):
                            i_cd = int(i_cd)
                            f.write(card_drag_strings[i_cd] + ' \n')                 
                    else:
                        f.write(line)
                        
        elif self.params['cd_adjustment_boolean'] == False: ### DONT allow CD to ADJUST, i.e. only 1 DRAG card, no time dep.
            print('   Running without DRAG time dependence')
            with open(iisset_file, "r") as f:
                lines_all = f.readlines()                
            with open(iisset_file, "w") as f:
                for line in lines_all:
                    if 'DRAG   0 0       '+SAT_ID+' 2.3000000000000E+00' in line:  #this finds the DRAG line.  
                        f.write('DRAG             '+SAT_ID+' '+CD_VALUE+'0000000E+00'+ ' \n')
                    else:
                        f.write(line)
              
        #####-----------------------------------------------------------------------------
        ##### Delete the SATPAR GPS, EPOCH, ELEMS110, and ELEMS2 lines after the SATPAR GPS
        #####   Do this by finding the SATPAR for our sat and then saving it and the next 3 lines
        #####   then delete all the SATPAR,EPOCH,ELEMS110, ELEMS2 and restore the ones we saved
        #####-----------------------------------------------------------------------------

        if change_elems_flag == False:
            ##### read in all lines of the file and save them
            with open(iisset_file, "r") as f:
                lines_all = f.readlines()    
            
            for iline, line in enumerate(lines_all):
                if 'ELEMS1'in line:
                    save_ELEMS1 = iline+1
                elif 'ELEMS2' in line:
                    save_ELEMS2 = iline+1
                
            line_ELEMS1 = linecache.getline(iisset_file, save_ELEMS1)
            line_ELEMS2  = linecache.getline(iisset_file, save_ELEMS2)
            
            card_strings['ELEMS1']  = line_ELEMS1
            card_strings['ELEMS2']  = line_ELEMS2
            
#             print(line_ELEMS1)
#             print(line_ELEMS2)

        ####----------------------------------------------------------------------
        #### REMOVE CARDS:: rewrite the file without the cards we specified in the cards_to_remove dict
        ####----------------------------------------------------------------------

        ##### read in all lines of the file and save them
        with open(iisset_file, "r") as f:
            lines_all = f.readlines()    
        ##### Re-write the file line-by-line WITHOUT the cards that we want to remove    
        with open(iisset_file, "w") as f:
            for iline, line in enumerate(lines_all):
                if any(card in line for card in cards_to_remove):
                    # IF the any of the cards in the list are in the line, dont add it
                    pass
                else:
                    f.write(line)                
        
                        
        
        ####----------------------------------------------------
        #### Add any cards that we want that are not in the file
        ##### this INCLUDES our saved 
        #####      SATPAR, EPOCH, ELEMS1, ELEMS2
        #####---------------------------------------------------------
        with open(iisset_file, "r") as f:
            lines_all = f.readlines()                  

        # use some switches to determine if things have already been written in the loop and avoid writing too many
        switch_cardcount = 0
        switch_2     = True
        
        for card in card_flag:
            if card_flag[card] == False:
                with open(iisset_file, "w") as f:
                    for line in lines_all:
                        if 'ALBEDO' in line:  #this overwrites the line after albedo. 
                            # MAYBE TODO:  this may not write multiple cards that aren't in the file
                            if switch_cardcount == 0:
                                f.write(line)
                                f.write(card_strings[card] + ' \n') 
                                switch_cardcount += 1
                            else: 
                                f.write(card_strings[card] + ' \n')
                        else:
                            f.write(line)
                            
        ##### Write our satellite parameters back in         
        with open(iisset_file, "w") as f:
            for line in lines_all:
                if (('REFSYS' in line) and (switch_2 == True)):
                    f.write(card_strings['REFSYS']  + ' \n')
                    f.write(card_strings['SATPAR']  + ' \n')
                    f.write(card_strings['EPOCH']   + ' \n')
                    if change_elems_flag == True:
                        f.write(card_strings['ELEMS1']  + ' \n')
                        f.write(card_strings['ELEMS2']  + ' \n')
                    elif change_elems_flag == False:
                        f.write(card_strings['ELEMS1'])
                        f.write(card_strings['ELEMS2'])

                    switch_2 = False
                else:
                    f.write(line)

                    
#         self.verboseprint('    ','Orig:')
#         self.verboseprint('    ','    ',line_ELEMS11.rstrip('\n'))
#         self.verboseprint('    ','    ',line_ELEMS2.rstrip('\n'))
        self.verboseprint('    ','PCE Update:')
        self.verboseprint('    ','    ',card_strings['ELEMS1'])
        self.verboseprint('    ','    ',card_strings['ELEMS2'])
        
        ####----------------------------------------------------------------------
        #### Add three lines to the start of the file.  This is the GLOBAL TITLE
        ####----------------------------------------------------------------------

        with open(iisset_file, 'r+') as f:
            content = f.read()
            f.seek(0, 0)   # find the first lines
            f.write('### \n') 
            f.write('###   '+self.arc_name_id+'  \n') 
            f.write('### \n') 
            f.write(content) 
            
            
        ####----------------------------------------------------------------------
        #### Try doing a complete job of removing the GPS satellites.
        ####----------------------------------------------------------------------
            
        delete_gps_sats = [ '5041144',
                            '5044284',
                            '5051204',
                            '5154184',
                            '5345214',
                            '5347224',
                            '5356164',
                            '5459194',
                            '5460234',
                            '5461024',
                            '5553175',
                            '5652315',
                            '5658125', 
                            '5755155',
                            '5757295',
                            '5848075',
                            '5950055',
                            '6062256',
                            '6163016',
                            '6265246',
                            '6366276',
                            '6464306',
                            '6467066',
                            '6468096',
                            '6469036',
                            '6571266',            
                            '6572086',
                            '6573106',
                            '6649045',
                            '6670326',
                            '9743134',
                            '9946114',        
                            ]
        ##### read in all lines of the file and save them
        with open(iisset_file, "r") as f:
            lines_all = f.readlines()    
        ##### Re-write the file line-by-line WITHOUT the cards that we want to remove    
        with open(iisset_file, "w") as f:
            for iline, line in enumerate(lines_all):
                if any(gps in line for gps in delete_gps_sats):
                    # IF the any of GPS IDs in the list are in the line, dont add it the line
                    pass
                else:
                    f.write(line)      

                    
                    
         #### WRITE TO THE LOG FILE! -------------------------------------------------------           
                    
        log_file.write(f"    Modified Cards                    \n")
        for card in card_strings:
            
            if card in ['SATPAR','EPOCH','ELEMS1','ELEMS2']:
                log_file.write(f"        {card.ljust(6)} (replacement) : {card_strings[card]} \n")

            else:
                log_file.write(f"        {card.ljust(20)} : {card_strings[card]} \n")
        log_file.write(f"    \n")

#         log_file.write(f"    DRAG Cards                    \n")
#         for card in card_drag_strings:
#             log_file.write(f"        {card.ljust(20)} : {card_drag_strings[card]} \n")
#         log_file.write(f"    \n")

        
        log_file.write(f"    Removed Cards                    \n")
        for card in cards_to_remove:
            log_file.write(f"        {card} \n")
        log_file.write(f"    \n")
        
        
        log_file.write(f"    DELETED GPS SATS                  \n")
        log_file.write(f"        {delete_gps_sats}             \n")

        
      # card_strings
      # card_drag_strings
        log_file.close()

        
        
            
            
            
    def ctrlStage4_populate_tmpdir_for_run(self):
        '''  This it the ICESAT2 version of this method.
             
             it is being overridden to INCLUDE the external attitude
        '''
        
        logger = logging.getLogger(self.execlog_filename)
        logger.info(f"ICESat2 - Construct a tmp directory in which to run IIS and IIE")

        
     
        #### Navigate to the tmp dirdir_tmp_arc
        os.chdir(self.dir_tmp_arc)
        
        ####-------------------------------------------------------------
        ####     Construct Common Setup of a GEODYN RUN
        ####         this is run in the TMPDIR_arc
        ####-------------------------------------------------------------
        self.verboseprint('-------------------------------------------------')
        self.verboseprint('       Linking files with the command line       ')
        self.verboseprint('-------------------------------------------------')
        
        self.verboseprint(self.tabtab,'Current DIR',os.getcwd())

        #### make copy to the External attitude file and save as EXAT01
        if not os.path.exists(self.dir_tmp_arc +'/EXAT01'+'.gz'):
#             if np.size(self.external_attitude) >= 1:
# #                 print('dict of EXATfilename: ',np.size(self.external_attitude))
#                 shutil.copyfile(self._EXTATTITUDE_filename[1], self.TMPDIR_arc +'/EXAT01'+'.gz')
#                 shutil.copyfile(self._EXTATTITUDE_filename[2], self.TMPDIR_arc +'/EXAT02'+'.gz')
#                 shutil.copyfile(self._EXTATTITUDE_filename[3], self.TMPDIR_arc +'/EXAT03'+'.gz')
#                 shutil.copyfile(self._EXTATTITUDE_filename[4], self.TMPDIR_arc +'/EXAT04'+'.gz')
#                 shutil.copyfile(self._EXTATTITUDE_filename[5], self.TMPDIR_arc +'/EXAT05'+'.gz')
#                 print('Copied 5 EXAT files')
#             else:
            shutil.copyfile(self.file_exat, self.dir_tmp_arc +'/EXAT01'+'.gz')
            self.verboseprint(self.tabtab,'copied:   exat file  > EXAT01'+'.gz')
            self.verboseprint(self.tabtab,'copied:   '+self.file_exat+' > EXAT01'+'.gz')
        else:
            self.verboseprint(self.tabtab,'copy is set up: EXAT01 file')

        
        #### make symlink to the G2B file and save as ftn40
        if not os.path.exists(self.dir_tmp_arc +'/ftn40'+''):
            os.symlink(self.file_G2B, self.dir_tmp_arc +'/ftn40'+'')
#             shutil.copyfile(self._G2B_filename, self.TMPDIR_arc +'/ftn40'+'')
            self.verboseprint(self.tabtab,'copied:   g2b file   > ftn40'+'')
        else:
            self.verboseprint(self.tabtab,'copy:  g2b file')

        #### make symlink to the gravity field and save as ftn12
        if not os.path.exists(self.dir_tmp_arc +'/ftn12'+''):
            shutil.copyfile(self.file_grav_field, self.dir_tmp_arc +'/ftn12'+'')
#             self.verboseprint(self.tabtab,'gravfield:',self._grav_field_filename)
            self.verboseprint(self.tabtab,'copied:   grav field > ftn12'+'')
        else:
            self.verboseprint(self.tabtab,'copy is set up: grav_field file')

        #### make symlink to the ephemerides and save as ftn01
        if not os.path.exists(self.dir_tmp_arc +'/ftn01'+''):
#             os.symlink(self._ephem_filename, self.TMPDIR_arc +'/ftn01')
            shutil.copyfile(self.file_ephem, self.dir_tmp_arc +'/ftn01'+'')
            self.verboseprint(self.tabtab,'copied:   ephem file > ftn01'+'')
        else:
            self.verboseprint(self.tabtab,'copy is set up: ephem file'+'')

        #### make symlink to the gdntable and save as ftn02
        if not os.path.exists(self.dir_tmp_arc +'/ftn02'):
            shutil.copyfile(self.file_gdntable, self.dir_tmp_arc +'/ftn02')
            self.verboseprint(self.tabtab,'copied:   gdntable   > ftn02')
        else:
            self.verboseprint(self.tabtab,'copy is set up: gdntable file')


        #### make symlink to the ATGRAVFIL and save as fort.18
        if not os.path.exists(self.dir_tmp_arc +'/fort.18'+''):
#             os.symlink(self._ATGRAV_filename, self.TMPDIR_arc +'/fort.18')
            shutil.copyfile(self.file_atmograv, self.dir_tmp_arc +'/fort.18'+'')
#             shutil.copyfile(self._ATGRAV_filename, self.TMPDIR_arc +'/ftn18')
#             self.verboseprint(self.tabtab,'ATGRAV:',self._ATGRAV_filename)
            self.verboseprint(self.tabtab,'copied:  atgrav     > fort.18'+'')
        else:
            self.verboseprint(self.tabtab,'symlink is set up: atgrav file')

            
        if not os.path.exists(self.dir_tmp_arc+'/ftn05'):
            os.system('cp '+self.filename_iisset+' '+self.dir_tmp_arc+'/ftn05')
            self.verboseprint(self.tabtab,'copying          : iieout file')
        else:
            self.verboseprint(self.tabtab,'copied           : iieout file')

        if not os.path.exists(self.dir_tmp_arc+'/giis.input'):
            os.system('cp  '+self.dir_tmp_arc+'/ftn05 '+self.dir_tmp_arc+'/giis.input')
            self.verboseprint(self.tabtab,'copying          : giis.input file')
        else:
            self.verboseprint(self.tabtab,'copied              : giis.input file')   

        self.verboseprint('-------------------------------------------------------------------------')
        self.verboseprint('-------------------------------------------------------------------------')


        #### GUNZIP the files:  gzip is a very fast compression option.
#         self.verboseprint(self.tabtab, "gunzipping the input data files")
        self.verboseprint(self.tabtab, "gunzipping the input data files")

        os.system('gunzip -vr *.gz')
#         os.system('gunzip -ftn01.gz')



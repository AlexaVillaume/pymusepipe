# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""MUSE-PHANGS core module
"""
# For print - see compatibility with Python 3
from __future__ import print_function

__authors__   = "Eric Emsellem"
__copyright__ = "(c) 2017, ESO + CRAL"
__license__   = "3-clause BSD License"
__contact__   = " <eric.emsellem@eso.org>"

# This module has been largely inspired by one developed 
# by Kyriakos and Martina from the GTO MUSE MAD team
# and further rewritten by Mark van den Brok. Thanks to all three for this!
#
# Eric Emsellem adapted a version from early 2017, provided by Mark
# and adapted it for the needs of the PHANGS project (PI Schinnerer)

# Importing modules
import numpy as np

# Standard modules
import os
from os.path import join as joinpath
import time

# cpl module to link with esorex
try :
    import cpl
except ImportError :
    raise Exception("cpl is required for this - MUSE related - module")

# Pyfits from astropy
try :
    import astropy as apy
    from astropy.io import fits as pyfits
except ImportError :
    raise Exception("astropy is required for this module")

# ascii reading
try :
    from astropy.io import ascii
except ImportError :
    raise Exception("astropy.io.ascii is required for this module")

try :
    from astropy.table import Table
except ImportError :
    raise Exception("astropy.table.Table is required for this module")

import warnings
from astropy.utils.exceptions import AstropyWarning

# Importing pymusepipe modules
from init_musepipe import InitMuseParameters
from recipes_pipe import PipeRecipes
from prep_recipes_pipe import PipePrep

# Likwid command
likwid = "likwid-pin -c N:"

# Included an astropy table
__version__ = '0.2.0 (22 May 2018)'
#__version__ = '0.1.0 (03 April    2018)'
#__version__ = '0.0.2 (08 March    2018)'
#__version__ = '0.0.1 (21 November 2017)'

############################################################
#                      BEGIN
# The following parameters can be adjusted for the need of
# the specific pipeline to be used
############################################################

# NOTE: most of the parameters have now been migrated to
# init_musepipe.py for consistency.

listexpo_types = {'DARK': 'DARK', 'BIAS' : 'BIAS', 'FLAT': 'FLAT,LAMP',
        'ILLUM': 'FLAT,LAMP,ILLUM', 'TWILIGHT': 'FLAT,SKY', 
        'WAVE': 'WAVE', 'STD': 'STD', 'AST': 'AST',
        'OBJECT': 'OBJECT', 'SKY': 'SKY'
        }

# This dictionary contains the types
dic_listMaster = {'DARK': 'MASTER_DARK', 
        'BIAS': 'MASTER_BIAS', 
        'FLAT': 'MASTER_FLAT',
        'TRACE': 'TRACE_TABLE',
        'TWILIGHT': 'TWILIGHT_CUBE', 
        'WAVE': 'WAVECAL_TABLE', 
        'LSF': 'LSF_PROFILE', 
        'STD': 'PIXTABLE_STD' 
        }

dic_listObject = {'OBJECT': 'PIXTABLE_OBJECT', 
        'SKY': 'PIXTABLE_SKY', 
        }

listexpo_files = {
        "OBJECT" : ['object', 'OBJECT', str, '20A'],
        "TYPE" : ['type', 'ESO DPR TYPE', str, '20A'],
        "DATE":  ['mjd', 'MJD-OBS', np.float, 'E'],
        "MODE":  ['mode', 'ESO INS MODE', str, '10A'],
        "EXPTIME":  ['exptime', 'EXPTIME', float, 'E'],
        "TPLS":  ['tpls', 'ESO TPL START', str, '30A'],
        "TPLN":  ['tplnexp', 'ESO TPL NEXP', np.int, 'J'],
        "TPLNO":  ['tplno', 'ESO TPL EXPNO', np.int, 'J']
         }

exclude_list_checkmode = ['BIAS', 'DARK']

esorex_rc = "/home/soft/ESO/MUSE/muse-kit-2.2-5/esorex-3.12.3/etc/esorex.rc"
        
dic_geo_table = {
        '1900-01-01': "geometry_table_wfm.fits",
        '2000-01-01': "geometry_table_wfm.fits",
        '2014-12-01': "geometry_table_wfm.fits",
        '2015-04-16': "geometry_table_wfm.fits",
        '2015-09-08': "geometry_table_wfm.fits",
        }

dic_astro_table = {
        '1900-01-01': "astrometry_table_wfm.fits",
        '2000-01-01': "astrometry_table_wfm.fits",
        '2014-12-01': "astrometry_table_wfm.fits",
        '2015-04-16': "astrometry_table_wfm.fits",
        '2015-09-08': "astrometry_table_wfm.fits",
        }

future_date = '2099-01-01'

############################################################
#                      END
############################################################
def lower_allbutfirst_letter(mystring):
    """Lowercase all letters except the first one
    """
    return mystring[0].upper() + mystring[1:].lower()

def create_time_name() :
    """Create a time-link name for file saving purposes

    Return: a string including the YearMonthDay_HourMinSec
    """
    return str(time.strftime("%Y%m%d_%H%M%S", time.localtime()))

def formatted_time() :
    """ Return: a string including the formatted time
    """
    return str(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime()))

def get_date_inD(indate) :
    """Transform date in Y-M-D
    """
    return np.datetime64(indate).astype('datetime64[D]')

def safely_create_folder(path, verbose=True):
    """Create a folder given by the input path
    This small function tries to create it and if it fails
    it checks whether the reason is because it is not a path
    and then warn the user
    and then warn the user
    """
    if path is None :
        if verbose : print_info("Input path is None, not doing anything")
        return
    if verbose : 
        print_info("Trying to create {folder} folder".format(folder=path), end='')
    try: 
        os.makedirs(path)
        print_endline("... Done", end='\n')
    except OSError:
        if not os.path.isdir(path):
            print_error("Failed to create folder! Please check the path")
            raise
            return
        if os.path.isdir(path):
            print_endline("... Folder already exists, doing nothing.")

def append_file(filename, content):
    """Append in ascii file
    """
    with open(filename, "a") as myfile:
        myfile.write(content)
        
def overwrite_file(filename, content):
    """Overwite in ascii file
    """
    with open(filename, "w+") as myfile:
        myfile.write(content)

def normpath(path) :
    """Normalise the path to get it short
    """
    return os.path.relpath(os.path.realpath(path))

HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[1;31;20m'
INFO = '\033[1;32;20m'
ERROR = '\033[91m'
ENDC = '\033[0m'
BOLD = "\033[1m"
def print_endline(text, **kwargs) :
    print(INFO + text + ENDC, **kwargs)

def print_warning(text, **kwargs) :
    print(WARNING + "# MusePipeWarning " + ENDC + text, **kwargs)

def print_info(text, **kwargs) :
    print(INFO + "# MusePipeInfo " + ENDC + text, **kwargs)

def print_error(text, **kwargs) :
    print(ERROR + "# MusePipeError " + ENDC + text, **kwargs)

#########################################################################
# Useful Classes for the Musepipe
#########################################################################
class MyDict(dict) :
    """New Dictionary with extra attributes
    """
    def __init__(self) :
        dict.__init__(self)

class PipeObject(object) :
    """New class to store the tables
    """
    def __init__(self, info=None) :
        """Initialise the nearly empty class
        Add _info for a description if needed
        """
        self._info = info

def lower_rep(text) :
    return text.replace("_","").lower()

#########################################################################
# Main class
#                           MusePipe
#########################################################################
    
class MusePipe(PipePrep, PipeRecipes):
    """Main Class to define and run the MUSE pipeline, given a certain galaxy name
    
    musep = MusePipe(galaxyname='NGC1087', rc_filename="", cal_filename="", 
                      outlog"NGC1087_log1.log", objects=[''])
    musep.run()
    """

    def __init__(self, galaxyname=None, pointing=0, objectlist=[], rc_filename=None, 
            cal_filename=None, outlog=None, logfile="MusePipe.log", reset_log=False,
            verbose=True, musemode="WFM-NOAO-N", checkmode=True, 
            strong_checkmode=False, **kwargs):
        """Initialise the file parameters to be used during the run

        Input
        -----
        galaxyname: string (e.g., 'NGC1208'). default is None. 
        objectlist= list of objects (string=filenames) to process. Default is empty

        rc_filename: filename to initialise folders
        cal_filename: filename to initiale FIXED calibration MUSE files
        outlog: string, output directory for the log files
        verbose: boolean. Give more information as output (default is True)
        musemode: string (default is WFM_N) String to define the mode to be considered
        checkmode: boolean (default is True) Check the mode or not when reducing
        strong_checkmode: boolean (default is False) Enforce the checkmode for all if True, 
                         or exclude DARK/BIAS if False

        Other possible entries
        ----------------------
        overwrite_astropy_table: boolean (default is False). Overwrite the astropy table even when
            it exists.
        warnings: strong  ('ignore'by default. If set to ignore, will ignore the Astropy Warnings.
        time_geo_table: boolean (default is True). Use the time dependent geo_table
        time_astro_table: boolean (default is True). Use the time dependent astro_table

        """
        # Verbose option
        self.verbose = verbose

        # Warnings for astropy
        self.warnings = kwargs.pop("warnings", 'ignore')
        if self.warnings == 'ignore':
           warnings.simplefilter('ignore', category=AstropyWarning)

        # Overwriting option for the astropy table
        self._overwrite_astropy_table = kwargs.pop("overwrite_astropy_table", False)

        # Use time dependent geo_table
        self._time_geo_table = kwargs.pop("time_geo_table", True)
        self._time_astro_table = kwargs.pop("time_astro_table", True)

#        super(MusePipe, self).__init__(**kwargs)

        # Setting the default attibutes #####################
        self.galaxyname = galaxyname
        self.pointing = pointing

        # Setting other default attributes
        if outlog is None : 
            outlog = "log_{timestamp}".format(timestamp=create_time_name())
            print_info("The Log folder will be {log}".format(outlog))
        self.outlog = outlog
        self.logfile = joinpath(self.outlog, logfile)

        # Further reduction options =====================================
        # Mode of the observations
        self.musemode = musemode
        # Checking if mode is correct
        self.checkmode = checkmode
        # Checking if mode is correct also for BIAS & DARK
        self.strong_checkmode = strong_checkmode

        # Set of objects to reduced
        self.objectlist = objectlist

        # End of parameter settings #########################

        # Init of the subclasses
        PipePrep.__init__(self)
        PipeRecipes.__init__(self, **kwargs)

        # =========================================================== #
        # Setting up the folders and names for the data reduction
        # Can be initialised by either an rc_file, 
        # or a default rc_file or harcoded defaults.
        self.my_params = InitMuseParameters(rc_filename=rc_filename, 
                            cal_filename=cal_filename)

        # Setting up the relative path for the data, using Galaxy Name + Pointing
        self.my_params.data = "{0}/P{1:02d}/".format(self.galaxyname, self.pointing)

        # Create full path folder 
        self.set_fullpath_names()

        # Go to the data directory
        # and Recording the folder where we start
        self.paths.orig = os.getcwd()

        # Making the output folders in a safe mode
        if self.verbose:
            print_info("Creating directory structure")
        self.goto_folder(self.paths.data)

        # ==============================================
        # Creating the extra pipeline folder structure
        for folder in self.my_params._dic_input_folders.keys() :
            safely_create_folder(self.my_params._dic_input_folders[folder], verbose=verbose)

        # ==============================================
        # Creating the folder structure itself if needed
        for folder in self.my_params._dic_folders.keys() :
            safely_create_folder(self.my_params._dic_folders[folder], verbose=verbose)

        # ==============================================
        # Init the Master exposure flag dictionary
        self.Master = {}
        for mastertype in dic_listMaster.keys() :
            safely_create_folder(self._get_path_expo(mastertype), verbose=self.verbose)
            self.Master[mastertype] = False

        # Init the Object folder
        for objecttype in dic_listObject.keys() :
            safely_create_folder(self._get_path_expo(objecttype), verbose=self.verbose)

        self._dic_listMasterObject = dict(dic_listMaster.items() + dic_listObject.items())
        # ==============================================

        # Going back to initial working directory
        self.goto_prevfolder()

        # ===========================================================
        # Now creating the raw table, and attribute containing the
        # astropy dataset probing the rawfiles folder
        # When creating the table, if the table already exists
        # it will read the old one, except if an overwrite_astropy_table
        # is set to True.
        self.create_raw_table()
        # ===========================================================

    def goto_prevfolder(self, logfile=False) :
        """Go back to previous folder
        """
        print_info("Going back to the original folder {0}".format(self.paths._prev_folder))
        self.goto_folder(self.paths._prev_folder, logfile=logfile, verbose=False)
            
    def goto_folder(self, newpath, logfile=False, verbose=True) :
        """Changing directory and keeping memory of the old working one
        """
        try: 
            prev_folder = os.getcwd()
            newpath = os.path.normpath(newpath)
            os.chdir(newpath)
            if verbose :
                print_info("Going to folder {0}".format(newpath))
            if logfile :
                append_file(joinpath(self.paths.data, self.logfile), "cd {0}\n".format(newpath))
            self.paths._prev_folder = prev_folder 
        except OSError:
            if not os.path.isdir(newpath):
                raise
    
    def set_fullpath_names(self) :
        """Create full path names to be used
        """
        # initialisation of the full paths 
        self.paths = PipeObject("All Paths useful for the pipeline")
        self.paths.root = self.my_params.root
        self.paths.data = joinpath(self.paths.root, self.my_params.data)

        for name in self.my_params._dic_folders.keys() + self.my_params._dic_input_folders.keys():
            setattr(self.paths, name, joinpath(self.paths.data, getattr(self.my_params, name)))

        # Creating the filenames for Master files
        self.paths.Master = PipeObject("All Paths for Master files useful for the pipeline")
        for expotype in dic_listMaster.keys() :
            # Adding the path of the folder
            setattr(self.paths.Master, self._get_attr_expo(expotype), 
                    joinpath(self.paths.data, self._get_path_expo(expotype)))

        self._dic_paths = {"master": self.paths.Master, "processed": self.paths}

    def read_astropy_table(self, expotype=None, stage="master"):
        """Read an existing Masterfile data table to start the pipeline
        """
        # Read the astropy table
        name_table = joinpath(self.paths.astro_tables, self._get_fitstablename_expo(expotype, stage))
        if not os.path.isfile(name_table):
            print_info("ERROR: Astropy table {0} does not exist".format(name_table))
        else :
            if self.verbose : print_info("Reading Astropy fits Table {0}".format(name_table))
            return Table.read(name_table, format="fits")
        
    def create_raw_table(self, overwrite_astropy_table=None, verbose=None, reset=True) :
        """ Create a fits table with all the information from
        the Raw files
        Also create an astropy table with the same info
        """
        if verbose is None: verbose = self.verbose
        if overwrite_astropy_table is not None: self._overwrite_astropy_table = overwrite_astropy_table
        if verbose :
            print_info("Creating the astropy fits raw data table")

        if reset:
            self._reset_tables()

        # Testing if raw table exists
        name_table = joinpath(self.paths.astro_tables, self._get_fitstablename_expo('RAWFILES', "raw"))

        # ---- File exists - we READ it ------------------- #
        if os.path.isfile(name_table) :
            if self._overwrite_astropy_table :
                print_warning("The raw-files table will be overwritten")
            else :
                print_warning("The raw files table already exists")
                print_warning("If you wish to overwrite it, "
                      " please turn on the 'overwrite_astropy_table' option to 'True'")
                print_warning("In the meantime, the existing table will be read and used")
                self.Tables.Rawfiles = self.read_astropy_table('RAWFILES', "raw")

        # ---- File does not exist - we create it ---------- #
        else:
            # Check the raw folder
            self.goto_folder(self.paths.rawfiles)
            # Get the list of files from the Raw data folder
            files = os.listdir(".")

            smalldic = {"FILENAME" : ['filename', '', str, '100A']}
            fulldic = listexpo_files.copy()
            fulldic.update(smalldic)

            # Init the lists
            MUSE_infodic = {}
            for key in fulldic.keys() :
                MUSE_infodic[key] = []

            # Looping over the files
            for f in files:
                # Excluding the files without MUSE and fits.fz
                if ('MUSE' in f) and ('.fits.fz')  in f:
                    MUSE_infodic['FILENAME'].append(f)
                    header = pyfits.getheader(f, 0)
                    for k in listexpo_files.keys() :
                        [namecol, keyword, func, form] = listexpo_files[k]
                        MUSE_infodic[k].append(func(header[keyword]))

            # Transforming into numpy arrayimport pymusepipe
            for k in fulldic.keys() :
                MUSE_infodic[k] = np.array(MUSE_infodic[k])

            # Getting a sorted array with indices
            idxsort = np.argsort(MUSE_infodic['FILENAME'])

            # Creating the astropy table
            self.Tables.Rawfiles = Table([MUSE_infodic['FILENAME'][idxsort]], 
                    names=['filename'], meta={'name': 'raw file table'})

            # Creating the columns
            for k in fulldic.keys() :
                [namecol, keyword, func, form] = fulldic[k]
                self.Tables.Rawfiles[namecol] = MUSE_infodic[k][idxsort]

            # Writing up the table
            self.Tables.Rawfiles.write(name_table, format="fits", 
                    overwrite=self._overwrite_astropy_table)
            # Going back to the original folder
            self.goto_prevfolder()

        # Sorting the types ====================================
        self.sort_types()

    def save_expo_table(self, expotype, tpl_gtable, stage="master", fits_tablename=None):
        """Save the Expo (Master or not) Table corresponding to the expotype
        """
        if fits_tablename is None :
            fits_tablename = self._get_fitstablename_expo(expotype, stage)

        attr_expo = self._get_attr_expo(expotype)
        setattr(self._dic_tables[stage], attr_expo, tpl_gtable.groups.aggregate(np.mean)['tpls','mjd', 'tplnexp'])
        full_tablename = joinpath(self.paths.astro_tables, fits_tablename)
        if (not self._overwrite_astropy_table) and os.path.isfile(full_tablename):
            print_warning("Astropy Table {0} already exists, "
                " use overwrite_astropy_table to overwrite it".format(fits_tablename))
        else :
            getattr(self._dic_tables[stage], attr_expo).write(full_tablename, 
                format="fits", overwrite=self._overwrite_astropy_table)

    def _reset_tables(self) :
        """Reseting the astropy Tables for expotypes
        """
        # Reseting the select_type item
        self.Tables = PipeObject("Astropy Tables")
        # Creating the other two Tables categories
        self.Tables.Raw = PipeObject("Astropy Tables for each raw expotype")
        self.Tables.Master = PipeObject("Astropy Tables for each mastertype")
        self.Tables.Processed = PipeObject("Astropy Tables for each processed type")
        self._dic_tables = {"raw": self.Tables.Raw, "master": self.Tables.Master,
                "processed": self.Tables.Processed}
        self._dic_attr_suffix = {"raw": "", "master": "master",
                "processed": ""}

        for expotype in listexpo_types.keys() :
            setattr(self.Tables.Raw, self._get_attr_expo(expotype), [])

    def sort_types(self, checkmode=None, strong_checkmode=None, reset=False) :
        """Provide lists of exposures with types defined in the dictionary
        """
        # Reseting the list if reset is True (default)
        if reset: self._reset_tables()

        if checkmode is not None : self.checkmode = checkmode
        else : checkmode = self.checkmode

        if strong_checkmode is not None : self.strong_checkmode = strong_checkmode
        else : strong_checkmode = self.strong_checkmode

        # Sorting alphabetically (thus by date)
        for expotype in listexpo_types.keys() :
            try :
                mask = (self.Tables.Rawfiles['type'] == listexpo_types[expotype])
                setattr(self.Tables.Raw, self._get_attr_expo(expotype), 
                        self.Tables.Rawfiles[mask])
            except AttributeError:
                pass

    def _get_attr_expo(self, expotype):
        return expotype.lower()

    def _get_fitstablename_expo(self, expotype, stage="master"):
        """Get the name of the fits table covering
        a certain expotype
        """
        nametable = "{0}_list_table.fits".format(expotype)
        if stage.lower() == "master":
            nametable = "MASTER_" + nametable
        return nametable

    def _get_table_expo(self, expotype, stage="master"):
        return getattr(self._dic_tables[stage], self._get_attr_expo(expotype))

    def _get_suffix_expo(self, expotype):
        return self._dic_listMasterObject[expotype]
 
    def _get_path_expo(self, expotype, stage="master"):
        masterfolder = lower_allbutfirst_letter(expotype)
        if stage.lower() == "master":
            masterfolder = joinpath(self.my_params.master, masterfolder)
        return masterfolder

    def _get_fullpath_expo(self, expotype, stage="master"):
        return normpath(getattr(self._dic_paths[stage], self._get_attr_expo(expotype)))

    def _get_path_files(self, expotype) :
        return normpath(getattr(self.paths, expotype.lower()))



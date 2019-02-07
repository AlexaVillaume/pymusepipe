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
import copy

# cpl module to link with esorex
#try :
#    import cpl
#except ImportError :
#    raise Exception("cpl is required for this - MUSE related - module")

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
    from astropy.table import Table, setdiff, vstack, TableMergeError
except ImportError :
    raise Exception("astropy.table.Table is required for this module")

import warnings
from astropy.utils.exceptions import AstropyWarning

# Importing pymusepipe modules
from pymusepipe.init_musepipe import InitMuseParameters
from pymusepipe.recipes_pipe import PipeRecipes
from pymusepipe.prep_recipes_pipe import PipePrep
import pymusepipe.util_pipe as upipe

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
        'STD': 'PIXTABLE_STD', 
        'REDUCED': 'PIXTABLE_REDUCED'
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

dic_astro_wcs = {
        '1900-01-01': "astrometry_wcs_wfm.fits",
        '2000-01-01': "astrometry_wcs_wfm.fits",
        '2014-12-01': "astrometry_wcs_wfm.fits",
        '2015-04-16': "astrometry_wcs_wfm.fits",
        '2015-09-08': "astrometry_wcs_wfm.fits",
        }

future_date = '2099-01-01'

############################################################
#                      END
############################################################

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
        vsystemic: float (default is 0), indicating the systemic velocity of the galaxy [in km/s]

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
        # Updating the astropy table
        self._update_astropy_table = kwargs.pop("update_astropy_table", False)

        # Use time dependent geo_table
        self._time_geo_table = kwargs.pop("time_geo_table", True)
        self._time_astro_table = kwargs.pop("time_astro_table", True)

#        super(MusePipe, self).__init__(**kwargs)

        # Setting the default attibutes #####################
        self.galaxyname = galaxyname
        self.pointing = pointing
        self.vsystemic = np.float(kwargs.pop("vsystemic", 0.))

        # Setting other default attributes
        if outlog is None : 
            outlog = "log_{timestamp}".format(timestamp = upipe.create_time_name())
            upipe.print_info("The Log folder will be {log}".format(outlog))
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
            upipe.print_info("Creating directory structure")
        self.goto_folder(self.paths.data)

        # ==============================================
        # Creating the extra pipeline folder structure
        for folder in self.my_params._dic_input_folders.keys() :
            upipe.safely_create_folder(self.my_params._dic_input_folders[folder], verbose=verbose)

        # ==============================================
        # Creating the folder structure itself if needed
        for folder in self.my_params._dic_folders.keys() :
            upipe.safely_create_folder(self.my_params._dic_folders[folder], verbose=verbose)

        # ==============================================
        # Init the Master exposure flag dictionary
        self.Master = {}
        for mastertype in dic_listMaster.keys() :
            upipe.safely_create_folder(self._get_path_expo(mastertype, "master"), verbose=self.verbose)
            self.Master[mastertype] = False

        # Init the Object folder
        for objecttype in dic_listObject.keys() :
            upipe.safely_create_folder(self._get_path_expo(objecttype, "processed"), verbose=self.verbose)

        self._dic_listMasterObject = {**dic_listMaster, **dic_listObject}
        # ==============================================

        # Going back to initial working directory
        self.goto_prevfolder()

        # ===========================================================
        # Now creating the raw table, and attribute containing the
        # astropy dataset probing the rawfiles folder
        # When creating the table, if the table already exists
        # it will read the old one, except if an overwrite_astropy_table
        # is set to True.
        self.init_raw_table()
        self.read_all_astro_tables()
        # ===========================================================

    def _set_option_astropy_table(self, overwrite=None, update=None):
        """Set the options for overwriting or updating the astropy tables
        """
        if overwrite is not None: self._overwrite_astropy_table = overwrite
        if update is not None: self._update_astropy_table = update

    def goto_prevfolder(self, logfile=False) :
        """Go back to previous folder
        """
        upipe.print_info("Going back to the original folder {0}".format(self.paths._prev_folder))
        self.goto_folder(self.paths._prev_folder, logfile=logfile, verbose=False)
            
    def goto_folder(self, newpath, logfile=False, verbose=True) :
        """Changing directory and keeping memory of the old working one
        """
        try: 
            prev_folder = os.getcwd()
            newpath = os.path.normpath(newpath)
            os.chdir(newpath)
            if verbose :
                upipe.print_info("Going to folder {0}".format(newpath))
            if logfile :
                upipe.append_file(joinpath(self.paths.data, self.logfile), "cd {0}\n".format(newpath))
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

        for name in list(self.my_params._dic_folders.keys()) + list(self.my_params._dic_input_folders.keys()):
            setattr(self.paths, name, joinpath(self.paths.data, getattr(self.my_params, name)))

        # Creating the filenames for Master files
        self.paths.Master = PipeObject("All Paths for Master files useful for the pipeline")
        for expotype in dic_listMaster.keys() :
            # Adding the path of the folder
            setattr(self.paths.Master, self._get_attr_expo(expotype), 
                    joinpath(self.paths.data, self._get_path_expo(expotype, "master")))

        self._dic_paths = {"master": self.paths.Master, "processed": self.paths}

    def _reset_tables(self) :
        """Reseting the astropy Tables for expotypes
        """
        # Reseting the select_type item
        self.Tables = PipeObject("Astropy Tables")
        # Creating the other two Tables categories
        self.Tables.Raw = PipeObject("Astropy Tables for each raw expotype")
        self.Tables.Master = PipeObject("Astropy Tables for each mastertype")
        self.Tables.Processed = PipeObject("Astropy Tables for each processed type")
        self.Tables.Reduced = PipeObject("Astropy Tables for each reduced type")
        self._dic_tables = {"raw": self.Tables.Raw, "master": self.Tables.Master,
                "processed": self.Tables.Processed, "reduced": self.Tables.Reduced}
        self._dic_suffix_astro = {"raw": "RAW", "master": "MASTER", 
                "processed": "PRO", "reduced": "RED"}

        for expotype in listexpo_types.keys() :
            setattr(self.Tables.Raw, self._get_attr_expo(expotype), [])

    def read_all_astro_tables(self) :
        """Initialise all existing Astropy Tables
        """
        for mastertype in dic_listMaster.keys():
            setattr(self._dic_tables["master"], self._get_attr_expo(mastertype),
                self.read_astropy_table(mastertype, stage="master"))

        for expotype in dic_listObject.keys():
            setattr(self._dic_tables["processed"], self._get_attr_expo(expotype),
                self.read_astropy_table(expotype, stage="processed"))

    def read_astropy_table(self, expotype=None, stage="master"):
        """Read an existing Masterfile data table to start the pipeline
        """
        # Read the astropy table
        name_table = self._get_fitstablename_expo(expotype, stage)
        if not os.path.isfile(name_table):
            upipe.print_warning("Astropy table {0} does not exist - setting up an empty one".format(name_table))
            return Table([[],[],[]], names=['tpls','mjd', 'tplnexp'])
        else :
            if self.verbose : upipe.print_info("Reading Astropy fits Table {0}".format(name_table))
            return Table.read(name_table, format="fits")
        
    def init_raw_table(self, reset=False):
        """ Create a fits table with all the information from
        the Raw files
        Also create an astropy table with the same info
        """
        if self.verbose :
            upipe.print_info("Creating the astropy fits raw data table")

        if reset or not hasattr(self, "Tables"):
            self._reset_tables()

        # Testing if raw table exists
        name_table = self._get_fitstablename_expo('RAWFILES', "raw")

        # ---- File exists - we READ it ------------------- #
        overwrite = True
        if os.path.isfile(name_table) :
            if self._overwrite_astropy_table :
                upipe.print_warning("The raw-files table will be overwritten")
            else :
                upipe.print_warning("The raw files table already exists")
                upipe.print_warning("If you wish to overwrite it, "
                      " please turn on the 'overwrite_astropy_table' option to 'True'")
                upipe.print_warning("In the meantime, the existing table will be read and used")
                self.Tables.Rawfiles = self.read_astropy_table('RAWFILES', "raw")
                overwrite = False

        # ---- File does not exist - we create it ---------- #
        if overwrite:
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
        self.sort_raw_tables()

    def save_expo_table(self, expotype, tpl_gtable, stage="master", 
            fits_tablename=None, aggregate=True, suffix="", overwrite=None, update=None):
        """Save the Expo (Master or not) Table corresponding to the expotype
        """
        self._set_option_astropy_table(overwrite, update)

        if fits_tablename is None :
            fits_tablename = self._get_fitstablename_expo(expotype, stage, suffix)

        attr_expo = self._get_attr_expo(expotype)
        full_tablename = joinpath(self.paths.astro_tables, fits_tablename)

        if aggregate:
            table_to_save = tpl_gtable.groups.aggregate(np.mean)['tpls', 'mjd', 'tplnexp']
        else :
            table_to_save = copy.copy(tpl_gtable)

        # If the file already exists
        if os.path.isfile(full_tablename):
            # Check if we update
            if self._update_astropy_table:
                # Reading the existing table
                upipe.print_warning("Reading the existing Astropy table {0}".format(fits_tablename))
                existing_table = Table.read(full_tablename, format="fits")
                # first try to see if they are compatible by using vstack
                try: 
                    stack_temptable = vstack([existing_table, table_to_save], join_type='exact')
                    upipe.print_warning("Updating the existing Astropy table {0}".format(fits_tablename))
                    table_to_save = apy.table.unique(stack_temptable, keep='first')
                except TableMergeError:
                    upipe.print_warning("Astropy Table cannot be joined to the existing one")
                    return

            # Check if we want to overwrite or add the line in
            elif not self._overwrite_astropy_table:
                upipe.print_warning("Astropy Table {0} already exists, "
                    " use overwrite_astropy_table to overwrite it".format(fits_tablename))
                return

        table_to_save.write(full_tablename, format="fits", overwrite=True)
        setattr(self._dic_tables[stage], attr_expo, table_to_save)

    def sort_raw_tables(self, checkmode=None, strong_checkmode=None) :
        """Provide lists of exposures with types defined in the dictionary
        """
        if checkmode is not None : self.checkmode = checkmode
        else : checkmode = self.checkmode

        if strong_checkmode is not None : self.strong_checkmode = strong_checkmode
        else : strong_checkmode = self.strong_checkmode

        # Sorting alphabetically (thus by date)
        for expotype in listexpo_types.keys() :
            try :
                mask = (self.Tables.Rawfiles['type'] == listexpo_types[expotype])
                if self.checkmode: 
                    maskmode = (self.Tables.Rawfiles['mode'] == self.musemode)
                    if (expotype.upper() not in exclude_list_checkmode) or self.strong_checkmode:
                        mask = maskmode & mask
                setattr(self.Tables.Raw, self._get_attr_expo(expotype), 
                        self.Tables.Rawfiles[mask])
            except AttributeError:
                pass

    def _get_attr_expo(self, expotype):
        return expotype.lower()

    def _get_fitstablename_expo(self, expotype, stage="master", suffix=""):
        """Get the name of the fits table covering
        a certain expotype
        """
        fitstablename = "{0}_{1}_{2}list_table.fits".format(self._dic_suffix_astro[stage], 
                expotype.lower(), suffix)
        return joinpath(self.paths.astro_tables, fitstablename)

    def _get_table_expo(self, expotype, stage="master"):
        try:
            return getattr(self._dic_tables[stage], self._get_attr_expo(expotype))
        except AttributeError:
            upipe.print_error("No attributed table with expotype {0} and stage {1}".format(expotype, stage))
            return Table()

    def _get_suffix_product(self, expotype):
        return self._dic_listMasterObject[expotype]
 
    def _get_path_expo(self, expotype, stage="master"):
        masterfolder = upipe.lower_allbutfirst_letter(expotype)
        if stage.lower() == "master":
            masterfolder = joinpath(self.my_params.master, masterfolder)
        return masterfolder

    def _get_fullpath_expo(self, expotype, stage="master"):
        return upipe.normpath(getattr(self._dic_paths[stage], self._get_attr_expo(expotype)))

    def _get_path_files(self, expotype) :
        return upipe.normpath(getattr(self.paths, expotype.lower()))

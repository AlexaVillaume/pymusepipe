# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""MUSE-PHANGS core module
"""

__authors__   = "Eric Emsellem"
__copyright__ = "(c) 2017, ESO + CRAL"
__license__   = "3-clause BSD License"
__contact__   = " <eric.emsellem@eso.org>"

# Importing modules
import numpy as np
import os
from os.path import join as joinpath

try :
    import astropy as apy
    from astropy.io import fits as pyfits
except ImportError :
    raise Exception("astropy is required for this module")

from astropy.utils.exceptions import AstropyWarning
import warnings

# Importing pymusepipe modules
from pymusepipe.recipes_pipe import PipeRecipes
from pymusepipe.prep_recipes_pipe import PipePrep
from pymusepipe.init_musepipe import InitMuseParameters
import pymusepipe.util_pipe as upipe
from pymusepipe import musepipe 

__version__ = '0.0.2 (28 Feb 2019)'
# 0.0.2 28 Feb, 2019: trying to make it work
# 0.0.1 21 Nov, 2017 : just setting up the scene

dic_combined_folders = {
        # Sof files
        "sof": "Sof/",
        # Combined products
        "cubes": "Cubes/",
         # esores log files
        "esorex_log" : "Esorex_log/",
        # Data Products - first writing
        "pipe_products": "Pipe_products/"
        }

class muse_combine(PipePrep, PipeRecipes) :
    def __init__(self, galaxyname=None, list_pointings=[1], rc_filename=None, 
            cal_filename=None, combined_folder_name="Combined",
            outlog=None, logfile="MusePipeCombine.log", reset_log=False,
            verbose=True, **kwargs):
        """Initialisation of class muse_expo

        Input
        -----
        galaxyname: string (e.g., 'NGC1208'). default is None. 

        rc_filename: filename to initialise folders
        cal_filename: filename to initiale FIXED calibration MUSE files
        outlog: string, output directory for the log files
        verbose: boolean. Give more information as output (default is True)
        vsystemic: float (default is 0), indicating the systemic velocity of the galaxy [in km/s]

        Other possible entries
        ----------------------
        warnings: strong  ('ignore'by default. If set to ignore, will ignore the Astropy Warnings.

        """
        # Verbose option
        self.verbose = verbose

        # Warnings for astropy
        self.warnings = kwargs.pop("warnings", 'ignore')
        if self.warnings == 'ignore':
           warnings.simplefilter('ignore', category=AstropyWarning)

        # Setting the default attibutes #####################
        self.galaxyname = galaxyname
        self.list_pointings = list_pointings
        self.combined_folder_name = combined_folder_name
        self.vsystemic = np.float(kwargs.pop("vsystemic", 0.))

        # Setting other default attributes
        if outlog is None : 
            outlog = "log_{timestamp}".format(timestamp = upipe.create_time_name())
            upipe.print_info("The Log folder will be {0}".format(outlog))
        self.outlog = outlog
        self.logfile = joinpath(self.outlog, logfile)

        # End of parameter settings #########################

        # Init of the subclasses
        PipeRecipes.__init__(self, **kwargs)

        # =========================================================== #
        # Setting up the folders and names for the data reduction
        # Can be initialised by either an rc_file, 
        # or a default rc_file or harcoded defaults.
        self.my_params = InitMuseParameters(rc_filename=rc_filename, 
                            cal_filename=cal_filename)
        # Setting up the relative path for the data, using Galaxy Name + Pointing
        self.my_params.data = "{0}/{1}/".format(self.galaxyname, self.combined_folder_name)

        self.my_params.init_default_param(dic_combined_folders)
        self._dic_combined_folders = dic_combined_folders

        self.set_fullpath_names()
        # Making the output folders in a safe mode
        if self.verbose:
            upipe.print_info("Creating directory structure")

        # and Recording the folder where we start
        self.paths.orig = os.getcwd()

        # First create the data Combined folder
        upipe.safely_create_folder(self.paths.data, verbose=verbose)

        # Go to the Combined Folder
        self.goto_folder(self.paths.data)

        # =========================================================== #
        # Now create full path folder 
        for folder in self._dic_combined_folders.keys() :
            upipe.safely_create_folder(self._dic_combined_folders[folder], verbose=verbose)

        # Going back to initial working directory
        self.goto_prevfolder()

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
        self.paths = musepipe.PipeObject("All Paths useful for the pipeline")
        self.paths.root = self.my_params.root
        self.paths.data = joinpath(self.paths.root, self.my_params.data)

        for name in list(self._dic_combined_folders.keys()):
            setattr(self.paths, name, joinpath(self.paths.data, getattr(self.my_params, name)))

        # Creating the filenames for Master files
        for pointing in self.list_pointings:
            name_pointing = "P{0:02d}".format(np.int(pointing))
            # Adding the path of the folder
            setattr(self.paths, name_pointing,
                    joinpath(self.paths.root, "{0}/P{1:02d}/".format(self.galaxyname, pointing)))

    def run_combine(self, sof_filename='exp_combine', expotype="REDUCED", 
            tpl="ALL", stage="reduced", list_pointing=None, 
            lambdaminmax=[4000.,10000.], suffix="", **kwargs):
        """MUSE Exp_combine treatment of the reduced pixtables
        Will run the esorex muse_exp_combine routine

        Parameters
        ----------
        sof_filename: string (without the file extension)
            Name of the SOF file which will contain the Bias frames
        tpl: ALL by default or a special tpl time
        list_expo: list of integers providing the exposure numbers
        """
        # Selecting the table with the right iexpo
        found_expo, list_expo, scipost_table = self._select_list_expo(expotype, tpl, stage, list_expo) 
        if not found_expo:
            return

        if len(list_expo) == 1: 
            suffix += "_{0:04d}".format(list_expo[0])
        
        # Lambda min and max?
        [lambdamin, lambdamax] = lambdaminmax
        # Save options
        save = kwargs.pop("save", "cube,skymodel,individual")
        # Filters
        filter_list = kwargs.pop("filter_list", "white,Cousins_R")
        filter_for_alignment = kwargs.pop("filter_for_alignment", "Cousins_R")
        offset_list = kwargs.pop("offset_list", "True")

        # Go to the data folder
        self.goto_folder(self.paths.data, logfile=True)

        # Create the dictionary for scipost
        # Selecting either one or all of the exposures
        for gtable in scipost_table.groups:
            # extract the tpl (string) and mean mjd (float) 
            tpl, mean_mjd = self._get_tpl_meanmjd(gtable)
            # Now starting with the standard recipe
            self._add_calib_to_sofdict("EXTINCT_TABLE", reset=True)
            self._add_calib_to_sofdict("SKY_LINES")
            self._add_calib_to_sofdict("FILTER_LIST")
            self._add_astrometry_to_sofdict(tpl)
            self._add_skycalib_to_sofdict("STD_RESPONSE", mean_mjd, 'STD')
            self._add_skycalib_to_sofdict("STD_TELLURIC", mean_mjd, 'STD')
            self._add_skycalib_to_sofdict("SKY_CONTINUUM", mean_mjd, 'SKY', "processed")
            self._add_tplmaster_to_sofdict(mean_mjd, 'LSF')
            if offset_list :
                self._sofdict['OFFSET_LIST'] = [joinpath(self._get_fullpath_expo(expotype, "processed"),
                        '{0}_{1}_{2}.fits'.format(dic_files_products['ALIGN'][0], 
                            filter_for_alignment, tpl))]

            # Selecting only exposures to be treated
            pixtable_name = self._get_suffix_product(expotype)
            self._sofdict[pixtable_name] = []
            for iexpo in list_expo:
                self._sofdict[pixtable_name] += [joinpath(self._get_fullpath_expo(expotype, "processed"),
                    '{0}_{1:04d}-{2:02d}.fits'.format(pixtable_name, iexpo, j+1)) for j in range(24)]
            self.write_sof(sof_filename="{0}_{1}{2}_{3}".format(sof_filename, expotype, 
                suffix, tpl), new=True)
            # products
            dir_products = self._get_fullpath_expo(expotype, "processed")
            name_products, suffix_products, suffix_finalnames = self._get_scipost_products(save, 
                    list_expo, filter_list) 
            self.recipe_scipost(self.current_sof, tpl, expotype, dir_products, 
                    name_products, suffix_products, suffix_finalnames, 
                    lambdamin=lambdamin, lambdamax=lambdamax, save=save, 
                    list_expo=list_expo, suffix=suffix, filter_list=filter_list, **kwargs)

            # Write the MASTER files Table and save it
            self.save_expo_table(expotype, scipost_table, "reduced", 
                    "IMAGES_FOV_{0}{1}_{2}_list_table.fits".format(expotype, 
                        suffix, tpl), aggregate=False)

        # Go back to original folder
        self.goto_prevfolder(logfile=True)



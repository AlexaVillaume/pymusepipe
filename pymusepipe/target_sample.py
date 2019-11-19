# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""MUSE-PHANGS target sample module
"""

__authors__   = "Eric Emsellem"
__copyright__ = "(c) 2017, ESO + CRAL"
__license__   = "3-clause BSD License"
__contact__   = " <eric.emsellem@eso.org>"

# Standard modules
import os
from os.path import join as joinpath
from pymusepipe import util_pipe as upipe
from pymusepipe.musepipe import MusePipe
from pymusepipe.config_pipe import dic_user_folders, PHANGS_config
from .version import __version__ as version_pack

# ----------------- Galaxies and Pointings ----------------#

# Sample of galaxies
# For each galaxy, we provide the pointings numbers and the run attached to that pointing
dic_SAMPLE_example = {
        "NGC628": ['P100', {1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 8:0, 9:0, 10:0, 11:0, 12:0}],
        "NGC1087": ['P101', {1:1}], 
        }

def insert_suffix(filename, suffix=""):
    """Create a new filename including the 
    suffix in the name

    Input
    -----
    filename: str
    suffix: str
    """
    # Create new file
    sfilename, extension = os.path.splitext(filename)
    return "{0}_{1}{2}".format(sfilename, subfolder, extension)

# Update the rc file with a subfolder name
def update_calib_file(filename, subfolder=""):
    """Update the rcfile with a new root
    """
    if filename is None:
        upipe.print_error("ERROR: input filename is None")
        return ""

    # Testing existence of filename
    if not os.path.isfile(filename) :
        upipe.print_error("ERROR: input filename {inputname} cannot be found. ".format(
                            inputname=filename))
        return ""

    # If it exists, open and read it
    old_rc = open(filename)
    lines = old_rc.readlines()

    # Create new file
    new_filename = insert_suffix(filename, subfolder)
    new_rc = open(new_filename, 'w')

    # loop on lines
    for line in lines :
        sline = line.split()
        if sline[0] != "root":
            new_rc.write(line)
            continue
        if not os.path.isdir(sline[1]):
            upipe.print_warning("{} not an existing folder (from rcfile)".format(sline[1]))

        newline = line.replace(sline[1], joinpath(sline[1], subfolder))
        new_rc.write(newline)

    new_rc.close()
    old_rc.close()
    return new_filename

####################################################
# Defining classes to get samples and objects
####################################################
class MusePipeTarget(object):
    def __init__(self, subfolder='P100', list_pointings=None):
        self.subfolder = subfolder
        self.list_pointings = list_pointings
        self.pipes = {}

class MusePipeSample(object):
    def __init__(self, TargetDic, rc_filename=None, cal_filename=None, start_recipe='all', **kwargs) :
        """Using a given dictionary to initialise the sample
        That dictionary should include the names of the targets
        as keys and the subfolder plus pointings to consider

        Input
        -----
        TargetDic: dic
            Dictionary of targets. Keys are target names.
            Values for each target name should be a list of 2 parameters.
                - The first one is the name of the subfolder (e.g. 'P101')
                - The second one is the list of pointings, itself a dictionary
                  with a 0 or 1 for each pointing number depending on whether
                  this should be included in the reduction or not.
                  Results can be seen in self.dic_targets dictionary.
        rc_filename: str
            Default to None
        cal_filename: str
            Default to None

        PHANGS: bool
            Default to False. If True, will use default configuration dictionary
            from config_pipe.
        """
        self.sample = TargetDic
        self.targetnames = list(TargetDic.keys())

        self.start_recipe = start_recipe

        self.__phangs = kwargs.pop("PHANGS", False)

        # Reading configuration filenames
        if rc_filename is None or cal_filename is None:
            upipe.print_error("rc_filename and/or cal_filename is None. Please define both.")
            return
        self.cal_filename = cal_filename
        self.rc_filename = rc_filename

        # Initialisation of rc and cal files
        self._init_calib_files()

        # Initialisation of targets
        self._init_targets()

    def _init_calib_files(self):
        """Initialise the calibration files with the new
        name using the subfolders
        """
        self._subfolders = np.unique([self.sample[target][0] for target in self.targetnames])
        for subfolder in self._subfolders:
            update_calib_file(self.rc_filename, subfolder)
            update_calib_file(self.cal_filename, subfolder)

    def _get_calib_filenames(self, targetname):
        """Get calibration file names

        Input
        ----
        targetname: str

        Returns
        -------
        folder_name: str
        rcname: str
        calname: str
        """
        # Checking the folders
        folder_rc, rc_filename_target = os.path.split(insert_suffix(self.rc_filename, 
                                    self.targets[targetname].subfolder))
        folder_cal, cal_filename_target = os.path.split(insert_suffix(self.cal_filename, 
                                     self.targets[targetname].subfolder))

        if rc_filename_target=="" or cal_filename_target=="":
            upipe.print_error()
            return

        if folder_rc == folder_cal:
            folder_config = folder_rc
        else:
            rc_filename_target = joinpath(folder_rc, rc_filename_target)
            cal_filename_target = joinpath(folder_cal, cal_filename_target)
            folder_config = ""

        return folder_config, rc_filename_target, cal_filename_target

    def _init_targets(self):
        """Initialise the targets using the dictionary
        Returning self.targets with the pointings to consider
        """
        self.targets = {}
        self.pipes = {}
        for target in self.targetnames:
            subfolder = self.sample[target][0]
            lpoints = self.sample[target][1]
            list_pointings = []
            for lp in lpoints.keys():
                if lpoints[lp] == 1:
                    list_pointings.append(lp)
            # Defining the MusePipe for that target
            self.targets[target] = MusePipeTarget(subfolder=subfolder, 
                                                      list_pointings=list_pointings)
            # Shortcut to call the musepipe instance
            self.pipes[target] = self.targets[target].pipes

            folder_config, rc_filename, cal_filename = self._get_calib_filenames(target)
            self.targets[target].rc_filename = rc_filename
            self.targets[target].cal_filename = cal_filename
            self.targets[target].folder_config = folder_config

    def _check_pointings(self, targetname, list_pointings):
        """Check if pointing is in the list of pointings
        Returns the list of pointings if ok. If not, return an empty list

        Input
        -----
        targetname: str
            name of the target
        list_pointings: list
            List of integer (pointings).

        Returns
        -------
        list_pointings: list
            Empty if input list of pointings is not fully in defined list.
        """
        # Info of the pointings and extracting the observing run for each pointing
        target_pointings = self.targets[targetname].list_pointings
        # if no list_pointings we just do them all
        if list_pointings == None:
            list_pointings = target_pointings
        else:
            if any([_ not in target_pointings for _ in list_pointings]) :
                upipe.print_error("ERROR: no pointing {0} for the given target".format(
                                    list_pointings))
                return []
        return list_pointings

    def _check_targetname(self, targetname):
        """Check if targetname is in list

        Input
        -----
        targetname: str

        Returns
        -------
        status: bool
            True if yes, False if no.
        """
        if targetname not in self.targetnames:
            upipe.print_error("ERROR: no Target named {name} in the defined sample".format(
                                name=targetname))
            return False
        else:
            return True

    def set_pipe_target(self, targetname=None, list_pointings=None, **kwargs):
        """Create the musepipe instance for that target and list of pointings

        Input
        -----
        targetname: str
            Name of the target
        list_pointings: list
            Pointing numbers. Default is None (meaning all pointings
            indicated in the dictonary will be reduced)
        config_args: dic
            Dictionary including extra configuration parameters to pass
            to MusePipe. This allows to define a global configuration.
            If self.__phangs is set to True, this is overwritten with the default
            PHANGS configuration parameters as provided in config_pipe.py.
        """
        # Check if targetname is valid
        if not self._check_targetname(targetname):
            return

        # Galaxy name
        upipe.print_info("Initialising MusePipe for Target {name}".format(name=targetname))

        # Check if pointings are valid
        list_pointings = self.check_pointings(targetname, list_pointings)
        if len(list_pointings) == 0:
            return

        # Get the filename and extension of log file
        log_filename, log_fileext = os.path.splitext(kwargs.pop("log_filename", 
                        "{0}_{1}.log".format(targetname, version_pack)))

        # Reading extra arguments from config dictionary
        if self.__phangs:
            config_args = PHANGS_config
        else:
            config_args = kwargs.pop("config_args", None)

        start_recipe = kwargs.pop("start_recipe", "all")
        reset_start = kwargs.pop("reset_start", False)

        # Over-writing the arguments in kwargs from config dictionary
        if config_args is not None:
            for attr in config_args.keys():
                kwargs[attr] = config_args[attr]

        # extracting the kwargs
        list_kwargs = ', '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()])

        # Loop on the pointings
        for pointing in list_pointings:
            # New log file name with pointing included
            log_filename_pointing = "{0}_P{1:02d}{2}".format(
                                    log_filename, pointing, log_fileext)
            # Setting up the names of the output files
            python_command = ("mypipe = musepipe.MusePipe(targetname='{0}', "
                              "pointing={1}, rc_filename='{2}', "
                              "cal_filename='{3}', log_filename='{4}', "
                              "{5})".format(targetname, pointing, rc_filename,
                                  cal_filename, log_filename_pointing, list_kwargs))

            upipe.print_info(python_command)

            # Creating the musepipe instance, using the shortcut
            self.pipes[target][pointing] = MusePipe(targetname=targetname, 
                            pointing=pointing, rc_filename=rc_filename, 
                            cal_filename=cal_filename, log_filename=log_filename_pointing, 
                            start_recipe=start_recipe, initialise_tables=False,
                            **kwargs)

            self.pipes[target][pointing].history = python_command

            # If reset start we reset start_recipe after the first pointing
            if reset_start:
                start_recipe = "all"

    def reduce_all_targets(self, start_recipe='all'):
        """Reduce all targets already initialised

        Input
        -----
        start_recipe: str
            One of the recipe to start with
        """
        for target in self.targets.keys():
            upipe.print_info("=== Start Reduction of Target {name} ===".format(target))
            self.reduce_target(targetname=target, start_recipe=start_recipe)
            upipe.print_info("===  End  Reduction of Target {name} ===".format(target))

    def reduce_target(self, targetname=None, list_pointings=None, **kwargs):
        """Reduce one target for a list of pointings

        Input
        -----
        targetname: str
            Name of the target
        list_pointings: list
            Pointing numbers. Default is None (meaning all pointings
            indicated in the dictonary will be reduced)
        config_args: dic
            Dictionary including extra configuration parameters to pass
            to MusePipe. This allows to define a global configuration.
            If self.__phangs is set to True, this is overwritten with the default
            PHANGS configuration parameters as provided in config_pipe.py.
        """
        # General print out
        upipe.print_info("---- Starting the Data Reduction for Target={0} ----".format(
                            targetname))
        # Loop on the pointings
        self.set_pipe_target(targetname=targetname, list_pointings=list_pointings, **kwargs)
        for pointing in list_pointings:
            upipe.print_info("====== START - POINTING {0:2d} ======".format(pointing))
            self.pipes[target][pointing]._init_tables()
            if self.__phangs:
                self.pipes[target][pointing].run_all_phangs_recipes()
            else:
                self.pipes[target][pointing].run_all_recipes()
            upipe.print_info("====== END   - POINTING {0:2d} ======".format(pointing))
    def combine_all_targets(self):
        pass

    def combine_target(self):
        pass

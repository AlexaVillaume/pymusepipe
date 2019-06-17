# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""MUSE-PHANGS recipe module
"""

__authors__   = "Eric Emsellem"
__copyright__ = "(c) 2017, ESO + CRAL"
__license__   = "3-clause BSD License"
__contact__   = " <eric.emsellem@eso.org>"

# This module has been largely inspired by work of
# Bern Husemann, Dimitri Gadotti, Kyriakos and Martina from the GTO MUSE MAD team
# and further rewritten by Mark van den Brok. 
# Thanks to all !

# Importing modules
import os
from os.path import join as joinpath

# pymusepipe modules
from pymusepipe import util_pipe as upipe
from pymusepipe.mpdaf_pipe import MuseCube

# Likwid command
default_likwid = "likwid-pin -c N:"

class PipeRecipes(object) :
    """PipeRecipes class containing all the esorex recipes for MUSE data reduction
    """
    def __init__(self, nifu=-1, first_cpu=0, ncpu=24, list_cpu=[], likwid=default_likwid,
            fakemode=True, domerge=True, nocache=True, nochecksum=True) :
        """Initialisation of PipeRecipes
        """
        # Fake mode
        self.fakemode = fakemode
        if self.verbose :
            if fakemode : upipe.print_warning("WARNING: running in FAKE mode")
            else : upipe.print_warning("WARNING: running actual recipes")

        if nocache : self.nocache = "nocache"
        else : self.nocache = ""

        # Addressing CPU by number (cpu0=start, cpu1=end)
        self.first_cpu = first_cpu
        self.ncpu = ncpu

        if likwid is None:
            self.likwid = ""
            self.list_cpu = ""
        else :
            self.likwid = likwid
            self._set_cpu(first_cpu, ncpu, list_cpu)
        self.nifu = nifu
        self._domerge = domerge

        self.nochecksum = nochecksum

    @property
    def esorex(self):
        return ("{likwid}{list_cpu} {nocache} esorex --output-dir={outputdir} {checksum}" 
                    " --log-dir={logdir}").format(likwid=self.likwid, 
                    list_cpu=self.list_cpu, nocache=self.nocache, outputdir=self.paths.pipe_products, 
                    checksum=self.checksum, logdir=self.paths.esorex_log)

    @property
    def checksum(self):
        if self.nochecksum:
            return "--no-checksum"
        else : 
            return ""
    @property
    def merge(self):
        if self._domerge: 
            return "--merge"
        else : 
            return ""

    def _set_cpu(self, first_cpu=0, ncpu=24, list_cpu=None) :
        """Setting the cpu format for calling the esorex command
        """
        if (list_cpu is None) | (len(list_cpu) < 1):
            self.list_cpu = "{0}-{1}".format(first_cpu, first_cpu + ncpu - 1)
        else :
            self.list_cpu = "{0}".format(list_cpu[0])
            for i in range(1, len(list_cpu)) :
                self.list_cpu += ":{0}".format(list_cpu[i])
        if self.verbose:
            upipe.print_info("LIST_CPU: {0}".format(self.list_cpu))

    def write_logfile(self, text):
        """Writing in log file
        """
        fulltext = "# At : {0}{1}\n{2}\n".format(
                upipe.formatted_time(),
                " FAKEMODE" if self.fakemode else "",
                text) 
        upipe.append_file(self.paths.logfile, fulltext)

    def run_oscommand(self, command, log=True) :
        """Running an os.system shell command
        Fake mode will just spit out the command but not actually do it.
        """
        if self.verbose : 
            print(command)
    
        if log :
            self.write_logfile(command)

        if not self.fakemode :
            os.system(command)

    def joinprod(self, name):
        return joinpath(self.paths.pipe_products, name)

    def recipe_bias(self, sof, dir_bias, name_bias, tpl):
        """Running the esorex muse_bias recipe
        """
        # Runing the recipe
        self.run_oscommand(("{esorex} --log-file=bias_{tpl}.log muse_bias " 
                "--nifu={nifu} {merge} {sof}").format(esorex=self.esorex, 
                    nifu=self.nifu, merge=self.merge, sof=sof, tpl=tpl))
        # Moving the MASTER BIAS
        self.run_oscommand("{nocache} mv {namein}.fits {nameout}_{tpl}.fits".format(nocache=self.nocache, 
            namein=self.joinprod(name_bias), nameout=joinpath(dir_bias, name_bias), tpl=tpl))

    def recipe_flat(self, sof, dir_flat, name_flat, dir_trace, name_trace, tpl):
        """Running the esorex muse_flat recipe
        """
        self.run_oscommand(("{esorex} --log-file=flat_{tpl}.log muse_flat " 
                "--nifu={nifu} {merge} {sof}").format(esorex=self.esorex, 
                    nifu=self.nifu, merge=self.merge, sof=sof, tpl=tpl))
        # Moving the MASTER FLAT and TRACE_TABLE
        self.run_oscommand("{nocache} mv {namein}.fits {nameout}_{tpl}.fits".format(nocache=self.nocache, 
            namein=self.joinprod(name_flat), nameout=joinpath(dir_flat, name_flat), tpl=tpl))
        self.run_oscommand("{nocache} mv {namein}.fits {nameout}_{tpl}.fits".format(nocache=self.nocache, 
            namein=self.joinprod(name_trace), nameout=joinpath(dir_trace, name_trace), tpl=tpl))

    def recipe_wave(self, sof, dir_wave, name_wave, tpl):
        """Running the esorex muse_wavecal recipe
        """
        self.run_oscommand(("{esorex} --log-file=wave_{tpl}.log muse_wavecal --nifu={nifu} "
                "--resample --residuals {merge} {sof}").format(esorex=self.esorex, 
                    nifu=self.nifu, merge=self.merge, sof=sof, tpl=tpl))
        # Moving the MASTER WAVE
        self.run_oscommand("{nocache} mv {namein}.fits {nameout}_{tpl}.fits".format(nocache=self.nocache, 
            namein=self.joinprod(name_wave), nameout=joinpath(dir_wave, name_wave), tpl=tpl))
    
    def recipe_lsf(self, sof, dir_lsf, name_lsf, tpl):
        """Running the esorex muse_lsf recipe
        """
        self.run_oscommand("{esorex} --log-file=wave_{tpl}.log muse_lsf --nifu={nifu} {merge} {sof}".format(esorex=self.esorex,
            nifu=self.nifu, merge=self.merge, sof=sof, tpl=tpl))
        # Moving the MASTER LST PROFILE
        self.run_oscommand("{nocache} mv {namein}.fits {nameout}_{tpl}.fits".format(nocache=self.nocache, 
            namein=self.joinprod(name_lsf), nameout=joinpath(dir_lsf, name_lsf), tpl=tpl))
    
    def recipe_twilight(self, sof, dir_twilight, name_twilight, tpl):
        """Running the esorex muse_twilight recipe
        """
        self.run_oscommand("{esorex} --log-file=twilight_{tpl}.log muse_twilight {sof}".format(esorex=self.esorex, 
            sof=sof, tpl=tpl))
        # Moving the TWILIGHT CUBE
        for name_prod in name_twilight:
            self.run_oscommand("{nocache} mv {namein}.fits {nameout}_{tpl}.fits".format(nocache=self.nocache, 
                namein=self.joinprod(name_prod), nameout=joinpath(dir_twilight, name_prod), tpl=tpl))

    def recipe_std(self, sof, dir_std, name_std, tpl):
        """Running the esorex muse_stc recipe
        """
        [name_cube, name_flux, name_response, name_telluric] = name_std
        self.run_oscommand("{esorex} --log-file=std_{tpl}.log muse_standard --filter=white {sof}".format(esorex=self.esorex,
                sof=sof, tpl=tpl))

        for name_prod in name_std:
            self.run_oscommand('{nocache} mv {name_prodin}_0001.fits {name_prodout}_{tpl}.fits'.format(nocache=self.nocache,
                name_prodin=self.joinprod(name_prod), name_prodout=joinpath(dir_std, name_prod), tpl=tpl))

    def recipe_sky(self, sof, dir_sky, name_sky, tpl, iexpo=1, fraction=0.8):
        """Running the esorex muse_stc recipe
        """
        self.run_oscommand("{esorex} --log-file=sky_{tpl}.log muse_create_sky --fraction={fraction} {sof}".format(esorex=self.esorex,
                sof=sof, fraction=fraction, tpl=tpl))

        for name_prod in name_sky:
            self.run_oscommand('{nocache} mv {name_prodin}.fits {name_prodout}_{tpl}_{iexpo:04d}.fits'.format(nocache=self.nocache,
                name_prodin=self.joinprod(name_prod), name_prodout=joinpath(dir_sky, name_prod), iexpo=iexpo, tpl=tpl))

    def recipe_scibasic(self, sof, tpl, expotype, dir_products=None, name_products=[], suffix=""):
        """Running the esorex muse_scibasic recipe
        """
        self.run_oscommand("{esorex} --log-file=scibasic_{expotype}_{tpl}.log muse_scibasic --nifu={nifu} "
                "--saveimage=FALSE {merge} {sof}".format(esorex=self.esorex, 
                    nifu=self.nifu, merge=self.merge, sof=sof, tpl=tpl, expotype=expotype))

        suffix_out = "{0}_{1}".format(suffix, tpl)
        for name_prod in name_products :
            self.run_oscommand('{nocache} mv {prod} {newprod}'.format(nocache=self.nocache,
                prod=self.joinprod("{0}_{1}".format(suffix, name_prod)), newprod=joinpath(dir_products, 
                    "{0}_{1}".format(suffix_out, name_prod))))
   
    # Name of the output combined files are described by several key arguments
    # Summary 
    # namein  = name_products + suffix_products
    # nameout = dir_prod+name_prod+{suffix}{suff_pre}_{tpl}{suff_post}.fits
    # Where:
    #       name_imaout = folder of products + generic name of product (e.g., PIXTABLE_REDUCED)
    #       suffix = User defined flag (suffix)
    #       suff_pre = filter name if IMAGE_FOV, otherwise ""
    #       tpl = tpls of the exposure
    #       suff_post = number of expo if relevant (2 integer)
    def recipe_scipost(self, sof, tpl, expotype, dir_products=None, name_products=[""], 
            suffix_products=[""], suffix_prefinalnames=[""], suffix_postfinalnames=[""], 
            save='cube,skymodel', filter_list='white', filter_for_alignment='Cousins_R',
            skymethod='model', pixfrac=0.8, darcheck='none', skymodel_frac=0.05, 
            astrometry='TRUE', lambdamin=4000., lambdamax=10000., suffix="",
            autocalib='none', rvcorr='bary'):
        """Running the esorex muse_scipost recipe
        """
        self.run_oscommand("{esorex} --log-file=scipost_{expotype}_{tpl}.log muse_scipost  "
                "--astrometry={astro} --save={save} "
                "--pixfrac={pixfrac}  --filter={filt} --skymethod={skym} "
                "--darcheck={darcheck} --skymodel_frac={model:02f} "
                "--lambdamin={lmin} --lambdamax={lmax} --autocalib={autocalib} "
                "--rvcorr={rvcorr} {sof}".format(esorex=self.esorex, astro=astrometry, 
                    save=save, pixfrac=pixfrac, filt=filter_list, skym=skymethod, 
                    darcheck=darcheck, model=skymodel_frac, lmin=lambdamin,
                    lmax=lambdamax, autocalib=autocalib, sof=sof, expotype=expotype, 
                    tpl=tpl, rvcorr=rvcorr))

        # Creating the images for the alignment, outside of scipost
        # The filter can be a private one

        for name_prod, suff_prod, suff_pre, suff_post in zip(name_products, suffix_products, 
                suffix_prefinalnames, suffix_postfinalnames) :
            # Create extra filter image if requested
            if 'CUBE' in name_prod and not self.fakemode \
                    and not filter_for_alignment in filter_list:
                upipe.print_info("Deriving filter alignment image "
                                 "[filter: {0}]".format(filter_for_alignment))
                cube_name = "{0}.fits".format(self.joinprod(name_prod+suff_prod))
                mycube = MuseCube(filename=cube_name)
                myimage = mycube.get_filter_image(filter_name=filter_for_alignment,
                        filter_folder=self.paths.root, 
                        dic_extra_filters=self.pipe_params._dic_extra_filters)
                name_imageout = ("{name_imaout}_{suffix}{myfilter}_{tpl}"
                                 "{suff_post}.fits".format(
                                 name_imaout=joinpath(dir_products, "IMAGE_FOV"), 
                                 myfilter=filter_for_alignment, suff_post=suff_post, 
                                 tpl=tpl, suffix=suffix))
                upipe.print_info("Adding filter alignment image [filter: {0}] "
                                 "to Object folder".format(filter_for_alignment))
                myimage.write(name_imageout, savemask='nan')

                # Save the alignment image in the right folder
                if self._save_alignment_image:
                    name_imageout_align = ("{name_imaout}_P{pointing:02d}_{suffix}{myfilter}"
                                          "_{tpl}{suff_post}.fits".format(
                                          name_imaout=joinpath(self.paths.alignment, "IMAGE_FOV"), 
                                          myfilter=filter_for_alignment, suff_post=suff_post, 
                                          tpl=tpl, suffix=suffix, pointing=self.pointing))
                    upipe.print_info("Adding filter alignment image [filter: {0}] "
                                     "to Alignment folder {1}".format(
                                         filter_for_alignment,
                                         self.paths.alignment))
                    myimage.write(name_imageout_align, savemask='nan')

            # In any case move the file from Pipe_products to the right folder
            fitsname_out = "{name_imaout}{suffix}{suff_pre}_{tpl}{suff_post}.fits".format(
                            name_imaout=joinpath(dir_products, name_prod), 
                            suff_pre=suff_pre, suff_post=suff_post, 
                            tpl=tpl, suffix=suffix)

            self.run_oscommand("{nocache} mv {name_imain}.fits {fitsname}".format(
                               nocache=self.nocache, 
                               name_imain=self.joinprod(name_prod+suff_prod), 
                               fitsname=fitsname_out))

            # Now if in need of an alignment image and it is the filter image
            # Copying it in the Alignment folder or write it 
            if self._save_alignment_image and filter_for_alignment in fitsname_out:
                name_imageout_align = ("{name_imaout}_P{pointing:02d}_{suffix}{myfilter}"
                                      "_{tpl}{suff_post}.fits".format(
                                      name_imaout=joinpath(self.paths.alignment, "IMAGE_FOV"), 
                                      myfilter=filter_for_alignment, suff_post=suff_post, 
                                      tpl=tpl, suffix=suffix, pointing=self.pointing))
                if filter_for_alignment in filter_list :
                    self.run_oscommand("{nocache} cp {fitsname} {nameima_out}".format(
                                       nocache=self.nocache, fitsname=fitsname_out,
                                       nameima_out=name_imageout_align))

    def recipe_align(self, sof, dir_products, namein_products, nameout_products, tpl, group,
            threshold=10.0, srcmin=3, srcmax=80, fwhm=5.0):
        """Running the muse_exp_align recipe
        """
        self.run_oscommand("{esorex} --log-file=exp_align_{group}_{tpl}.log "
                "muse_exp_align --srcmin={srcmin} --srcmax={srcmax} "
                "--threshold={threshold} --fwhm={fwhm} {sof}".format(
                    esorex=self.esorex, srcmin=srcmin, srcmax=srcmax, 
                    threshold=threshold, fwhm=fwhm, sof=sof, tpl=tpl,
                    group=group))
    
        for namein_prod, nameout_prod in zip(namein_products, nameout_products) :
            self.run_oscommand('{nocache} mv {name_imain}.fits {name_imaout}.fits'.format(
                nocache=self.nocache, name_imain=self.joinprod(namein_prod), 
                name_imaout=joinpath(dir_products, nameout_prod)))

    def recipe_combine(self, sof, dir_products, name_products, tpl, expotype,
            suffix_products=[""], suffix_prefinalnames=[""], 
            save='cube', pixfrac=0.6, suffix="", 
            format_out='Cube', filter_list='white',
            filter_for_alignment="Cousins_R", lambdamin=4000., lambdamax=10000.):
        """Running the muse_exp_combine recipe for one single pointing
        """
        self.run_oscommand("{esorex}  --log-file=exp_combine_cube_{expotype}_{tpl}.log "
               " muse_exp_combine --save={save} --pixfrac={pixfrac:0.2f} "
               "--format={form} --filter={filt} "
               "--lambdamin={lmin} --lambdamax={lmax} {sof}".format(
                   esorex=self.esorex, save=save, 
                   pixfrac=pixfrac, form=format_out, filt=filter_list, sof=sof, 
                   tpl=tpl, expotype=expotype, lmin=lambdamin, lmax=lambdamax))

        for name_prod, suff_prod, suff_pre in zip(name_products, suffix_products, 
                suffix_prefinalnames):
            if 'CUBE' in name_prod and not self.fakemode \
                    and not filter_for_alignment in filter_list:
                cube_name = "{0}.fits".format(self.joinprod(name_prod+suff_prod))
                mycube = MuseCube(filename=cube_name)
                myimage = mycube.get_filter_image(filter_name=filter_for_alignment,
                        filter_folder=self.paths.root, 
                        dic_extra_filters=self.pipe_params._dic_extra_filters)
                name_imageout = ("{name_imaout}_{suffix}{myfilter}_{pointing}_{tpl}"
                                 ".fits".format(
                                 name_imaout=joinpath(dir_products, "IMAGE_FOV"), 
                                 myfilter=filter_for_alignment, 
                                 pointing="P{0:02d}".format(self.pointing),
                                 tpl=tpl, suffix=suffix))
                myimage.write(name_imageout, savemask='nan')

            self.run_oscommand("{nocache} mv {name_imain}.fits "
                '{name_imaout}{suffix}{suff_pre}_{pointing}_{tpl}.fits'.format(nocache=self.nocache,
                name_imain=self.joinprod(name_prod+suff_prod), 
                name_imaout=joinpath(dir_products, name_prod),
                suff_pre=suff_pre, suffix=suffix, 
                tpl=tpl, pointing="P{0:02d}".format(self.pointing)))

    def recipe_combine_pointings(self, sof, dir_products, name_products,
            suffix_products=[""], suffix_prefinalnames=[""], 
            save='cube', pixfrac=0.6, suffix="", 
            format_out='Cube', filter_list='white', 
            lambdamin=4000., lambdamax=10000.,
            filter_for_alignment="Cousins_R"):
        """Running the muse_exp_combine recipe for pointings
        """
        self.run_oscommand("{esorex}  --log-file=exp_combine_pointings.log "
               " muse_exp_combine --save={save} --pixfrac={pixfrac:0.2f} "
               "--format={form} --filter={filt} "
               "--lambdamin={lmin} --lambdamax={lmax} "
               "{sof}".format(esorex=self.esorex, 
                   save=save, pixfrac=pixfrac, form=format_out, 
                   filt=filter_list, sof=sof, 
                   lmin=lambdamin, lmax=lambdamax))

        for name_prod, suff_prod, suff_pre in zip(name_products, suffix_products, 
                suffix_prefinalnames):
             # Create extra filter image if requested
            if 'CUBE' in name_prod and not self.fakemode \
                    and not filter_for_alignment in filter_list:
                cube_name = "{0}.fits".format(self.joinprod(name_prod+suff_prod))
                mycube = MuseCube(filename=cube_name)
                myimage = mycube.get_filter_image(filter_name=filter_for_alignment,
                        filter_folder=self.paths.root, 
                        dic_extra_filters=self.pipe_params._dic_extra_filters)
                name_imageout = ("{name_imaout}_{myfilter}{suffix}.fits".format(
                                 name_imaout=joinpath(dir_products, "IMAGE_FOV"), 
                                 myfilter=filter_for_alignment, suffix=suffix))
                myimage.write(name_imageout, savemask='nan')

            self.run_oscommand("{nocache} mv {name_imain}.fits "
                              "{name_imaout}{suffix}{suff_pre}.fits".format(
                                  nocache=self.nocache, 
                                  name_imain=self.joinprod(name_prod+suff_prod), 
                                  name_imaout=joinpath(dir_products, name_prod),
                                  suff_pre=suff_pre, suffix=suffix))


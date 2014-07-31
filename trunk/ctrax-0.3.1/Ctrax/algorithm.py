# algorithm.py
# KMB 09/07/07

import numpy as num
import time
import wx
from wx import xrc
import setarena
import chooseorientations
import os

from version import DEBUG
import annfiles as annot
import ellipsesk as ell
import settings
import hindsight
import sys

from params import params

import os
import codedir
SETTINGS_RSRC_FILE = os.path.join(codedir.codedir,'xrc','tracking_settings.xrc')

if DEBUG: import pdb
DEBUG_LEVEL = 1
if not DEBUG:
    DEBUG_LEVEL = 0


# CtraxApp.Track #################################################
class CtraxAlgorithm (settings.AppWithSettings):
    """Cannot be used alone -- this class only exists
    to keep algorithm code together in one file."""
    def Track( self ):
        """Run the m-tracker."""

        ## initialization ##

        if DEBUG: print "Tracking from frame %d..."%self.start_frame
        if DEBUG: print "Last frame tracked = %d"%self.ann_file.lastframetracked


        # maximum number of frames we will look back to fix errors
        self.maxlookback = max(params.lostdetection_length,
                               params.spuriousdetection_length,
                               params.mergeddetection_length,
                               params.splitdetection_length)

        if params.interactive:
            wx.Yield()

        # initialize hindsight data structures
        self.hindsight = hindsight.Hindsight(self.ann_file,self.bg_imgs)

        self.break_flag = False

        if DEBUG: print "Initializing buffer for tracking"
        self.ann_file.InitializeBufferForTracking(self.start_frame)

        # initialize dfore and connected component buffer
        self.bg_imgs.set_buffer_maxnframes()

        for self.start_frame in range(self.start_frame,self.movie.get_n_frames()):

            # KB 20120109 added last_frame command-line option
            if self.start_frame >= self.last_frame:
                break

            if DEBUG_LEVEL > 0: print "Tracking frame %d / %d"%(self.start_frame,self.movie.get_n_frames()-1)
        
            #if DEBUG:
            #    break

            if self.break_flag:
                break

            last_time = time.time()

            # perform background subtraction
            #try:
            (self.dfore,self.isfore,self.cc,self.ncc) = \
                self.bg_imgs.sub_bg( self.start_frame, dobuffer=True )
            #except:
            #    # catch all error types here, and just break out of loop
            #    break

            # write to sbfmf
            if self.dowritesbfmf:
                self.movie.writesbfmf_writeframe(self.isfore,
                                                 self.bg_imgs.curr_im,
                                                 self.bg_imgs.curr_stamp,
                                                 self.start_frame)
            
            # process gui events
            if params.interactive:
                wx.Yield()
            if self.break_flag:
                break

            # find observations
            self.ellipses = ell.find_ellipses( self.dfore, self.cc, self.ncc )

            #if params.DOBREAK:
            #    print 'Exiting at frame %d'%self.start_frame
            #    sys.exit(1)

            # process gui events
            if params.interactive:
                wx.Yield()
            if self.break_flag:
                break

            # match target identities to observations
            if len( self.ann_file ) > 1:
                flies = ell.find_flies( self.ann_file[-2],
                                        self.ann_file[-1],
                                        self.ellipses,
                                        self.ann_file)
            elif len( self.ann_file ) == 1:
                flies = ell.find_flies( self.ann_file[-1],
                                        self.ann_file[-1],
                                        self.ellipses,
                                        self.ann_file )
            else:
                flies = ell.TargetList()
                for i,obs in enumerate(self.ellipses):
                    if obs.isEmpty():
                        if DEBUG: print 'empty observation'
                    else:
                        newid = self.ann_file.GetNewId()
                        obs.identity = newid
                        flies.append(obs)

            if DEBUG_LEVEL > 0: print "Done with frame %d, appending to ann_file"%self.start_frame

            # save to ann_data
            self.ann_file.append( flies )

            if DEBUG_LEVEL > 0: print "Added to ann_file, now running fixerrors"

            # fix any errors using hindsight
            self.hindsight.fixerrors()
            #print 'time to fix errors: '+str(time.time() - last_time)

            # draw?
            if self.request_refresh or (self.do_refresh and ((self.start_frame % self.framesbetweenrefresh) == 0)):
                if params.interactive:
                    if self.start_frame:
                        self.ShowCurrentFrame()
                else:
                    print "    Frame %d / %d"%(self.start_frame,self.movie.get_n_frames())
                self.request_refresh = False

            # process gui events
            if params.interactive:
                wx.Yield()
            if self.break_flag:
                break

            if (self.start_frame % 100) == 0 and self.has( 'diagnostics_filename' ):
                self.write_diagnostics() # save ongoing

        self.Finish()

    def write_diagnostics( self ):
        """Safely write diagnostics file."""
        if not self.has( 'diagnostics_filename' ):
            self.diagnostics_filename = self.get_filename_with_extension( '_ctraxdiagnostics.txt' )
        annot.WriteDiagnostics( self.diagnostics_filename )

    def Finish(self):

        # write the rest of the frames to file
        self.ann_file.finish_writing()
        if self.has( 'diagnostics_filename' ):
            self.write_diagnostics()

    # enddef: Track()


    def StopThreads( self ):
        # stop algorithm
        self.break_flag = True


    def DoAllPreprocessing(self):

        # estimate the background
        if (not self.IsBGModel()) or params.batch_autodetect_bg_model:
            print "Estimating background model"
            if not params.batch_autodetect_bg_model:
                print "**autodetecting background because no existing model is loaded"
            print "BG Modeling parameters:"
            print "n_bg_frames = " + str(self.bg_imgs.n_bg_frames)
            print "use_median = " + str(self.bg_imgs.use_median)
            print "bg_firstframe = " + str(self.bg_imgs.bg_firstframe)
            print "bg_lastframe = " + str(self.bg_imgs.bg_lastframe)
            if not self.OnComputeBg(): return
        else:
            print "Not estimating background model"

        # detect arena if it has not been set yet
        if params.do_set_circular_arena and params.batch_autodetect_arena:
            print "Auto-detecting circular arena"
            setarena.doall(self.bg_imgs.center)
        else:
            print "Not detecting arena"

        self.bg_imgs.UpdateIsArena()

        # estimate the shape
        if params.batch_autodetect_shape:
            print "Estimating shape model"
            self.OnComputeShape()
        else:
            print "Not estimating shape model"

    def DoAll(self):

        if not params.interactive:
            self.RestoreStdio()

        print "Performing preprocessing...\n"
	self.DoAllPreprocessing()

        # initialize ann files

        # if resuming tracking, we will keep the tracks from 
        # frames firstframetracked to lastframetracked-1 
        # (remove last frame in case writing the last frame 
        # was interrupted)
        if params.noninteractive_resume_tracking and self.ann_file.lastframetracked > 0:
            self.start_frame = self.ann_file.lastframetracked
            if DEBUG_LEVEL > 0: print "start_frame = " + str(self.start_frame)
            if DEBUG_LEVEL > 0: print "cropping annotation file to frames %d through %d"%(self.ann_file.firstframetracked,self.ann_file.lastframetracked-1)
            self.ann_file.InitializeData(self.ann_file.firstframetracked,
                                         self.ann_file.lastframetracked-1)

        else:
            print "Initializing annotation file...\n"
            self.ann_file.InitializeData(self.start_frame,self.start_frame-1)

        print "Done preprocessing, beginning tracking...\n"

        # begin tracking
        if params.interactive:
            self.UpdateToolBar('started')

        # write sbfmf header
        if self.dowritesbfmf:
            # open an sbfmf file if necessary
            self.movie.writesbfmf_start(self.bg_imgs,
                                        self.writesbfmf_filename)

        print "Tracking..."
        try:
            self.Track()
        except:
            print "Error during Track"
            raise
        print "Done tracking"

        # write the sbfmf index and close the sbfmf file
        if self.dowritesbfmf and self.movie.writesbfmf_isopen():
            self.movie.writesbfmf_close(self.start_frame)
        
        print "Choosing Orientations..."
        # choose orientations
        choose_orientations = chooseorientations.ChooseOrientations(self.frame,interactive=False)
        self.ann_file = choose_orientations.ChooseOrientations(self.ann_file)

        # save to a .mat file
        if self.has( 'matfilename' ):
            savename = self.matfilename
        else:
            savename = self.get_filename_with_extension( '.mat' )
        print "Saving to mat file "+savename+"...\n"
        self.ann_file.WriteMAT( savename )

        print "Done\n"


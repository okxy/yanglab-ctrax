#!/usr/bin/env python
# KMB 11/06/2008


import os # use os for manipulating path names
import sys # use sys for parsing command line
import time # use time for setting playback rate

# we need to import pyglet.media before scipy.linalg.decomp is 
# imported by kcluster, as this seems to cause have_avbin to be false
# on windows
# and now we need to import ctypes before media because this seems to 
# be necessary to be able to find the avbin dll on windows. 
# man!
try:
    if 'win' in sys.platform:
        import ctypes
        avbin = ctypes.cdll.avbin
except:
    pass

from version import USE_AVBIN
if USE_AVBIN:
    import pyglet.media as media

import wx
from wx import xrc
import numpy as num
num.seterr( invalid='raise' ) # raise errors on numerical exceptions
num.seterr( divide='raise' )
from scipy.misc.pilutil import imresize

from version import __version__, DEBUG, DEBUG_REPEATABLE_BEHAVIOR
import annfiles as annot
import batch
import bg
import algorithm
import draw
import imagesk
import movies
import ellipsesk as ell
from params import params, const

if DEBUG:
    import pdb

class CtraxApp (algorithm.CtraxAlgorithm): # eventually inherits from wx.App
    def has( self, attr ):
        return hasattr( self, attr ) and getattr( self, attr ) is not None
    
    def OnInit( self ):
	"""
	Start up the Ctrax GUI
	"""
	self.InitState() # in settings.py

        self.ParseCommandLine()

        self.InitGUI() # in settings.py

        # read saved settings, overwriting defaults
        self.ReadUserfile() # in settings.py

        # draw GUI
        self.frame.Show()
        self.alive = True
        params.app_instance = self

	# open movie, ann file
	self.OpenMovie( new_movie=False )

        if params.interactive:
            print "******** Ctrax Warning and Error Messages ********"
            print ">>> Yang Lab version <<<"
            print '  additional output typically prefixed with "YL:"\n'
            print "Ctrax is currently under development, and you may"
            print "encounter bugs with the program, or correct usage"
            print "may not be obvious. Error and warning messages"
            print "will appear in this window. If you have trouble"
            print "and are contacting the Ctrax mailing list (see"
            print "http://groups.google.com/group/ctrax ), be sure"
            print "to copy and paste the relevant messages from this"
            print "window into your email. Your Ctrax version is %s."%__version__
            print "******************** Ctrax ***********************\n"

        return True


    def PrintUsage(self):
	"""
	Print command line arguments for Ctrax.
	"""
        self.RestoreStdio()
        print """Ctrax:
Optional Command Line Arguments:
--Interactive={True,False}
--Output=<movie.fmf.ann>
--Input=<movie.fmf>
--SettingsFile=<settings.ann>
--AutoEstimateBackground={True,False}
--AutoEstimateShape={True,False}
--AutoDetectCircularArena={True,False}
--CompressMovie=<movie.sbfmf>
--Matfile=<movie.mat>
--DiagnosticsFile=<movie_ctraxdiagnostics.txt>
--FirstFrameTrack={0,1,...}
--LastFrameTrack={-1,0,1,...}
--ResumeTracking={True,False}

Example:
Ctrax --Interactive=True --Input=movie1.fmf \\
  --Output=movie1.fmf.ann \\
  --SettingsFile=exp1.ann \\
  --Matfile=movie1.mat \\
  --DiagnosticsFile=movie1_ctraxdiagnostics.txt

By default, Interactive=True, AutoEstimateBackground=True,
AutoEstimateShape=True, AutoDetectCircularArena=True, 
FirstFrameTrack=0, LastFrameTrack=-1 
(meaning to track until the end of the video),
ResumeTracking=False

If not in interactive mode, then Input must be defined.

If Input is movie1.fmf and Output is not defined, then output
and settings will go to movie1.fmf.ann in non-interactive mode.

Existing annotation files are always backed up before being
overwritten, as long as the user has the appropriate
permissions to the output directory.

If CompressMovie is not set, then a compressed SBFMF will not
be created.

If Matfile is not set, then <basename>.mat will be used,
where <basename> is the base name of the movie.

If DiagnosticsFile is not set, then
<basename>_ctraxdiagnostics.txt will be used.
"""

    def ParseCommandLine(self):
	"""
	Interpret command line arguments.
	"""
        args = sys.argv[1:]

        self.movie = None
        self.ann_filename = None
        self.start_frame = 0
        # KB 20120109: added support for last_frame command-line argument
        self.last_frame = num.inf
        self.dowritesbfmf = False

        self.input_file_was_specified = False
        self.output_file_was_specified = False

        if len( args ) == 1:
            if args[0] == '--help':
                self.PrintUsage()
                exit( 1 )
            elif not '=' in args[0]:
                # in Windows, it could be a bare movie name
                args = ['--input=%s'%args[0]]

        # parse first for arguments that could alter other arguments' effects
        for arg in args:
            if arg.lower() == '--interactive=false':
                params.interactive = False
                params.enable_feedback( False )
                # if we were redirecting to an output window,
                # restore stdio to the command line prompt
                self.RestoreStdio()
            
        for i in range(len(args)):
	    # the arguments should be of the form --<paramname>=<paramvalue>
            try:
                name,value = args[i].split('=',1)
            except:
                print 'Error parsing command line arguments. No equals sign found. Usage: '
                self.PrintUsage()
                raise NotImplementedError
            if name.lower() == '--interactive':
                continue # already handled
            elif name.lower() == '--input':
                if hasattr( self, 'frame' ):
                    openframe = self.frame
                else:
                    openframe = None
                self.movie = movies.Movie( value, interactive=params.interactive,
                                           parentframe=openframe, open_now=True )
                self.input_file_was_specified = True
            elif name.lower() == '--output':
                self.ann_filename = value
                self.output_file_was_specified = True
            elif name.lower() == '--settingsfile':
                self.settingsfilename = value
                print "settingsfile = " + str(self.settingsfilename)
            elif name.lower() == '--autoestimatebackground':
                if value.lower() == 'false':
                    params.batch_autodetect_bg_model = False
            elif name.lower() == '--autoestimateshape':
                if value.lower() == 'false':
                    params.batch_autodetect_shape = False
            elif name.lower() == '--autodetectcirculararena':
                if value.lower() == 'false':
                    params.batch_autodetect_arena = False
                elif value.lower() == 'none':
                    params.batch_autodetect_arena = None
            elif name.lower() == '--compressmovie':
                self.writesbfmf_filename = value
                self.dowritesbfmf = True
            elif name.lower() == '--matfile':
                self.matfilename = value
            elif name.lower() == '--diagnosticsfile':
                self.diagnostics_filename = value
            elif name.lower() == '--firstframetrack':
                # KB 20120109: added support for start_frame command-line argument
                try:
                    start_frame = float(value)
                    if start_frame < 0 or round(start_frame) != start_frame:
                        raise NotImplementedError
                except:
                    print "FirstFrameTrack must be an integer greater than or equal to 0"
                    self.PrintUsage()
                    raise
                self.start_frame = int(start_frame)
                print "setting params.start_frame = " + str(int(start_frame))
                params.start_frame = int(start_frame)
            elif name.lower() == '--lastframetrack':
                try:
                    last_frame = float(value)
                    if round(last_frame) != last_frame:
                        raise NotImplementedError
                    if last_frame < 0:
                        last_frame = num.inf
                except:
                    print "LastFrameTrack must be an integer"
                    self.PrintUsage()
                    raise
                self.last_frame = last_frame
            elif name.lower() == '--resumetracking':
                if value.lower() == 'true':
                    params.noninteractive_resume_tracking = True
            else:
                print 'Error parsing command line arguments. Unknown parameter name "%s". Usage: '%name
                self.PrintUsage()
                raise NotImplementedError

        if self.start_frame > self.last_frame:
            print "FirstFrameTrack must be <= LastFrameTrack"
            self.PrintUsage()
            raise NotImplementedError

        if params.noninteractive_resume_tracking:
            # to resume tracking, output file must exist
            # (and should have ann data in it)
            if (not self.output_file_was_specified) or \
                   self.ann_filename is None or \
                   (not os.path.isfile( self.ann_filename )):
                print "To resume tracking, an existing output file must be specified."
                raise NotImplementedError

        # run noninteractive mode
        if params.interactive == False:
            self.run_noninteractive()
            exit( 0 )


    def run_noninteractive(self):
	"""
	Run Ctrax in non-interactive mode.
	"""

        self.frame = None

	# input movie name must be specified on the command line
        if not self.has( 'movie' ):
            print 'Error parsing command line arguments.\n\
            Input file must be specified in non-interactive mode.\n\
            Usage: '
            self.PrintUsage()
            raise NotImplementedError

        if not self.has( 'ann_filename' ):
            self.ann_filename = self.get_filename_with_extension( '+.ann' )

        if self.has( 'ann_filename' ):
            print "ann_filename = " + str(self.ann_filename)

        if not self.has( 'settingsfilename' ):
	    self.settingsfilename = self.ann_filename

        # open the movie
        print "Opening movie " + self.movie.filename
        self.OpenMovie( new_movie=False )

        # read parameters from the settings file
        print "Reading parameters from settings file " + self.settingsfilename
        self.LoadSettings()

        # KB 20120109: do_refresh not set otherwise
        self.do_refresh = True
        # actually, it's previously set to False in InitState() -JAB 1/10/12
        # does it need to be True? what happens if it's not set here?
        
        if not self.has('diagnostics_filename'):
            self.diagnostics_filename = self.get_filename_with_extension( '_ctraxdiagnostics.txt' )
        print "Diagnostics info will be written to " + self.diagnostics_filename

	# do the tracking steps
        print "DoAll..."
        self.DoAll()

    def LoadSettings( self ):
	"""
	Load parameter values from another annotation file.
	"""

        doreadbgmodel = not( params.interactive or self.IsBGModel() )
        print "loading settings from file " + str(self.settingsfilename)
        try:
            annot.LoadSettings(self.settingsfilename,self.bg_imgs,
                               doreadbgmodel=doreadbgmodel)
        except:
            print 'Could not read annotation file ' + self.settingsfilename
            

    def OpenMovie( self, new_movie=True ):
        """Attempt to open a movie given the current filename."""
        if new_movie:
            try:
                # open movie file
                self.movie = movies.Movie( self.dir, params.interactive,
                                           default_extension=self.last_movie_ext )
                if DEBUG:
                    print "Opened movie " + str(self.movie.filename)
            except ImportError: # open was cancelled
                return
            except Exception, details:
                # error messages should be handled by the movie object
                if self.has( 'movie' ):
                    if params.interactive:
                        wx.MessageBox( "Could not open the movie " + self.movie.filename,
                                       "Error", wx.ICON_ERROR )
                    else:
                        print "Could not open the movie " + self.movie.filename
                    print details
                    self.movie = None
                    self.ShowCurrentFrame()
                self.start_frame = 0
                return

        if not self.has( 'movie' ):
            return

        if new_movie:
            self.start_frame = 0

        # close settings windows
        if self.has( 'bg_imgs' ):
            self.OnQuitBGModel( None )
        if self.bg_window_open:
            self.OnQuitBG( None )
        if self.tracking_settings_window_open:
            self.OnQuitTrackingSettings( None )
        if self.choose_orientations_window_open:
            self.OnQuitChooseOrientations( None )
        if self.has( 'wizard' ):
            self.OnQuitTrackingWizard( None )

        params.movie_name = self.movie.filename
        self.dir = self.movie.dirname
        draw.const.filepath = self.movie.fullpath
        base, self.last_movie_ext = os.path.splitext( self.movie.filename )
        
        self.img_size = [self.movie.get_height(),self.movie.get_width()]

        # get a pointer to the "Ctraxmain" child
        if params.interactive:
            self.reset_img_wind()
            img = num.zeros((self.img_size[0],self.img_size[1]),dtype=num.uint8)
            sys.stdout.flush()
            self.img_wind.update_image_and_drawings("Ctraxmain",
                                                    img,
                                                    format="MONO8")
            sys.stdout.flush()
            self.img_wind_child = self.img_wind.get_child_canvas("Ctraxmain")
            # mouse click
            self.img_wind_child.Bind(wx.EVT_LEFT_DOWN,self.OnMouseDown)
            self.img_wind_child.Bind( wx.EVT_MOTION, self.OnMouseMoved )
            self.img_wind_child.Bind( wx.EVT_LEFT_UP, self.OnMouseUp )
            self.img_wind_child.Bind( wx.EVT_LEFT_DCLICK, self.OnMouseDoubleClick )
            
        # setup background-subtraction pieces
        params.bgs_file = self.get_filename_with_extension('_bg.data')
        self.bg_imgs = bg.BackgroundCalculator( self.movie )
        if DEBUG: print "initialized backsub data structure"

        # read settings
        if self.has( 'settingsfilename' ):
            self.LoadSettings()

        # open annotation file, read header if readable, read
        # tracks if user wants to load tracks
        if params.interactive:
            start_color = self.status.GetBackgroundColour()
            self.status.SetBackgroundColour( params.status_blue )
            self.status.SetStatusText( "Reading annotation from file",
                                       params.status_box )
            wx.BeginBusyCursor()
            try:
                wx.Yield() # error when called recursively, as when playing
            except: pass

        # create annotation file
        if DEBUG: print "creating/reading annotation file"
        if self.has( 'ann_filename' ): # only if sent on command line
            new_ann_filename = self.ann_filename
        else:
            if self.menu.IsChecked( xrc.XRCID("menu_settings_annprompt") ):
                prompt_title = "Choose annotation file"
            else:
                prompt_title = None
            new_ann_filename = self.get_filename_with_extension( '+.ann', prompt_title=prompt_title )
            # KB 20120109: if cancel hit, program should exit
            if new_ann_filename is None:
                self.OnQuit( None )
                exit( 2 )

        self.close_annfile() # if one is currently open
        # KB 20120109: in non-interactive mode, weird things were happening if the file exists.
        # set to overwrite file and ignore existing trajectories if in non-interactive mode
        # KB 20120111: adding option to resume tracking in non-interactive mode
        self.ann_file = annot.AnnotationFile( new_ann_filename, self.bg_imgs, doreadtrx=(params.interactive or params.noninteractive_resume_tracking) )
        if DEBUG: print "done reading annotation file"

        # done reading annotation file
        if params.interactive:
            self.status.SetBackgroundColour( start_color )
            self.status.SetStatusText( "", params.status_box )
            wx.EndBusyCursor()
            try:
                wx.Yield() # error when called recursively, as when playing
            except: pass

        if params.interactive and self.ann_file.IsAnnData():
            self.menu.Check( xrc.XRCID("menu_playback_show_ann"), True )

        # notification for newer Ctrax version, if available
        if self.has( 'update_alert_string' ):
            if params.interactive and \
                   self.menu.IsChecked( xrc.XRCID("menu_help_updates") ):
                wx.MessageBox( self.update_alert_string,
                               "Ctrax can be updated", wx.OK )
            elif not params.interactive:
                print "============================================"
                print self.update_alert_string
                print "============================================"
            delattr( self, 'update_alert_string' )
            if self.has( 'newer_ctrax_avail' ):
                self.newest_ctrax_notified = self.newer_ctrax_avail
            if self.has( 'newer_matlab_avail' ):
                self.newest_matlab_notified = self.newer_matlab_avail

        # show movie and update GUI
        if params.interactive:
            params.bg_sub_file = self.get_filename_with_extension('_bg_sub.png')
            self.OnMouseDoubleClick( None ) # zoom out
            self.ShowCurrentFrame()
            self.EnableControls()
            self.UpdateStatusMovie()
	    self.InitializeFrameSlider()
            self.OnResize()


    def OnOpen( self, evt ):
        """Movie file selection dialog."""

        old_mov = self.movie

        # open movie
        self.OpenMovie( new_movie=True )

        if self.movie is not old_mov:
            if self.menu.GetLabel( xrc.XRCID("menu_track_start") ) == const.TRACK_STOP:
                self.OnStopTracking( None ) # quit in mid-operation
            self.play_break = True # stop playback, if in progress
            self.start_frame = 0


    def OnLoadSettings( self, evt ):
        settings_file = self.get_filename_with_extension( '+.ann', "Load Settings from File" )

        if settings_file is not None:
            if self.menu.GetLabel( xrc.XRCID("menu_track_start") ) == const.TRACK_STOP:
                self.OnStopTracking( None ) # quit in mid-operation
            self.play_break = True # stop playback, if in progress
            self.settingsfilename = settings_file
            self.start_frame = 0
            self.LoadSettings()


    def get_filename_with_extension( self, new_ext, prompt_title=None ):
        """Prompt user for a new filename, based on the movie filename but with a new extension.
Setting '+' as the first character of new_ext indicates that the new extension
should be appended rather than altered/replaced. If prompt_title is None, then
the new name is created and returned without user input."""
        if not self.has( 'movie' ): return None

        if new_ext[0] == '+':
            new_ext = new_ext[1:]
            replace_ext = False # append extension
        else:
            replace_ext = True # replace extension
        
        if (prompt_title is not None) and (params.feedback_enabled) and (not DEBUG):
            # prompt for new filename
            if replace_ext:
                (basename, ext) = os.path.splitext( self.movie.filename )
            else:
                basename = self.movie.filename
            new_name = basename + new_ext
            
            prompt_base, prompt_ext = os.path.splitext( new_ext )
            if prompt_ext == '':
                prompt_ext = prompt_base
            
            dlg = wx.FileDialog( self.frame, prompt_title, self.movie.dirname,
                                 new_name, "*" + prompt_ext, wx.SAVE )

            # concatenate new path name and return
            if dlg.ShowModal() == wx.ID_OK:
                save_path = os.path.join( dlg.GetDirectory(), dlg.GetFilename() )
            else:
                save_path = None

            dlg.Destroy()

        else:
            # do it without prompting
            if replace_ext:
                (basename, ext) = os.path.splitext( self.movie.fullpath )
            else:
                basename = self.movie.fullpath
            save_path = basename + new_ext
                
        return save_path
            

    def OnSave( self, evt ):
        """Choose filename to save annotation data as MAT-file."""
        # check data validity
        if not self.ann_file.IsAnnData():
            if params.interactive:
                wx.MessageBox( "No valid annotation\nexists for this movie\nor no movie is loaded.",
                               "Error", wx.ICON_ERROR )
            else:
                print "Not saving -- no data"
            return

        # prompt to choose orientations, if not already done
        if not self.ann_file.orientations_chosen:
            if params.interactive:
                if wx.MessageBox( "Fly orientations have not been disambiguated yet. Do it now?", "Choose orientations?", wx.YES_NO ) == wx.YES:
                    self.OnChooseOrientations()
                    while hasattr( self, 'choose_orientations' ):
                        self.choose_orientations.frame.Raise()
                        wx.Yield()
                        time.sleep( 0.1 )
            else:
                choose_orientations = chooseorientations.ChooseOrientations(self.frame,interactive=False)
                self.ann_file = choose_orientations.ChooseOrientations(self.ann_file)

        # get save filename
        mat_name = self.get_filename_with_extension( '.mat', "Save as MAT-file" )

        # do save
        if mat_name is not None:
            # set up to save file
            start_color = self.status.GetBackgroundColour()
            self.status.SetBackgroundColour( params.status_blue )
            self.status.SetStatusText( "writing annotation data to file", params.status_box )
            wx.BeginBusyCursor()
            wx.Yield()

            # save file
            self.ann_file.WriteMAT( mat_name )

            # restore UI
            self.status.SetBackgroundColour( start_color )
            self.status.SetStatusText( "", params.status_box )
            wx.EndBusyCursor()
            wx.Yield()


    def OnSaveAvi( self, evt ):
        """Choose filename to save tracks as AVI-file."""
        if not self.ann_file.IsAnnData():
            if params.interactive:
                wx.MessageBox( "No valid annotation\nexists for this movie\nor no movie is loaded.",
                               "Error", wx.ICON_ERROR )
            else:
                print "Not saving -- no data"
            return

        dlg = wx.TextEntryDialog(self.frame,"Frames to output to AVI file: (startframe:endframe): ","Save as AVI-file","%d:%d"%(self.ann_file.firstframetracked,self.ann_file.lastframetracked))
        isgood = False
        while isgood == False:
            if dlg.ShowModal() == wx.ID_OK:
                isgood = True
                s = dlg.GetValue()
                s = s.rsplit(':')
            else:
                break
            if len(s) == 2:
                if s[0].isdigit() and s[1].isdigit():
                    framestart = int(s[0])
                    frameend = int(s[1])
                else:
                    isgood = False
                    continue
            else:
                isgood = False
                continue

        dlg.Destroy()

        if isgood == False:
            return

        avi_name = self.get_filename_with_extension( '_annot.avi', "Save as AVI file" )

        if avi_name is not None:
            if params.interactive:
                start_color = self.status.GetBackgroundColour()
                self.status.SetBackgroundColour( params.status_blue )
                self.status.SetStatusText( "writing movie of results", params.status_box )
                wx.BeginBusyCursor()
                wx.Yield()

            movies.write_results_to_avi( self.movie, self.ann_file, avi_name,
                                         framestart, frameend )

            if self.alive and params.interactive:
                self.status.SetBackgroundColour( start_color )
                self.status.SetStatusText( "", params.status_box )
                wx.EndBusyCursor()
                wx.Yield()

            print "movie exported successfully"


    def OnSaveDiagnostics( self, evt ):
        """Choose filename to save diagnostics to."""

        diag_name = self.get_filename_with_extension( '_ctraxdiagnostics.txt',
                                                      "Save diagnostics to text file" )

        if diag_name is not None:
            start_color = self.status.GetBackgroundColour()
            self.status.SetBackgroundColour( params.status_blue )
            self.status.SetStatusText( "writing diagnostics to file",
                                       params.status_box )
            wx.BeginBusyCursor()
            wx.Yield()

            annot.WriteDiagnostics( diag_name )

            self.status.SetBackgroundColour( start_color )
            self.status.SetStatusText( "", params.status_box )
            wx.EndBusyCursor()
            wx.Yield()


    def EnableControls( self ):
        """Enable or disable GUI controls based on current state of tracker."""

	if not params.interactive:
	    return

        if self.has( 'batch' ):
            self.batch.EnableControls()

        twiddling_enabled = params.feedback_enabled and not self.tracking

	movieready = self.has( 'movie' )
        if movieready:
            issbfmf = (self.movie.type == 'sbfmf')
        else:
            issbfmf = False

	annready = movieready and self.has( 'ann_file' ) and self.ann_file.IsAnnData()

	isplaying = hasattr(self,'play_break') and not self.play_break

	self.menu.Enable( xrc.XRCID("menu_track_start"), # could be "stop"
			  movieready and (not isplaying) )

        settings_enabled = movieready and twiddling_enabled
        
        self.menu.Enable( xrc.XRCID("menu_track_writesbfmf"), settings_enabled and not issbfmf )
        self.dowritesbfmf = self.dowritesbfmf and not issbfmf
        self.menu.Check( xrc.XRCID("menu_track_writesbfmf"), self.dowritesbfmf )

	self.menu.Enable( xrc.XRCID("menu_track_resume"),
			  settings_enabled and (not isplaying) and annready \
                          and len( self.ann_file ) < self.movie.get_n_frames() )
	self.menu.Enable( xrc.XRCID("menu_track_resume_here"),
			  settings_enabled and (not isplaying) and annready )

	self.menu.Enable( xrc.XRCID("menu_load_settings"), settings_enabled )
	self.menu.Enable( xrc.XRCID("menu_settings_bg"), settings_enabled )
	self.menu.Enable( xrc.XRCID("menu_settings_bg_model"), settings_enabled )
	self.menu.Enable( xrc.XRCID("menu_settings_tracking"), settings_enabled )
        self.menu.Enable( xrc.XRCID("menu_tracking_wizard"), settings_enabled )
	self.menu.Enable( xrc.XRCID("menu_compute_background"), settings_enabled )
	self.menu.Enable( xrc.XRCID("menu_compute_shape"), settings_enabled )
        self.menu.Enable( xrc.XRCID("menu_file_save_diagnostics"), settings_enabled )
        self.framenumber_text.Enable( settings_enabled )
	self.slider.Enable( settings_enabled )

        saving_enabled = annready and twiddling_enabled
	self.menu.Enable( xrc.XRCID("menu_playback_show_ann"), saving_enabled )
	self.menu.Enable( xrc.XRCID("menu_file_export"), saving_enabled )
	self.menu.Enable( xrc.XRCID("menu_file_save_avi"), saving_enabled )
	self.menu.Enable( xrc.XRCID("menu_choose_orientations"), saving_enabled )
        self.menu.Enable( xrc.XRCID("menu_analyze_plottraj"), saving_enabled )
        self.menu.Enable( xrc.XRCID("menu_analyze_histpos"), saving_enabled )
        self.menu.Enable( xrc.XRCID("menu_analyze_histspeed"), saving_enabled )
        self.menu.Enable( xrc.XRCID("menu_analyze_histdtheta"), saving_enabled )


    def InitializeFrameSlider(self):
	self.slider.SetThumbPosition( self.start_frame )
	self.slider.SetScrollbar( self.start_frame,1,self.movie.get_n_frames()-1,100 )
	self.framenumber_text.SetValue( "%05d"%(self.movie.get_n_frames()) )
        

    def UpdateStatusMovie( self ):
        """Update status bar with movie filename."""
        try:
            if not self.has( 'movie' ) or len( self.movie.filename ) == 0:
                self.status.SetStatusText( "[no file loaded]", params.file_box )
            elif len( self.movie.filename ) < params.file_box_max_width:
                self.status.SetStatusText( self.movie.filename, params.file_box )
            else:
                self.status.SetStatusText( "..." + os.sep + self.movie.filename, params.file_box )
        except (TypeError, AttributeError): pass


    def ShowCurrentFrame( self ):
        """Grab current frame, draw on it, and display in GUI.
        Also update zoom-ellipse windows, if present."""
	if not params.interactive: return
        if not self.alive: return
        if not self.has( 'movie' ): return
        if self.start_frame < 0: return

        # get frame
        try:
            frame, self.last_timestamp = self.movie.get_frame( self.start_frame )
            if num.isnan(self.last_timestamp):
                self.last_timestamp = float(self.start_frame) / float(params.DEFAULT_FRAME_RATE)
        except movies.NoMoreFramesException:
            self.start_frame = min(self.start_frame,self.movie.get_n_frames()-1)
            self.slider.SetScrollbar( self.start_frame,1,self.movie.get_n_frames()-1,100 )
            return
        except IndexError: # framenumber out of range
            return

	# set frame number display
        self.framenumber_text.SetValue( "%05d"%(self.start_frame) )

        # dim frame
        if self.menu.IsChecked( xrc.XRCID("menu_playback_dim") ):
            frame = frame / 2

        # annotate image
        dodrawann = self.ann_file.IsAnnData() and \
            self.start_frame >= self.ann_file.firstframetracked and \
            self.start_frame <= self.ann_file.lastframetracked

        frame8 = imagesk.double2mono8(frame,donormalize=False)
        height, width = frame8.shape

        # choose correct region of interest
        if self.has( 'zoom_drag_roi' ):
            left = int( round( width*self.zoom_drag_roi[0] ) )
            top = int( round( height*self.zoom_drag_roi[1] ) )
            right = int( round( width*self.zoom_drag_roi[2] ) )
            bottom = int( round( height*self.zoom_drag_roi[3] ) )
            frame8 = frame8[top:bottom,left:right]

            # resize the image
            resizew = float( width )/max( float( frame8.shape[1] ), 0.1 )
            resizeh = float( height )/max( float( frame8.shape[0] ), 0.1 )
            self.zoom_drag_roi_scale = min( resizew, resizeh )
            try:
                new_frame8 = imresize( frame8, self.zoom_drag_roi_scale )
            except ValueError:
                return # "tile cannot extend outside image", seems to be harmless
            
            # fill in with gray at margins
            frame8 = num.ones( frame.shape, dtype=num.uint8 )*127
            #x = (frame8.shape[1] - new_frame8.shape[1])/2
            #y = (frame8.shape[0] - new_frame8.shape[0])/2
            # centering is a lot of work for subsequent clicks
            frame8[:new_frame8.shape[0],:new_frame8.shape[1]] = new_frame8
            
        # draw bounding box for drag rectangle
        lines_to_draw = []
        line_colors = []
        if self.zoom_dragging:
            lines_to_draw.extend( [(width*self.zoom_drag_origin[0],
                                    height*self.zoom_drag_origin[1],
                                    width*self.zoom_drag_origin[0],
                                    height*self.zoom_drag_current[1]),
                                   (width*self.zoom_drag_origin[0],
                                    height*self.zoom_drag_current[1],
                                    width*self.zoom_drag_current[0],
                                    height*self.zoom_drag_current[1]),
                                   (width*self.zoom_drag_current[0],
                                    height*self.zoom_drag_current[1],
                                    width*self.zoom_drag_current[0],
                                    height*self.zoom_drag_origin[1]),
                                   (width*self.zoom_drag_current[0],
                                    height*self.zoom_drag_origin[1],
                                    width*self.zoom_drag_origin[0],
                                    height*self.zoom_drag_origin[1])] )
            line_colors.extend( [params.zoom_drag_rectangle_color,
                                 params.zoom_drag_rectangle_color,
                                 params.zoom_drag_rectangle_color,
                                 params.zoom_drag_rectangle_color] )

        # draw annotation
        if self.menu.IsChecked( xrc.XRCID("menu_playback_show_ann") ) and dodrawann:
            # first frame of tail of trajectory
            tailframe = max( self.ann_file.firstframetracked,
                             self.start_frame - params.tail_length )
            dataframes = self.ann_file.get_frames( tailframe, self.start_frame )

            # update small ellipse windows
            if self.menu.IsChecked( xrc.XRCID("menu_settings_zoom") ):
                self.zoom_window.SetData(dataframes[-1],frame)
                self.zoom_window.Redraw()

            ellipses = dataframes[-1]
            old_pts = []
            for dataframe in dataframes:
                these_pts = []
                for ellipse in dataframe.itervalues():
                    these_pts.append( (ellipse.center.x, ellipse.center.y, ellipse.identity) )
                old_pts.append( these_pts )

            # draw on image
            linesegs = ell.annotate_image(ellipses,old_pts,self.ellipse_thickness)

            (linesegs,linecolors) = imagesk.separate_linesegs_colors(linesegs)
            lines_to_draw.extend( linesegs )
            line_colors.extend( linecolors )

            self.num_flies_text.SetValue( "N. Flies: %02d"%len(ellipses) )
        else:
            self.num_flies_text.SetValue( "" )

        # scale the drawings
        if self.has( 'zoom_drag_roi' ):
            for si in range( len( lines_to_draw ) ):
                orig_seg = lines_to_draw[si]
                new_seg = ((orig_seg[0] - left)*self.zoom_drag_roi_scale,
                           (orig_seg[1] - top)*self.zoom_drag_roi_scale,
                           (orig_seg[2] - left)*self.zoom_drag_roi_scale,
                           (orig_seg[3] - top)*self.zoom_drag_roi_scale)
                lines_to_draw[si] = new_seg

        # draw
        self.img_wind.update_image_and_drawings('Ctraxmain',frame8,
                                                format='MONO8',
                                                linesegs=lines_to_draw,
                                                lineseg_colors=line_colors)
        self.img_wind.Refresh( eraseBackground=False )

        # update the slider
        self.slider.SetThumbPosition( self.start_frame )


    def OnSlider( self, evt ):
        """Frame slider callback. Display new frame."""
        # tone down the duplicated events as much as possible (Windows, I mean you)
        new_fr = self.slider.GetThumbPosition()
        if new_fr != self.start_frame:
            try:
                wx.Yield()
            except:
                pass
            else:
                self.play_break = True
                self.start_frame = new_fr
                self.ShowCurrentFrame()
            finally:
                evt.Skip()
                

    def OnResize( self, evt=None ):
        """Window resized. Repaint in new window size."""

        if hasattr( self, 'img_size' ):
            top_sizer = self.frame.GetSizer()
            panel_item = top_sizer.GetItem( self.img_panel )
            panel_item.SetFlag( panel_item.GetFlag() | wx.SHAPED )
            panel_item.SetRatio( float( self.img_size[1] )/self.img_size[0] )

        self.frame.Layout()

        try:
            # redraw
            self.ShowCurrentFrame()
            # scale slider to new width
            new_size = wx.Size( self.toolbar.GetRect().GetWidth() - 30,
                                self.slider.GetRect().GetHeight() )
            self.slider.SetMinSize( new_size )
            self.slider.SetSize( new_size )
            new_pos = wx.Point( self.toolbar.GetPosition().x + 15,
                                self.slider.GetPosition().y )
            self.slider.SetPosition( new_pos )
            # scale movie-name box
            const.file_box_max_width = int(float(self.img_wind.GetRect().GetWidth())/11.)
            self.UpdateStatusMovie()
        except AttributeError: pass # during initialization


    def close_annfile( self ):
        """Close annotation file, typically in preparation for opening a new movie or quitting."""

        if self.has( 'ann_file' ):

            if not self.ann_file.file.closed:
                self.ann_file.finish_writing()
                self.ann_file.file.close()
            
            if self.dowritesbfmf:
                self.ann_file.copy_to_sbfmf()

        
    def OnQuit( self, evt ):
        """Quit selected (or window closing). Stop threads and close window."""

        # stop tracking
        if self.menu.GetLabel( xrc.XRCID("menu_track_start") ) == const.TRACK_STOP:
            self.OnStopTracking( None ) # quit in mid-operation
        self.play_break = True

        try:
            self.close_annfile()
        except Exception, details:
            print "error closing annotation: %s"%details

        # write user settings
        self.WriteUserfile()

        # kill
        self.alive = False
        self.frame.Destroy()


    def OnStopTracking( self, evt=None ):
        """Stop button pressed. Stop threads."""

        self.StopThreads() # located in algorithm.py
        params.enable_feedback( True )
        if self.has( 'batch' ):
            self.batch.executing = False

        if self.dowritesbfmf and self.movie.writesbfmf_isopen():
            self.movie.writesbfmf_close(self.start_frame)

        # set tracking flag
        self.tracking = False


    def OnStartTrackingMenu( self, evt ):
        """Start button pressed. Begin tracking."""
        if self.menu.GetLabel( xrc.XRCID("menu_track_start") ) == const.TRACK_STOP:
            # stop tracking
            self.OnStopTracking()
        else:
            self.OnStartTracking(evt)


    def OnWriteSBFMF( self, evt=None ):
        """Set SBFMF filename. Use user input if running interactively."""
        self.dowritesbfmf = False

        if self.has( 'movie' ) and \
               self.menu.IsChecked( xrc.XRCID("menu_track_writesbfmf") ):
            self.writesbfmf_filename = self.get_filename_with_extension( '.sbfmf' )
            self.dowritesbfmf = True


    def OnPlayButton( self, evt ):
        self.OnStartPlayback()


    def OnStopButton(self,evt):
        if self.tracking:
            self.OnStopTracking()
        else:
            self.OnStopPlayback()


    def OnStartTracking(self,evt=None):

        # check for bg model
        if not self.CheckForBGModel():
            return

        if not self.CheckForShapeModel():
            return

        # will data be lost?
        if evt is not None and params.interactive and self.has( 'ann_file' ) and \
                self.ann_file.IsAnnData() and not DEBUG:
           if evt.GetId() == xrc.XRCID("menu_track_start"): 
               msgtxt = 'Frames %d to %d have been tracked.\nErase these results and start tracking over?' % (self.ann_file.firstframetracked,self.ann_file.lastframetracked)
               if wx.MessageBox( msgtxt, "Erase trajectories and start tracking?", wx.OK|wx.CANCEL ) == wx.CANCEL:
                   return
           elif evt.GetId() == xrc.XRCID("menu_track_resume_here"):
               if self.ann_file.lastframetracked >= self.start_frame:
                   msgtxt = 'Frames %d to %d have been tracked.\nRestarting tracking at frame %d will cause old trajectories from %d to %d to be erased.\nErase these results and restart tracking in the current frame?' % (self.ann_file.firstframetracked, self.ann_file.lastframetracked, self.start_frame, self.start_frame, self.ann_file.lastframetracked)
                   if wx.MessageBox( msgtxt, "Erase trajectories and start tracking?", wx.OK|wx.CANCEL ) == wx.CANCEL:
                       return
        # end check for trajectory overwriting

        # set tracking flag
        self.tracking = True

        # update toolbar functions
        self.UpdateToolBar('started')

        self.menu.SetLabel( xrc.XRCID("menu_track_start"), const.TRACK_STOP )
        self.menu.Check( xrc.XRCID("menu_playback_show_ann"), True )

	self.EnableControls()

        wx.Yield() # refresh GUI

        # crop data
        if evt is not None and evt.GetId() == xrc.XRCID("menu_track_resume"):
            # if resuming tracking, we will keep the tracks from 
            # frames firstframetracked to lastframetracked-1 
            # (remove last frame in case writing the last frame 
            # was interrupted)
            self.start_frame = self.ann_file.lastframetracked
            if DEBUG: print "start_frame = " + str(self.start_frame)
            if DEBUG: print "cropping annotation file to frames %d through %d"%(self.ann_file.firstframetracked,self.ann_file.lastframetracked-1)
            self.ann_file.InitializeData(self.ann_file.firstframetracked,
                                         self.ann_file.lastframetracked-1)
            
            # restart writing to the sbfmf
            if self.dowritesbfmf:
                try:
                    self.movie.writesbfmf_restart(self.start_frame,self.bg_imgs,
                                                  self.writesbfmf_filename)
                except Exception, details:
                    self.abort_sbfmf_writing( details )

        elif evt is not None and evt.GetId() == xrc.XRCID("menu_track_resume_here"):
	    # if resuming here, then erase parts of track after current frame

            # the latest possible frame to start tracking on is 
            # lastframetracked
            if self.start_frame > self.ann_file.lastframetracked:
                print "Restarting tracking at frame %d (current frame > last frame tracked)"%self.ann_file.lastframetracked
                self.start_frame = self.ann_file.lastframetracked

            # crop to the frames before the current frame
            self.ann_file.InitializeData(self.ann_file.firstframetracked,self.start_frame-1)
            
            # restart writing to the sbfmf
            if self.dowritesbfmf:
                try:
                    self.movie.writesbfmf_restart(self.start_frame,self.bg_imgs,
                                                  self.writesbfmf_filename)
                except Exception, details:
                    self.abort_sbfmf_writing( details )

        else:
            # start(over) tracking

            self.start_frame = 0
            params.start_frame = self.start_frame

            # empty annotations
            self.ann_file.InitializeData(self.start_frame,self.start_frame-1)
            if self.dowritesbfmf:
                # open an sbfmf file if necessary
                self.movie.writesbfmf_start( self.bg_imgs, self.writesbfmf_filename )

        self.Track() # located in algorithm.py

        if self.alive:
            self.OnStopTracking()

            # update toolbar function
            self.UpdateToolBar('stopped')
	    self.menu.SetLabel( xrc.XRCID("menu_track_start"), const.TRACK_START )

	    self.EnableControls()


    def abort_sbfmf_writing( self, exception ):
        msgtxt = 'Could not restart writing sbfmf; file %s was unreadable. Not writing sbfmf.'%self.writesbfmf_filename
        if params.interactive:
            wx.MessageBox( msgtxt, "Warning", wx.ICON_WARNING )
        else:
            print msgtxt
        print "SBFMF restart error was:", str( exception )
        self.dowritesbfmf = False
        self.menu.Check( xrc.XRCID("menu_track_writesbfmf"), False)
        self.movie.writesbfmf_close( self.start_frame )
        

    def OnComputeBg(self,evt=None):

        if params.interactive:
            start_color = self.status.GetBackgroundColour()
            self.status.SetBackgroundColour( params.status_green )
            self.status.SetStatusText( "calculating background", params.status_box )

            success = self.bg_imgs.OnCalculate( parent=self.frame )
            
            self.status.SetBackgroundColour( start_color )
            self.status.SetStatusText( "", params.status_box )

        else:
            success = self.bg_imgs.OnCalculate()

        print "YL: updateParameters()"
        self.bg_imgs.updateParameters()

        return success


    def OnComputeShape(self,evt=None):
        if not self.CheckForBGModel(): return

        if params.interactive:
            start_color = self.status.GetBackgroundColour()
            self.status.SetBackgroundColour( params.status_red )
            self.status.SetStatusText( "calculating shape", params.status_box )
            wx.BeginBusyCursor()
            wx.Yield()

            success = ell.est_shape( self.bg_imgs, self.frame )
            
            wx.EndBusyCursor()
            self.status.SetBackgroundColour( start_color )
            self.status.SetStatusText( "", params.status_box )
            
        else:
            success = ell.est_shape( self.bg_imgs )

        return success


    def OnStopPlayback( self, evt=None ):
        # pause playback
        self.play_break = True

        # update toolbar function
        self.UpdateToolBar('stopped')

        # change menu items
	self.EnableControls()


    def OnStartPlayback( self, evt=None ):
        """Begin playback."""
        if not self.has( 'movie' ): return

        # update toolbar function
        self.UpdateToolBar('started')

        self.play_break = False

        # change menu items
	self.EnableControls()

        # start playback
        self.start_frame += 1 # don't play current frame again
        if self.start_frame >= self.movie.get_n_frames():
            self.start_frame = 0 # start over
            self.last_timestamp = self.movie.get_some_timestamps( 0, 1 )[0]
        self.play_start_stamp = self.last_timestamp
        self.play_start_time = time.time()
        while self.start_frame < self.movie.get_n_frames():
            # show current frame
            self.slider.SetThumbPosition( self.start_frame )
            self.ShowCurrentFrame()
            wx.Yield()
            if self.play_break: break

            # calculate which frame to show next
            # test actual and movie elapsed time
            actual_time = max( time.time() - self.play_start_time, 0.05 )
            movie_time = max( self.last_timestamp - self.play_start_stamp, 0.05 )
            # the ratio of these two should equal the play_speed...
            if movie_time / actual_time > self.play_speed:
                # more movie time has elapsed than real time, so slow down
                time.sleep( movie_time - actual_time*self.play_speed )
                self.start_frame += 1
            else:
                # more actual time has elapsed than movie time, so skip frames
                self.start_frame += int(round( actual_time*self.play_speed / movie_time ))

        if self.start_frame >= self.movie.get_n_frames():
            self.start_frame = self.movie.get_n_frames() - 1
            self.slider.SetScrollbar( self.start_frame, 1,
                                      self.movie.get_n_frames() - 1, 100 )

        if self.alive:
            self.OnStopPlayback()

    def OnSpeedUpButton( self, evt ):
        if self.tracking:
            self.OnSpeedUpTracking()
        else:
            self.OnChangePlaybackSpeed(evt)

    def OnSlowDownButton( self, evt ):
        if self.tracking:
            self.OnSlowDownTracking()
        else:
            self.OnChangePlaybackSpeed(evt)

    def OnRefreshButton( self, evt ):
        self.request_refresh = True

    def OnSpeedUpTracking(self):

        self.framesbetweenrefresh = max(1,self.framesbetweenrefresh-1)
        self.set_rate_text( use_refresh=True )

    def OnSlowDownTracking(self):

        self.framesbetweenrefresh += 1
        self.set_rate_text( use_refresh=True )

    def OnChangePlaybackSpeed(self,evt=None):
        """Change playback speed."""
        
        if evt.GetId() == self.speedup_id:
            self.play_speed *= 2
        elif evt.GetId() == self.slowdown_id:
            self.play_speed /= 2
        self.play_speed = min( self.play_speed, 32.0 )
        self.play_speed = max( self.play_speed, 1/32. )
        self.set_rate_text( use_refresh=False )

        # reset timers
        if self.has( 'movie' ):
            self.play_start_stamp = self.last_timestamp
            self.play_start_time = time.time()

    def OnBatch( self, evt ):
        """Open batch processing window."""
        if self.batch is not None and self.batch.is_showing:
            self.batch.frame.Raise()
            return

        # open selector window
        if self.batch is None:
            if self.has( 'movie' ):
                self.batch = batch.BatchWindow( self.frame, self.dir, self.movie.fullpath )
            else:
                self.batch = batch.BatchWindow( self.frame, self.dir )
        else: # not none but not showing, either
            self.batch.ShowWindow( self.frame )

        # bind callbacks
        self.batch.frame.Bind( wx.EVT_SIZE, self.OnBatchResize )
        self.batch.frame.Bind( wx.EVT_MOVE, self.OnBatchResize )
        self.batch.frame.Bind( wx.EVT_BUTTON, self.OnBatchExecute, id=xrc.XRCID("button_execute") )

        # set window position from memory
        if self.last_batch_pos is not None:
            batch_pos = self.constrain_window_to_screen( self.last_batch_pos, self.last_batch_size )
            self.batch.frame.SetPosition( batch_pos )
            self.batch.frame.SetSize( self.last_batch_size )

        # set "save SBFMF" checkbox based on own state
        self.batch.sbfmf_checkbox.SetValue( self.menu.IsChecked( xrc.XRCID("menu_track_writesbfmf") ) )

    def OnBatchResize( self, evt ):
        """Batch window was moved or resized, remember new location."""
        evt.Skip()
        try:
            self.last_batch_size = self.batch.frame.GetSize()
            self.last_batch_pos = self.batch.frame.GetPosition()
        except AttributeError: pass # during initialization

    def OnBatchExecute( self, evt ):
        """Begin executing batch processing."""
        if params.interactive and wx.MessageBox( "Execute batch processing now?", "Execute?", wx.YES_NO ) == wx.NO:
            return

        if params.maxshape.area >= 10000 and \
               (not params.batch_autodetect_shape) and \
               params.interactive and \
               wx.MessageBox( "Shape parameters have not been set. Continue anyway, calculating automatically?", "Auto-calculate shape?", wx.YES_NO ) == wx.NO:
                return

        # disable GUI
        params.enable_feedback( False )
        self.menu.SetLabel( xrc.XRCID("menu_track_start"), const.TRACK_STOP )
        self.EnableControls()

        if not self.menu.IsEnabled( xrc.XRCID("menu_playback_show_ann") ):
            # assume it's only not checked because this movie isn't annotated
            self.menu.Check( xrc.XRCID("menu_playback_show_ann"), True )
        wx.Yield() # refresh GUI

        write_sbfmfs_init = self.dowritesbfmf
        write_sbfmfs = self.batch.sbfmf_checkbox.IsChecked()

        if params.batch_autodetect_arena is None:
            params.do_set_circular_arena = False
        else:
            params.do_set_circular_arena = params.batch_autodetect_arena

        first_ann_name = None
        self.batch.executing = True

        # run batch
        start_list = self.batch.file_list[:]
        for filename in start_list:
            # open movie
            self.movie = movies.Movie( filename, interactive=False )
            self.OpenMovie( new_movie=False )
            self.start_frame = 0

            if write_sbfmfs and self.movie.type != 'sbfmf':
                self.dowritesbfmf = True
                self.writesbfmf_filename = self.get_filename_with_extension( '.sbfmf' )
            else:
                self.dowritesbfmf = False

            # load settings
            if first_ann_name is None:
                first_ann_name = self.ann_file.filename
            elif (params.batch_autodetect_arena == False) or \
                     (not params.batch_autodetect_shape) or \
                     (not params.batch_autodetect_bg_model):
                try:
                    annot.LoadSettings( first_ann_name, self.bg_imgs,
                                        doreadbgmodel=(not params.batch_autodetect_bg_model) )
                except:
                    print 'Could not read first annotation file', first_ann_name

                if params.batch_autodetect_arena == True and \
                       params.do_set_circular_arena == False:
                    # arena settings were read, but we won't be autodetecting
                    params.do_set_circular_arena = True

            # do tracking
            if self.menu.IsEnabled( xrc.XRCID("menu_track_start") ):
                self.tracking = True
                self.UpdateToolBar( 'started' )
                wx.Yield()

                self.DoAll()
                self.close_annfile()

                if self.alive:
                    self.UpdateToolBar( 'stopped' )
                    wx.Yield()
                self.tracking = False

            # bail out if "stop" was pressed
            if not self.batch.executing: break

            # remove file from list
            self.batch.file_list.pop( 0 )
            if self.batch.is_showing:
                self.batch.list_box.Set( self.batch.file_list )

        self.batch.executing = False
        self.dowritesbfmf = write_sbfmfs_init

        if self.alive:
            # re-enable GUI
            params.enable_feedback( True )

            self.menu.SetLabel( xrc.XRCID("menu_track_start"), const.TRACK_START )
            self.EnableControls()

    def OnCheckBatchStats( self, evt ):
        """Batch statistics box checked. Force re-read of annotation data."""
        self.batch_data = None # currently irrelevant

    def OnHelp( self, evt ):
        """Help requested. Popup box with website."""
        wx.MessageBox( "Documentation available at\nhttp://ctrax.sourceforge.net", "Help" )

    def OnAbout( self, evt ):
        """About box requested."""
        wx.AboutBox( const.info )

def main():
    args = (0,)
    kw = {}
    if (not int(os.environ.get('CTRAX_NO_REDIRECT','0'))) and not DEBUG:
        # redirect to a window
        args = ()
        kw = dict(redirect=True)

    # for debugging only: reseed the random number generator at 0 for repeatable behavior
    if DEBUG_REPEATABLE_BEHAVIOR:
        num.random.seed(0)

    app = CtraxApp( *args, **kw )
    app.MainLoop()

if __name__ == '__main__':
    #import hotshot
    #prof = hotshot.Profile("hotshot_ctrax_stats")
    #prof.runcall(main)
    #prof.close()
    main()

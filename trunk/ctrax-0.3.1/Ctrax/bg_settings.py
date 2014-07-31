# bg_settings.py
# KMB 09/11/07
# split from bg.py JAB 10/17/11

import os.path
import codedir

import numpy as num
import scipy.io
import wx
from wx import xrc
import motmot.wxvalidatedtext.wxvalidatedtext as wxvt # part of Motmot

from colormapk import colormap_image
from ellipsesk import find_ellipses
from ellipses_draw import draw_ellipses
import imagesk
from params import params
import setarena
import roi
import fixbg
from version import DEBUG
from zoomable_image_canvas import ZoomableImageCanvas

THRESH_RSRC_FILE = os.path.join(codedir.codedir,'xrc','bg_thresh.xrc')
SETTINGS_RSRC_FILE = os.path.join(codedir.codedir,'xrc','bg_settings.xrc')


class BackgroundSettings:
    """Class to separate background GUI code from other calculation code."""

    def ShowBG( self, parent, framenumber, old_thresh, dosub_callback=None ):
        
        # clear buffer
        self.initialize_buffer()

        self.old_thresh = params.n_bg_std_thresh
        self.show_frame = framenumber
        self.dosub_callback = dosub_callback

        rsrc = xrc.XmlResource( THRESH_RSRC_FILE )
        self.frame = rsrc.LoadFrame( parent, "frame_Ctrax_bg" )

        # calculate background image, if not already done
        if not hasattr( self, 'center' ):
            success = self.OnCalculate( parent=parent )
            if not success: return

        # event bindings
        self.hf.SetFrame(self.frame)
        self.hf.frame.Bind( wx.EVT_BUTTON, self.OnQuitHF, id=xrc.XRCID("hm_done_button") )
        self.hf.frame.Bind( wx.EVT_CLOSE, self.OnQuitHF )

        self.menu = self.frame.GetMenuBar()
        #self.frame.Bind( wx.EVT_MENU, self.OnShowBG, id=xrc.XRCID("menu_show_bg") )
        #self.frame.Bind( wx.EVT_MENU, self.OnShowThresh, id=xrc.XRCID("menu_show_thresh") )
        #self.frame.Bind( wx.EVT_MENU, self.OnFrameSlider, id=xrc.XRCID("menu_show_bin") )
        #self.frame.Bind( wx.EVT_BUTTON, self.OnCalcButton, id=xrc.XRCID("button_calculate") )
        #self.frame.Bind( wx.EVT_BUTTON, self.OnResetButton, id=xrc.XRCID("button_reset") )
        
        # control handles
        self.frame_text = xrc.XRCCTRL( self.frame, "text_frame" )
        self.range_text = xrc.XRCCTRL( self.frame, "text_range" )
        #self.reset_button = xrc.XRCCTRL( self.frame, "button_reset" )
        #if self.old_thresh is None:
        #    self.reset_button.Enable( False )
        
        # set threshold
        self.thresh_slider = xrc.XRCCTRL( self.frame, "slider_thresh" )
        self.thresh_slider.SetScrollbar(self.GetThresholdScrollbar(),0,255,255-25)
        self.thresh_low_slider = xrc.XRCCTRL( self.frame, "slider_low_thresh" )
        self.thresh_low_slider.SetScrollbar(self.GetThresholdLowScrollbar(),0,255,255-25)

        # we can also input the threshold by typing it; make sure slider and text input
        # show the same value
        self.thresh_textinput = xrc.XRCCTRL( self.frame, "threshold_text_input" )
        self.frame.Bind( wx.EVT_SCROLL, self.OnThreshSlider, self.thresh_slider )
        wxvt.setup_validated_float_callback( self.thresh_textinput,
                                             xrc.XRCID("threshold_text_input"),
                                             self.OnThreshTextEnter,
                                             pending_color=params.wxvt_bg )
        self.thresh_low_textinput = xrc.XRCCTRL( self.frame, "low_threshold_text_input" )
        self.frame.Bind( wx.EVT_SCROLL, self.OnThreshSlider, self.thresh_low_slider )
        wxvt.setup_validated_float_callback( self.thresh_low_textinput,
                                             xrc.XRCID("low_threshold_text_input"),
                                             self.OnThreshTextEnter,
                                             pending_color=params.wxvt_bg )
        self.SetThreshold()
        self.frame_slider = xrc.XRCCTRL( self.frame, "slider_frame" )
        self.frame.Bind( wx.EVT_SCROLL, self.OnFrameSlider, self.frame_slider )
        self.frame_slider.SetScrollbar(self.show_frame,0,params.n_frames-1,params.n_frames/10)
        # which image are we showing
        self.bg_img_chooser = xrc.XRCCTRL( self.frame, "view_type_input" )
        if params.use_expbgfgmodel:
            self.bg_img_chooser.SetItems(params.BG_SHOW_STRINGS+params.EXPBGFGMODEL_SHOW_STRINGS)
        else:
            self.bg_img_chooser.SetItems(params.BG_SHOW_STRINGS)
        if self.show_img_type > self.bg_img_chooser.GetCount():
            self.show_img_type = 0
        self.bg_img_chooser.SetSelection(self.show_img_type)
        self.frame.Bind( wx.EVT_CHOICE, self.OnImgChoice, self.bg_img_chooser)
        # background type
        self.bg_type_chooser = xrc.XRCCTRL(self.frame,"bg_type_input")
        if self.bg_type == 'light_on_dark':
            self.bg_type_chooser.SetSelection( 0 )
        elif self.bg_type == 'dark_on_light':
            self.bg_type_chooser.SetSelection( 1 )
        else:
            self.bg_type_chooser.SetSelection( 2 )
        self.frame.Bind(wx.EVT_CHOICE,self.OnBgTypeChoice, self.bg_type_chooser)
        # minimum bg std
        self.bg_minstd_textinput = xrc.XRCCTRL(self.frame,"bg_min_std_input")
        wxvt.setup_validated_float_callback( self.bg_minstd_textinput,
                                             xrc.XRCID("bg_min_std_input"),
                                             self.OnMinStdTextEnter,
                                             pending_color=params.wxvt_bg )
        self.bg_minstd_textinput.SetValue( str(params.bg_std_min) )
        # maximum bg std
        self.bg_maxstd_textinput = xrc.XRCCTRL(self.frame,"bg_max_std_input")
        wxvt.setup_validated_float_callback( self.bg_maxstd_textinput,
                                             xrc.XRCID("bg_max_std_input"),
                                             self.OnMinStdTextEnter,
                                             pending_color=params.wxvt_bg )
        self.bg_maxstd_textinput.SetValue( str(params.bg_std_max) )
        # normalization type
        self.bg_norm_chooser = xrc.XRCCTRL(self.frame,"bg_normalization_input")
        if self.norm_type == 'homomorphic':
            self.bg_norm_chooser.SetSelection( 2 )
        elif self.norm_type == 'intensity':
            self.bg_norm_chooser.SetSelection( 1 )
        else:
            self.bg_norm_chooser.SetSelection( 0 )
        self.frame.Bind( wx.EVT_CHOICE, self.OnNormChoice, self.bg_norm_chooser)
        # homomorphic filter settings dialog
        self.hf_button = xrc.XRCCTRL(self.frame,"homomorphic_settings")
        self.hf_button.Enable(False)
        self.frame.Bind(wx.EVT_BUTTON,self.OnHFClick,self.hf_button)
        self.hf_window_open = False

        # detect arena button
        self.detect_arena_button = xrc.XRCCTRL(self.frame,"detect_arena_button")
        self.detect_arena_checkbox = xrc.XRCCTRL(self.frame,"detect_arena_checkbox")
        self.detect_arena_button.Enable(params.do_set_circular_arena)
        self.detect_arena_checkbox.SetValue(params.do_set_circular_arena)
        
        self.frame.Bind(wx.EVT_BUTTON,self.OnDetectArenaClick,self.detect_arena_button)
        self.frame.Bind(wx.EVT_CHECKBOX,self.OnDetectArenaCheck,self.detect_arena_checkbox)
        self.detect_arena_window_open = False
        
        # min value for isarena
        self.min_nonarena_textinput = xrc.XRCCTRL(self.frame,"min_nonfore_intensity_input")
        wxvt.setup_validated_float_callback( self.min_nonarena_textinput,
                                             xrc.XRCID("min_nonfore_intensity_input"),
                                             self.OnMinNonArenaTextEnter,
                                             pending_color=params.wxvt_bg )
        self.min_nonarena_textinput.SetValue( str(params.min_nonarena ))
        # min value for isarena
        self.max_nonarena_textinput = xrc.XRCCTRL(self.frame,"max_nonfore_intensity_input")
        wxvt.setup_validated_float_callback( self.max_nonarena_textinput,
                                             xrc.XRCID("max_nonfore_intensity_input"),
                                             self.OnMaxNonArenaTextEnter,
                                             pending_color=params.wxvt_bg )
        self.max_nonarena_textinput.SetValue( str(params.max_nonarena ))

        # morphology
        self.morphology_checkbox = xrc.XRCCTRL(self.frame,"morphology_checkbox")
        self.morphology_checkbox.SetValue(params.do_use_morphology)
        self.frame.Bind(wx.EVT_CHECKBOX,self.OnMorphologyCheck,self.morphology_checkbox)
        self.opening_radius_textinput = xrc.XRCCTRL(self.frame,"opening_radius")
        wxvt.setup_validated_integer_callback( self.opening_radius_textinput,
                                               xrc.XRCID("opening_radius"),
                                               self.OnOpeningRadiusTextEnter,
                                               pending_color=params.wxvt_bg )
        self.opening_radius_textinput.SetValue( '%d'%params.opening_radius )
        self.opening_radius_textinput.Enable(params.do_use_morphology)
        self.closing_radius_textinput = xrc.XRCCTRL(self.frame,"closing_radius")
        self.opening_struct = self.create_morph_struct(params.opening_radius)
        wxvt.setup_validated_integer_callback( self.closing_radius_textinput,
                                               xrc.XRCID("closing_radius"),
                                             self.OnClosingRadiusTextEnter,
                                             pending_color=params.wxvt_bg )
        self.closing_radius_textinput.SetValue( '%d'%params.closing_radius )
        self.closing_radius_textinput.Enable(params.do_use_morphology)
        self.closing_struct = self.create_morph_struct(params.closing_radius)

        # prior model stuff

        # whether to show the panel
        self.expbgfgmodel_panel = xrc.XRCCTRL(self.frame,"expbgfgmodel_panel")
        self.expbgfgmodel_panel.Show(params.use_expbgfgmodel)
        
        # minimum fraction of frames nec. for estimating bg model
        self.min_frac_frames_isback_textinput = xrc.XRCCTRL(self.frame,"min_frac_frames_isback")
        wxvt.setup_validated_float_callback( self.min_frac_frames_isback_textinput,
                                               xrc.XRCID("min_frac_frames_isback"),
                                               self.OnMinFracFramesIsBackTextEnter,
                                               pending_color=params.wxvt_bg )
        
        # fill
        self.expbgfgmodel_fill_chooser = xrc.XRCCTRL(self.frame,"expbgfgmodel_fill")
        self.expbgfgmodel_fill_chooser.SetItems(params.EXPBGFGMODEL_FILL_STRINGS)
        self.expbgfgmodel_fill_chooser.SetSelection(params.EXPBGFGMODEL_FILL_STRINGS.index(params.expbgfgmodel_fill))        
        self.frame.Bind( wx.EVT_CHOICE, self.OnExpBGFGModelFillChoice, self.expbgfgmodel_fill_chooser)
        
        self.fixbg_button = xrc.XRCCTRL(self.frame,"fixbg_button")
        self.frame.Bind(wx.EVT_BUTTON,self.OnFixBgClick,self.fixbg_button)
        self.fixbg_window_open = False

        self.roi_button = xrc.XRCCTRL(self.frame,"roi_button")
        self.frame.Bind(wx.EVT_BUTTON,self.OnROIClick,self.roi_button)
        self.roi_window_open = False

        # make image window
        self.img_panel = xrc.XRCCTRL( self.frame, "panel_img" )
        box = wx.BoxSizer( wx.VERTICAL )
        self.img_panel.SetSizer( box )
        self.img_wind = ZoomableImageCanvas( self.img_panel, -1 )
        box.Add( self.img_wind, 1, wx.EXPAND )
        self.img_panel.SetAutoLayout( True )
        self.img_panel.Layout()

        
    def SetThreshold(self):
        params.n_bg_std_thresh = min( 255., max( params.n_bg_std_thresh, 0. ) )
        params.n_bg_std_thresh_low = min( 255., max( params.n_bg_std_thresh_low, 0. ) )
        params.n_bg_std_thresh_low = min( params.n_bg_std_thresh_low, params.n_bg_std_thresh )

        self.thresh_slider.SetThumbPosition( 255. - self.GetThresholdScrollbar() )
        self.thresh_low_slider.SetThumbPosition( 255. - self.GetThresholdLowScrollbar() )
        self.thresh_textinput.SetValue(str(params.n_bg_std_thresh))
        self.thresh_low_textinput.SetValue(str(params.n_bg_std_thresh_low))


    def GetThresholdScrollbar(self):
        return params.n_bg_std_thresh


    def GetThresholdLowScrollbar(self):
        return params.n_bg_std_thresh_low


    def ReadScrollbar(self):
        return 255. - float( self.thresh_slider.GetThumbPosition() )


    def ReadScrollbarLow(self):
        return 255. - float( self.thresh_low_slider.GetThumbPosition() )


    def OnCalculate( self, evt=None, parent=None, reestimate=True ):
        if params.interactive:
            wx.BeginBusyCursor()
            wx.Yield()
        success = self.est_bg( parent, reestimate )
        if params.interactive:
            wx.EndBusyCursor()
        return success


    def OnShowBG( self, evt ):
        self.frame_slider.Enable( False )
        self.DoSub()

        
    def OnShowThresh( self, evt ):
        self.frame_slider.Enable( True )
        self.DoSub()


    def OnImgChoice( self, evt ):
        new_img_type = self.bg_img_chooser.GetSelection()
        if new_img_type is not wx.NOT_FOUND:
            self.show_img_type = new_img_type
            self.DoSub()


    def OnBgTypeChoice( self, evt ):
        new_bg_type = self.bg_type_chooser.GetSelection()
        if new_bg_type is not wx.NOT_FOUND:
            if new_bg_type == 0:
                self.bg_type = 'light_on_dark'
            elif new_bg_type == 1:
                self.bg_type = 'dark_on_light'
            else:
                self.bg_type = 'other'
            self.DoSub()
            if params.n_bg_std_thresh > 255.:
                params.n_bg_std_thresh = 255.
                self.SetThreshold()
                self.DoSub()


    def OnNormChoice( self, evt ):
        # save threshold settings for old norm type
        setattr( self, '%s_bg_thresh'%self.norm_type, params.n_bg_std_thresh )
        setattr( self, '%s_bg_thresh_low'%self.norm_type, params.n_bg_std_thresh_low )
        
        new_norm_type = self.bg_norm_chooser.GetSelection()

        if new_norm_type is wx.NOT_FOUND:
            return

        elif new_norm_type == 2:
            self.norm_type = 'homomorphic'
            self.dev[:] = self.hfnorm
            self.hf_button.Enable(True)

        elif new_norm_type == 1:
            self.norm_type = 'intensity'
            self.dev[:] = self.center
            self.hf_button.Enable(False)

        else:
            self.norm_type = 'std'
            if self.use_median:
                self.dev[:] = self.mad
                self.dev[self.dev < params.bg_std_min] = params.bg_std_min
                self.dev[self.dev > params.bg_std_max] = params.bg_std_max
            else:
                self.dev[:] = self.std
                self.dev[self.dev < params.bg_std_min] = params.bg_std_min
                self.dev[self.dev > params.bg_std_max] = params.bg_std_max
            self.hf_button.Enable(False)
            
        # get the old maxdfore
        donormalize = False
        if hasattr( self, '%s_bg_thresh'%self.norm_type ):
            params.n_bg_std_thresh = getattr( self, '%s_bg_thresh'%self.norm_type )
            params.n_bg_std_thresh_low = getattr( self, '%s_bg_thresh_low'%self.norm_type )
        elif hasattr(self,'dfore'):
            oldmaxdfore = num.max(self.dfore)
            donormalize = True
        (self.dfore,self.bw) = self.sub_bg(self.show_frame,docomputecc=False)
        if donormalize:
            params.n_bg_std_thresh *= 255./oldmaxdfore
            params.n_bg_std_thresh_low *= 255./oldmaxdfore
        self.SetThreshold()
        self.DoSub()

    def OnHFClick( self, evt ):
        if self.hf_window_open:
            self.hf.frame.Raise()
            return
        self.hf_window_open = True
        self.hf.frame.Show()

    def OnDetectArenaCheck( self, evt ):
        params.do_set_circular_arena = self.detect_arena_checkbox.GetValue()
        self.detect_arena_button.Enable(params.do_set_circular_arena)
        self.UpdateIsArena()
        self.DoSub()

    def OnMorphologyCheck( self, evt ):
        params.do_use_morphology = self.morphology_checkbox.GetValue()
        self.opening_radius_textinput.Enable(params.do_use_morphology)
        self.closing_radius_textinput.Enable(params.do_use_morphology)
        self.DoSub()

    def OnOpeningRadiusTextEnter(self, evt):
        textentered = self.opening_radius_textinput.GetValue()
        # convert to number
        try:
            params.opening_radius = int(textentered)
        except ValueError:
            # if not a number, then set the value to the previous threshold
            self.opening_radius_textinput.SetValue('%d'%params.opening_radius)
            return
        self.opening_struct = self.create_morph_struct(params.opening_radius)
        self.DoSub()

    def OnClosingRadiusTextEnter(self, evt):
        textentered = self.closing_radius_textinput.GetValue()
        # convert to number
        try:
            params.closing_radius = int(textentered)
        except ValueError:
            # if not a number, then set the value to the previous threshold
            self.closing_radius_textinput.SetValue('%d'%params.closing_radius)
            return
        self.closing_struct = self.create_morph_struct(params.closing_radius)
        self.DoSub()
            
    def OnMinFracFramesIsBackTextEnter(self,evt):
        textentered = self.min_frac_frames_isback_textinput.GetValue()
        # convert to number
        try:
            val = float(textentered)
        except ValueError:
            # if not a number, then set the value to the previous threshold
            self.min_frac_frames_isback_textinput.SetValue('%f'%params.min_frac_frames_isback)
            return
        
        # only do something if the number changes
        if val == params.min_frac_frames_isback:
            return

        params.min_frac_frames_isback = val
        # update the model
        success = self.OnCalculate( reestimate=False )
        
        # update the display
        if success:
            self.DoSub()

    def OnExpBGFGModelFillChoice(self,evt):
        params.expbgfgmodel_fill = self.expbgfgmodel_fill_chooser.GetStringSelection()
        success = self.OnCalculate( reestimate=False )
        
        # update the display
        if success:
            self.DoSub()

    def UpdateIsArena(self):
        # update isarena
        self.isarena = num.ones(params.movie_size,num.bool)
        if hasattr(params,'max_nonarena') and hasattr( self, 'center' ):
            self.isarena = self.center > params.max_nonarena
        if hasattr(params,'min_nonarena') and hasattr( self, 'center' ):
            self.isarena = self.isarena & \
                              (self.center < params.min_nonarena)
        if params.do_set_circular_arena and \
               hasattr(params,'arena_center_x') and \
           (params.arena_center_x is not None):
            self.isarena = self.isarena & ( ((params.GRID.X - params.arena_center_x)**2. + (params.GRID.Y - params.arena_center_y)**2) <= params.arena_radius**2. )
        if hasattr(self,'roi'):
            self.isarena = self.isarena & self.roi

    def OnDetectArenaClick( self, evt ):
        if self.detect_arena_window_open:
            self.detect_arena.frame.Raise()
            return
        self.detect_arena_window_open = True
        self.detect_arena = setarena.SetArena(self.frame,self.center)
        self.detect_arena.frame.Bind( wx.EVT_CLOSE, self.OnQuitDetectArena )
        self.detect_arena.frame.Show()

    def OnQuitDetectArena( self, evt ):
        # save parameters found
        [params.arena_center_x,params.arena_center_y,
         params.arena_radius] = self.detect_arena.GetArenaParameters()

        # update isarena
        self.UpdateIsArena()

        # close frame
        self.detect_arena_window_open = False
        self.detect_arena.frame.Destroy()
        delattr(self,'detect_arena')

        # redraw
        self.DoSub()

    def OnFixBgClick( self, evt ):
        if self.fixbg_window_open:
            self.fixbg.frame.Raise()
            return
        self.fixbg_window_open = True
        self.fixbg = fixbg.FixBG(self.frame,self)
        self.fixbg.frame.Bind( wx.EVT_BUTTON, self.OnQuitFixBg, id=xrc.XRCID("quit_button") )
        self.fixbg.frame.Bind( wx.EVT_CLOSE, self.OnQuitFixBg )
        self.fixbg.frame.Show()

    def OnQuitFixBg( self, evt ):
        # close frame
        reallyquit = self.fixbg.CheckSave()

        if not reallyquit:
            return

        self.fixbg_window_open = False
        self.fixbg.frame.Destroy()
        delattr(self,'fixbg')

        # redraw
        self.DoSub()

    def SetCenter(self,newcenter):
        self.center = newcenter.copy()
        if self.use_median:
            self.med = newcenter.copy()
        else:
            self.mean = newcenter.copy()

    def SetDev(self,newdev):
        self.dev = newdev.copy()
        if self.use_median:
            self.mad = newdev.copy()
        else:
            self.std = newdev.copy()

    def SetFixBgPolygons(self,polygons,undo_data):
        self.fixbg_polygons = polygons[:]
        self.undo_data = undo_data[:]

    def OnROIClick( self, evt ):
        if self.roi_window_open:
            self.roigui.frame.Raise()
            return
        self.roi_window_open = True
        self.roigui = roi.ROI(self.frame,self)
        self.roigui.frame.Bind( wx.EVT_BUTTON, self.OnQuitROI, id=xrc.XRCID("quit_button") )
        self.roigui.frame.Bind( wx.EVT_CLOSE, self.OnQuitROI )
        self.roigui.frame.Show()

    def OnQuitROI( self, evt ):
        if not self.roigui.CheckSave():
            return

        self.roi_window_open = False
        self.roigui.frame.Destroy()
        delattr(self,'roigui')

        # redraw
        self.DoSub()

    def SetROI(self,roi):
        self.roi = roi.copy()
        self.UpdateIsArena()

    def OnQuitHF(self, evt ):
        self.hf_window_open = False
        self.hf.frame.Hide()
        self.DoSub()


    def update_thresh_gui_elements( self ):
        """Threshold settings may have been altered outside GUI. Update GUI to current settings."""
        self.thresh_slider.SetThumbPosition( 255. - self.GetThresholdScrollbar() )
        self.thresh_low_slider.SetThumbPosition( 255. - self.GetThresholdLowScrollbar() )
        self.thresh_textinput.SetValue( str(params.n_bg_std_thresh) )
        self.thresh_low_textinput.SetValue( str(params.n_bg_std_thresh_low) )

    
    def OnThreshSlider( self, evt ):
        start_std_thresh = params.n_bg_std_thresh
        start_std_thresh_low = params.n_bg_std_thresh_low

        params.n_bg_std_thresh = self.ReadScrollbar()
        params.n_bg_std_thresh_low = self.ReadScrollbarLow()

        if params.n_bg_std_thresh_low > params.n_bg_std_thresh:
            params.n_bg_std_thresh_low = params.n_bg_std_thresh

        self.update_thresh_gui_elements()

        if start_std_thresh != params.n_bg_std_thresh or \
               start_std_thresh_low != params.n_bg_std_thresh_low:
            self.DoSub()


    def OnThreshTextEnter( self, evt ):
        start_std_thresh = params.n_bg_std_thresh
        start_std_thresh_low = params.n_bg_std_thresh_low

        # get the value entered
        params.n_bg_std_thresh = float(self.thresh_textinput.GetValue())
        params.n_bg_std_thresh_low = float(self.thresh_low_textinput.GetValue())

        # make sure it is in a valid interval
        if params.n_bg_std_thresh < 0: params.n_bg_std_thresh = 0
        if params.n_bg_std_thresh_low < 0: params.n_bg_std_thresh_low = 0
        if params.n_bg_std_thresh_low > params.n_bg_std_thresh:
            params.n_bg_std_thresh_low = params.n_bg_std_thresh

        self.update_thresh_gui_elements()

        if start_std_thresh != params.n_bg_std_thresh or \
               start_std_thresh_low != params.n_bg_std_thresh_low:
            self.DoSub()


    def OnMinStdTextEnter( self, evt ):
        # get the value entered
        textentered = self.bg_minstd_textinput.GetValue()
        maxtextentered = self.bg_maxstd_textinput.GetValue()
        # convert to number
        try:
            numentered = float(textentered)
            maxnumentered = float(maxtextentered)

            # make sure that min <= max
            if numentered > maxnumentered:
                self.bg_minstd_textinput.SetValue(str(params.bg_std_min))
                self.bg_maxstd_textinput.SetValue(str(params.bg_std_max))
                return

            # make sure it is in a valid interval
            if numentered < .001:
                numentered = .001
            if maxnumentered < .001:
                maxnumentered = .001
            params.bg_std_min = numentered
            params.bg_std_max = maxnumentered
            self.bg_minstd_textinput.SetValue(str(params.bg_std_min))
            self.bg_maxstd_textinput.SetValue(str(params.bg_std_max))
            if self.use_median:
                self.dev[:] = self.mad
            else:
                self.dev[:] = self.std
            self.dev[self.dev < params.bg_std_min] = params.bg_std_min
            self.dev[self.dev > params.bg_std_max] = params.bg_std_max
        except ValueError:
            # if not a number, then set the value to the previous threshold
            self.bg_minstd_textinput.SetValue(str(params.bg_std_min))
            self.bg_maxstd_textinput.SetValue(str(params.bg_std_max))
            return
        
        self.DoSub()
        if params.n_bg_std_thresh > 255.:
            params.n_bg_std_thresh = 255.
            self.SetThreshold()
            self.DoSub()

    def OnMinNonArenaTextEnter( self, evt ):
        # get the value entered
        textentered = self.min_nonarena_textinput.GetValue()
        # convert to number
        try:
            params.min_nonarena = float(textentered)
        except ValueError:
            # if not a number, then set the value to the previous threshold
            self.min_nonarena_textinput.SetValue(str(params.min_nonarena))
            return
        self.UpdateIsArena()
        self.DoSub()

    def OnMaxNonArenaTextEnter( self, evt ):
        # get the value entered
        textentered = self.max_nonarena_textinput.GetValue()
        # convert to number
        try:
            params.max_nonarena = float(textentered)
        except ValueError:
            # if not a number, then set the value to the previous threshold
            self.max_nonarena_textinput.SetValue(str(params.max_nonarena))
            return
        self.UpdateIsArena()
        self.DoSub()


    def OnFrameSlider( self, evt ):
        self.show_frame = self.frame_slider.GetThumbPosition()
        self.frame_text.SetLabel( "frame %d"%(self.show_frame) )
        self.DoSub()


    def get_sub_image( self, sub_type, framenumber ):
        """Do background subtraction and return a particular image type."""
        wx.BeginBusyCursor()
        try: wx.Yield()
        except: pass # sometimes complains about recursive Yield()
        
        # do background subtraction if necessary
        if sub_type in [params.SHOW_DISTANCE,params.SHOW_THRESH,
                        params.SHOW_CC,params.SHOW_ELLIPSES]:
            (dfore,bw,cc,ncc) = self.sub_bg( framenumber )
        else:
            if hasattr( self, 'dfore' ):
                dfore = self.dfore
                bw = self.bw
                cc = self.cc
                ncc = self.ncc
            else:
                dfore = None
                bw = None
                cc = None
                ncc = None

        line_segs = []
        line_clrs = []
        img_format = None

        # format image in "subtraction type"
        if sub_type == params.SHOW_BACKGROUND:
            img_8 = imagesk.double2mono8(self.center,donormalize=False)
            img_format = 'MONO8'
            preview_range = (0,255)
        elif sub_type == params.SHOW_DISTANCE:
            img_8 = imagesk.double2mono8(dfore)
            img_format = 'MONO8'
            preview_range = (dfore.min(), dfore.max())
        elif sub_type == params.SHOW_THRESH:
            img_8 = imagesk.double2mono8(bw.astype(float))
            img_format = 'MONO8'
            preview_range = (0,1)
        elif sub_type == params.SHOW_NONFORE:
            isnotarena = (self.isarena == False)
            img_8 = imagesk.double2mono8(isnotarena.astype(float))
            img_format = 'MONO8'
            preview_range = (0,1)
        elif sub_type == params.SHOW_DEV:
            mu = num.mean(self.dev)
            sig = num.std(self.dev)
            if sig == 0:
                img_8 = imagesk.double2mono8(self.dev)
                n1 = mu
                n2 = mu
            else:
                n1 = max(0,mu - 3.*sig)
                n2 = mu + 3.*sig
                img_8 = imagesk.double2mono8(self.dev.clip(n1,n2))
            img_format = 'MONO8'
            preview_range = (n1,n2)
        elif sub_type == params.SHOW_CC:
            img_8,clim = colormap_image(cc)
            img_format = 'RGB8'
            preview_range = clim
        elif sub_type == params.SHOW_ELLIPSES:
            # find ellipse observations
            obs = find_ellipses(dfore,cc,ncc,False)
            im, stamp = params.movie.get_frame( int(framenumber) )
            img_8 = imagesk.double2mono8(im,donormalize=False)
            plot_linesegs = draw_ellipses(obs)
            (linesegs,linecolors) = \
                imagesk.separate_linesegs_colors(plot_linesegs)
            img_8 = imagesk.double2mono8(im,donormalize=False)
            img_format = 'MONO8'
            preview_range = (0,255)
            line_segs.extend( linesegs )
            line_clrs.extend( linecolors )
        elif sub_type in params.SHOW_EXPBGFGMODEL: 
            # check for expbgfgmodel
            if not params.use_expbgfgmodel or not hasattr(self,'expbgfgmodel') or \
            self.expbgfgmodel is None:
                resp = wx.MessageBox("No prior model loaded.","No prior model loaded",wx.OK)
            else:
                if sub_type == params.SHOW_EXPBGFGMODEL_LLR:
                    # read the current image, classify pixels
                    im, stamp = params.movie.get_frame( int(framenumber) )
                    llr = self.expbgfgmodel_llr(im)
                    img_8,clim = colormap_image(llr)
                    img_format = 'RGB'
                    preview_range = clim
                elif sub_type == params.SHOW_EXPBGFGMODEL_ISBACK:
                    im, stamp = params.movie.get_frame( int(framenumber) )
                    isback = self.thresh_expbgfgmodel_llr(im)
                    img_8 = imagesk.double2mono8(isback.astype(float))
                    img_format = 'MONO8'
                    preview_range = (0,1)
                elif sub_type == params.SHOW_EXPBGFGMODEL_BGMU:
                    img_8 = imagesk.double2mono8(self.expbgfgmodel.bg_mu,donormalize=False)
                    img_format = 'MONO8'
                    preview_range = (0,255)
                elif sub_type == params.SHOW_EXPBGFGMODEL_FGMU:
                    img_8 = imagesk.double2mono8(self.expbgfgmodel.fg_mu,donormalize=False)
                    img_format = 'MONO8'
                    preview_range = (0,255)
                elif sub_type == params.SHOW_EXPBGFGMODEL_BGSIGMA:
                    mu = num.mean(self.expbgfgmodel.bg_sigma)
                    sig = num.std(self.expbgfgmodel.bg_sigma)
                    if sig == 0:
                        n1 = mu
                        n2 = mu
                        img_8 = imagesk.double2mono8(self.expbgfgmodel.bg_sigma)
                    else:
                        n1 = max(0,mu - 3.*sig)
                        n2 = mu + 3.*sig
                        img_8 = imagesk.double2mono8(self.expbgfgmodel.bg_sigma.clip(n1,n2))
                    img_format = 'MONO8'
                    preview_range = (n1,n2)
                elif sub_type == params.SHOW_EXPBGFGMODEL_FGSIGMA:
                    mu = num.mean(self.expbgfgmodel.fg_sigma)
                    sig = num.std(self.expbgfgmodel.fg_sigma)
                    if sig == 0:
                        img_8 = imagesk.double2mono8(self.expbgfgmodel.fg_sigma)
                        n1 = mu
                        n2 = mu
                    else:
                        n1 = max(0,mu - 3.*sig)
                        n2 = mu + 3.*sig
                        img_8 = imagesk.double2mono8(self.expbgfgmodel.fg_sigma.clip(n1,n2))
                    img_format = 'MONO8'
                    preview_range = (n1,n2)
                elif sub_type == params.SHOW_EXPBGFGMODEL_FRACFRAMESISBACK:
                    if not hasattr(self,'fracframesisback') or self.fracframesisback is None:
                        resp = wx.MessageBox("fracframesisback not yet computed","fracframesisback Not Computed",wx.OK)
                        return
                    img_8,clim = colormap_image(self.fracframesisback)
                    img_format = 'RGB8'
                    preview_range = clim
                elif sub_type == params.SHOW_EXPBGFGMODEL_MISSINGDATA:
                    if not hasattr(self,'fracframesisback') or self.fracframesisback is None:
                        resp = wx.MessageBox("fracframesisback not yet computed","fracframesisback Not Computed",wx.OK)
                        return
                    missingdata = self.fracframesisback <= params.min_frac_frames_isback
                    img_8 = imagesk.double2mono8(missingdata.astype(float))
                    img_format = 'MONO8'
                    preview_range = (0,1)

        wx.EndBusyCursor()

        return img_8, img_format, line_segs, line_clrs, dfore, bw, cc, ncc, preview_range
    

    def DoSub( self ):
        """Do background subtraction and draw to screen."""

        img_8, img_format, line_segs, line_clrs, \
        self.dfore, self.bw, self.cc, self.ncc, preview_range \
          = self.get_sub_image( self.show_img_type, self.show_frame )

        self.img_wind.update_image_and_drawings( 'bg_img', img_8,
                                                 format=img_format,
                                                 linesegs=line_segs,
                                                 lineseg_colors=line_clrs )

        self.SetPreviewRange( preview_range[0], preview_range[1] )

        if self.dosub_callback is not None:
            self.dosub_callback()


    def redraw( self ):
        self.img_wind.redraw()


    def SetPreviewRange(self,l,u):
        self.range_text.SetLabel("Range: [" + str(l) + "," + str(u) + "]")


class BgSettingsDialog:

    def __init__(self,parent,bg):
        #self.const = bg.const
        #const.n_frames = bg.n_frames
        self.bg = bg
        
        # copy some settings
        #self.use_median = bg.use_median
        #self.n_bg_frames = bg.n_bg_frames
        #self.bg_firstframe = bg.bg_firstframe
        #self.bg_lastframe = bg.bg_lastframe

        # clear buffer
        self.bg.initialize_buffer()
        rsrc = xrc.XmlResource( SETTINGS_RSRC_FILE )
        self.frame = rsrc.LoadFrame(parent, "bg_settings")
        self.algorithm = xrc.XRCCTRL( self.frame, "algorithm" )
        self.nframes = xrc.XRCCTRL( self.frame, "nframes" )
        self.firstframe_box = xrc.XRCCTRL( self.frame, "bg_firstframe" )
        self.lastframe_box = xrc.XRCCTRL( self.frame, "bg_lastframe" )
        self.expbgfgmodel_checkbox = xrc.XRCCTRL( self.frame, "expbgfgmodel_checkbox")
        self.expbgfgmodel_text = xrc.XRCCTRL( self.frame, "expbgfgmodel_text")
        self.expbgfgmodel_button = xrc.XRCCTRL( self.frame, "expbgfgmodel_button")
        self.expbgfgmodel_llr_thresh = xrc.XRCCTRL(self.frame, "llr_thresh")
        self.expbgfgmodel_llr_thresh_low = xrc.XRCCTRL(self.frame, "llr_thresh_low")
        self.calculate = xrc.XRCCTRL( self.frame, "calculate_button" )
        if self.bg.use_median:
            self.algorithm.SetSelection(params.ALGORITHM_MEDIAN)
        else:
            self.algorithm.SetSelection(params.ALGORITHM_MEAN)
        self.nframes.SetValue( str(self.bg.n_bg_frames))
        wxvt.setup_validated_integer_callback( self.nframes,
                                               xrc.XRCID("nframes"),
                                               self.OnTextValidatedNFrames,
                                               pending_color=params.wxvt_bg )
        self.firstframe_box.SetValue( str(self.bg.bg_firstframe))
        wxvt.setup_validated_integer_callback( self.firstframe_box,
                                               xrc.XRCID("bg_firstframe"),
                                               self.OnTextValidatedFirstframe,
                                               pending_color=params.wxvt_bg )
        self.lastframe_box.SetValue( str(self.bg.bg_lastframe))
        wxvt.setup_validated_integer_callback( self.lastframe_box,
                                               xrc.XRCID("bg_lastframe"),
                                               self.OnTextValidatedLastframe,
                                               pending_color=params.wxvt_bg )
        self.frame.Bind( wx.EVT_CHOICE, self.OnAlgorithmChoice, self.algorithm)
        self.frame.Bind( wx.EVT_BUTTON, self.OnCalculate, self.calculate )

        self.expbgfgmodel_text.SetEditable(False)
        self.frame.Bind(wx.EVT_BUTTON, self.OnChooseExpBGFGModelFileName, self.expbgfgmodel_button)
        self.frame.Bind(wx.EVT_CHECKBOX, self.OnCheckExpBGFGModel, self.expbgfgmodel_checkbox)
        
        wxvt.setup_validated_integer_callback( self.expbgfgmodel_llr_thresh,
                                               xrc.XRCID("llr_thresh"),
                                               self.OnTextValidatedLLRThresh,
                                               pending_color=params.wxvt_bg )
        wxvt.setup_validated_integer_callback( self.expbgfgmodel_llr_thresh_low,
                                               xrc.XRCID("llr_thresh_low"),
                                               self.OnTextValidatedLLRThresh,
                                               pending_color=params.wxvt_bg )
        
        self.UpdateExpBGFGModelControls()
        self.frame.Show()
        
    def UpdateExpBGFGModelControls(self):
        if params.expbgfgmodel_filename is None:
            self.expbgfgmodel_text.SetValue('None')
        else:
            self.expbgfgmodel_text.SetValue(params.expbgfgmodel_filename)

        if not params.use_expbgfgmodel:
            self.expbgfgmodel_checkbox.SetValue(False)
            self.expbgfgmodel_button.Enable(False)
        else:
            self.expbgfgmodel_checkbox.SetValue(True)
            self.expbgfgmodel_button.Enable(True)
            
        self.expbgfgmodel_llr_thresh.SetValue(str(params.expbgfgmodel_llr_thresh))
        self.expbgfgmodel_llr_thresh_low.SetValue(str(params.expbgfgmodel_llr_thresh_low))
            
    def OnCalculate( self, evt=None, reestimate=True ):
        if params.interactive:
            wx.BeginBusyCursor()
            wx.Yield()
        success = self.bg.est_bg( self.frame, reestimate )
        if params.interactive:
            wx.EndBusyCursor()
        return success


    def OnTextValidatedNFrames(self,evt):
        tmp = int(self.nframes.GetValue())
        if tmp > 1:
            self.bg.n_bg_frames = tmp
            if self.bg.n_bg_frames > params.n_frames:
                self.bg.n_bg_frames = params.n_frames
            elif self.bg.n_bg_frames < 1:
                self.bg.n_bg_frames = 1

            if params.n_frames - self.bg.n_bg_frames < self.bg.bg_firstframe:
                self.bg.bg_firstframe = params.n_frames - self.bg.n_bg_frames
                self.firstframe_box.SetValue( str( self.bg.bg_firstframe ) )
                
        self.nframes.SetValue(str(self.bg.n_bg_frames))

    def OnTextValidatedFirstframe(self,evt):
        tmp0 = int(self.firstframe_box.GetValue())
        tmp = tmp0
        tmp = max(tmp,0)
        tmp = min(tmp,self.bg.bg_lastframe)
        tmp = min(tmp,params.n_frames - self.bg.n_bg_frames)
        self.bg.bg_firstframe = tmp
        if not tmp == tmp0:
            self.firstframe_box.SetValue(str(self.bg.bg_firstframe))

    def OnTextValidatedLastframe(self,evt):
        tmp0 = int(self.lastframe_box.GetValue())
        tmp = tmp0
        tmp = max(tmp,self.bg.bg_firstframe + self.bg.n_bg_frames - 1)
        self.bg.bg_lastframe = tmp
        if not tmp == tmp0:
            self.lastframe_box.SetValue(str(self.bg.bg_lastframe))

    def OnTextValidatedLLRThresh(self,evt):
        try:
            tmp = float(self.expbgfgmodel_llr_thresh.GetValue())
            tmp_low = float(self.expbgfgmodel_llr_thresh_low.GetValue())
        except:
            self.expbgfgmodel_llr_thresh.SetValue(str(params.expbgfgmodel_llr_thresh))
            self.expbgfgmodel_llr_thresh_low.SetValue(str(params.expbgfgmodel_llr_thresh_low))
            return
        if tmp_low > tmp:
            tmp_low = tmp

        params.expbgfgmodel_llr_thresh = tmp
        params.expbgfgmodel_llr_thresh_low = tmp_low

    def OnAlgorithmChoice(self,evt):
        new_alg_type = self.algorithm.GetSelection()
        if new_alg_type is not wx.NOT_FOUND:
            if new_alg_type == params.ALGORITHM_MEDIAN:
                self.bg.use_median = True
            else:
                self.bg.use_median = False
                
    def OnChooseExpBGFGModelFileName(self,evt=-1):
        success = False
        if params.expbgfgmodel_filename is None:
            dir = ''
        else:
            dir = os.path.dirname(params.expbgfgmodel_filename)
        
        dlg = wx.FileDialog( self.frame, "Select global back/foreground model", dir, "", "Pickled files (*.pickle)|*.pickle|Any (*)|*", wx.OPEN )
        didchoose = dlg.ShowModal() == wx.ID_OK

        if didchoose:
            filename = dlg.GetFilename()
            dir = dlg.GetDirectory()
            filename = os.path.join( dir, filename )
            success = self.bg.setExpBGFGModel(filename)
            if success:
                params.expbgfgmodel_filename = filename
                self.UpdateExpBGFGModelControls()

        dlg.Destroy()

        return success

    def OnCheckExpBGFGModel(self,evt=-1):
        params.use_expbgfgmodel = self.expbgfgmodel_checkbox.IsChecked()
        if params.use_expbgfgmodel and params.expbgfgmodel_filename is None:
            success = self.OnChooseExpBGFGModelFileName()
            if not success:
                self.expbgfgmodel_checkbox.SetValue(False)
                params.use_expbgfgmodel = False
                return
        self.UpdateExpBGFGModelControls()
        

if DEBUG:
    def save_image( filename, img ):
        """Saves an image as a MATLAB array."""
        scipy.io.savemat( filename + '.mat', {filename: img})
        print "saved", filename, ".mat"

    def read_image( filename ):
        """Reads an image from a mat-file."""
        new_dict = scipy.io.loadmat( filename )
        print "loaded", filename, ".mat"
        return new_dict[filename]

    def write_img_text( img, filename ):
        fp = open( filename, "w" )
        for r in img:
            for c in r:
                fp.write( "%f\t"%c )
            fp.write( "\n" )
        fp.close()


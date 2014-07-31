USEGL = False
import wx
import params
import ellipsesk as ell
from ellipses_draw import draw_ellipses
from wx import xrc
if USEGL:
    import motmot.wxglvideo.simple_overlay as wxvideo
else:
    import motmot.wxvideo.wxvideo as wxvideo
import motmot.wxvalidatedtext.wxvalidatedtext as wxvt # part of Motmot
import numpy as num
#from scipy.misc.pilutil import imresize
import imagesk
import copy
from matchidentities import cvpred
import sys
from version import DEBUG_TRACKINGSETTINGS

import os
import codedir
RSRC_FILE = os.path.join(codedir.codedir,'xrc','tracking_settings.xrc')

SHOW_UNFILTERED_OBSERVATIONS = 0
SHOW_FILTERED_OBSERVATIONS = 1
SHOW_SMALL_OBSERVATIONS = 2
SHOW_LARGE_OBSERVATIONS = 3
SHOW_DELETED_OBSERVATIONS = 4
SHOW_SPLIT_OBSERVATIONS = 5
SHOW_MERGED_OBSERVATIONS = 6
SHOW_LOWERED_OBSERVATIONS = 7
SHOW_MAXJUMP = 8
SHOW_MOTIONMODEL = 9

class StoredObservations:

    def __init__(self,obs,frame,ellsmall=None,elllarge=None,didlowerthresh=None,
                 didmerge=None,diddelete=None,didsplit=None):

        self.obs = obs
        self.frame = frame
        #self.params = params.params.copy()
        #self.params = None
        self.isvalid = True
        self.ellsmall = ellsmall
        self.elllarge = elllarge
        self.didlowerthresh = didlowerthresh
        self.didmerge = didmerge
        self.diddelete = diddelete
        self.didsplit = didsplit


    def SetInvalid(self):
      self.isvalid = False

    def issame(self,frame):
        return (self.isvalid and (self.frame == frame))

    def __str__(self):
      s = ''
      if hasattr(self,'isvalid') and self.isvalid is not None:
        s += 'isvalid = ' + str(self.isvalid) + '\n'
      if hasattr(self,'frame') and self.frame is not None:
        s += 'frame = ' + str(self.frame) + '\n'
      if hasattr(self,'obs') and self.obs is not None:
        s += 'obs = ' + str(self.obs) + ', len = ' + str(len(self.obs)) + '\n'
      if hasattr(self,'ellsmall') and self.ellsmall is not None:
        s += 'ellsmall = ' + str(self.ellsmall) + '\n'
      if hasattr(self,'elllarge') and self.elllarge is not None:
        s += 'elllarge = ' + str(self.elllarge) + '\n'
      if hasattr(self,'didlowerthresh') and self.didlowerthresh is not None:
        s += 'didlowerthresh = ' + str(self.didlowerthresh) + '\n'
      if hasattr(self,'didmerge') and self.didmerge is not None:
        s += 'didmerge = ' + str(self.didmerge) + '\n'
      if hasattr(self,'diddelete') and self.diddelete is not None:
        s += 'diddelete = ' + str(self.diddelete) + '\n'
      if hasattr(self,'didsplit') and self.didsplit is not None:
        s += 'didsplit = ' + str(self.didsplit) + '\n'

      return s

class TrackingSettings:

    def __init__(self,parent,bg_imgs,currframe):

        self.parent = parent
        # background model
        self.bg_imgs = bg_imgs
        self.show_frame = currframe
        self.bg_img_frame = -1
        # zoom mode
        self.zoomin = False
        self.zoomout = False
        self.info = False
        self.zoomaxes = [0,params.params.movie.get_width()-1,0,params.params.movie.get_height()-1]
        self.zoomfactor = 1

        self.shape_uptodate = False
        self.automatic_minshape = params.ShapeParams()
        self.automatic_maxshape = params.ShapeParams()
        self.automatic_meanshape = params.ShapeParams()

        rsrc = xrc.XmlResource( RSRC_FILE )
        self.frame = rsrc.LoadFrame(parent,"trackingframe")

        self.InitControlHandles()
        self.InitializeValues()
        self.BindCallbacks()
        self.OnResize()
        self.ShowImage()

    def RegisterParamChange(self):
      if hasattr(self,'obs_filtered'):
        self.obs_filtered.SetInvalid()
      if hasattr(self,'obs_unfiltered'):
        self.obs_unfiltered.SetInvalid()
      if hasattr(self,'obs_prev'):
        self.obs_prev.SetInvalid()

    def InitControlHandles(self):

        #self.min_ntargets_input = self.control('min_ntarets')
        #self.max_ntargets_input = self.control('max_ntargets')
        self.automatic_shape_input = self.control('automatic_bounds')
        self.automatic_panel = self.control('automatic_panel')
        self.nstd_shape_input = self.control('nstd_shape')
        self.nframes_shape_input = self.control('nframes_shape')
        self.compute_shape_input = self.control('compute_shape')
        self.automatic_shape_text = self.control('automatic_shape_text')
        self.manual_shape_input = self.control('manual_bounds')
        self.manual_panel = self.control('manual_panel')
        self.min_area_input = self.control('min_area')
        self.mean_area_input = self.control('mean_area')
        self.max_area_input = self.control('max_area')
        self.min_major_input = self.control('min_major')
        self.mean_major_input = self.control('mean_major')
        self.max_major_input = self.control('max_major')
        self.min_minor_input = self.control('min_minor')
        self.mean_minor_input = self.control('mean_minor')
        self.max_minor_input = self.control('max_minor')
        self.min_ecc_input = self.control('min_ecc')
        self.mean_ecc_input = self.control('mean_ecc')
        self.max_ecc_input = self.control('max_ecc')
        self.angle_weight_input = self.control('angle_weight')
        self.max_jump_input = self.control('max_jump')
		# KB 20120109: allow jumps of distance max_jump_split if an observation is the result of 
		# splitting a connected component
        self.max_jump_split_input = self.control('max_jump_split')
        self.min_jump_input = self.control('min_jump')
        self.center_dampen_input = self.control('center_dampen')
        self.angle_dampen_input = self.control('angle_dampen')
        self.max_area_delete_input = self.control('max_area_delete')
        self.min_area_ignore_input = self.control('min_area_ignore')
        self.max_penalty_merge_input = self.control('max_penalty_merge')
        self.lower_thresh_input = self.control('lower_thresh')
        self.maxclustersperblob_input = self.control('maxclustersperblob')
        self.max_blobs_input = self.control( 'max_blobs_detect' )
        self.done_input = self.control('done')
        self.img_panel = self.control('img_panel')
        self.frame_scrollbar = self.control('frame_scrollbar')
        self.frame_number_text = self.control('frame_number')
        self.show_img_input = self.control('show_img')
        self.toolbar = xrc.XRCCTRL(self.frame,'toolbar')
        if self.toolbar is None:
            self.toolbar = self.frame.GetToolBar()
        self.zoomin_id = xrc.XRCID('zoomin')
        self.zoomout_id = xrc.XRCID('zoomout')
        self.info_id = xrc.XRCID('moreinfo')
        self.info_text = xrc.XRCCTRL( self.toolbar, "text_obsinfo" )
##        if 'win' in sys.platform:
##            self.toolbar.AddSeparator()
##            self.info_text = wx.TextCtrl(self.toolbar, -1, 'Observation Info', pos=(80,0),size=(300,20),style=wx.TE_READONLY|wx.TE_CENTRE)
##            self.toolbar.AddControl(self.info_text)
##        else:
##            self.info_text = wx.TextCtrl(self.toolbar, -1, 'Observation Info', size=(300,20),style=wx.TE_READONLY|wx.TE_CENTRE)
        self.info_text.SetValue('Observation Info')
        #self.info_text.SetEditable(False)
        self.hindsight_panel = self.control('hindsight_panel')
        self.splitdetection_panel = self.control('splitdetection_panel')
        self.mergeddetection_panel = self.control('mergeddetection_panel')
        self.spuriousdetection_panel = self.control('spuriousdetection_panel')
        self.lostdetection_panel = self.control('lostdetection_panel')
        self.do_fix_split_input = self.control('do_fix_split')
        self.do_fix_merged_input = self.control('do_fix_merged')
        self.do_fix_spurious_input = self.control('do_fix_spurious')
        self.do_fix_lost_input = self.control('do_fix_lost')
        self.splitdetection_length_input = self.control('splitdetection_length')
        self.splitdetection_cost_input = self.control('splitdetection_distance')
        self.mergeddetection_length_input = self.control('mergeddetection_length')
        self.mergeddetection_distance_input = self.control('mergeddetection_distance')
        self.spuriousdetection_length_input = self.control('spuriousdetection_length')
        self.lostdetection_length_input = self.control('lostdetection_length')

        box = wx.BoxSizer( wx.VERTICAL )
        self.img_panel.SetSizer( box )
        self.img_wind = wxvideo.DynamicImageCanvas( self.img_panel, -1 )
        self.img_wind.set_resize(True)
        box.Add( self.img_wind, 1, wx.EXPAND )
        self.img_panel.SetAutoLayout( True )
        self.img_panel.Layout()

    def InitializeValues(self):
        #self.min_ntargets_input.SetValue(str(params.params.min_ntargets))
        #self.max_ntargets_input.SetValue(str(params.params.max_ntargets))
        self.automatic_shape_input.SetValue(True)
        self.manual_shape_input.SetValue(False)
        self.nstd_shape_input.SetValue(str(params.params.n_std_thresh))
        self.nframes_shape_input.SetValue(str(params.params.n_frames_size))
        self.min_area_input.SetValue(str(params.params.minshape.area))
        self.min_major_input.SetValue(str(params.params.minshape.major))
        self.min_minor_input.SetValue(str(params.params.minshape.minor))
        self.min_ecc_input.SetValue(str(params.params.minshape.ecc))
        self.mean_area_input.SetValue(str(params.params.meanshape.area))
        self.mean_major_input.SetValue(str(params.params.meanshape.major))
        self.mean_minor_input.SetValue(str(params.params.meanshape.minor))
        self.mean_ecc_input.SetValue(str(params.params.meanshape.ecc))
        self.max_area_input.SetValue(str(params.params.maxshape.area))
        self.max_major_input.SetValue(str(params.params.maxshape.major))
        self.max_minor_input.SetValue(str(params.params.maxshape.minor))
        self.max_ecc_input.SetValue(str(params.params.maxshape.ecc))
        self.angle_dampen_input.SetValue(str(params.params.ang_dist_wt))
        self.max_area_delete_input.SetValue(str(params.params.maxareadelete))
        self.min_area_ignore_input.SetValue(str(params.params.minareaignore))
        self.max_penalty_merge_input.SetValue(str(params.params.maxpenaltymerge))
        self.max_jump_input.SetValue(str(params.params.max_jump))
		# KB 20120109: allow jumps of distance max_jump_split if an observation is the result of 
		# splitting a connected component
        self.max_jump_split_input.SetValue(str(params.params.max_jump_split))
        self.min_jump_input.SetValue(str(params.params.min_jump))
        self.angle_weight_input.SetValue(str(params.params.ang_dist_wt))
        self.center_dampen_input.SetValue(str(params.params.dampen))
        self.angle_dampen_input.SetValue(str(params.params.angle_dampen))
        self.lower_thresh_input.SetValue(str(params.params.minbackthresh))
        self.maxclustersperblob_input.SetValue(str(params.params.maxclustersperblob))
        self.max_blobs_input.SetValue( str( params.params.max_n_clusters ) )
        self.frame_scrollbar.SetThumbPosition(self.show_frame)
        self.frame_scrollbar.SetScrollbar(self.show_frame,0,params.params.n_frames-1,30)
        self.img_chosen = SHOW_UNFILTERED_OBSERVATIONS
        self.show_img_input.SetSelection(self.img_chosen)
        self.toolbar.SetToggle(self.zoomin,self.zoomin_id)
        self.toolbar.SetToggle(self.zoomout,self.zoomout_id)
        self.toolbar.SetToggle(self.info,self.info_id)

        self.do_fix_split_input.SetValue(params.params.do_fix_split)
        self.do_fix_merged_input.SetValue(params.params.do_fix_merged)
        self.do_fix_spurious_input.SetValue(params.params.do_fix_spurious)
        self.do_fix_lost_input.SetValue(params.params.do_fix_lost)
        self.splitdetection_panel.Enable(params.params.do_fix_split)
        self.mergeddetection_panel.Enable(params.params.do_fix_merged)
        self.spuriousdetection_panel.Enable(params.params.do_fix_spurious)
        self.lostdetection_panel.Enable(params.params.do_fix_lost)
        
        self.splitdetection_length_input.SetValue(str(params.params.splitdetection_length))
        self.splitdetection_cost_input.SetValue('%.2f'%params.params.splitdetection_cost)
        self.mergeddetection_length_input.SetValue(str(params.params.mergeddetection_length))
        self.mergeddetection_distance_input.SetValue('%.2f'%params.params.mergeddetection_distance)
        self.spuriousdetection_length_input.SetValue(str(params.params.spuriousdetection_length))
        self.lostdetection_length_input.SetValue(str(params.params.lostdetection_length))

        
    def BindCallbacks(self):

        # number of targets
        #self.bindctrl(('min_ntargets','max_ntargets'),('int','int'),self.SetNTargets)

        # shape
        
        # automatic computation of bounds on shape
        self.frame.Bind(wx.EVT_RADIOBUTTON,self.OnAutomatic,self.automatic_shape_input)
        self.frame.Bind(wx.EVT_RADIOBUTTON,self.OnAutomatic,self.manual_shape_input)

        # automatic shape
        self.bindctrl(('nstd_shape','nframes_shape'),('float','float'),self.SetAutomatic)

        # compute shape now
        self.frame.Bind(wx.EVT_BUTTON,self.ComputeShapeNow,self.compute_shape_input)

        # manual shape
        self.bindctrl(('min_area','mean_area','max_area',
                       'min_major','mean_major','max_major',
                       'min_minor','mean_minor','max_minor',
                       'min_ecc','mean_ecc','max_ecc'),
                      ('float','float','float',
                       'float','float','float',
                       'float','float','float',
                       'float','float','float'),
                      self.SetManual)

        # motion

		# KB 20120109: allow jumps of distance max_jump_split if an observation is the result of 
		# splitting a connected component
        self.bindctrl(('angle_weight','max_jump','max_jump_split','min_jump','center_dampen','angle_dampen'),
                      ('float','float','float','float','float','float'),
                      self.SetMotion)

        # observation

        self.bindctrl(('max_area_delete','min_area_ignore','max_penalty_merge','lower_thresh','maxclustersperblob', 'max_blobs_detect'),
                      ('float','float','float','float','int','int'),self.SetObservation)


        # hindsight
        self.frame.Bind(wx.EVT_CHECKBOX,self.OnSplit,self.do_fix_split_input)
        self.frame.Bind(wx.EVT_CHECKBOX,self.OnMerged,self.do_fix_merged_input)
        self.frame.Bind(wx.EVT_CHECKBOX,self.OnSpurious,self.do_fix_spurious_input)
        self.frame.Bind(wx.EVT_CHECKBOX,self.OnLost,self.do_fix_lost_input)
        self.bindctrl(('splitdetection_length','splitdetection_distance'),
                      ('int','float'),self.SetSplit)
        self.bindctrl(('mergeddetection_length','mergeddetection_distance'),
                      ('int','float'),self.SetMerged)
        self.bindctrl(('spuriousdetection_length',),('int',),self.SetSpurious)
        self.bindctrl(('lostdetection_length',),('int',),self.SetLost)
        
        # frame scrollbar
        self.frame.Bind(wx.EVT_SCROLL,self.FrameScrollbarMoved,self.frame_scrollbar)

        # img choice 
	self.frame.Bind(wx.EVT_CHOICE,self.ImageChosen,self.show_img_input)

        # resize
        self.frame.Bind( wx.EVT_SIZE, self.OnResize )
        #self.frame.Bind( wx.EVT_MOVE, self.OnResizeBG )

        # toolbar
        self.frame.Bind(wx.EVT_TOOL, self.ZoominToggle, id=self.zoomin_id)
        self.frame.Bind(wx.EVT_TOOL, self.ZoomoutToggle, id=self.zoomout_id)
        self.frame.Bind(wx.EVT_TOOL, self.InfoToggle, id=self.info_id)

        # mouse click
        # get a pointer to the "trackset" child
        self.img_size = [params.params.movie.get_height(),params.params.movie.get_width()]
        img = num.zeros((self.img_size[0],self.img_size[1]),dtype=num.uint8)
        self.img_wind.update_image_and_drawings("trackset",
                                                img,
                                                format="MONO8")
        self.img_wind_child = self.img_wind.get_child_canvas("trackset")
        self.img_wind_child.Bind(wx.EVT_LEFT_DOWN,self.MouseClick)
        self.img_wind_child.Bind(wx.EVT_LEFT_DCLICK,self.MouseDoubleClick)

    def control(self,ctrlname):
        return xrc.XRCCTRL(self.frame,ctrlname)

    def bindctrl(self,ctrlnames,type,validatef):
        for i,v in enumerate(ctrlnames):
            if type[i] == 'int':
                wxvt.setup_validated_integer_callback(self.control(v),
                                                      xrc.XRCID(v),
                                                      validatef,
                                                      pending_color=params.params.wxvt_bg)
            else:
                wxvt.setup_validated_float_callback(self.control(v),
                                                    xrc.XRCID(v),
                                                    validatef,
                                                    pending_color=params.params.wxvt_bg)
    #def SetNTargets(self,evt):
    #    
    #    n1 = int(self.min_ntargets_input.GetValue())
    #    n2 = int(self.max_ntargets_input.GetValue())
    #
    #    if n1 <= n2:
    #        params.params.min_ntargets = n1
    #        params.params.max_ntargets = n2
    #    else:
    #        self.min_ntargets_input.SetValue(str(params.params.min_ntargets))
    #        self.max_ntargets_input.SetValue(str(params.params.max_ntargets))
    #
    #    self.ShowImage()

    def OnAutomatic(self,evt):

        isautomatic = self.automatic_shape_input.GetValue()
        if isautomatic == self.manual_shape_input.GetValue():
            print 'error: isautomatic == ismanual'
        if isautomatic:
            self.automatic_panel.Enable(True)
            self.manual_panel.Enable(False)
            if not self.shape_uptodate:
                self.automatic_shape_text.SetLabel('Bounds on shape not up to date.')
            else:
                self.automatic_shape_text.SetLabel('')
                params.params.minshape = self.automatic_minshape.copy()
                params.params.maxshape = self.automatic_maxshape.copy()
                params.params.meanshape = self.automatic_meanshape.copy()
                self.PrintShape()
                self.RegisterParamChange()
                self.ShowImage()
        else:
            self.automatic_panel.Enable(False)
            self.manual_panel.Enable(True)
            self.automatic_shape_text.SetLabel('')
            self.SetManual( evt ) # register current values

    def OnSplit(self,evt):

        params.params.do_fix_split = self.do_fix_split_input.GetValue()
        self.splitdetection_panel.Enable(params.params.do_fix_split)

    def OnMerged(self,evt):

        params.params.do_fix_merged = self.do_fix_merged_input.GetValue()
        self.mergeddetection_panel.Enable(params.params.do_fix_merged)

    def OnSpurious(self,evt):

        params.params.do_fix_spurious = self.do_fix_spurious_input.GetValue()
        self.spuriousdetection_panel.Enable(params.params.do_fix_spurious)

    def OnLost(self,evt):

        params.params.do_fix_lost = self.do_fix_lost_input.GetValue()
        self.lostdetection_panel.Enable(params.params.do_fix_lost)

    def SetSplit(self,evt):

        params.params.splitdetection_length = int(self.splitdetection_length_input.GetValue())
        params.params.splitdetection_cost = float(self.splitdetection_cost_input.GetValue())

    def SetMerged(self,evt):

        params.params.mergeddetection_length = int(self.mergeddetection_length_input.GetValue())
        params.params.mergeddetection_distance = float(self.mergeddetection_distance_input.GetValue())

    def SetSpurious(self,evt):

        params.params.spuriousdetection_length = int(self.spuriousdetection_length_input.GetValue())

    def SetLost(self,evt):

        params.params.lostdetection_length = int(self.lostdetection_length_input.GetValue())

    def SetAutomatic(self,evt):
        nstd = float(self.nstd_shape_input.GetValue())
        nframes = int(self.nframes_shape_input.GetValue())

        # check to make sure valid
        if nstd <= 0:
            self.nstd_shape_input.SetValue(str(params.params.n_std_thresh))
            nstd = params.params.n_std_thresh

        if nframes <= 0:
            self.nframes_shape_input.SetValue(str(params.params.n_frames_size))
            nframes = params.params.n_frames_size
        
        if (nstd != params.params.n_std_thresh) or (nframes != params.params.n_frames_size):
            params.params.n_std_thresh = nstd
            params.params.n_frames_size = nframes
            self.shape_uptodate = False
            self.automatic_shape_text.SetLabel('Bounds on shape not up to date.')

    def ComputeShapeNow(self,evt):

        # estimate shape now
        wx.BeginBusyCursor()
        wx.Yield()
        succeeded = ell.est_shape( self.bg_imgs,self.frame )
        wx.EndBusyCursor()
        
        if not succeeded:
          return

        # copy to temporary variable
        self.automatic_minshape = params.params.minshape.copy()
        self.automatic_maxshape = params.params.maxshape.copy()
        self.automatic_meanshape = params.params.meanshape.copy()

        # show shape
        self.PrintShape()

        # set up to date
        self.shape_uptodate = True
        self.automatic_shape_text.SetLabel('')
        self.RegisterParamChange()

        self.ShowImage()

    def PrintShape(self):

        self.min_area_input.SetValue(str(params.params.minshape.area))
        self.min_major_input.SetValue(str(params.params.minshape.major))
        self.min_minor_input.SetValue(str(params.params.minshape.minor))
        self.min_ecc_input.SetValue(str(params.params.minshape.ecc))
        self.mean_area_input.SetValue(str(params.params.meanshape.area))
        self.mean_major_input.SetValue(str(params.params.meanshape.major))
        self.mean_minor_input.SetValue(str(params.params.meanshape.minor))
        self.mean_ecc_input.SetValue(str(params.params.meanshape.ecc))
        self.max_area_input.SetValue(str(params.params.maxshape.area))
        self.max_major_input.SetValue(str(params.params.maxshape.major))
        self.max_minor_input.SetValue(str(params.params.maxshape.minor))
        self.max_ecc_input.SetValue(str(params.params.maxshape.ecc))

    def SetManual(self,evt):

        minarea = float(self.min_area_input.GetValue())
        meanarea = float(self.mean_area_input.GetValue())
        maxarea = float(self.max_area_input.GetValue())
        if (minarea <= meanarea) and (meanarea <= maxarea) and \
              (minarea >= 0):
            params.params.minshape.area = minarea
            params.params.meanshape.area = meanarea
            params.params.maxshape.area = maxarea
        else:
            self.min_area_input.SetValue(str(params.params.minshape.area))
            self.mean_area_input.SetValue(str(params.params.meanshape.area))
            self.max_area_input.SetValue(str(params.params.maxshape.area))
        minmajor = float(self.min_major_input.GetValue())
        meanmajor = float(self.mean_major_input.GetValue())
        maxmajor = float(self.max_major_input.GetValue())
        if (minmajor <= meanmajor) and (meanmajor <= maxmajor) and \
              (minmajor >= 0):
            params.params.minshape.major = minmajor
            params.params.meanshape.major = meanmajor
            params.params.maxshape.major = maxmajor
        else:
            self.min_major_input.SetValue(str(params.params.minshape.major))
            self.mean_major_input.SetValue(str(params.params.meanshape.major))
            self.max_major_input.SetValue(str(params.params.maxshape.major))
        minminor = float(self.min_minor_input.GetValue())
        meanminor = float(self.mean_minor_input.GetValue())
        maxminor = float(self.max_minor_input.GetValue())
        if (minminor <= meanminor) and (meanminor <= maxminor) and \
              (minminor >= 0):
            params.params.minshape.minor = minminor
            params.params.meanshape.minor = meanminor
            params.params.maxshape.minor = maxminor
        else:
            self.min_minor_input.SetValue(str(params.params.minshape.minor))
            self.mean_minor_input.SetValue(str(params.params.meanshape.minor))
            self.max_minor_input.SetValue(str(params.params.maxshape.minor))
        minecc = float(self.min_ecc_input.GetValue())
        meanecc = float(self.mean_ecc_input.GetValue())
        maxecc = float(self.max_ecc_input.GetValue())
        if (minecc <= meanecc) and (meanecc <= maxecc) and \
              (minecc >= 0) and (maxecc <= 1):
            params.params.minshape.ecc = minecc
            params.params.meanshape.ecc = meanecc
            params.params.maxshape.ecc = maxecc
        else:
            self.min_ecc_input.SetValue(str(params.params.minshape.ecc))
            self.mean_ecc_input.SetValue(str(params.params.meanshape.ecc))
            self.max_ecc_input.SetValue(str(params.params.maxshape.ecc))

        #params.params.meanshape = params.averageshape(params.params.minshape,
        #                                              params.params.maxshape)

        self.RegisterParamChange()
        self.ShowImage()

    def SetMotion(self,evt):
        
        angle_weight = float(self.angle_weight_input.GetValue())
        if angle_weight >= 0:
            params.params.ang_dist_wt = angle_weight
        else:
            self.angle_weight_input.SetValue(str(params.params.ang_dist_wt))

        max_jump = float(self.max_jump_input.GetValue())
        if max_jump > 0:
            params.params.max_jump = max_jump
        else:
            self.max_jump_input.SetValue(str(params.params.max_jump))

		# KB 20120109: allow jumps of distance max_jump_split if an observation is the result of 
		# splitting a connected component
        max_jump_split = float(self.max_jump_split_input.GetValue())
        if max_jump_split > 0:
            params.params.max_jump_split = max_jump_split
        else:
            self.max_jump_split_input.SetValue(str(params.params.max_jump_split))

        min_jump = float(self.min_jump_input.GetValue())
        if min_jump >= 0:
            params.params.min_jump = min_jump
        else:
            self.min_jump_input.SetValue(str(params.params.min_jump))

        center_dampen = float(self.center_dampen_input.GetValue())
        if center_dampen >= 0 and center_dampen <= 1:
            params.params.dampen = center_dampen
        else:
            self.center_dampen_input.SetValue(str(params.params.dampen))

        angle_dampen = float(self.angle_dampen_input.GetValue())
        if angle_dampen >= 0 and angle_dampen <= 1:
            params.params.angle_dampen = angle_dampen
        else:
            self.angle_dampen_input.SetValue(str(params.params.angle_dampen))

        self.RegisterParamChange()
        self.ShowImage()

    def SetObservation(self,evt):

        params.params.maxareadelete = float(self.max_area_delete_input.GetValue())
        params.params.minareaignore = float(self.min_area_ignore_input.GetValue())
        params.params.maxpenaltymerge = float(self.max_penalty_merge_input.GetValue())
        minbackthresh = float(self.lower_thresh_input.GetValue())
        maxclustersperblob = int(self.maxclustersperblob_input.GetValue())
        max_blobs_detect = int( self.max_blobs_input.GetValue() )
        if minbackthresh > 0 and minbackthresh <= 1:
            params.params.minbackthresh = minbackthresh
        else:
            self.lower_thresh_input.SetValue( str( params.params.minbackthresh ) )
        if maxclustersperblob >= 1:
            params.params.maxclustersperblob = maxclustersperblob
        else:
            self.maxclustersperblob_input.SetValue( str( params.params.maxclustersperblob ) )
        if max_blobs_detect >= 1:
            params.params.max_n_clusters = max_blobs_detect
        else:
            self.max_blobs_input.SetValue( str( params.params.max_n_clusters ) )
        self.RegisterParamChange()
        self.ShowImage()

    def FrameScrollbarMoved(self,evt):
	
	# get the value on the scrollbar now
	self.show_frame = self.frame_scrollbar.GetThumbPosition()

        if hasattr(self,'obs_filtered'):
            self.obs_prev = self.obs_filtered

	# show the image and update text
	self.ShowImage()


    def ShowImage(self):

        if DEBUG_TRACKINGSETTINGS: print 'ShowImage ' + str(self.show_frame)

        try:
            wx.Yield()
        except: pass # can be recursive sometimes in Windows
        wx.BeginBusyCursor()
        im, stamp = params.params.movie.get_frame( int(self.show_frame) )

        windowsize = [self.img_panel.GetRect().GetHeight(),self.img_panel.GetRect().GetWidth()]

        self.GetBgImage()
        
        if self.img_chosen == SHOW_UNFILTERED_OBSERVATIONS:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_UNFILTERED_OBSERVATIONS'
            obs_unfiltered = self.GetObsUnfiltered()
            plot_linesegs = draw_ellipses(obs_unfiltered)
            
        elif self.img_chosen == SHOW_FILTERED_OBSERVATIONS:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_FILTERED_OBSERVATIONS'
            obs_filtered = self.GetObsFiltered()
            plot_linesegs = draw_ellipses(obs_filtered)
            
        elif self.img_chosen == SHOW_SMALL_OBSERVATIONS:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_SMALL_OBSERVATIONS'
            obs_unfiltered = self.GetObsUnfiltered()
            obs_small = []
            for obs in obs_unfiltered:
                if obs.area < params.params.minshape.area:
                    obs_small.append(obs)
            plot_linesegs = draw_ellipses(obs_small)
            
        elif self.img_chosen == SHOW_LARGE_OBSERVATIONS:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_LARGE_OBSERVATIONS'
            obs_unfiltered = self.GetObsUnfiltered()
            obs_large = []
            for obs in obs_unfiltered:
                if obs.area > params.params.maxshape.area:
                    obs_large.append(obs)
            plot_linesegs = draw_ellipses(obs_large)

        elif self.img_chosen == SHOW_DELETED_OBSERVATIONS:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_DELETED_OBSERVATIONS'
            (obs_unfiltered,obs_deleted) = self.GetObsUnfiltered('diddelete')
            plot_linesegs = draw_ellipses(obs_deleted)

        elif self.img_chosen == SHOW_SPLIT_OBSERVATIONS:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_SPLIT_OBSERVATIONS'
            (obs_unfiltered,obs_split) = self.GetObsUnfiltered('didsplit')
            plot_linesegs = draw_ellipses(obs_split)

        elif self.img_chosen == SHOW_MERGED_OBSERVATIONS:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_MERGED_OBSERVATIONS'
            (obs_unfiltered,obs_merge) = self.GetObsUnfiltered('didmerge')
            plot_linesegs = draw_ellipses(obs_merge)

        elif self.img_chosen == SHOW_LOWERED_OBSERVATIONS:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_LOWERED_OBSERVATIONS'
            (obs_unfiltered,obs_lowered) = self.GetObsUnfiltered('didlowerthresh')
            plot_linesegs = draw_ellipses(obs_lowered)

        # MAXJUMP
        elif self.img_chosen == SHOW_MAXJUMP:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_MAXJUMP'

            # either grab or compute observations
            obs_filtered = self.GetObsFiltered()
            plot_linesegs = draw_ellipses(obs_filtered)

            # draw circles
            for i,obs in enumerate(obs_filtered):
                plot_new_stuff = imagesk.draw_circle(obs.center.x,
                                                     obs.center.y,params.params.max_jump*2.,
                                                     params.params.colors[i%len(params.params.colors)])
                plot_linesegs.extend(plot_new_stuff)
                plot_new_stuff = imagesk.draw_circle(obs.center.x,
                                                     obs.center.y,params.params.min_jump,
                                                     params.params.colors[i%len(params.params.colors)])
                plot_linesegs.extend(plot_new_stuff)
                

        elif self.img_chosen == SHOW_MOTIONMODEL:
            if DEBUG_TRACKINGSETTINGS: print 'SHOW_MOTIONMODEL'

            (target_prev,target_curr,target_pred) = self.GetTargetMotion()

            # show the next frame, if there is one
            nextframe = num.minimum(int(self.show_frame+1),params.params.n_frames-1)
            im, stamp = params.params.movie.get_frame(nextframe)

            # draw previous positions
            plot_linesegs = draw_ellipses(target_prev)

            # draw current positions
            plot_new_stuff = draw_ellipses(target_curr,colors=[[255,255,0]])
            plot_linesegs.extend(plot_new_stuff)

            # draw predicted positions
            plot_new_stuff = draw_ellipses(target_pred)
            plot_linesegs.extend(plot_new_stuff)

            scaleunit = params.params.max_jump / params.params.DRAW_MOTION_SCALE
            parcolor = [0,255,0]
            perpcolor = [0,255,0]
            anglecolor = [0,0,255]

            for i in target_pred.iterkeys():
                # compute direction of motion
                vx = target_pred[i].center.x - target_curr[i].center.x
                vy = target_pred[i].center.y - target_curr[i].center.y
                thetamotion = num.arctan2(vy,vx)

                # angle
                theta = target_pred[i].angle
                
                # we want to choose to add pi if that makes difference from motion direction smaller
                dtheta = abs( ((theta - thetamotion + num.pi) % (2.*num.pi)) - num.pi )
                if dtheta > (num.pi/2.):
                    theta += num.pi

                # compute end points of parallel motion
                x0 = target_pred[i].center.x + scaleunit*num.cos(theta)
                x1 = target_pred[i].center.x - scaleunit*num.cos(theta)
                y0 = target_pred[i].center.y + scaleunit*num.sin(theta)
                y1 = target_pred[i].center.y - scaleunit*num.sin(theta)

                # add parallel motion annotation line
                plot_new_stuff = imagesk.draw_line(x0+1,y0+1,x1+1,y1+1,parcolor)
                plot_linesegs.extend(plot_new_stuff)

                # compute end points of perpendicular motion
                x0 = target_pred[i].center.x + scaleunit*num.cos(num.pi/2.+theta)
                x1 = target_pred[i].center.x - scaleunit*num.cos(num.pi/2.+theta)
                y0 = target_pred[i].center.y + scaleunit*num.sin(num.pi/2.+theta)
                y1 = target_pred[i].center.y - scaleunit*num.sin(num.pi/2.+theta)
                
                # add perpendicular motion annotation line
                plot_new_stuff = imagesk.draw_line(x0+1,y0+1,x1+1,y1+1,perpcolor)
                plot_linesegs.extend(plot_new_stuff)
                

                # compute end points of angular motion
                if params.params.ang_dist_wt > 0:
                    
                    dtheta = scaleunit*num.sqrt(1./params.params.ang_dist_wt)
                    if dtheta >= (num.pi/2.):
                        print 'dtheta is more than pi/2'
                    else:
                        theta0 = theta - dtheta
                        theta1 = theta + dtheta
                        
                        # draw arc
                        plot_new_stuff = imagesk.draw_arc(target_pred[i].center.x,
                                                          target_pred[i].center.y,
                                                          scaleunit/2,
                                                          theta0,theta1,
                                                          anglecolor)
                        plot_linesegs.extend(plot_new_stuff)
                   
        im = imagesk.double2mono8(im,donormalize=False)
        linesegs,im = imagesk.zoom_linesegs_and_image(plot_linesegs,im,self.zoomaxes)
        (linesegs,linecolors) = imagesk.separate_linesegs_colors(linesegs)

        self.img_wind.update_image_and_drawings('trackset',
                                                im,
                                                format='MONO8',
                                                linesegs=linesegs,
                                                lineseg_colors=linecolors
                                                )
        self.img_wind.Refresh(eraseBackground=False)

        self.frame_number_text.SetLabel('Frame %d'%self.show_frame)
        
        if self.info == True:
            self.ShowInfo( None, None )

        wx.EndBusyCursor()

        if DEBUG_TRACKINGSETTINGS: sys.stdout.flush()
        

    def ImageChosen(self,evt):

        self.img_chosen = self.show_img_input.GetSelection()
        self.ShowImage()

    def OnResize(self,evt=None):

        if evt is not None: evt.Skip()
        self.frame.Layout()
        try:
            #self.ShowImage()
            self.frame_scrollbar.SetMinSize( wx.Size(
                self.img_panel.GetRect().GetWidth(),
                self.frame_scrollbar.GetRect().GetHeight() ) )
        except AttributeError: pass # during initialization

    def ZoominToggle(self,evt):

        self.zoomin = not self.zoomin
        if self.zoomin == True and self.zoomout == True:
            self.toolbar.ToggleTool(self.zoomout_id,False)
            self.zoomout = False
        if self.zoomin == True and self.info == True:
            self.toolbar.ToggleTool(self.info_id,False)
            self.info = False

    def ZoomoutToggle(self,evt):

        self.zoomout = not self.zoomout
        if self.zoomin == True and self.zoomout == True:
            self.toolbar.ToggleTool(self.zoomin_id,False)
            self.zoomin = False
        if self.zoomout == True and self.info == True:
            self.toolbar.ToggleTool(self.info_id,False)
            self.info = False

    def InfoToggle(self,evt):

        self.info = not self.info
        if self.info == True and self.zoomin == True:
            self.toolbar.ToggleTool(self.zoomin_id,False)
            self.zoomin = False
        if self.zoomout == True and self.info == True:
            self.toolbar.ToggleTool(self.zoomout_id,False)
            self.zoomout = False

    def MouseDoubleClick(self,evt):

        if self.zoomout == True:
            self.zoomfactor = 1
            self.SetZoomAxes()

    def MouseClick(self,evt):

        # get the clicked position
        if USEGL:
          windowheight = self.img_wind_child.GetRect().GetHeight()
          windowwidth = self.img_wind_child.GetRect().GetWidth()
          x = evt.GetX() * self.img_size[1] / windowwidth
          y = self.img_size[0] - evt.GetY() * self.img_size[0] / windowheight
        else:
          resize = self.img_wind.get_resize()
          x = evt.GetX() / resize
          h = self.zoomaxes[3] - self.zoomaxes[2] + 1
          y = h - evt.GetY() / resize
          
        x += self.zoomaxes[0]
        y += self.zoomaxes[2]

        if (x > self.img_size[1]) or (y > self.img_size[0]):
            return
        if self.zoomin:
            self.ZoomIn(x,y)
        elif self.zoomout:
            self.ZoomOut()
        elif self.info:
            self.ShowInfo(x,y)
        
    def ZoomIn(self,x,y):

        self.zoomfactor *= 1.5
        self.zoompoint = [x,y]
        self.SetZoomAxes()

    def SetZoomAxes(self):

        x = self.zoompoint[0]
        y = self.zoompoint[1]
        
        W = params.params.movie.get_width()
        H = params.params.movie.get_height()
        h = H/self.zoomfactor
        w = W/self.zoomfactor
        x1 = x-w/2
        x2 = x+w/2
        y1 = y-h/2
        y2 = y+h/2

        if x1 < 0:
            x2 -= x1
            x1 = 0
        elif x2 > W-1:
            x1 -= (x2 - W + 1)
            x2 = W-1
        if y1 < 0:
            y2 -= y1
            y1 = 0
        elif y2 > H-1:
            y1 -= (y2 - H + 1)
            y2 = H-1
        x1 = num.maximum(int(x1),0)
        x2 = num.minimum(int(x2),W-1)
        y1 = num.maximum(int(y1),0)
        y2 = num.minimum(int(y2),H-1)

        self.zoomaxes = [x1,x2,y1,y2]
        self.ShowImage()

    def ZoomOut(self):

        if self.zoomfactor <= 1:
            return

        self.zoomfactor /= 1.5
        self.SetZoomAxes()

    def ShowInfo(self,x,y):

        # grab targets
        if (self.img_chosen == SHOW_MAXJUMP) or (self.img_chosen == SHOW_FILTERED_OBSERVATIONS):
            obs = self.obs_filtered.obs
        else:
            obs = self.obs_unfiltered.obs

        if (x is None or y is None):
            if self.info_mini < len( obs ):
                mini = self.info_mini
                x = obs[mini].center.x
                y = obs[mini].center.y
            else:
                self.ShowObsInfo( None )
                return

        # determine closest target
        mind = num.inf
        for i,v in enumerate(obs):
            d = (v.center.x-x)**2 + (v.center.y-y)**2
            if d <= mind:
                mini = i
                mind = d

        maxdshowinfo = (num.maximum(self.zoomaxes[1]-self.zoomaxes[0],
                                    self.zoomaxes[2]-self.zoomaxes[1])/params.params.MAXDSHOWINFO)**2

        if mind < maxdshowinfo:
            self.ShowObsInfo(obs[mini])
            self.info_mini = mini
        else:
            self.ShowObsInfo( None )

        
    def ShowObsInfo(self,ellipse):
        """Output text describing currently selected ellipse."""
        if ellipse is None:
            self.info_text.SetValue( "" )
        else:
            self.info_text.SetValue('area=%.2f, maj=%.2f, min=%.2f, ecc=%.2f'%(ellipse.area,ellipse.major,ellipse.minor,ellipse.minor/ellipse.major))


    def GetObsFiltered(self):
        if not(hasattr(self,'obs_filtered') and self.obs_filtered.issame(self.show_frame)):
            if DEBUG_TRACKINGSETTINGS: print 'computing filtered observations'
            obs_filtered = ell.find_ellipses(self.bg_imgs.dfore.copy(),self.bg_imgs.cc.copy(),self.bg_imgs.ncc,True)
            self.obs_filtered = StoredObservations(obs_filtered,self.show_frame)
        else:
            if DEBUG_TRACKINGSETTINGS: print 'filtered observations already computed'
        if DEBUG_TRACKINGSETTINGS: print 'obs_filtered:\n' + str(self.obs_filtered)

        return self.obs_filtered.obs
    def GetObsUnfiltered(self,*args):

        # do we need to recompute?
        mustcompute = False
        if hasattr(self,'obs_unfiltered') and self.obs_unfiltered.issame(self.show_frame):
            for arg in args:
               if self.obs_unfiltered.__dict__[arg] is None:
                   mustcompute = True
                   break
        else:
            mustcompute = True

        if DEBUG_TRACKINGSETTINGS: print 'mustcompute = ' + str(mustcompute)
        if DEBUG_TRACKINGSETTINGS and not mustcompute:
          print 'stored obs_unfiltered = ' + str(self.obs_unfiltered)

        # if we are only interested in the unfiltered observation
        if len(args) == 0:
            # if it has not yet been computed for this frame, compute
            if mustcompute:
                obs_unfiltered = ell.find_ellipses(self.bg_imgs.dfore.copy(),self.bg_imgs.cc.copy(),self.bg_imgs.ncc,False)
                self.obs_unfiltered = StoredObservations(obs_unfiltered,self.show_frame)
            return self.obs_unfiltered.obs
          
        # compute if necessary
        if mustcompute:
            wx.BeginBusyCursor()
            wx.YieldIfNeeded()
            (obs_unfiltered,ellsmall,elllarge,didlowerthresh,didmerge,diddelete,didsplit) = \
                                         ell.find_ellipses_display(self.bg_imgs.dfore.copy(),self.bg_imgs.cc.copy(),self.bg_imgs.ncc)
            if DEBUG_TRACKINGSETTINGS: print 'computed obs_unfiltered = ' + str(obs_unfiltered) + ', len = ' + str(len(obs_unfiltered))
            if DEBUG_TRACKINGSETTINGS: print 'ellsmall = ' + str(ellsmall)
            if DEBUG_TRACKINGSETTINGS: print 'elllarge = ' + str(elllarge)
            if DEBUG_TRACKINGSETTINGS: print 'didlowerthresh = ' + str(didlowerthresh)
            if DEBUG_TRACKINGSETTINGS: print 'didmerge = ' + str(didmerge)
            if DEBUG_TRACKINGSETTINGS: print 'diddelete = ' + str(diddelete)
            if DEBUG_TRACKINGSETTINGS: print 'didsplit = ' + str(didsplit)
            wx.EndBusyCursor()
            self.obs_unfiltered = StoredObservations(obs_unfiltered,self.show_frame,
                                                     ellsmall,elllarge,didlowerthresh,
                                                     didmerge,diddelete,didsplit)
            if DEBUG_TRACKINGSETTINGS: print 'stored obs_unfiltered: '
            if DEBUG_TRACKINGSETTINGS: print str(self.obs_unfiltered)

        # create return list
        ret = (self.obs_unfiltered.obs,)
        for arg in args:
            ret += (self.obs_unfiltered.__dict__[arg],)

        return ret

    def GetBgImage(self):
        
        if not (self.bg_img_frame == self.show_frame):
            (self.bg_imgs.dfore,self.bg_imgs.bw,
             self.bg_imgs.cc,self.bg_imgs.ncc) = \
             self.bg_imgs.sub_bg(self.show_frame)
            self.bg_img_frame = self.show_frame
        
    def GetObsPrev(self):
        if not(hasattr(self,'obs_prev') and self.obs_filtered.issame(self.show_frame-1)):
            wx.BeginBusyCursor()
            wx.Yield()
            prevframe = num.maximum(0,self.show_frame-1)
            (dfore,bw,cc,ncc) = self.bg_imgs.sub_bg(prevframe)
            obs_filtered = ell.find_ellipses(dfore,cc,ncc,True)
            wx.EndBusyCursor()
            self.obs_prev = StoredObservations(obs_filtered,self.show_frame)
        return self.obs_prev.obs

    def GetTargetMotion(self):

        # get current positions
        obs_curr = self.GetObsFiltered()
        # get previous positions
        obs_prev = self.GetObsPrev()
        # give identities to previous positions
        target_prev = ell.TargetList()
        for i,obs in enumerate(obs_prev):
            obs.identity = i
            target_prev.append(obs)
        # match previous and current targets, no velocity
        oldnids = params.params.nids
        target_curr = ell.find_flies(target_prev,target_prev,obs_curr)
        # don't actually assign new identities
        params.params.nids = oldnids
        # delete targets that aren't in both frames
        keyscurr = set(target_curr.keys())
        keysprev = set(target_prev.keys())
        keysremove = keyscurr - keysprev
        for i in keysremove:
            tmp = target_curr.pop(i)
        keysremove = keysprev - keyscurr
        for i in keysremove:
            tmp = target_prev.pop(i)
        
        # compute predicted positions
        target_pred = cvpred(target_prev,target_curr)
        # store
        targetmotion = (target_prev,target_curr,target_pred)
        # return
        return targetmotion

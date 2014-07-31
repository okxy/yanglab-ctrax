
import os.path
import codedir

import wx
from wx import xrc
import scipy.signal as signal
import scipy.misc.pilutil as pilutil
import numpy as num
import motmot.wxvideo.wxvideo as wxvideo
import motmot.wxvalidatedtext.wxvalidatedtext as wxvt # part of Motmot

import houghcircles as hough
from params import params
import imagesk
import colormapk

RSRC_FILE = os.path.join(codedir.codedir,'xrc','setarena.xrc')

RESIZE = 500
NTHRESHSTEPS = 30
NRADIUSSTEPS = RESIZE/2
NXSTEPS = RESIZE
NYSTEPS = RESIZE
DCLICK = 8
CIRCLEWIDTH = 3
USEGL = False

class SetArena:

    def __init__(self,parent,bg):

        self.parent = parent
        self.im = bg.copy()

        rsrc = xrc.XmlResource(RSRC_FILE )
        self.frame = rsrc.LoadFrame(parent,"detect_arena_frame")

        self.InitControlHandles()
        self.InitializeValues()
        self.BindCallbacks()
        self.OnResize()
        self.ShowImage()

    def control(self,ctrlname):
        return xrc.XRCCTRL(self.frame,ctrlname)

    def InitControlHandles(self):

        self.edge_threshold_button = self.control('edge_threshold_button')
        self.detect_button = self.control('detect_button')
        self.refine_button = self.control('refine_button')
        self.done_button = self.control('done_button')
        self.img_panel = self.control('img_panel')
        box = wx.BoxSizer( wx.VERTICAL )
        self.img_panel.SetSizer( box )
        self.img_wind = wxvideo.DynamicImageCanvas( self.img_panel, -1 )
        self.img_wind.set_resize(True)
        box.Add( self.img_wind, 1, wx.EXPAND )
        self.img_panel.SetAutoLayout( True )
        self.img_panel.Layout()
        self.directions_text = self.control('directions_text')
        self.radius_text = self.control('radius_text')
        self.x_text = self.control('x_text')
        self.y_text = self.control('y_text')
        self.radius_spin = self.control('radius_spin')
        self.x_spin = self.control('x_spin')
        self.y_spin = self.control('y_spin')
        self.minradius_text = self.control('minradius_text')
        self.maxradius_text = self.control('maxradius_text')
        self.minx_text = self.control('minx_text')
        self.maxx_text = self.control('maxx_text')
        self.miny_text = self.control('miny_text')
        self.maxy_text = self.control('maxy_text')

    def InitializeValues(self):

        wx.BeginBusyCursor()
        wx.Yield()

        # resize the image for speed
        (self.im,self.nr_resize_ratio,self.nc_resize_ratio) = resize_image_for_speed(self.im)

        imblank = num.zeros(self.im.shape+(3,),dtype=num.uint8)
        self.img_wind.update_image_and_drawings('setarena',imblank,
                                                format='RGB8')
        self.img_wind_child = self.img_wind.get_child_canvas('setarena')

        # compute the edge magnitude image
        self.edgemag = edge(self.im)
        # initialize value for edge threshold
        if params.arena_edgethresh is None:
            params.arena_edgethresh = choose_edge_threshold(self.edgemag)

        # initialize arena parameters if not set yet
        (nr,nc) = self.im.shape
        if params.arena_center_x is None:
            self.arena_center_x = .5*nc
        else:
            self.arena_center_x = params.arena_center_x * self.nc_resize_ratio
        if params.arena_center_y is None:
            self.arena_center_y = .5*nr
        else:
            self.arena_center_y = params.arena_center_y * self.nr_resize_ratio
        if params.arena_radius is None:
            self.arena_radius = .375*min(nc,nr)
        else:
            self.arena_radius = params.arena_radius * .5 * (self.nr_resize_ratio + self.nc_resize_ratio)

        # set bounds on the threshold
        self.minedgemag = num.min(self.edgemag)
        self.maxedgemag = num.max(self.edgemag)
        self.edge_threshold_button.SetRange(0,NTHRESHSTEPS-1)

        params.arena_edgethresh = min(params.arena_edgethresh,self.maxedgemag)
        params.arena_edgethresh = max(params.arena_edgethresh,self.minedgemag)

        # set value of threshold displayed
        v = int(num.round((params.arena_edgethresh-self.minedgemag)/(self.maxedgemag-self.minedgemag)*NTHRESHSTEPS))
        self.edge_threshold_button.SetValue(v)

        # create the threshold image
        self.CreateEdgeImage()

        self.edgepoint = [self.arena_center_x + self.arena_radius,
                          self.arena_center_y]

        # set click mode
        self.selected_point = 'none'

        # set text
        self.radius_text.SetValue("%.1f"%self.arena_radius)
        self.x_text.SetValue("%.1f"%self.arena_center_x)
        self.y_text.SetValue("%.1f"%self.arena_center_y)

        # set min, max text
        self.minradius_text.SetValue("%.3f"%params.min_arena_radius)
        self.maxradius_text.SetValue("%.3f"%params.max_arena_radius)
        self.minx_text.SetValue("%.3f"%params.min_arena_center_x)
        self.maxx_text.SetValue("%.3f"%params.max_arena_center_x)
        self.miny_text.SetValue("%.3f"%params.min_arena_center_y)
        self.maxy_text.SetValue("%.3f"%params.max_arena_center_y)

        # set-up spinners
        self.maxradius = max(params.movie.get_width()*self.nc_resize_ratio,
                              params.movie.get_height()*self.nr_resize_ratio)/2.
        self.maxx = (params.movie.get_width()-1.)*self.nc_resize_ratio
        self.maxy = (params.movie.get_height()-1.)*self.nr_resize_ratio
        self.radius_spinner_scale = float(NRADIUSSTEPS)/self.maxradius
        self.x_spinner_scale = float(NXSTEPS)/self.maxx
        self.y_spinner_scale = float(NYSTEPS)/self.maxy
        self.radius_spin.SetRange(0,NRADIUSSTEPS-1)
        self.x_spin.SetRange(0,NXSTEPS-1)
        self.y_spin.SetRange(0,NYSTEPS-1)
        self.set_radius_spinner_value()
        self.set_x_spinner_value()
        self.set_y_spinner_value()
        
        wx.EndBusyCursor()

    def get_radius_spinner_value(self):
        self.arena_radius = float(self.radius_spin.GetValue()) / self.radius_spinner_scale

    def set_radius_spinner_value(self):
        self.radius_spin.SetValue(self.arena_radius*self.radius_spinner_scale)

    def get_x_spinner_value(self):
        self.arena_center_x = float(self.x_spin.GetValue()) / self.x_spinner_scale

    def set_x_spinner_value(self):
        self.x_spin.SetValue(self.arena_center_x*self.x_spinner_scale)

    def get_y_spinner_value(self):
        self.arena_center_y = float(self.y_spin.GetValue()) / self.y_spinner_scale

    def set_y_spinner_value(self):
        self.y_spin.SetValue(self.arena_center_y*self.y_spinner_scale)

    def BindCallbacks(self):

        # threshold button
        self.frame.Bind(wx.EVT_SPIN,self.ChangeThreshold,self.edge_threshold_button)
        # mode button
        self.frame.Bind(wx.EVT_BUTTON,self.Detect,self.detect_button)
        # enter button
        self.frame.Bind(wx.EVT_BUTTON,self.Refine,self.refine_button)

        # parameter spinners
        self.frame.Bind(wx.EVT_SPIN,self.ChangeRadius,self.radius_spin)
        self.frame.Bind(wx.EVT_SPIN,self.ChangeCenterX,self.x_spin)
        self.frame.Bind(wx.EVT_SPIN,self.ChangeCenterY,self.y_spin)

        # text input
        wxvt.setup_validated_float_callback( self.radius_text,
                                             xrc.XRCID("radius_text"),
                                             self.OnRadiusValidated,
                                             pending_color=params.wxvt_bg )
        wxvt.setup_validated_float_callback( self.x_text,
                                             xrc.XRCID("x_text"),
                                             self.OnXValidated,
                                             pending_color=params.wxvt_bg )
        wxvt.setup_validated_float_callback( self.y_text,
                                             xrc.XRCID("y_text"),
                                             self.OnYValidated,
                                             pending_color=params.wxvt_bg )

        # min, max text input
        wxvt.setup_validated_float_callback( self.minradius_text,
                                             xrc.XRCID("minradius_text"),
                                             self.OnRadiusBoundsValidated,
                                             pending_color=params.wxvt_bg )
        wxvt.setup_validated_float_callback( self.maxradius_text,
                                             xrc.XRCID("maxradius_text"),
                                             self.OnRadiusBoundsValidated,
                                             pending_color=params.wxvt_bg )
        wxvt.setup_validated_float_callback( self.minx_text,
                                             xrc.XRCID("minx_text"),
                                             self.OnXBoundsValidated,
                                             pending_color=params.wxvt_bg )
        wxvt.setup_validated_float_callback( self.maxx_text,
                                             xrc.XRCID("maxx_text"),
                                             self.OnXBoundsValidated,
                                             pending_color=params.wxvt_bg )
        wxvt.setup_validated_float_callback( self.miny_text,
                                             xrc.XRCID("miny_text"),
                                             self.OnYBoundsValidated,
                                             pending_color=params.wxvt_bg )
        wxvt.setup_validated_float_callback( self.maxy_text,
                                             xrc.XRCID("maxy_text"),
                                             self.OnYBoundsValidated,
                                             pending_color=params.wxvt_bg )


        # mouse click
        self.img_wind_child.Bind(wx.EVT_LEFT_DOWN,self.MouseDown)
        self.img_wind_child.Bind(wx.EVT_LEFT_UP,self.MouseUp)

    def ChangeThreshold(self,evt):

        if evt is None:
            return

        v = self.edge_threshold_button.GetValue()
        params.arena_edgethresh = float(v) / float(NTHRESHSTEPS) * (self.maxedgemag - self.minedgemag) + self.minedgemag
        self.CreateEdgeImage()
        wx.Yield()
        self.ShowImage()

    def OnRadiusValidated(self,evt):
        v = float(self.radius_text.GetValue())
        if v < 0:
            v = 0
        self.arena_radius = v
        self.set_edgepoint()        
        wx.Yield()
        self.display_parameters(self.radius_text)
        self.ShowImage()


    def force_range( self, minv, maxv ):
        minv = min( max( minv, 0. ), 1. )
        maxv = min( max( maxv, 0. ), 1. )
        if maxv < minv:
            maxv = minv

        return minv, maxv


    def OnRadiusBoundsValidated(self,evt):
        minv = float(self.minradius_text.GetValue())
        maxv = float(self.maxradius_text.GetValue())
        minv, maxv = self.force_range( minv, maxv )
        params.min_arena_radius = minv
        params.max_arena_radius = maxv
        self.minradius_text.SetValue( str(minv) )
        self.maxradius_text.SetValue( str(maxv) )

    def OnXBoundsValidated(self,evt):
        minv = float(self.minx_text.GetValue())
        maxv = float(self.maxx_text.GetValue())
        minv, maxv = self.force_range( minv, maxv )
        params.min_arena_center_x = minv
        params.max_arena_center_x = maxv
        self.minx_text.SetValue( str(minv) )
        self.maxx_text.SetValue( str(maxv) )

    def OnYBoundsValidated(self,evt):
        minv = float(self.miny_text.GetValue())
        maxv = float(self.maxy_text.GetValue())
        minv, maxv = self.force_range( minv, maxv )
        params.min_arena_center_y = minv
        params.max_arena_center_y = maxv
        self.miny_text.SetValue( str(minv) )
        self.maxy_text.SetValue( str(maxv) )

    def OnXValidated(self,evt):
        self.arena_center_x = float(self.x_text.GetValue())
        self.set_edgepoint()        
        wx.Yield()
        self.display_parameters(self.x_text)
        self.ShowImage()

    def OnYValidated(self,evt):
        self.arena_center_y = float(self.y_text.GetValue())
        self.set_edgepoint()        
        wx.Yield()
        self.display_parameters(self.y_text)                
        self.ShowImage()
        
    def ChangeRadius(self,evt):

        if evt is None:
            return
        self.get_radius_spinner_value()
        self.set_edgepoint()        
        wx.Yield()
        self.display_parameters(self.radius_spin)                
        self.ShowImage()

    def ChangeCenterX(self,evt):

        if evt is None:
            return
        self.get_x_spinner_value()
        self.set_edgepoint()        
        wx.Yield()
        self.display_parameters(self.radius_spin)                
        self.ShowImage()

    def ChangeCenterY(self,evt):

        if evt is None:
            return
        self.get_y_spinner_value()
        self.set_edgepoint()        
        wx.Yield()
        self.display_parameters(self.radius_spin)                
        self.ShowImage()

    def Detect(self,evt=None):

        wx.BeginBusyCursor()
        wx.Yield()
        [self.arena_center_x,self.arena_center_y,self.arena_radius] = \
                       detectarena(self.edgemag_zero)
        self.set_edgepoint()
        self.force_edgepoint_inbounds()
            
        self.display_parameters()
        self.ShowImage()
        
        wx.EndBusyCursor()

    def set_edgepoint(self):
        if self.edgepoint is None:
            theta = 0.
        else:
            theta = num.arctan2(self.edgepoint[1] - self.arena_center_y,
                                self.edgepoint[0] - self.arena_center_x)
        self.edgepoint[0] = self.arena_center_x + self.arena_radius*num.cos(theta)
        self.edgepoint[1] = self.arena_center_y + self.arena_radius*num.sin(theta)


    def Refine(self,evt=None):

        if self.arena_center_x is None:
            self.Detect(evt)
            return
        wx.BeginBusyCursor()
        wx.Yield()
        [self.arena_center_x,self.arena_center_y,self.arena_radius] = \
                       detectarena(self.edgemag_zero,
                                   approxa=self.arena_center_x,
                                   approxb=self.arena_center_y,
                                   approxr=self.arena_radius)
        self.set_edgepoint()
        self.force_edgepoint_inbounds()
        self.display_parameters()
        self.ShowImage()
        wx.EndBusyCursor()
        
    def CreateEdgeImage(self):

        self.edgemag_zero = self.edgemag.copy()
        self.edgemag_zero[self.edgemag < params.arena_edgethresh] = 0
        wx.Yield()
        self.image_shown,clim = colormapk.colormap_image(self.edgemag_zero)
        #self.image_shown = self.edgemag_zero

    def display_parameters(self,cbo=None):
        if not (cbo == self.radius_spin):
            self.set_radius_spinner_value()
        if not (cbo == self.x_spin):
            self.set_x_spinner_value()
        if not (cbo == self.y_spin):
            self.set_y_spinner_value()
        if not (cbo == self.radius_text):
            self.radius_text.SetValue("%.1f"%self.arena_radius)
        if not (cbo == self.x_text):
            self.x_text.SetValue("%.1f"%self.arena_center_x)
        if not (cbo == self.y_text):
            self.y_text.SetValue("%.1f"%self.arena_center_y)
            
    def force_edgepoint_inbounds(self,theta=None):
        if theta is None:
            if self.edgepoint is None:
                theta = 0.
            else:
                theta = num.arctan2(self.edgepoint[1] - self.arena_center_y,self.edgepoint[0] - self.arena_center_x)        
        if (self.edgepoint[0] < 0):
            self.arena_radius = -self.arena_center_x / num.cos(theta)
        elif (self.edgepoint[0] > self.maxx):
            self.arena_radius = (self.maxx - self.arena_center_x) / num.cos(theta)
        elif (self.edgepoint[1] < 0):
            self.arena_radius = -self.arena_center_y / num.sin(theta)
        elif (self.edgepoint[1] > self.maxy):
            self.arena_radius = (self.maxy - self.arena_center_y) / num.sin(theta)            
        self.edgepoint[0] = self.arena_center_x + self.arena_radius*num.cos(theta)
        self.edgepoint[1] = self.arena_center_y + self.arena_radius*num.sin(theta)            


    def OnResize(self,evt=None):

        if evt is not None: evt.Skip()
        self.frame.Layout()
        try:
            self.ShowImage()
        except AttributeError: pass # during initialization

    def MouseDown(self,evt):

        if USEGL:
            windowheight = self.img_wind_child.GetRect().GetHeight()
            windowwidth = self.img_wind_child.GetRect().GetWidth()
            x = evt.GetX() * self.im.shape[1] / windowwidth
            y = self.im.shape[0] - evt.GetY() * self.im.shape[0] / windowheight
        else:
            resize = self.img_wind.get_resize()
            x = evt.GetX() / resize
            y = self.im.shape[0] - evt.GetY() / resize

        #x = evt.GetX()/self.resize
        #y = evt.GetY()/self.resize

        # compute distance to center
        dcenter = num.sqrt((x - self.arena_center_x)**2. + (y - self.arena_center_y)**2.)
        # compute distance to edgepoint
        dedge = num.sqrt((x - self.edgepoint[0])**2. + (y - self.edgepoint[1])**2.)
        mind = min(dcenter,dedge)
        if mind > DCLICK:
            return
        elif dcenter <= dedge:
            self.selected_point = 'center'
        else:
            self.selected_point = 'edge'

        wx.SetCursor(wx.StockCursor(wx.CURSOR_BULLSEYE))

    def ShowImage( self, evt=None ):
        
        """Draw circle on a color image (MxNx3 numpy array)."""

        #circlecolor = (0,0,0)
        #centercolor = (1,1,1,1)
        #edgecolor = (0,0,0,1)
        circlecolor = (255,0,0)
        centercolor = (0,1,0,1)
        edgecolor = (1,1,0,1)
        
        x = self.arena_center_x
        y = self.arena_center_y
        r = self.arena_radius
        edgepoint = self.edgepoint

        if edgepoint is None:
            edgepoint = [x+r,y]

        pointlist = [[x,y],edgepoint]
        pointcolors = [centercolor,edgecolor]
        pointsizes = [DCLICK/2,DCLICK/2]
        linesegs = imagesk.draw_circle(x,y,r,color=circlecolor)
        circlewidths = [CIRCLEWIDTH]*len(linesegs)
        (linesegs,linecolors) = imagesk.separate_linesegs_colors(linesegs)
        #img_8 = imagesk.double2mono8(self.image_shown,donormalize=True)
        self.img_wind.update_image_and_drawings('setarena',self.image_shown,
                                                format="RGB8",
                                                linesegs=linesegs,
                                                lineseg_colors=linecolors,
                                                points=pointlist,
                                                point_colors=pointcolors,
                                                point_radii=pointsizes,
                                                lineseg_widths=circlewidths)
        self.img_wind.Refresh(eraseBackground=False)

    def MouseUp(self,evt):


        if self.selected_point == 'none':
            return

        wx.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

        #x = evt.GetX()
        #y = evt.GetY()
        #x /= self.resize
        #y /= self.resize

        if USEGL:
            windowheight = self.img_wind_child.GetRect().GetHeight()
            windowwidth = self.img_wind_child.GetRect().GetWidth()
            x = evt.GetX() * self.im.shape[1] / windowwidth
            y = self.im.shape[0] - evt.GetY() * self.im.shape[0] / windowheight
        else:
            resize = self.img_wind.get_resize()
            x = evt.GetX() / resize
            #y = evt.GetY() / resize
            y = self.im.shape[0] - evt.GetY() / resize

        if (x > self.im.shape[1]) or (y > self.im.shape[0]):
            self.selected_point = 'none'
            return

        if self.selected_point == 'center':
            self.arena_center_x = x
            self.arena_center_y = y
        else:
            self.edgepoint[0] = x
            self.edgepoint[1] = y

        self.arena_radius = num.sqrt((self.edgepoint[0]-self.arena_center_x)**2.+(self.edgepoint[1]-self.arena_center_y)**2.)
        self.force_edgepoint_inbounds()

        self.selected_point = 'none'
        
        self.display_parameters()
        self.ShowImage()

    def GetArenaParameters(self):
        x = self.arena_center_x / self.nc_resize_ratio
        y = self.arena_center_y / self.nr_resize_ratio
        r = self.arena_radius * 2. / (self.nc_resize_ratio + self.nr_resize_ratio)
        return [x,y,r]
        
def choose_edge_threshold(edgemag,FracPixelsNotEdges=.95):

    
    NPixelsNotEdges = FracPixelsNotEdges * edgemag.shape[0] * edgemag.shape[1]
    [counts,loweredges] = num.histogram(edgemag,100)
    idx, = num.where(counts.cumsum() > NPixelsNotEdges)
    idx = idx[0]+1
    if idx >= len(loweredges):
        idx = -1
    edgethresh = loweredges[idx]

    return edgethresh

def doall(im):

    # resize the image for speed
    (imr,nr_resize_ratio,nc_resize_ratio) = resize_image_for_speed(im)
    # compute the edge magnitude image
    edgemag = edge(im)
    # initialize value for edge threshold
    if params.arena_edgethresh is None:
        params.arena_edgethresh = choose_edge_threshold(edgemag)
    # zero out some edges
    edgemag_zero = edgemag.copy()
    edgemag_zero[edgemag < params.arena_edgethresh] = 0
    [params.arena_center_x,params.arena_center_y,params.arena_radius] = \
        detectarena(edgemag_zero)


def detectarena(edgemag,approxa=None,approxb=None,approxr=None):

    nr = edgemag.shape[0]
    nc = edgemag.shape[1]

    isguesseda = True
    isguessedb = True
    isguessedr = True
    if approxa is None:
        approxa = (params.min_arena_center_x + \
                       params.max_arena_center_x) / 2. * float(nc)
        isguesseda = False
    if approxb is None:
        approxb = (params.min_arena_center_y + \
                       params.max_arena_center_y) / 2. * float(nr)
        isguessedb = False
    if approxr is None:
        approxr = (params.min_arena_radius + \
                       params.max_arena_radius) / 2. * float(min(nr,nc))
        isguessedr = False

    if isguesseda:
        mina = approxa - .025*nc
        maxa = approxa + .025*nc
    else:
        mina = params.min_arena_center_x * float(nc)
        maxa = params.max_arena_center_x * float(nc)

    if isguessedb:
        minb = approxb - .025*nc
        maxb = approxb + .025*nc
    else:
        minb = params.min_arena_center_y * float(nr)
        maxb = params.max_arena_center_y * float(nr)

    if isguessedr:
        minr = max(0.,approxr - .025*min(nc,nr))
        maxr = approxr + .025*min(nc,nr)
    else:
        minr = params.min_arena_radius * float(min(nc,nr))
        maxr = params.max_arena_radius * float(min(nc,nr))
    
    nbinsa = 20
    nbinsb = 20
    nbinsr = 20
    peaksnhoodsize = num.array([1,1,1])
    
    binedgesa = num.linspace(mina,maxa,nbinsa+1)
    bincentersa = (binedgesa[:-1]+binedgesa[1:])/2.
    binedgesb = num.linspace(minb,maxb,nbinsb+1)
    bincentersb = (binedgesb[:-1]+binedgesb[1:])/2.
    binedgesr = num.linspace(minr,maxr,nbinsr+1)
    bincentersr = (binedgesr[:-1]+binedgesr[1:])/2.
    [x,y,r] = detectcircles(edgemag,binedgesa=binedgesa,
                            bincentersb=bincentersb,
                            bincentersr=bincentersr,
                            peaksnhoodsize=peaksnhoodsize,
                            peaksthreshold=0.,
                            maxncircles=1)


    t = num.linspace(0,2.*num.pi,200)
    
    # second pass
    binsizea = binedgesa[1] - binedgesa[0]
    mina = x - binsizea/2.
    maxa = x + binsizea/2.
    binsizeb = binedgesb[1] - binedgesb[0]
    minb = y - binsizeb/2.
    maxb = y + binsizeb/2.
    binsizer = binedgesr[1] - binedgesr[0]
    minr = r - binsizer/2.
    maxar= r + binsizer/2.

    binedgesa = num.linspace(mina,maxa,nbinsa+1)
    bincentersa = (binedgesa[:-1]+binedgesa[1:])/2.
    binedgesb = num.linspace(minb,maxb,nbinsb+1)
    bincentersb = (binedgesb[:-1]+binedgesb[1:])/2.
    binedgesr = num.linspace(minr,maxr,nbinsr+1)
    bincentersr = (binedgesr[:-1]+binedgesr[1:])/2.
    
    [x,y,r] = detectcircles(edgemag,binedgesa=binedgesa,
                            bincentersb=bincentersb,
                            bincentersr=bincentersr,
                            peaksnhoodsize=peaksnhoodsize,
                            peaksthreshold=0.,
                            maxncircles=1)
    
    return [x,y,r]

def sub2ind(sz,sub):

    nd = len(sub)
    ind = num.zeros(sub[0].shape,dtype='int')
    d = 1
    for i in range(nd-1,-1,-1):
        ind += sub[i]*d
        d *= sz[i]
    return ind

def houghcirclepeaks(h,numpeaks,threshold,nhood):

    # initialize the loop variables
    hnew = h
    nhood_center = (nhood-1)/2
    ia = num.array([],dtype='int')
    ib = num.array([],dtype='int')
    ir = num.array([],dtype='int')
    score = num.array([])

    while True:

        max_idx = num.argmax(hnew)
        (p,q,r) = ind2sub(hnew.shape,max_idx)

        if hnew[p,q,r] < threshold:
            break

        ia = num.append(ia,p)
        ib = num.append(ib,q)
        ir = num.append(ir,r)
        score = num.append(score,hnew[p,q,r])
        
        # suppress this maximum and its close neighbors
        p1 = p - nhood_center[0]
        p2 = p + nhood_center[0]
        q1 = q - nhood_center[1]
        q2 = q + nhood_center[1]
        r1 = r - nhood_center[2]
        r2 = r + nhood_center[2]
        
        # throw away out of bounds coordinates
        p1 = max(p1,0)
        p2 = min(p2,h.shape[0]-1)
        q1 = max(q1,0)
        q2 = min(q2,h.shape[1]-1)
        r1 = max(r1,0)
        r2 = min(r2,h.shape[2]-1)
        
        hnew[p1:p2,q1:q2,r1:r2] = 0

        if len(ir) == numpeaks:
            break

    return [ia,ib,ir,score]


def detectcircles(edgemag,
                  binedgesa=None,bincentersb=None,bincentersr=None,nbinsa=10,
                  nbinsb=10,nbinsr=10,mina=0.,minb=0.,minr=None,
                  maxa=None,maxb=None,maxr=None,
                  peaksnhoodsize=None,peaksthreshold=None,maxncircles=1):

    # set parameters
    (binedgesa,bincentersa,bincentersb,bincentersr,nbinsa,nbinsb,nbinsr,
     peaksnhoodsize,peaksthreshold,maxncircles) = \
     detectcircles_setparameters(edgemag,binedgesa,bincentersb,bincentersr,nbinsa,nbinsb,nbinsr,
                                 mina,minb,minr,maxa,maxb,maxr,peaksnhoodsize,peaksthreshold,maxncircles)

    bw = edgemag>0
    [r,c] = num.where(bw)
    c = c.astype('float')
    r = r.astype('float')
    w = edgemag[bw]
    npts = len(r)
    # find circles using the hough transform
    acc = hough.houghcircles(c,r,w,binedgesa,bincentersb,bincentersr)
    
    if peaksthreshold is None:
        peaksthreshold = num.max(acc)/2.

    [idxa,idxb,idxr,score] = houghcirclepeaks(acc,maxncircles,peaksthreshold,peaksnhoodsize)

    #idx = num.argmax(acc)
    #(idxa,idxb,idxr) = ind2sub([nbinsa,nbinsb,nbinsr],idx)

    x = bincentersa[idxa]
    y = bincentersb[idxb]
    r = bincentersr[idxr]

    return (x,y,r)

def ind2sub(sz,ind):

    n = len(sz)
    sub = ()
    for i in range(n-1,0,-1):
        sub = (ind % sz[i],) + sub
        ind = (ind - sub[0])/sz[i]
    sub = (ind,)+sub

    return sub
    
def edge(im,sigma=1.):

    im = im.astype('float')

    m = im.shape[0]
    n = im.shape[1]

    # Magic numbers
    GaussianDieOff = .0001
    PercentOfPixelsNotEdges = .99

    # Design the filters - a Gaussian and its derivative

    # possible widths
    pw = num.array(range(1,31))
    ssq = sigma**2
    width, = num.where(num.exp(-pw**2/(2.*ssq))>GaussianDieOff)
    if len(width) == 0:
        width = 1
    else:
        width = width[-1]

    # gaussian 1D filter
    t = num.array(range(-width,width+1))
    t = t.astype('float')
    gau = num.exp(-(t*t)/(2.*ssq))/(2.*num.pi*ssq)
    
    # Find the directional derivative of 2D Gaussian (along X-axis)
    # Since the result is symmetric along X, we can get the derivative along
    # Y-axis simply by transposing the result for X direction.
    [y,x] = num.mgrid[-width:(width+1),-width:(width+1)]
    dgau2D=-x*num.exp(-(x**2+y**2)/(2.*ssq))/(num.pi*ssq)

    # smooth the image out
    gau = gau.reshape([1,len(t)])
    imSmooth = signal.convolve2d(im,gau,'same','symm')
    imSmooth = signal.convolve2d(imSmooth,gau.T,'same','symm')
    
    # apply directional derivatives
    imx = signal.convolve2d(imSmooth,dgau2D,'same','symm')
    imy = signal.convolve2d(imSmooth,dgau2D.T,'same','symm')

    # compute the squared edge magnitude
    mag = num.sqrt(imx**2 + imy**2)

    # normalize
    magmax = num.max(mag)
    if magmax > 0:
        mag /= magmax

    return mag

def detectcircles_setparameters(im,binedgesa,bincentersb,bincentersr,nbinsa,nbinsb,nbinsr,
                                mina,minb,minr,maxa,maxb,maxr,peaksnhoodsize,peaksthreshold,maxncircles):

    # set parameters
    nr = im.shape[0]
    nc = im.shape[1]
    if maxa is None:
        maxa = float(nc-1)
    if maxb is None:
        maxb = float(nr-1)
    if minr is None:
        minr = min(nr,nc)/4.
    if maxr is None:
        maxr = min(nr,nc)/2.
    if binedgesa is None:
        binedgesa = num.linspace(mina,maxa,nbinsa+1)
    bincentersa = (binedgesa[:-1] + binedgesa[1:])/2.
    if bincentersb is None:
        binedgesb = num.linspace(minb,maxb,nbinsb+1)
        bincentersb = (binedgesb[:-1] + binedgesb[1:])/2.
    if bincentersr is None:
        binedgesr = num.linspace(minr,maxr,nbinsr+1)
        bincentersr = (binedgesr[:-1] + binedgesr[1:])/2.
    nbinsa = len(bincentersa)
    nbinsb = len(bincentersb)
    nbinsr = len(bincentersr)
    
    if peaksnhoodsize is None:
        peakratio = 50.
        peaksnhoodsize = num.array([len(bincentersa)/peakratio,
                                    len(bincentersb)/peakratio,
                                    len(bincentersr)/peakratio])
        peaksnhoodsize = max(2*num.ceil(peaksnhoodsize/2.) + 1, 1)

    return (binedgesa,bincentersa,bincentersb,bincentersr,nbinsa,nbinsb,nbinsr,
            peaksnhoodsize,peaksthreshold,maxncircles)

def resize_image_for_speed(im):
    
    # resize the image for speed
    nr0 = im.shape[0]
    nc0 = im.shape[1]
    if RESIZE > min(nr0,nc0):
        nc_resize_ratio = 1.
        nr_resize_ratio = 1.
        nc = nc0
        nr = nr0
    else:
        if nr0 < nc0:
            nc = nc0*RESIZE/nr0
            nr = RESIZE
            # multiply by nc_resize_ratio to go from real coordinates to smaller, resized
            # coordinates
            nc_resize_ratio = float(nc)/float(nc0)
            nr_resize_ratio = float(nr)/float(nr0)
        else:
            nr = nr0*RESIZE/nc0
            nc = RESIZE
            nc_resize_ratio = float(nc)/float(nc0)
            nr_resize_ratio = float(nr)/float(nr0)
        im = pilutil.imresize(im,[nr,nc])

    return (im,nr_resize_ratio,nc_resize_ratio)

# ellipses_draw.py
# split from ellipsesk JAB 8/20/11

import os

import numpy as num
import wx
from wx import xrc

import codedir
from params import params
import imagesk
from ellipsesk import TargetList

from version import DEBUG

USEGL = False
if USEGL:
    import motmot.wxglvideo.simple_overlay as wxvideo
else:
    import motmot.wxvideo.wxvideo as wxvideo

ZOOM_RSRC_FILE = os.path.join(codedir.codedir,'xrc','ellipses_zoom.xrc')
SETTINGS_RSRC_FILE = os.path.join(codedir.codedir,'xrc','ellipses_settings.xrc')

DEFAULT_WIND_SIZE = 20
DEFAULT_IMG = num.ones( (DEFAULT_WIND_SIZE,DEFAULT_WIND_SIZE), num.uint8 )*127


class EllipseWindow:
    """Container class for each ellipse drawing window."""
    def __init__( self, img_panel, ell_id=0 ):
        # create drawing window
        self.box = wx.BoxSizer( wx.HORIZONTAL )
        self.window = wxvideo.DynamicImageCanvas( img_panel, -1 )
        self.window.set_resize(True)
        self.box.Add( self.window, 1, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL )

        # create spin control and text label in a separate sizer
        inbox = wx.BoxSizer( wx.HORIZONTAL )
        self.stext = wx.StaticText( img_panel, -1, "ID" )
        inbox.Add( self.stext, 0, wx.ALIGN_CENTER_VERTICAL )
        self.spinner = wx.SpinCtrl( img_panel, -1, min=0, max=params.nids,
                                    size=(params.id_spinner_width,-1),
                                    style=wx.SP_ARROW_KEYS|wx.SP_WRAP )
        self.spinner.SetValue( ell_id )
        inbox.Add( self.spinner, 0, wx.ALIGN_CENTER_VERTICAL )
        img_panel.Bind(wx.EVT_SPINCTRL,self.OnSpinner,self.spinner)
        
        self.box.Add( inbox, 0, wx.ALIGN_TOP )

        # initialize display information
        self.ellipse_size = None
        self.data = DEFAULT_IMG
        self.offset = (0,0)
        self.ellipses = TargetList()
        self.color = [0,0,0]
        self.name = 'ellipse_%d'%ell_id

    def set_ellipse_size( self ):
        ind = self.spinner.GetValue()
        if self.ellipses.hasItem( ind ):
            self.ellipse_size = int( 8*self.ellipses[ind].major )
        else:
            self.ellipse_size = None

    def SetData(self,ellipses,img):
        self.ellipses = ellipses
        self.data = img
        self.spinner.SetRange(0,params.nids-1)
        if self.ellipse_size is None:
            self.set_ellipse_size()

    def OnSpinner(self,evt):
        self.set_ellipse_size()
        self.redraw()

    def redraw(self,eraseBackground=False):
        """Scale data and draw on window."""

        ind = self.spinner.GetValue()

        if self.ellipse_size is None:
            wind_size = DEFAULT_WIND_SIZE
        else:
            wind_size = self.ellipse_size
        
        if not self.ellipses.hasItem(ind):
            blank = num.ones( (self.data.shape[0],self.data.shape[1]), num.uint8 )*127
            self.window.update_image_and_drawings(self.name,blank,format='MONO8')
        else:
            # get box around ellipse
            valx = self.ellipses[ind].center.x - self.ellipse_size/2
            valx = max( valx, 0 )
            valx = min( valx, self.data.shape[1] - self.ellipse_size )
            valy = self.ellipses[ind].center.y - self.ellipse_size/2
            valy = max( valy, 0 )
            valy = min( valy, self.data.shape[0] - self.ellipse_size )
            self.offset = (valx,valy)
            zoomaxes = [self.offset[0],self.offset[0]+self.ellipse_size-1,
                        self.offset[1],self.offset[1]+self.ellipse_size-1]
            linesegs = draw_ellipses([self.ellipses[ind],],
                                     colors=[params.colors[ind%len(params.colors)],])
            im = imagesk.double2mono8(self.data,donormalize=False)
            linesegs,im = imagesk.zoom_linesegs_and_image(linesegs,im,zoomaxes)
            (linesegs,linecolors) = imagesk.separate_linesegs_colors(linesegs)
            self.window.update_image_and_drawings(self.name,im,format='MONO8',
                                                  linesegs=linesegs,lineseg_colors=linecolors)
            self.window.Refresh( eraseBackground=eraseBackground )

    def __del__( self ):
        try:
            self.window.Destroy() # could fail if EllipseFrame is already closed
            self.spinner.Destroy()
            self.stext.Destroy()
        except:
            pass

            
class EllipseFrame:
    """Window to show zoomed objects with their fit ellipses."""
    def __init__( self, parent ):
        rsrc = xrc.XmlResource( ZOOM_RSRC_FILE )
        self.frame = rsrc.LoadFrame( parent, "frame_ellipses" )

        self.n_ell_spinner = xrc.XRCCTRL( self.frame, "spin_n_ellipses" )
        self.frame.Bind( wx.EVT_SPINCTRL, self.OnNEllSpinner, id=xrc.XRCID("spin_n_ellipses") )

        # set up image panel
        self.img = DEFAULT_IMG
        self.img_panel = xrc.XRCCTRL( self.frame, "panel_show" )
        self.img_box = wx.BoxSizer( wx.VERTICAL )
        self.img_panel.SetSizer( self.img_box )

        # make ellipse window
        self.ellipses = TargetList()
        self.ellipse_windows = [EllipseWindow( self.img_panel, 0 )]
        self.n_ell = 1
        #self.n_ell_spinner.SetValue( self.n_ell )

        # add ellipse window to img_panel
        self.img_box.Add( self.ellipse_windows[0].box, 1, wx.EXPAND )
        self.img_panel.SetAutoLayout( True )
        self.img_panel.Layout()

        self.frame.Show()

    def SetData(self,ellipses,img):
        self.ellipses = ellipses
        self.img = img
        for window in self.ellipse_windows:
            window.SetData(ellipses,img)
        if len( ellipses ) > 0:
            self.n_ell_spinner.Enable( True )

    def AddEllipseWindow( self, id ):
        id_list = [] # currently shown IDs
        for window in self.ellipse_windows:
            id_list.append( window.spinner.GetValue() )
        id_list.append(id)
        self.SetEllipseWindows(id_list)
        self.n_ell += 1
        self.n_ell_spinner.SetValue(self.n_ell)

    def OnNEllSpinner( self, evt ):
        """Remove or add a window."""

        id_list = [] # currently shown IDs
        for window in self.ellipse_windows:
            id_list.append( window.spinner.GetValue() )
                
        # determine whether to add or remove a window
        new_n_ell = self.n_ell_spinner.GetValue()
        if new_n_ell > self.n_ell:
            # add a window; try to be intelligent about which initial ID
            max_id = params.nids
            use_id = max_id-1
            while use_id in id_list and use_id >= 0:
                use_id -= 1
            id_list.append(use_id)
        elif new_n_ell < self.n_ell:
            id_list.pop()
        
        self.SetEllipseWindows(id_list)
        self.n_ell = new_n_ell
    
    def SetEllipseWindows(self,id_list):
        self.img_box.DeleteWindows()
        #for i in range(len(self.ellipse_windows)):
        #    self.ellipse_windows[i].Destroy()
        self.ellipse_windows = []
        for id in id_list:
            self.ellipse_windows.append( EllipseWindow( self.img_panel, id ) )
            self.ellipse_windows[-1].SetData(self.ellipses,self.img)
            self.img_box.Add( self.ellipse_windows[-1].box, 1, wx.EXPAND )
            # TODO: update a zoom window when its spinctrl spins
            #self.frame.Bind( wx.EVT_SPINCTRL, self.ellipse_windows[-1].

        # resize panel
        self.img_box.Layout()
        self.img_panel.Layout()
        self.Redraw(True)

    def Redraw( self,eraseBackground=False ):
        """Scale images and display."""
        for window in self.ellipse_windows:
            window.redraw(eraseBackground=eraseBackground)


def draw_ellipses( targets, thickness=1, step=10*num.pi/180., colors=None ):
    """Returns a list of line segments corresponding to ellipse perimeters.
Skips empty ellipses (center==size==area==0)."""

    if hasattr(targets,'iteritems'):
        targetiterator = targets.iteritems()
    else:
        targetiterator = enumerate(targets)

    if colors is None:
        colors = params.colors

    # create list of lines to draw
    lines = []
    for i, target in targetiterator:
        # don't draw empty ellipses
        if target.isEmpty(): continue

	# color of this ellipse
	color = colors[i % len( colors )]

        # create line	
        points = []
        alpha = num.sin( target.angle )
        beta = num.cos( target.angle )
	
	# do the first point
	aa = 0.
        ax = 2.*target.size.width * num.cos( aa )
        ay = 2.*target.size.height * num.sin( aa )
        xx = target.center.x + ax*alpha - ay*beta
        yy = target.center.y - ax*beta - ay*alpha

        for aa in num.arange( step, (2.*num.pi+step), step ):
	    
	    # save previous position
	    xprev = xx
	    yprev = yy

            ax = 2.*target.size.width * num.cos( aa )
            ay = 2.*target.size.height * num.sin( aa )
            xx = target.center.x + ax*alpha - ay*beta
            yy = target.center.y - ax*beta - ay*alpha
	    
            lines.append([xprev+1,yprev+1,xx+1,yy+1,color])

    return lines


def draw_ellipses_bmp( img, targets, thickness=1, step=10*num.pi/180., colors=params.colors, windowsize=None, zoomaxes=None ):
    """Draw ellipses on a color image (MxNx3 numpy array).
    Refuses to draw empty ellipses (center==size==area==0)."""

    if zoomaxes is None:
        zoomaxes = [0,img.shape[1]-1,0,img.shape[0]-1]
    
    if hasattr(targets,'iteritems'):
        targetiterator = targets.iteritems()
    else:
        targetiterator = enumerate(targets)

    # create list of line colors
    linecolors = []
    for i, target in targetiterator:
        # don't draw empty ellipses
        if target.isEmpty(): continue
        # set color
        linecolors.append(colors[i%len(colors)])

    if hasattr(targets,'iteritems'):
        targetiterator = targets.iteritems()
    else:
        targetiterator = enumerate(targets)

    # create list of lines to draw
    linelists = []
    for i, target in targetiterator:
        # don't draw empty ellipses
        if target.isEmpty(): continue
        # create line
        points = []
        alpha = num.sin( target.angle )
        beta = num.cos( target.angle )
        for aa in num.arange( 0., (2.*num.pi+step), step ):
            ax = 2.*target.size.width * num.cos( aa )
            ay = 2.*target.size.height * num.sin( aa )
            xx = target.center.x + ax*alpha - ay*beta
            yy = target.center.y - ax*beta - ay*alpha
            if xx < zoomaxes[0] or xx > zoomaxes[1] or yy < zoomaxes[2] or yy > zoomaxes[3]: continue
            points.append([xx+1,yy+1])
        linelists.append(points)

    bmp = imagesk.draw_annotated_image(img,linelists=linelists,windowsize=windowsize,zoomaxes=zoomaxes,
                                       linecolors=linecolors)

    return bmp

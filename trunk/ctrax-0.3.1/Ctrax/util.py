#
# utilities
#
# 4 Aug 2013 by Ulrich Stern
#

import cv2
import numpy as np
import cPickle
import os, platform, sys
import re, operator, time, collections

import util

# - - -

# OpenCV-style (BGR)
COL_W = 3*(255,)
COL_BK = (0,0,0)
COL_B = (255,0,0)
COL_G = (0,255,0)
COL_G_L = (64,255,64)
COL_G_D = (0,192,0)
COL_R = (0,0,255)
COL_Y = (0,255,255)
COL_O = (0,127,255)

JPG_X = re.compile(r'\.jpg$', re.IGNORECASE)
AVI_X = re.compile(r'\.avi$', re.IGNORECASE)

MODULE_DIR = os.path.dirname(os.path.realpath(__file__))

MAC = platform.system() == 'Darwin'

# - - - general

# raise this for internal errors
class InternalError(Exception):
  pass

# print warning
def warn(msg):
  print "warning: %s" %msg

# print message and exit
def error(msg):
  print "error: %s" %msg
  sys.exit(1)

# returns anonymous object with the given attributes (dictionary)
# note: cannot be pickled
def anonObj(attrs=None):
  return type('', (), {} if attrs is None else attrs)

# returns tuple with rounded ints
def intR(*val):
  if val and isinstance(val[0], collections.Iterable):
    val = val[0]
  return tuple([int(round(v)) for v in val])

# returns the distance of two points
def distance(pnt1, pnt2):
  return np.linalg.norm(np.array(pnt1)-pnt2)

# converts the given seconds since epoch to YYYY-MM-DD HH:MM:SS format
def time2str(secs):
  return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(secs))

# - - - tuples

# returns t2 as tuple
#  if t2 is int, float, or string, t2 is replicated len(t1) times
#  otherwise, t2 is passed through
def _toTuple(t1, t2):
  if isinstance(t2, (int,float,str)):
    t2 = len(t1) * (t2,)
  return t2

# applies the given operation to the given tuples; t2 can also be number
def tupleOp(op, t1, t2):
  return tuple(map(op, t1, _toTuple(t1, t2)))

# tupleOp() add
def tupleAdd(t1, t2): return tupleOp(operator.add, t1, t2)

# tupleOp() subtract
def tupleSub(t1, t2): return tupleOp(operator.sub, t1, t2)

# tupleOp() multiply
def tupleMul(t1, t2): return tupleOp(operator.mul, t1, t2)

# - - - file

# returns absolute path for file that is part of package given relative name
def packageFilePath(fn):
  return os.path.join(MODULE_DIR, fn)

# backs up (by renaming) the given file
def backup(fn):
  if os.path.isfile(fn):
    fn1 = fn+'.1'
    if os.path.isfile(fn1):
      os.remove(fn1)
    os.rename(fn, fn1)

# saves the given object in the given file, possibly creating backup
def pickle(obj, fn, backup=False):
  if backup:
    util.backup(fn)
  f = open(fn, 'wb')
  cPickle.dump(obj, f, -1)
  f.close()

# loads object from the given file
def unpickle(fn):
  if not os.path.isfile(fn):
    return None
  f = open(fn, 'rb')
  obj = cPickle.load(f)
  f.close()
  return obj

# - - - OpenCV

# show image, possibly resizing window
def imshow(winName, img, resizeFctr=None, maxH=1000):
  h, w = img.shape[:2]
  h1 = None
  if resizeFctr is None and h > maxH:
    resizeFctr = float(maxH)/h
  if resizeFctr is not None:
    h1, w1 = intR(h*resizeFctr, w*resizeFctr)
    if MAC:
      img = cv2.resize(img, (0,0), fx=resizeFctr, fy=resizeFctr)
    else:
      cv2.namedWindow(winName, cv2.WINDOW_NORMAL)
  cv2.imshow(winName, img)
  if h1 and not MAC:
    cv2.resizeWindow(winName, w1, h1)

# min max normalizes the given image
def normalize(img, min=0, max=255):
  return cv2.normalize(img, None, min, max, cv2.NORM_MINMAX, -1)

# shows normalized image
def showNormImg(winName, img):
  imshow(winName, normalize(img, max=1))

# converts the given image to gray
def toGray(img):
  return img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# returns rectangular subimage, allowing tl and br points outside the image
# note: tl is included, br is excluded
def subimage(img, tl, br):
  h, w = img.shape[:2]
  tlx, tly = tl
  brx, bry = br
  return img[max(tly,0):min(bry,h), max(tlx,0):min(brx,w)]

# returns image rotated by the given angle (in degrees, counterclockwise)
def rotateImg(img, angle):
  cntr = tupleMul(img.shape[:2], .5)
  mat = cv2.getRotationMatrix2D(cntr, angle, 1.)
  return cv2.warpAffine(img, mat, img.shape[:2], flags=cv2.INTER_LINEAR)

# returns the median of the given image
def median(img):
  return np.median(img.copy())

# returns Canny edge image and fraction of non-black pixels (before post blur)
def edgeImg(img, thr1=20, thr2=100, preBlur=True, postBlur=True, preNorm=False):
  img = toGray(img)
  if preNorm:
    img = normalize(img)
  if preBlur:
    img = cv2.GaussianBlur(img, (3, 3), 0)
  img = cv2.Canny(img, thr1, thr2)
  nz, npx = img.nonzero()[0].size, img.shape[0]*img.shape[1]
  if postBlur:
    img = cv2.GaussianBlur(img, (3, 3), 0)
  return img, float(nz)/npx

# matches the given template(s) against the given image(s)
#  e.g., (img, tmpl, img2, tmpl2, 0.5)
#    note: second match is weighted with factor 0.5 (default: 1)
# returns result image, top left x, top left y, bottom right (as tuple),
#  minimum distance between template and image border, match value,
#  and non-normalized match values
def matchTemplate(img, tmpl, *args):
  imgs, tmpls, fctrs = [img], [tmpl], [1]
  idx = 0
  for arg in args:
    if isinstance(arg, (int,float)):
      fctrs[idx] = arg
    else:
      if idx > len(tmpls)-1:
        tmpls.append(arg)
      else:
        imgs.append(arg)
        fctrs.append(1)
        idx += 1
  res, maxVals = 0, []
  for i, t, f in zip(imgs, tmpls, fctrs):
    r = cv2.matchTemplate(i, t, cv2.TM_CCOEFF_NORMED)
    maxVals.append(cv2.minMaxLoc(r)[1])
    if len(imgs) > 1:
      r = normalize(r, max=1) * f
    res += r
  minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(res)
  tlx, tly = maxLoc
  br = (tlx+tmpl.shape[1], tly+tmpl.shape[0])
  minD = min(min(maxLoc), img.shape[1]-br[0], img.shape[0]-br[1])
  return res, tlx, tly, br, minD, maxVal, maxVals

# returns tuple with text width, height, and baseline; style is list with
#  putText() args fontFace, fontScale, color, thickness, ...
# note: 'o', 'g', and 'l' are identical in height and baseline
def textSize(txt, style):
  wh, baseline = cv2.getTextSize(txt, *[style[i] for i in [0,1,3]])
  return wh + (baseline,)

# puts the given text on the given image; whAdjust adjusts the text position
#  using text width and height (e.g., (-1, 0) subtracts the width)
def putText(img, txt, pos, whAdjust, style):
  adj = tupleMul(whAdjust, textSize(txt, style)[:2])
  cv2.putText(img, txt, tupleAdd(pos, adj), *style)

# returns FOURCC for the given VideoCapture (e.g., 'MJPG')
def fourcc(cap):
  fcc = int(cap.get(cv2.cv.CV_CAP_PROP_FOURCC))
  return "".join([chr(fcc >> s & 0xff) for s in range(0,32,8)])

# - - -

if __name__ == "__main__":
  print "TO DO: add tests"


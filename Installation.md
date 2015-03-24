## Building yanglab-ctrax ##

_yanglab-ctrax_ refers to "Ctrax that includes the Yang Lab extensions" here.  There is no installer at this point, and the installation requires building Ctrax from source.

  * Download the [Ctrax 0.3.1 source code](http://sourceforge.net/projects/ctrax/files/Ctrax%20source/).  Version 0.3.1 of Ctrax is what our extensions were developed for.
  * Follow the [instructions for building Ctrax from source](http://ctrax.sourceforge.net/install.html#distutils) with these changes:
    * Additional requirements
      * NumPy ≥ 1.7
        * Ctrax already requires NumPy ≥ 1.3; for new installs, NumPy ≥ 1.7 will likely be true automatically.
      * [OpenCV](http://opencv.org)
        * On Windows, I usually just copy cv2.pyd (included in the OpenCV Windows package) to C:\Python27\Lib\site-packages\, kudos to [this blog post](http://opencvpython.blogspot.com/2012/05/install-opencv-in-windows-for-python.html).
    * After the step to extract Ctrax-0.3.1.tar.gz, execute the following commands to get our extensions into the Ctrax source (i.e., patch the source)
```
cd ctrax-0.3.1
svn co https://yanglab-ctrax.googlecode.com/svn/trunk/ctrax-0.3.1/Ctrax --force
svn revert --depth=infinity Ctrax
```
> > and continue the build instructions.
    * We have some [notes](http://yanglab.pbworks.com/Building-Ctrax) on our "experiences" building Ctrax on our lab's Wiki.  The notes are mainly about Windows since we do all our tracking on several Windows 7 machines.
  * After you successfully built Ctrax, you should see the following in the stdout/stderr window when you start it:
```
******** Ctrax Warning and Error Messages ********
>>> Yang Lab version <<<
...
```
    * On Windows, I usually copy Ctrax.bat (from the [run-ctrax](https://code.google.com/p/yanglab-ctrax/source/browse/#svn%2Ftrunk%2Frun-ctrax) directory, see next section) into C:\Python27\Scripts and can then call the self-built Ctrax with `Ctrax.bat`.


## Installing the script to _run_ yanglab-ctrax ##

We run tracking exclusively from the command line via a script -- **runCtrax.py** -- that runs several Ctrax processes in parallel.  (But we start the GUI, e.g., to examine tracking problems.)

The runCtrax.py script and some files it needs can be installed in a directory of your choice using
```
svn co https://yanglab-ctrax.googlecode.com/svn/trunk/run-ctrax
```

The run-ctrax directory contains "template images" that are needed by both yanglab-ctrax and our analysis scripts.  The best way to let the code know the path to the template images is by creating the environment variable
```
YL_TMPLT_PATH
```
and setting its value to the path of your run-ctrax directory (e.g., "C:/SSD/tracking/run-ctrax").

## Installing our (MATLAB) analysis scripts ##

  * Download the [Ctrax Matlab Toolboxes](http://sourceforge.net/projects/ctrax/files/Matlab%20complete/).
    * Our analysis scripts depend only "mildly" on the version of the Matlab Toolboxes; both versions 0.2.11 and 0.2.16 work.
  * After you unzipped the Ctrax-allmatlab zip file, execute the following commands:
```
cd Ctrax-allmatlab-X.Y.Z
svn co https://yanglab-ctrax.googlecode.com/svn/trunk/Ctrax-allmatlab/yanglab
```

## Installing the goodies ##

The goodies are currently only some scripts to automate Avidemux video conversions.  I [posted](https://groups.google.com/d/msg/ctrax/ZdFBLfGYdTw/rWPVJFCXs20J) some of the scripts on the Ctrax Google Group.  Note the the scripts required Avidemux [2.5.6](http://sourceforge.net/projects/avidemux/files/avidemux/2.5.6/) last time I checked.

The goodies can be installed in a directory of your choice using
```
svn co https://yanglab-ctrax.googlecode.com/svn/trunk/goodies
```

## Next step ##

The [Usage](Usage.md) page describes how to track and analyze for a sample video.
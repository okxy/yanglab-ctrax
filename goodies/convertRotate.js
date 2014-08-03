//AD  <- needed by Avidemux
//
// Avidemux script ("project") to convert all videos matching FILES_TO_CONV
// in the directory the user selects
//
// 17 Aug 2012 by Ulrich Stern
//
// notes
// * execute this script via File -> Load/Run Project
// * I first tried to automate Avidemux via the command line, but the
//  --filters command did not work for me (Avidemux 2.5.6, Windows 7)

var DEBUG = false;

var FILES_TO_CONV = /\.avi$/;
var REPLACE = FILES_TO_CONV;   // how output filename is derived from input
var WITH = ' AD.avi';          //  filename
var FIRST_FRAME = 3;           // use non-zero value to skip frames from the
                               //  beginning of the input video

var app = new Avidemux();
var ds = new DirectorySearch();

displayInfo('Please select video directory by selecting a file in it.');
var dir = pathOnly(fileReadSelect());
if (! ds.Init(dir))
  displayError('Could not init DirectorySearch for dir='+dir);
while (ds.NextFile()) {
  var f = ds.GetFileName();
  if (FILES_TO_CONV.test(f))
    convert(dir, f);
}
displayInfo('Converted all videos.');

// convert the given file in the given directory
// note: JavaScript sample code can be generated by configuring Avidemux for
//  the desired video conversion and then File -> Save Project As
function convert(dir, f) {
  if (DEBUG) displayInfo('file: '+f);
  app.load(dir+'/'+f);
  app.markerA = FIRST_FRAME;

  // filters
  app.video.addFilter("resamplefps","newfps=7500","use_linear=0");
  app.video.addFilter("lumaonly");
  app.video.addFilter("rotate","width=480","height=640","angle=90");

  // codec
  app.video.codecPlugin("075E8A4E-5B3D-47c6-9F70-853D6B855106",
    "mjpeg", "CBR=1000", "(null)");

  // save AVI
  app.setContainer("AVI");
  app.save(dir+'/'+f.replace(REPLACE, WITH));

  // save jpg
  app.currentFrame = app.markerB;
  app.video.saveJpeg(dir+'/'+f.replace(REPLACE, ".jpg").replace(/^c/, "p"));
}


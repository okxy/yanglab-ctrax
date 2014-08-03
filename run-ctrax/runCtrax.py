#
# run Ctrax in parallel
#
# 18 Mar 2012 by Ulrich Stern
#
# notes:
# * on Yang-Lab-Dell (Dell XPS 8300), one can run 4 copies of Ctrax in
#  parallel with essentially no slowdown
#

import subprocess, sys, os, time, re, string

DEBUG = True

PY_EX, LOG_DIR = sys.executable, "log/"
RUN_DIR = os.path.dirname(os.path.realpath(__file__))
BASE_DIR = os.path.dirname(RUN_DIR)

AD_AVI, AVI = re.compile(r"AD\.avi$"), re.compile(r"\.avi$")
SETT_FILE = re.compile(r"^settings.*\.ann.*$")

# extracts the given parameter
# example line in settings file: n_bg_std_thresh:0.25
def xp(content, name, dflt=None):
    r = re.search('^'+name+r':(\S+)$', content, re.M)
    return r.groups()[0] if r else dflt

# - - -

if DEBUG and not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

settFs = [f for f in os.listdir(RUN_DIR) if SETT_FILE.match(f)]
settFList = "\n".join(["%d: %s" %(i+1, f) for i, f in enumerate(settFs)])

print """=== run Ctrax %s===

this script runs Ctrax in parallel for all movies ending in AD.avi in the
given subdirectory.

settings files:
%s
""" %("[DEBUG mode] " if DEBUG else "", settFList)

settF = settFs[int(raw_input('choose number: '))-1]
settFP = os.path.join(RUN_DIR, settF)
with open(settFP) as f:
    c = f.read()

print "\nchosen file: %s" %settF
print "  thresholds: %s and %s" \
    %(xp(c, 'n_bg_std_thresh'), xp(c, 'n_bg_std_thresh_low'))
print "  use shadow detector: %s" %(bool(int(xp(c, 'use_shadow_detector', 0))))
rbgm = int(xp(c, 'recalc_bg_minutes', 60))
print "  recalculate background: %s" %('%s min'%rbgm if rbgm else '-')
pfb = xp(c, 'percentile_for_bg')
print "  percentile for background: %s" %('-' if pfb is None else pfb)
print

sd = raw_input('movie subdirectory (of %s): ' %BASE_DIR)

movieDir = os.path.join(BASE_DIR, sd)
doneFile = movieDir+"/__done__"
if os.path.exists(doneFile):
    os.remove(doneFile)

of = open(os.devnull, "w")
ps, ofs = [], []

print "\nmovies:"

files = os.listdir("../"+sd)
for f in files:
    if (not AD_AVI.search(f)):
        continue
    vid = AVI.sub("", f)
    print "  %s" %vid
    cmd = [PY_EX, os.path.dirname(PY_EX)+"/Scripts/Ctrax",
      "--Interactive=False", "--AutoEstimateBackground=True",
      "--AutoEstimateShape=False", "--AutoDetectCircularArena=False",
      "--SettingsFile="+settFP, "--Input="+vid+".avi"]
    if DEBUG:
        of = open(LOG_DIR+vid+".out", "w")
        ofs.append(of)
        of.write(" ".join(cmd) + 2*'\n')
        of.flush()
    ps.append(subprocess.Popen(cmd, cwd=movieDir, stdout=of, stderr=of))

print "\ntracking..."

while any([p.poll() == None for p in ps]):
    time.sleep(1)

# the above poll-based "done detection" sometimes stopped before all
#  subprocesses were done, causing missing MAT-files
while True:
    if os.path.exists(doneFile):
        df = open(doneFile)
        done = df.read()
        df.close()
        if string.count(done, "d") == len(ps):
            break
    time.sleep(3)

# note: arguably better to move this into exception handler
for of in ofs:
    of.close()

raw_input("done.  Press enter to continue.")


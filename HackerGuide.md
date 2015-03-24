## Ctrax extensions ##

  * To see (almost) all of the changes to Ctrax 0.3.1 to implement the Ctrax extensions, check out [r6](https://code.google.com/p/yanglab-ctrax/source/detail?r=6).
  * The on/off detector (see [paper](http://arxiv.org/abs/1409.7272)) learns the on/off state for each frame during tracking, and adds the info to the Ctrax MAT-file in field `YL_on_changes`.  The format is best explained in an example:
```
>> trx(1).YL_on_changes(1:5, :)

ans =

           1           1
        2237           0
        4488           1
        6740           0
        8992           1
```
    * There is one row for each _change_ in on/off state.
      * The first column has the number (index) of the _first_ frame in the new state.  (Following MATLAB style, the first frame of the video has number 1.)
      * The second column has the new state ("on"=1).
    * So in this example, the state was detected as "on" from frame 1 to 2236, then "off" from frame 2237 to 4487, etc.

## Analysis scripts ##

  * The code for the analysis scripts should be refactored.  E.g., it should be split into more files.  My so-so excuse is that I learned MATLAB while writing [analyze\_tracks.m](https://code.google.com/p/yanglab-ctrax/source/browse/trunk/Ctrax-allmatlab/yanglab/analyze_tracks.m) and that I dislike (strongly) that MATLAB does not seem to support multiple "utility" functions in a single file, typically resulting in too many files for my taste.
  * I used a nice trick to speed up [analyze\_tracks.m](https://code.google.com/p/yanglab-ctrax/source/browse/trunk/Ctrax-allmatlab/yanglab/analyze_tracks.m) more than 100-fold.  The code initially looped over each frame, and the runtime of this loop was starting to irritate me.  (About one minute for our typical 8h video with 216k frames, so not terrible, but I run the script often when working on it, and the code in the loop and, in turn, its runtime tended to grow from time to time.)  I hence replaced the _interpreted_ loop with array operations (where the frame index was one array dimension), reducing the runtime from about one minute to less than one second.  The rewrite made some parts of the code more complicated, but just a little.  For example, in the loop MATLAB's [det()](http://www.mathworks.com/help/matlab/ref/det.html) was used to calculate determinants for each frame.  Since MATLAB's det() can calculate only one determinant per call, without loop it needed to be replaced.  Fortunately, the determinants for _all_ frames can easily be calculated "manually" with just a few array operations.  In analyze\_tracks.m, the calculation looks like this:  (The third dimension in `m1` and `m2` is the frame index.)
```
  det = @(m) squeeze(m(1,1,:) .* m(2,2,:) - m(1,2,:) .* m(2,1,:))';
  [det1, det2] = deal(det(m1), det(m2));
```
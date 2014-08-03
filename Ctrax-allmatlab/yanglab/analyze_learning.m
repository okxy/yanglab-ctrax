%% analyze_learning

% script that analyzes Ctrax trajectories for learning experiments
%
% 3 Feb 2013 by Ulrich Stern
%
% notes:
% * originally based on simple_diagnostics
% * egg file line format: S|P,hh:mm:ss
%    details on fields:
%    - sucrose or plain (other types possible, too; shown in figure)
%    - end time for the "by egg" trajectory (e.g., time fly entered egg-laying area)
% * to select control areas:
%    area numbers: 1:Tl (Top left), 2:tL, 3:bL, 4:Bl, 5:Br, 6:bR, 7:tR, 8:Tr (clockwise)
%    e.g., YL.ca = [2,4];   % for tL,Bl

setuppath;

%% set all defaults

% whether to flip y values
%  Ctrax flips y values in MAT-file, e.g., for M-JPEG (see yanglab: Ctrax Bugs)
flipY = true;
height1 = 320 + 1;   % video used for tracking

% number of periods (intervals of equal size)
numPeriods = 8;   % 8 gives 1h periods for 8h videos

% number of seconds of trajectory to show before each egg-laying event
trackS = 30;

% how may frames convertCrop1080p cuts from beginning of video (FIRST_FRAME)
%  code assumes 1080p video is recorded at 7.5fps, which should likely be checked
firstFrame1080p = 20;

% whether to include position histograms
histograms = false;

% default control areas (see above)
if ~(exist('YL') && isfield(YL, 'ca'))
  YL.ca = [1,2];
end

debug = false;

matname = '';
matpath = '';
efname = '';
efpath = '';

%% load settings
scriptpath = which('analyze_learning');
settingsfile = strrep(scriptpath,'analyze_learning.m','.analyzelearningsrc.mat');
append = '';
if exist(settingsfile, 'file')
  load(settingsfile);
  append = '-append';
end

%% choose a mat file to analyze
[matname, matpath] = uigetfilehelp('*.mat', 'Choose mat file to analyze', [matpath, matname]);
if isnumeric(matname) && matname == 0,
  return;
end
fprintf('MAT-file: %s\n', matname);

[efname, efpath] = uigetfilehelp('*.txt', 'Choose an egg file (optional)', [efpath, efname]);
eggfile = ~(isnumeric(efname) && efname == 0);
if eggfile
  fprintf('egg file: %s\n', efname);
end
fprintf('\n');

%% save setting
if eggfile
  save(settingsfile,'matname','matpath','efname','efpath',append);
else
  save(settingsfile,'matname','matpath',append);
end

%% load the data
matname = [matpath,matname];
[trx,matname1,loadsucceeded] = load_tracks(matname);
  % note: load_tracks does not always return correct matname
if ~loadsucceeded,
  msgbox('Could not load trx from file %s\n',matname);
  return;
end

% remove flies with less than 2 frames of data
trx = prune_short_trajectories(trx, 2);

if eggfile
  ef = fopen([efpath, efname]);
  C = textscan(ef, '%s %u %u %u %s', 'delimiter', {',',':'}, 'commentStyle', '#');
  fclose(ef);

  if debug
    for e=1:length(C{1})
      fprintf('%d: %s %d:%d:%d\n', e, C{1}{e}, C{2}(e), C{3}(e), C{4}(e));
    end
  end
end
fprintf('\n');

%% checks and calculations
warn = @(m) fprintf('\n*** %s ***\n', m);

nflies = length(trx);
trxL = max([trx.nframes]);
if trxL ~= min([trx.nframes])
  warn('trajectory lengths differ');
end
if eggfile && nflies > 1
  warn('egg file requires single fly');
  return;
end

fps = trx(1).nframes / (trx(1).timestamps(end)-trx(1).timestamps(1));
fprintf('fps: %.1f\n', fps);

ncols = ceil(numPeriods/2);
p2idx = @(x, r, c) 1 + r*mod(x-1, c) + floor((x-1)/c);

% period length and indexes (fi:li)
pL = trxL/numPeriods;
p2fi = @(x) 1 + floor((x-1)*pL);
p2li = @(x) min(floor(x*pL), trxL);
fprintf('period length: %.1fh\n', pL/fps/3600);

% distance
dis = @(x1,y1, x2,y2) sqrt((x1-x2)^2 + (y1-y2)^2);

% get bounds for all flies
xA = [trx.x];
xA1 = xA(~isnan(xA) & ~isinf(xA));
yA = [trx.y];
yA1 = yA(~isnan(yA) & ~isinf(yA));
minx = min(xA1);
maxx = max(xA1);
miny = min(yA1);
maxy = max(yA1);
dx = maxx - minx;
dy = maxy - miny;

%% plot trajectories

figure('Name', 'Trajectories');

hold on;
for f = 1:nflies,
  plot(trx(f).x,trx(f).y,'k.-','markersize',3,'linewidth',.5);
end
hold off;
axis equal;
axis([minx-.02*dx, maxx+.02*dx, miny-.02*dy, maxy+.02*dy]);

%% plot trajectories by period

figure('Name', 'Trajectories by Period');
hax = createsubplots(2, ncols, 0.03)';

for p = 1:numPeriods

  axes(hax(p2idx(p, 2, ncols)));

  hold on;
  for f = 1:nflies,
    fi = p2fi(p);
    li = p2li(p);
%    if f == 1
%      fprintf('fi=%d, li=%d\n', fi, li);
%    end
    plot(trx(f).x(fi:li),trx(f).y(fi:li),'k.-','markersize',3,'linewidth',.5);
  end
  hold off;

  title(sprintf('period %d', p));
  axis equal;
  axis([minx-.02*dx,maxx+.02*dx,miny-.02*dy,maxy+.02*dy]);
  % hide axes (for paper)
  set(gca, 'XTick', [], 'XColor', 'w', 'YTick', [], 'YColor', 'w', 'ZColor', 'w');

end

%% template matching

% determine image name
imgname = '';
if matname
  imgname = regexprep(matname, '\\c(\d)(S?)__', '\\p$1$2__');
  imgname = regexprep(imgname, ' AD\.mat$', '.jpg');
  if strcmp(matname, imgname) || ~exist(imgname, 'file')
    imgname = '';
  end
end

% template matching
match = false;
if isempty(imgname)
  warn('could not get image');
else
  is1080p = false;
  tmpltE = '.jpg';
  if regexp(matname, '\\c\dS__')
    is1080p = true;
    tmpltE = '1080p.jpg';
  end
  fprintf('using template match to determine control areas\n');
  try
    res = python('match_template_old.py', imgname, ['C:/SSD/tracking/Ctrax/tmpltLearning', tmpltE], '1');
    rC = textscan(res, '%f %f %f', 'delimiter', ',');
    match = rC{3} >= 25;   % whether match worked
  catch
    warn('template match failed');
  end
  if match
    % coordinates for Tl, tL, bL, Bl, Br, bR, tR, and Tr from template
    if is1080p
      cx2 = [530;689;689;530;376;215;215;375] + rC{1};
      cy2 = [218;379;535;694;694;534;379;217] + rC{2};
    else
      cx2 = [317;411;412;316;225;131;131;226] + rC{1};
      cy2 = [131;226;317;413;412;318;226;132] + rC{2};
    end
    cx2 = cx2(YL.ca);
    cy2 = cy2(YL.ca);
    if is1080p
      cx = (cx2 - 420)*320/1060;
      cy = (cy2 - 20)*320/1060;
    else
      cx = (cx2 - 320)/2;
      cy = (cy2 - 30)/2;
    end
    if flipY
      cy = height1 - cy;
    end
    % area (circle) radius
    if is1080p
      cr2 = 48;
    else
      cr2 = 28;
    end
    cr = cr2/2;
    ma = mean(trx(1).a);
    mb = mean(trx(1).b);
    if abs(ma-2.6) > 0.5 || abs(mb-1) > 0.3
      warn(sprintf('mean values for a (%.2f) or b (%.2f) off', ma, mb));
    end
    crO = cr + ma*2/3;   % outer and inner
    crI = cr - mb*2;

    % edge coordinates
    if is1080p
      ex2 = [4;900;900;  4;4] + rC{1};
      ey2 = [5;  5;904;903;4] + rC{2};
      ex = (ex2 - 420)*320/1060;
      ey = (ey2 - 20)*320/1060;
    else
      ex2 = [4;536;536;  4;4] + rC{1};
      ey2 = [4;  4;537;537;4] + rC{2};
      ex = (ex2 - 320)/2;
      ey = (ey2 - 30)/2;
    end
    if flipY
      ey = height1 - ey;
    end

    % show circles and edge in image
    im = imread(imgname);
    figure('Name', 'control areas');
    imagesc(im);
    th = 0:0.01:2*pi;
    hold on;
    for i=1:length(cx2)
      plot(cx2(i)+cr2*cos(th), cy2(i)+cr2*sin(th), 'y');
    end
    plot(ex2, ey2, 'y');
    hold off;
    axis image;
  end
end

%% plot trajectories by egg
if eggfile

  fprintf('length of by egg trajectories: %ds\n', trackS);
  if is1080p
    fprintf('adjusting times by %d frames\n', firstFrame1080p);
  end

  numSPs = 18;   % subplots per figure
  ncolsBE = numSPs/3;
  idx1 = 1;
  t = 0;   % count of egg trajectories
  pIsE = true;   % previous isE
  pli = -trxL;   % previous li

  eForEach = sum(strcmp(C{5}, 'E')) >= length(C{1})/2;
  if eForEach
    warn('assuming the egg file is old style; ignoring E lines after non-E lines')
  end

  for e=1:length(C{1})

    isE = strcmp(C{5}{e}, 'E');
    skip = isE && ~pIsE;
    pIsE = isE;
    if eForEach && skip
      continue;
    end
    t = t + 1;

    idx1 = 1 + mod(t-1, numSPs);
    % start figure?
    if idx1 == 1
      figure('Name', sprintf('Trajectories by Egg (%d)', 1+floor((t-1)/numSPs)));
      hax = createsubplots(3, ncolsBE, 0.03)';
    end

    axes(hax(p2idx(idx1, 3, ncolsBE)));
    li = (C{2}(e)*3600 + C{3}(e)*60 + C{4}(e)) * fps;
    if is1080p
      li = li - firstFrame1080p;
    end
    fi = max(1, li - floor(trackS * fps));

    lnSp = 'b.-';
    if fi < pli
      lnSp = 'r.-';
    end
    mi = floor((fi+li)/2);
    hold on;
    if match
      plot(ex, ey, 'g','linewidth',.5);
    end
    plot(trx(1).x(fi:mi),trx(1).y(fi:mi),'k.:', ...
      trx(1).x(mi:li),trx(1).y(mi:li),lnSp,'markersize',3,'linewidth',.5);
    hold off;

    isES = '';
    if isE
      isES = ' E';
    end
    title(sprintf('egg %d (type %s) (%02d:%02d:%02d%s)', t, C{1}{e}, C{2}(e), C{3}(e), C{4}(e), isES));
    axis equal;
    axis([minx-.02*dx,maxx+.02*dx,miny-.02*dy,maxy+.02*dy]);
    pli = li;
  end

  % remove unused subplots
  if idx1 < numSPs
    for i=idx1+1:numSPs
      delete(hax(p2idx(i, 3, ncolsBE)));
    end
  end
end

%% plot controls for trajectories by egg
if eggfile && match

  cId = 0;   % id of area approached or where fly is (0 when fly away from areas)
  li = 0;    % frame index when crO crossed (0 when fly not between crO and crI)
  pli = -trxL;   % previous li
  t = 0;     % count of control trajectories
  for i=1:trxL
    x = trx(1).x(i);
    y = trx(1).y(i);
    if cId > 0   % approaching or in area
      d = dis(x,y, cx(cId),cy(cId));
      if d < crI
        if li > 0   % entry

          t = t + 1;
          idx1 = 1 + mod(t-1, numSPs);
          if idx1 == 1
            figure('Name', sprintf('Controls for Trajectories by Egg (%d)', 1+floor((t-1)/numSPs)));
            hax = createsubplots(3, ncolsBE, 0.03)';
          end

          axes(hax(p2idx(idx1, 3, ncolsBE)));
          fi = max(1, li - floor(trackS * fps));
          lnSp = 'b.-';
          if fi < pli
            lnSp = 'r.-';
          end
          mi = floor((fi+li)/2);
          hold on;
          plot(ex, ey, 'g','linewidth',.5);
          plot(trx(1).x(fi:mi),trx(1).y(fi:mi),'k.:', ...
            trx(1).x(mi:li),trx(1).y(mi:li),lnSp,'markersize',3,'linewidth',.5);
          hold off;
          time = li / fps;
          ts = floor(mod(time, 60));
          tm = mod(floor(time/60), 60);
          th = floor(time/3600);
          title(sprintf('control %d (%02d:%02d:%02d)', t, th, tm, ts));
          axis equal;
          axis([minx-.02*dx,maxx+.02*dx,miny-.02*dy,maxy+.02*dy]);

          pli = li;
          li = 0;
        end
      elseif d > crO
        cId = 0;   % no longer approaching or in area
      end
    else   % check whether approaching now?
      for c=1:length(cx)
        if dis(x,y, cx(c),cy(c)) < crO
          cId = c;
          li = i;
          break
        end
      end
    end
  end

  % remove unused subplots
  if t > 0 && idx1 < numSPs
    for i=idx1+1:numSPs
      delete(hax(p2idx(i, 3, ncolsBE)));
    end
  end

end

%% plot position histogram

if histograms
  figure('Name', 'Position Histogram');
  clf;

  nbinsx = 100;
  nbinsy = max(1,round(nbinsx*dy/dx));
  edgesx = linspace(minx,maxx,nbinsx+1);
  edgesy = linspace(miny,maxy,nbinsy+1);
  centersx = (edgesx(1:end-1)+edgesx(2:end))/2;
  centersy = (edgesy(1:end-1)+edgesy(2:end))/2;
  counts = hist3([[trx.x];[trx.y]]',{centersx,centersy});
  freq_position = counts / sum(counts(:));

  imagesc([centersx(1),centersx(end)],[centersy(1),centersy(end)],log(freq_position'));
  axis image;
  axis xy;
  colorbar;
end

%% plot position histogram by period

if histograms
  figure('Name', 'Position Histogram by Period');
  hax = createsubplots(2, ncols, 0.03)';

  for p = 1:numPeriods

    axes(hax(p2idx(p, 2, ncols)));

    counts = zeros(size(counts));
    for f = 1:nflies,
      fi = p2fi(p);
      li = p2li(p);
      counts = counts + hist3([[trx(f).x(fi:li)];[trx(f).y(fi:li)]]',{centersx,centersy});
    end
    freq_position = counts / sum(counts(:));

    imagesc([centersx(1),centersx(end)],[centersy(1),centersy(end)],log(freq_position'));
    title(sprintf('period %d', p));
    axis image;
    axis xy;
    %colorbar;

  end
end

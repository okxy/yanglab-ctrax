@echo off
rem  the parameter passing here does not work properly for Ctrax since it uses
rem  --foo=bar style parameters and = is delimiter in Windows
"C:\Python27\python.exe" "C:\Python27\Scripts\Ctrax" %1 %2 %3 %4 %5 %6 %7 %8 %9

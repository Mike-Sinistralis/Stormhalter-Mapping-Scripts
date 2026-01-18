cd backup
"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U postgres -d stormhalter -F c -f "stormhalter.dump" -v
set D=%date:~10,4%-%date:~4,2%-%date:~7,2%
set T=%time:~0,8%
set T=%T::=-%
set T=%T: =0%
rename "stormhalter.dump" "%D%--%T% stormhalter.dump"

pause

@echo off
echo Exportando base de datos bd_afe...
mysqldump -u root -p bd_afe > backup_bd_afe.sql
echo Listo. El respaldo se guardó como backup_bd_afe.sql
pause
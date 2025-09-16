@echo off
echo Importando base de datos bd_afe...
mysql -u root -p bd_afe < backup_bd_afe.sql
echo Listo. La base de datos fue restaurada desde backup_bd_afe.sql
pause
# Monitoring for ZTE OLT C320 

This is simple scripts which collect data from (multiple) OLT devices, for each connected ONU and saves it into 2 format:

* Json file, which can be exported by Zabbix Agent (using UserParameter)
* MySQL database for future integration with billing (billing is not a part of this project)

Zabbix template is included

# How it works
Script is running periodically from cron or any other timer.
It collect data using `telnet` connection to the OLTs, because:

* There is no public SNMP OIDs, so I cam't use SNMP
* Also, there is information that SNMP implementation has memory leaks at least for ZTE C320 v 1.3
* CPU is not powerfull so I do not want to use `ssh`, and this script should be used only on private management networ, not over public internet

# How to install

* Install and configure Zabbix Agent on host which has private connection to the OLT(s), install `jq` tool and the follwing Python modules: `scrapli`, `json`, `argparse`, `pymysql`. For Python modules you can use pip3 or deb/rpms depends on your Linux distro.
* Download source code 
```
git clone https://github.com/sirmax123/zabbix-zte-c320.git
```
* Copy `zabbix-scripts` folder to place you are usung for such scropts, e.g. `/usr/local/zabbix-scripts`
* Configure devices and mysql credentials in files `config.json` and `mysql.json`.  Note: Config file names are passed to the script using parameters, so you can rename files or move to any other location
* Configure Zabbix Agent: copy `UserParameter-ZTE.conf` file to the Zabbix Agent configuration folder, e.g. `/etc/zabbix/zabbix_agentd.d` and restart zabbix agent, `systemctl  restart zabbix-agent`
* Configure MySQL, create database and user/password and create table: `mysql -u<USER_NAME> -p<PASSWORD> <DATABASE_NAME>  < pon.sql`. Note: name of table MUST be same as you set in `mysql.json` for `pon_table`
* Execute script manually (but you can use your own config files and output dir) 
```
/usr/local/zabbix-scripts/zte_olt.py -c /usr/local/zabbix-scripts/config.json  -o /etc/zabbix/zabbix_agentd.d -m /usr/local/zabbix-scripts/mysql.json 2>/var/log/zte-olt.err
```
And check file `/var/log/zte-olt.err` for errors.

* Output dir `-o /etc/zabbix/zabbix_agentd.d` must match path defined in the Zabbix Agent configuration (`UserParameter-ZTE.conf`)
* Check iffile with ONU data is created (`zte.json` in the folder defined as output, `/etc/zabbix/zabbix_agentd.d` in this example) File size depends of number of active ONUs on all listed devoces
* Check Zabbix Agent configuration with command: `zabbix_get  -s 127.0.0.1 -k  zte_olt[172.31.0.249-1/1/1:5,SIGNAL_LEVEL_DOWN_ATTENUATION]`, but replace parameters to your own: `172.31.0.249` is OLT ip address, `1/1/1:5` is interface number where ONU is configured and active.

If everething is OK, continue to the Zabbix Server configuration

# Zabbix Server
* Export template `Template-ZTE-C320-ONU.xml`
* Add template to host where script is installed


# License





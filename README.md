# PiVPN Sessions Report

This script will run `pivpn -c` and parse the client data to individual sensor for HomeAssistant. MQTT Discovery is enabled to there is need to configure mqtt sensors in your home assistant configuration. The sensor's state is configured as a timestamp while its attributes consist of the remaining info as shown below:

![](resources/entity_card.png)

## Schedule a cron job

run ```crontab -e```
and add the following to the file to run every 3m 
``` 
*/3 * * * * python3 /home/pi/pivpn.py
```
## Remove the cron job
Use `crontab -r` to remove entire crontab file (note there is only one file per user, so this will remove all cron jobs from the file) or use `crontab -e` to edit the cron job file and remove the corresponding line.
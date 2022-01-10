#!/usr/bin/env python3
import sys
import os
import json
import paho.mqtt.client as mqtt
import credentials
import time 
import datetime
import logging
import logging.handlers
logging.basicConfig(filename="/var/log/vpnreport",level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')
logging.info("checking vpn status")

def error_handler(type, value, tb):
    logging.exception("Uncaught Exception: {0}".format(str(value)))
sys.excepthook = error_handler
mqttclient = mqtt.Client()
mqttclient.username_pw_set(username=credentials.mqttuser,password=credentials.mqttpass)
# Topics
discoveryTopicPrefix = 'homeassistant/sensor/vpnclients/'
topicPrefix = 'home/nodes/vpnclients/' 

# Get client list from pivpn
clients={}
resp = os.popen("sudo pivpn -c").read()
logging.debug(resp)
header = resp.split("\n")[1].replace("\x1b[4m","").replace("\x1b[0m","").split("  ")
clientlines = resp.split("\x1b[0m\n")[-1].split("\n")

# clean up header list:
i=0
while i<len(header):
    if header[i]=="":
        del header[i]
    else:
        header[i]=header[i].replace(" ","")
        i+=1
    d=2


# Create clients dictionary:
for line in clientlines:

    if line == "": # continue next iteration when line is empty
        continue
    client = line.split("  ")

    # clean up line
    i = 0 
    while i<len(client): # remove empty strings
        if client[i]=="":
            del client[i]
        else:
            i+=1
    st = {}
    for i in range(len(client)):
        st[header[i]]=client[i]
    st['RemoteIP'] = st['RemoteIP'].replace(" ","")
    logging.debug(st)
    clients[client[0]]=st



def on_mqtt_connect(mqttclient,obj, flags, rc):
    logging.debug("Connected to MQTT server")

def on_mqtt_disconnect(mqttclienct,userdata,rc):
    logging.debug("Disconnected from MQTT server")


def on_mqtt_message(mqttclient,obj,msg):
    top = msg.topic.split(discoveryTopicPrefix)
    if len(top)>1:
        name = top[1].split("/config")[0]
        if not name in clients and msg.payload!=b'{}': #delete config if client does not exist anymore:
            logging.warning("%s does not exist anymore. Deleting from home assistant.."%name)
            mqttclient.publish(msg.topic,"{}",retain=True)

def publishDiscovery(device): #publish config payload for MQTT Discovery in HA
    discoveryTopic=discoveryTopicPrefix +"%s/config" % device['Name']
    payload={}
    payload['name']='VPN Client '+ device['Name']
    payload['uniq_id'] = 'VPN%s%sClient'%('WireGuard',device['Name'])
    payload['dev_cla'] = "timestamp"
    payload['state_topic'] = "%s%s/state"%(topicPrefix,device['Name'])
    payload['icon'] = 'mdi:vpn'
    payload['json_attributes_topic'] = "%s%s/attr"%(topicPrefix,device['Name'])
    payload['dev'] = {
                'identifiers' : ['vpnClient{}'.format(device['Name'])],
                'manufacturer' : 'WireGuard',
                'name' : 'VPN-Client-{}'.format(device['Name']),
                'model' : 'VPN Client',
                'sw_version': "not applicable"            
            }
    logging.debug("Publishing Config for %s"%device['Name'])
    mqttclient.publish(discoveryTopic,json.dumps(payload),0,retain=True)


logging.debug("connecting to mqtt")
mqttclient.on_connect = on_mqtt_connect
mqttclient.on_disconnect = on_mqtt_disconnect
mqttclient.on_message = on_mqtt_message
mqttclient.connect(credentials.mqtthost,credentials.mqttport)
mqttclient.subscribe(discoveryTopicPrefix+"#") # Subscribe to find old clients to delete


# Publish config, state and attributes for each client that has a Last Seen timestamp
for devicename in clients: 
    device = clients[devicename]
    if device['LastSeen']=='(not yet)':
        logging.debug("skipping %s"%devicename)
        continue

    publishDiscovery(device)
    attr_payload = json.dumps(device)
    date= device['LastSeen'].replace(" ","")
    state = datetime.datetime.strptime(date,"%b%d%Y-%H:%M:%S").replace(tzinfo=datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo).isoformat() # get datetime object with timezone indication
    statetopic = "%s%s/state"%(topicPrefix,device['Name'])
    attrtopic = "%s%s/attr"%(topicPrefix,device['Name'])
    logging.debug("Publishing state and attributes for %s"%(device['Name']))
    mqttclient.publish(statetopic,state,0,retain=False)
    mqttclient.publish(attrtopic,attr_payload,0,retain=False)

t1 = time.time()
mqttclient.loop_start()

# run loop to receive subscriptions and delete old retained clients from mqtt.
while True: 
    if time.time()-t1 > 2:
        mqttclient.loop_stop()
        break
mqttclient.disconnect()
logging.info("finished")
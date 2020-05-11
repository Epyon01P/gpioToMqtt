# -*- coding: utf-8 -*-
"""
Created on Mon May  4 23:15:18 2020
Read and control GPIO, taking write commands from the MQTT bus and publishing input changes to the bus
Currently uses a mix of local GPIO and an MCP23S17 SPI port expander (for controlling relays)
This is meant to run as a daemon, so it includes termination signal handling
@author: Epyon01P
"""

import signal
import paho.mqtt.client as mqtt
import pifacedigitalio as p
from gpiozero import LED, Button
from time import sleep

#Initialisation of the GPIO components
p.init()
viessmanncontrolled = LED(23)
viessmannmonintoringled = LED(24)
viessmanncontrolswitch = Button(27)
viessmannmonitoringswitch = Button(22)
viessmanndo7 = Button(6)
viessmanndo3 = Button(12)
prevStateControlswitch = False
prevStateMonitoringswitch = False
prevStatedo7 = False
prevStatedo3 = False

#Initialisation of the MQTT component
brokers_out={"broker1":"localhost"}
subs = [('gpio/write/#',0)]
client=mqtt.Client("gpio")
client.connect(brokers_out["broker1"])
client.subscribe(subs)

class GracefulDeath:
  #When the Grim Sysadmin comes to reap with his scythe, 
  #let this venerable daemon process die a Graceful Death
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)
  def exit_gracefully(self,signum, frame):
    self.kill_now = True

#Callback functions to write GPIO outputs and optionally write back the state of the output
def on_message_write_viessmannmonitoringled(mosq, obj, msg):
    try:
        if msg.payload.decode() == "enabled":
            viessmannmonintoringled.on()
        else:
            viessmannmonintoringled.off()
    except: print("GPIO error: could not set viessmann-monitoring LED")
        
def on_message_write_viessmanncontrolled(mosq, obj, msg): 
    try:
        if msg.payload.decode() == "enabled":
            viessmanncontrolled.on()
        else:
            viessmanncontrolled.off()
    except: print("GPIO error: could not set viessmann-control LED")
    
def on_message_write_viessmannmodbus(mosq, obj, msg):
    resptopic="status/viessmann-modbus"
    try:
        if msg.payload.decode() == "enabled":
            p.digital_write(2, 1)
            p.digital_write(3, 1)
            resp = "enabled"
            client.publish(resptopic,resp, retain=True)
        else:
            p.digital_write(2, 0)
            p.digital_write(3, 0)
            resp = "disabled"
            client.publish(resptopic,resp, retain=True)
    except: print("GPIO error: could not set viessmann-modbus relay")

def on_message_write_viessmannonoff(mosq, obj, msg):
    resptopic="status/viessmann-onoff"
    try:
        if msg.payload.decode() == "disabled":
            p.digital_write(1, 1)
            resp = "disabled"
            client.publish(resptopic,resp, retain=True)
        else:
            p.digital_write(1, 0)
            resp = "enabled"
            client.publish(resptopic,resp, retain=True)
    except: print("GPIO error: could not set viessmann-onoff relay")

def on_message_write_viessmannid9(mosq, obj, msg):
    resptopic="status/viessmann-id9"
    try:
        if msg.payload.decode() == "enabled":
            p.digital_write(0, 1)
            resp = "enabled"
            client.publish(resptopic,resp, retain=True)
        else:
            p.digital_write(0, 0)
            resp = "disabled"
            client.publish(resptopic,resp, retain=True)
    except: print("GPIO error: could not set viessmann-id9 relay")

#Initial read and publish of the input states
sleep(1)
monitoringswitch = viessmannmonitoringswitch.is_held
resptopic="status/viessmann-monitoring"
if monitoringswitch: resp = "enabled"
else: resp = "disabled"
client.publish(resptopic,resp, retain=True)
controlswitch = viessmanncontrolswitch.is_held
resptopic="status/viessmann-control"
if monitoringswitch: resp = "enabled"
else: resp = "disabled"
client.publish(resptopic,resp, retain=True)
do7 = viessmanndo7.is_held
resptopic="status/viessmann-do7"
if do7: resp = "enabled"
else: resp = "disabled"
client.publish(resptopic,resp, retain=True)
do3 = viessmanndo3.is_held
resptopic="status/viessmann-do3"
if do7: resp = "enabled"
else: resp = "disabled"
client.publish(resptopic,resp, retain=True)
  
#The main loop
if __name__ == '__main__':
  killer = GracefulDeath()
  while not killer.kill_now:
    client.loop_start()
    #Read the state of the GPIO inputs, but only publish on change
    monitoringswitch = viessmannmonitoringswitch.is_held
    if prevStateMonitoringswitch != monitoringswitch:
        resptopic="status/viessmann-monitoring"
        if monitoringswitch: resp = "enabled"
        else: resp = "disabled"
        client.publish(resptopic,resp, retain=True)
    controlswitch = viessmanncontrolswitch.is_held
    if prevStateControlswitch != controlswitch:
        resptopic="status/viessmann-control"
        if monitoringswitch: resp = "enabled"
        else: resp = "disabled"
        client.publish(resptopic,resp, retain=True)
    do7 = viessmanndo7.is_held
    if prevStatedo7 != do7:
        resptopic="status/viessmann-do7"
        if do7: resp = "enabled"
        else: resp = "disabled"
        client.publish(resptopic,resp, retain=True)
    do3 = viessmanndo3.is_held
    if prevStatedo3 != do3:
        resptopic="status/viessmann-do3"
        if do7: resp = "enabled"
        else: resp = "disabled"
        client.publish(resptopic,resp, retain=True)
    #check for any new messages on the subscribed topics
    client.message_callback_add('gpio/write/viessmann-monitoring-led', on_message_write_viessmannmonitoringled)
    client.message_callback_add('gpio/write/viessmann-control-led', on_message_write_viessmanncontrolled)
    client.message_callback_add('gpio/write/viessmann-modbus', on_message_write_viessmannmodbus)
    client.message_callback_add('gpio/write/viessmann-onoff', on_message_write_viessmannonoff)
    client.message_callback_add('gpio/write/viessmann-id9', on_message_write_viessmannid9)
    client.loop_stop()
  #Make a graceful exit when this daemon gets terminated
  print("Termination signal received")
  print("Setting all outputs to safe mode... ", end='')
  try:
      #restore Modbus communication between thermostat and HP
      p.digital_write(2, 0)
      p.digital_write(3, 0)
      #enable the HP
      p.digital_write(1, 0)
      p.digital_write(0, 0)
      #disable the LEDs
      viessmannmonintoringled.off()
      viessmanncontrolled.off()
      p.deinit()
      print("done")
  except:
      print("failed!")
  print("Unsubscribing from topics... ", end='')
  for topic in subs:
      client.unsubscribe(topic[0])
  print("done")
  print("Disconnecting from broker... ", end='')
  client.disconnect()
  print("done")
  print("Goodbye, cruel Unix world")

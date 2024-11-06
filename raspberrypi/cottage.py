# coding: utf-8
'''
------------------------------------------------------------------------------
SPDX-FileCopyrightText: 2023 Steven Hartley

See the NOTICE file(s) distributed with this work for additional
information regarding copyright ownership.

This program and the accompanying materials are made available under
the terms of the Apache License Version 2.0 which is available at
https://www.apache.org/licenses/LICENSE-2.0

SPDX-FileType: DOCUMENTATION
SPDX-License-Identifier: Apache-2.0
------------------------------------------------------------------------------

This is the program that runs on my RaspberryPi 3 to control a heating system.
The heating system contains a geothermal heat pump, hydronic boiler, and oil. 
This program and system was written so that I can monitor remotely the system 
on my phone, and to account for the fact that the external loop of the 
geothermal system sometimes freezes when it is extremely cold outside and I need
to supliment the heat with other sources. 

Feel free to use the code as inspiration for what you might want/need. Some code
came from https://github.com/adafruit/Adafruit_Python_ADS1x15.
'''

import math
import os
import glob
import time
import RPi.GPIO as GPIO
import logging
import logging.handlers
from datetime import datetime
from datetime import timedelta
import uptime
from uptime import *
from io import StringIO
from enum import Enum

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

import json
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
#from firebase_admin import messaging
from datetime import datetime



##################################################################
# Fetch the pressure from the ADS1115.
# 
# The following function is passes the pin number (1-4) and the 
# max pressure that the transducer can measure. Function returns 
# the calculated measured pressure.
##################################################################
def FetchPressure(pin,max):
    chan = AnalogIn(ads, pin)
    result = max * ((chan.voltage - 0.5) / 4.0)
    return result
    

#GPIO Basic initialization
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


#Output Pins
geo_ctrl_out = 20	# GEO Thermal Control pin
oil_ctrl_out = 16	# Oil system control pin (No longer used)
pwr_ctrl_out = 12	# 3.3V power control pin for the 1-wire thermostats
electric_ctrl_out = 19  # 9kW Hydronic heating system control pin



# Zone Class contains a name, address, and value
class Zone:
    def __init__(self, name, address, value):
        self.name = name
        self.address = address
        self.value = value

# Cottage Heating Zones
zones = [
        Zone("Zone1", 17, 0),
        Zone("Zone2", 18, 0),
        Zone("Zone3", 24, 0),
        Zone("Zone4", 25, 0),
        Zone("Zone5", 5, 0),
        Zone("Zone6", 23, 0),
        Zone("Zone7", 22, 0),
        Zone("Zone8", 27, 0)
    ]

# Heating System modes
class Mode(Enum):
    OFF = 0
    GEOTHERMAL = 1
    GEO_ELECTRIC = 2
    ELECTRIC_OIL = 3
    AUTOMATIC = 4
    ELECTRIC = 5
    INVALID = -1

#Got to love global variables!
currentMode = Mode.GEOTHERMAL
switchTime = datetime.now() + timedelta(minutes=5)
setMode = Mode.AUTOMATIC

system = {
    "m": currentMode.value
}



##################################################################
# Read the information from the 1-wire temerature device.
#
# Function returns a string with all the data from the 1-wire device
##################################################################
def GetOneWireTempValue(var):
    device_file = var + '/w1_slave'
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines


##################################################################
# Fetch Current Temperature from 1-wire Device.
#
# Parses the returned string from the 1-wire device to read the temerature.
# Returns the read temperature.
##################################################################
def ReadTemperature(addr):
    lines = GetOneWireTempValue(addr)
    # Analyze if the last 3 characters are 'YES'.
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = GetOneWireTempValue(addr)
    # Find the index of 't=' in a string.
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        # Read the temperature .
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c


######################################################################
# Reset 1-Wire Bus.
#
# Function will toggle the 1-wire power line to cause the temerature
# sensors to reset and send the updated temperature information again.
######################################################################
def Reset1Wire():
    msg = "1-Wire Reset"
    log.error(msg)
    UploadMsg(msg)
    GPIO.output(pwr_ctrl_out,0)
    time.sleep(5)
    GPIO.output(pwr_ctrl_out,1)
    time.sleep(20)



######################################################################
# Switch Heating System Mode.
#
# The function will set the heating system into the desired mode (ex. 
# geothermal, off, automatic, etc...). When force==true, the mode is 
# set immediately, otherwise there is a settling period to ensure that
# the heating system is not flip-floping modes often that can damage
# the systems. 
######################################################################
def SetSystemMode(mode, force):
    global currentMode
    global switchTime
    value = ReadOverride()

    # Check if there is a manual override
    if (value == None):
        setMode = mode.AUTOMATIC
    else :
        setMode = Mode(value)

    log.info("Override is set to %s", setMode.name)

    # Override if I set it in my application
    if (setMode != Mode.AUTOMATIC) :
        force = True
        mode = setMode

    # No change in the mode so  just return
    if (currentMode == mode):
        return

    # Debounce check wait for 30 minutes from last system change
    if ((force == False) and (datetime.now() < switchTime)):
        log.info("Waiting for System to settle")
        return

    # System has settled and we can safely switch to a new mode
    switchTime = datetime.now() + timedelta(minutes=5)
    currentMode = mode
    system['m'] = currentMode.value

    #  Enable Oil (set to 1) when mode is ELECTRIC_OIL
    GPIO.output(oil_ctrl_out, 0 if (mode == Mode.ELECTRIC_OIL) else 1)

    # Enable Geothermal (set to 1) when mode == GEOTHERMAL
    GPIO.output(geo_ctrl_out, 1 if (mode == Mode.GEOTHERMAL or mode == Mode.GEO_ELECTRIC) else 0)

    # Enable Electric Boiler (set to 0) when mode uses Electric
    GPIO.output(electric_ctrl_out, 0 if (mode == Mode.ELECTRIC or mode == Mode.GEO_ELECTRIC or mode == Mode.ELECTRIC_OIL) else 1)
    msg = "Switching to:" + currentMode.name
    log.info(msg)
    UploadMsg(msg)
    UploadMsg(json.dumps(system))



######################################################################
# Read Heating Zones.
#
# Function to read all zones and check if a given zone is on (value of
# 0) or off (value > 0 VAC). We sample the GPIO input ever 2ms for 30
# times since the input is AC.
# The function populates the global variable zones with the results.
######################################################################
def ReadZones():
    global zones
    try:
        # Clear the current zone info
        for i in range(len(zones)):
            zones[i].value = 0

        # Zones are 60hz and we need to sample to see that it
        # really is on or not, if we detect on, we break
        for i in range(len(zones)):
            for y in range(30):
                if GPIO.input(zones[i].address) == 0:
                    zones[i].value = 1
                    break
                time.sleep(0.002)

    except Exception as e:
        print("An error occured:",e)



######################################################################
# Initialize the Google Firebase Access.
#
# Firebase is used to upload data and fetch override commands so the 
# RaspberryPi can communicate with my Android app on my phone.
# This function loads in the json token used to authenticate and includes
# the URL of my subscription.
######################################################################
def InitFirebase():
    try:
        cred = credentials.Certificate("raspberrypi-371718-firebase-adminsdk-6tdt2-9a98bc37c6.json")
        global app
        app = firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://raspberrypi-371718-default-rtdb.firebaseio.com/'
        })
        UploadMsg("Program Started")
    except Exception as e:
        print(e)



######################################################################
# Update Data to Firebase db.
#
# Upload the data to a specific location in the firebase database
# (under the cottage folder).
######################################################################
def UploadData(where, data):
    newData = data
    newData.update( {"time": datetime.now().strftime("%y/%d/%m %H:%M:%S")})
#    newData.update( {"uptime": uptime() })
    try:
       ref = db.reference("/cottage/")
       ref = ref.child(where)
       ref.child("current").set(json.dumps(data, indent=4))
#       ref.child("push").push(json.dumps(data, indent=4))
    except Exception as e:
        print(e)



######################################################################
# Upload Log Message to Firebase db.
######################################################################
def UploadMsg(msg):
    try:
        ref = db.reference("/cottage/geo/logs")
        log = datetime.now().strftime("%y/%m/%d %H:%M:%S ") + msg
        ref.push(log)
#        message = messaging.Message(
#            data={ msg },
#        token=registration_token,
#        )
#        response = messaging.send(message)
        # Response is a message ID string.
#        print('Successfully sent message:', response)
    except Exception as e:
        print(e)



######################################################################
# Read Override Value from Firebase db
#
# Override value is set by the Android application and read by the 
# RaspberryPi to force the system into a specific mode
######################################################################
def ReadOverride():
    try:
        ref = db.reference("/cottage/geo/override")
        return ref.get()
    except Exception as e:
        print(e)


def SendMessage(msg):
    try:
        message = messaging.Message(
            data={'msg',msg},
            topic='/topics/messaging',
        )
    except Exception as e:
        print(e)



######################################################################
# Main Loop for the Program.
#
# The main loop will read the temperatures & pressures, determine the 
# correct heating mode to be in, and then upload the results to the 
# Google firebase server so that it can be read from the Android App. 
#
######################################################################
def MainLoop():
    global currentMode
    try:
        geo_out = round(ReadTemperature('/sys/bus/w1/devices/28-3c2df648c6be'),1)
        geo_in = round(ReadTemperature('/sys/bus/w1/devices/28-3c2df648f4f6'),1)
        outside = round(ReadTemperature('/sys/bus/w1/devices/28-3cc3f6486763'),1)
        heating = round(ReadTemperature('/sys/bus/w1/devices/28-3c18f648ac75'),1)
        electric = round(ReadTemperature('/sys/bus/w1/devices/28-3c70f6498884'),1)
        return_temp = round(ReadTemperature('/sys/bus/w1/devices/28-3c75f6496451'),1)
        geo_p_out = round(FetchPressure(2,100),1)
        main_pressure = round(FetchPressure(1,200),1)
        geo_p_in = round(FetchPressure(0,200),1)
        geo_p_heating = 0 #round(FetchPressure(1),1)
        ReadZones()
    except Exception as e:
        log.warning(e)
        Reset1Wire()
        return -1

    # Fill in te zone info
    zone_values = []
    num_on_zones = 0
    for i in range(len(zones)):
        zone_values.append(zones[i].value)
        if (zones[i].value):
            num_on_zones = num_on_zones +1

    system['z'] = zone_values

    temperatures = [geo_in, geo_out, heating, outside, electric, return_temp]
    system['t'] = temperatures

    pressures = [ geo_p_out, geo_p_in, main_pressure, geo_p_heating]
    system['p'] = pressures

    # Switch to GEO_ELECTRIC if it is colder than -25 outside
    if (outside < -25):
        SetSystemMode(Mode.GEO_ELECTRIC, False)

    # Switch to electric if pressure has gone to high, 
    # or the temperature of the geothermal water is too cold. 
    # When the pressure is too high we consider that a critical issue and we switch from
    # geothermal to electric right away. 
    # If the electric system is running and there are multiple zones on and the temperature
    # is still to cold, we turn on Oil and electric (last resort)
    elif (geo_p_out > 50.0 or geo_out < -3 or geo_in < 1):
        SetSystemMode(Mode.ELECTRIC, True)

    # We have too many zones on so we need to supliment with electric
    elif (num_on_zones > 4):
        SetSystemMode(Mode.GEO_ELECTRIC, False)

    # Everything seems to be ok and we can stay in geothermal mode
    else :
        SetSystemMode(Mode.GEOTHERMAL, False)

    log.info("%s", json.dumps(system))
    UploadData("geo", system);
    return 0




######################################################################
# MAIN PROGRAM
######################################################################

# Initialize the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# you can specify an I2C adress instead of the default 0x48
ads = ADS.ADS1115(i2c, address=0x48)

# Setup Output pins
GPIO.setup(geo_ctrl_out,GPIO.OUT)
GPIO.setup(oil_ctrl_out,GPIO.OUT)
GPIO.setup(pwr_ctrl_out,GPIO.OUT)
GPIO.setup(electric_ctrl_out, GPIO.OUT)

# Setup all the Zone inputs
for x in range(len(zones)):
    GPIO.setup(zones[x].address, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.output(geo_ctrl_out,1) # Turn on Geothermal by default
GPIO.output(oil_ctrl_out,1) # Turn off oil by default
GPIO.output(pwr_ctrl_out,1) # Turn on 3.3 V by default (for temp sensors)
GPIO.output(electric_ctrl_out, 1) # Turn off electrical by default

# Setup the Logger
logging.basicConfig(
    format="[%(asctime)s] %(levelname)s [%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%d/%b/%Y %H:%M:%S")
log = logging.getLogger()
log.setLevel(os.environ.get("LOGLEVEL", "INFO"))
log.info("Start of Program")

# Init the backend database
InitFirebase()


# The main loop!
while True:
    if (MainLoop() == 0):
        time.sleep(10)
    else:
        time.sleep(5)
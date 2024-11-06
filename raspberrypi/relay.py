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

Simple test code to manually set high or low a GPIO pin for testing.
'''

#import libraries
import RPi.GPIO as GPIO
import time

#GPIO Basic initialization
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#Use a variable for the Pin to use
#If you followed my pictures, it's port 7 => BCM 4
#led1 = 20
#led2 = 16
#Initialize your pin
while True :
    print("Which Relay To ctrl?")
    print("geo_off(20)")
    print("oil_on (16)")
    print("3.3v (12)")
    print("electric_on (5)")
    
    pin = int(input())
    value = int(input("True(0) or False(1)?:"))
    GPIO.setup(pin,GPIO.OUT)
    GPIO.output(pin,value)

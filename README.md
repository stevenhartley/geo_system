# geo_system
Pet project I did to control my cottage heating system using a Raspberry Pi, the Google cloud, and my mobile phone 

## Android Code
The Cottage2 project contains the android application that will talk with the Google firebase backend to fetch the current information and set any override modes.
In order for this application to work you will need realtime firebase account and then set up access with your username and password (I hide the password). Also the google APIs requires a google-services.json that you can generate from the firebase CLI or web page. 


## Raspbery Pi
The entire program can be found in cottage.py, any of the imports that are not on your pi will need to be installed using `pip install`.  I setup the python script to be launched automatically using `pm2` command. 


Take what you like and enjoy, it was a lot of fun writing this, hopefully someone else will find it useful.

_Steven._


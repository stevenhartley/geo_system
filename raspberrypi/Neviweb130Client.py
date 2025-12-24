# coding: utf-8
'''
------------------------------------------------------------------------------
The following code come from https://github.com/claudegel/sinope-130, thank you Claude!
'''

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from NeviwebConst import *
import requests

REQUESTS_TIMEOUT = 30
HOST = "https://neviweb.com"
LOGIN_URL = f"{HOST}/api/login"
LOCATIONS_URL = f"{HOST}/api/locations?account$id="
GATEWAY_DEVICE_URL = f"{HOST}/api/devices?location$id="
DEVICE_DATA_URL = f"{HOST}/api/device/"
NEVIWEB_LOCATION = f"{HOST}/api/location/"
NEVIWEB_WEATHER = f"{HOST}/api/weather?code="

#SCAN_INTERVAL = DEFAULT_SCAN_INTERVAL
#HOMEKIT_MODE = DEFAULT_HOMEKIT_MODE
#IGNORE_MIWI = DEFAULT_IGNORE_MIWI
#STAT_INTERVAL = DEFAULT_STAT_INTERVAL
#NOTIFY = DEFAULT_NOTIFY

DEFAULT_LOG_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_LOG_BACKUP_COUNT = 3
DEFAULT_LOG_RESET_ON_START = False
LOGGER_NAME = "neviweb130"

LOG_PATH = "neviweb130_log.txt"

existing_logger = logging.getLogger(LOGGER_NAME)
level_name = logging.getLevelName(10)
_LOGGER = logging.getLogger(__name__)

class PyNeviweb130Error(Exception):
    pass


class Neviweb130Client:
    def __init__(
        self,
        username,
        password,
        network,
        network2,
        network3,
        ignore_miwi,
        timeout=REQUESTS_TIMEOUT,
    ):
        """Initialize the client object."""
        self._email = username
        self._password = password
        self._network_name = network
        self._network_name2 = network2
        self._network_name3 = network3
        self._code: str | None = None
        self._ignore_miwi = ignore_miwi
        self._gateway_id = None
        self._gateway_id2 = None
        self._gateway_id3 = None
        self.gateway_data = {}
        self.gateway_data2 = {}
        self.gateway_data3 = {}
        self._headers = None
        self._account = None
        self._cookies: RequestsCookieJar | None = None
        self._timeout = timeout
        self._occupancyMode = None
        self.user = None

        self.__post_login_page()
        self.__get_network()
        self.__get_gateway_data()

    def update(self):
        self.__get_gateway_data()

    def test_connect(self):
        self.__post_login_page()

    def reconnect(self):
        self.__post_login_page()
        self.__get_network()
        self.__get_gateway_data()
    def __post_login_page(self) -> None:
        """Login to Neviweb."""
        data = {
            "username": self._email,
            "password": self._password,
            "interface": "neviweb",
            "stayConnected": 1,
        }
        try:
            raw_res = requests.post(
                LOGIN_URL,
                json=data,
                cookies=self._cookies,
                allow_redirects=False,
                timeout=self._timeout,
            )
        except OSError:
            raise PyNeviweb130Error("Cannot submit login form... Check your network or firewall")
        if raw_res.status_code != 200:
            _LOGGER.debug("Login status: %s", raw_res.json())
            raise PyNeviweb130Error("Cannot log in")

        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)

        data = raw_res.json()
        _LOGGER.debug("Login response: %s", data)
        if "error" in data:
            if data["error"]["code"] == "ACCSESSEXC":
                raise ConfigEntryNotReady(
                    "Too many active sessions. "
                    "Close all neviweb130 sessions you have opened on other platform (mobile, browser, ...). "
                    "If this error persists, deactivate this integration (or shutdown homeassistant), "
                    f"wait a few minutes, then reactivate (or restart) it. Error code: {data['error']['code']}"
                )
            elif data["error"]["code"] == "USRBADLOGIN":
                raise ConfigEntryAuthFailed(
                    "Invalid Neviweb username and/or password... "
                    f"Check your configuration parameters. Error code: {data['error']['code']}"
                )

            raise ConfigEntryError(f"Unknown error while logging to Neviweb. Error code: {data['error']['code']}")

        self.user = data["user"]
        self._headers = {"Session-Id": data["session"]}
        self._account = str(data["account"]["id"])
        _LOGGER.debug("Successfully logged in to: %s", self._account)


    def __get_network(self) -> None:
        """Get gateway id associated to the desired network."""
        # Http requests
        if self._account is None:
            raise ConfigEntryAuthFailed("Account ID is empty, check your username and password to log into Neviweb...")

        try:
            raw_res = requests.get(
                LOCATIONS_URL + self._account,
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
            networks = raw_res.json()
            _LOGGER.warning("Number of networks found on Neviweb: %s", len(networks))
            _LOGGER.warning("networks: %s", networks)
            if (
                self._network_name is None and self._network_name2 is None and self._network_name3 is None
            ):  # Use 1st network found, second or third if found
                self._gateway_id = networks[0]["id"]
                self._network_name = networks[0]["name"]
                self._occupancyMode = networks[0]["mode"]
                self._code = networks[0]["postalCode"]
                _LOGGER.warning("Selecting %s as first network", self._network_name)
                if len(networks) > 1:
                    self._gateway_id2 = networks[1]["id"]
                    self._network_name2 = networks[1]["name"]
                    self._occupancyMode = networks[1]["mode"]
                    self._code = networks[1]["postalCode"]
                    _LOGGER.warning("Selecting %s as second network", self._network_name2)
                    if len(networks) > 2:
                        self._gateway_id3 = networks[2]["id"]
                        self._network_name3 = networks[2]["name"]
                        self._occupancyMode = networks[2]["mode"]
                        self._code = networks[2]["postalCode"]
                        _LOGGER.warning("Selecting %s as third network", self._network_name3)
            else:
                for network in networks:
                    if network["name"] == self._network_name:
                        self._gateway_id = network["id"]
                        self._occupancyMode = network["mode"]
                        self._code = network["postalCode"]
                        _LOGGER.warning(
                            "Selecting %s network among: %s",
                            self._network_name,
                            networks,
                        )
                        continue
                    elif (network["name"] == self._network_name.capitalize()) or (
                        network["name"] == self._network_name[0].lower() + self._network_name[1:]
                    ):
                        self._gateway_id = network["id"]
                        self._occupancyMode = network["mode"]
                        self._code = network["postalCode"]
                        _LOGGER.warning(
                            "Please check first letter of your network name. "
                            "Is it a capital letter or not? "
                            f"Selecting {self._network_name} network among: {networks}"
                        )
                        continue
                    else:
                        _LOGGER.warning(
                            f"Your network name {self._network_name} do not correspond to "
                            f"discovered network {network['name']}, skipping this one... "
                            f"Please check your config if nothing get discovered"
                        )

                    if self._network_name2 is not None and self._network_name2 != "":
                        if network["name"] == self._network_name2:
                            self._gateway_id2 = network["id"]
                            self._occupancyMode = network["mode"]
                            self._code = network["postalCode"]
                            _LOGGER.debug(
                                "Selecting %s network among: %s",
                                self._network_name2,
                                networks,
                            )
                            continue
                        elif (network["name"] == self._network_name2.capitalize()) or (
                            network["name"] == self._network_name2[0].lower() + self._network_name2[1:]
                        ):
                            self._gateway_id = network["id"]
                            self._occupancyMode = network["mode"]
                            self._code = network["postalCode"]
                            _LOGGER.warning(
                                "Please check first letter of your network2 name. "
                                "Is it a capital letter or not? "
                                f"Selecting {self._network_name2} network among: {networks}"
                            )
                            continue
                        else:
                            _LOGGER.warning(
                                f"Your network2 name {self._network_name2} do not correspond to "
                                f"discovered network {network['name']}, skipping this one..."
                            )

                    if self._network_name3 is not None and self._network_name3 != "":
                        if network["name"] == self._network_name3:
                            self._gateway_id3 = network["id"]
                            self._occupancyMode = network["mode"]
                            self._code = network["postalCode"]
                            _LOGGER.warning(
                                "Selecting %s network among: %s",
                                self._network_name3,
                                networks,
                            )
                            continue
                        elif (network["name"] == self._network_name3.capitalize()) or (
                            network["name"] == self._network_name3[0].lower() + self._network_name3[1:]
                        ):
                            self._gateway_id = network["id"]
                            self._occupancyMode = network["mode"]
                            self._code = network["postalCode"]
                            _LOGGER.warning(
                                "Please check first letter of your network3 name. "
                                "Is it a capital letter or not? "
                                f"Selecting {self._network_name3} network among: {networks}"
                            )
                            continue
                        else:
                            _LOGGER.warning(
                                f"Your network3 name {self._network_name3} do not correspond to "
                                f"discovered network {network['name']}, skipping this one..."
                            )
        except OSError:
            raise PyNeviweb130Error("Cannot get Neviweb's networks")

        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)

        # Prepare data
        self.gateway_data = raw_res.json()

    def __get_gateway_data(self) -> None:
        print("Get gateway data.")
        # Check if gateway_id was set
        if self._gateway_id is None and self._gateway_id2 is None and self._gateway_id3 is None:
            _LOGGER.warning("No gateway defined, check your config for networks names...")
            self.notify_ha(
                "All Gateway ID are None. Network selection failed. "
                + "Check that your configuration network names match one of the networks in your Neviweb account. "
                + "Available networks were logged during network selection. Check your log"
            )
        # Http requests
        try:
            raw_res = requests.get(
                GATEWAY_DEVICE_URL + str(self._gateway_id),
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
            _LOGGER.debug("Received gateway data: %s", raw_res.json())
        except OSError:
            raise PyNeviweb130Error("Cannot get gateway data")

        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)

        # Prepare data
        self.gateway_data = raw_res.json()
        _LOGGER.debug("Gateway_data: %s", self.gateway_data)

        if self._gateway_id2 is not None:
            try:
                raw_res2 = requests.get(
                    GATEWAY_DEVICE_URL + str(self._gateway_id2),
                    headers=self._headers,
                    cookies=self._cookies,
                    timeout=self._timeout,
                )
                _LOGGER.debug("Received gateway data 2: %s", raw_res2.json())
            except OSError:
                raise PyNeviweb130Error("Cannot get gateway data 2")

            # Prepare data
            self.gateway_data2 = raw_res2.json()
            _LOGGER.debug("Gateway_data2: %s", self.gateway_data2)

        if self._gateway_id3 is not None:
            try:
                raw_res3 = requests.get(
                    GATEWAY_DEVICE_URL + str(self._gateway_id3),
                    headers=self._headers,
                    cookies=self._cookies,
                    timeout=self._timeout,
                )
                _LOGGER.debug("Received gateway data 3: %s", raw_res3.json())
            except OSError:
                raise PyNeviweb130Error("Cannot get gateway data 3")

            # Prepare data
            self.gateway_data3 = raw_res3.json()
            _LOGGER.debug("Gateway_data3: %s", self.gateway_data3)

        for device in self.gateway_data:
            data = self.get_device_attributes(str(device["id"]), [ATTR_SIGNATURE])
            if ATTR_SIGNATURE in data:
                device[ATTR_SIGNATURE] = data[ATTR_SIGNATURE]
            _LOGGER.debug("Received signature data: %s", data)
            if data[ATTR_SIGNATURE]["protocol"] == "miwi":
                if not self._ignore_miwi:
                    _LOGGER.debug(
                        "The Neviweb location selected for parameter «network» contain unsupported device "
                        "with protocol miwi. If this location contain only miwi devices, "
                        "it should be added to custom_component «sinope neviweb» instead. "
                        "If the location contain mixed miwi, Zigbee and/or Wi-Fi devices, "
                        "add parameter: ignore_miwi: True, in your neviweb130 configuration"
                    )
        if self._gateway_id2 is not None:
            for device in self.gateway_data2:
                data2 = self.get_device_attributes(str(device["id"]), [ATTR_SIGNATURE])
                if ATTR_SIGNATURE in data2:
                    device[ATTR_SIGNATURE] = data2[ATTR_SIGNATURE]
                _LOGGER.debug("Received signature data: %s", data2)
                if data2[ATTR_SIGNATURE]["protocol"] == "miwi":
                    if not self._ignore_miwi:
                        _LOGGER.debug(
                            "The Neviweb location selected for parameter «network2» contain unsupported device "
                            "with protocol miwi. If this location contain only miwi devices, "
                            "it should be added to custom_component «sinope neviweb» instead. "
                            "If the location contain mixed miwi, Zigbee and/or Wi-Fi devices, "
                            "add parameter: ignore_miwi: True, in your neviweb130 configuration"
                        )
        if self._gateway_id3 is not None:
            for device in self.gateway_data3:
                data3 = self.get_device_attributes(str(device["id"]), [ATTR_SIGNATURE])
                if ATTR_SIGNATURE in data3:
                    device[ATTR_SIGNATURE] = data3[ATTR_SIGNATURE]
                _LOGGER.debug("Received signature data: %s", data3)
                if data3[ATTR_SIGNATURE]["protocol"] == "miwi":
                    if not self._ignore_miwi:
                        _LOGGER.debug(
                            "The Neviweb location selected for parameter «network3» contain unsupported device "
                            "with protocol miwi. If this location contain only miwi devices, "
                            "it should be added to custom_component «sinope neviweb» instead. "
                            "If the location contain mixed miwi, Zigbee and/or Wi-Fi devices, "
                            "add parameter: ignore_miwi: True, in your neviweb130 configuration"
                        )

    def get_device_attributes(self, device_id: str, attributes: list[str]) -> Any:
        """Get device attributes."""
        # Http requests
        try:
            raw_res = requests.get(
                DEVICE_DATA_URL + device_id + "/attribute?attributes=" + ",".join(attributes),
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
        #            _LOGGER.debug("Received devices data: %s", raw_res.json())
        except requests.exceptions.ReadTimeout:
            return {"errorCode": "ReadTimeout"}
        except Exception as e:
            raise PyNeviweb130Error(f"Cannot get device attributes {e}")
        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        if "error" in data:
            if data["error"]["code"] == "USRSESSEXP":
                _LOGGER.error(
                    "Session expired. Set a scan_interval less than 10 minutes, otherwise the session will end"
                )
                # raise PyNeviweb130Error("Session expired... Reconnecting...")
        return data

    def get_device_status(self, device_id: str):
        """Get device status for the GT130."""
        # Http requests
        try:
            raw_res = requests.get(
                DEVICE_DATA_URL + device_id + "/status",
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
            _LOGGER.debug("Received devices status: %s", raw_res.json())
        except requests.exceptions.ReadTimeout:
            return {"errorCode": "ReadTimeout"}
        except Exception as e:
            raise PyNeviweb130Error("Cannot get device status", e)
        # Prepare data
        data = raw_res.json()
        if "error" in data:
            if data["error"]["code"] == "USRSESSEXP":
                _LOGGER.error(
                    "Session expired. Set a scan_interval less than 10 minutes, otherwise the session will end"
                )
                # raise PyNeviweb130Error("Session expired... Reconnecting...")
        return data

    def get_neviweb_status(self, location):
        """Get neviweb occupancyMode status."""
        # Http requests
        try:
            raw_res = requests.get(
                NEVIWEB_LOCATION + str(location) + "/notifications",
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
            _LOGGER.debug("Received neviweb status: %s", raw_res.json())
        except requests.exceptions.ReadTimeout:
            return {"errorCode": "ReadTimeout"}
        except Exception as e:
            raise PyNeviweb130Error("Cannot get neviweb status", e)
        data = raw_res.json()
        if "error" in data:
            if data["error"]["code"] == "USRSESSEXP":
                _LOGGER.error(
                    "Session expired. Set a scan_interval less than 10 minutes, otherwise the session will end"
                )
                # raise PyNeviweb130Error("Session expired...reconnecting...")
        return data

    def get_device_alert(self, device_id: str):
        """Get device alert for Sedna valve."""
        # Http requests
        try:
            raw_res = requests.get(
                DEVICE_DATA_URL + device_id + "/alert",
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
            _LOGGER.debug("Received devices alert (%s): %s", device_id, raw_res.json())
        except requests.exceptions.ReadTimeout:
            return {"errorCode": "ReadTimeout"}
        except Exception as e:
            raise PyNeviweb130Error("Cannot get device alert", e)
        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        if "error" in data:
            if data["error"]["code"] == "USRSESSEXP":
                _LOGGER.error(
                    "Session expired. Set a scan_interval less than 10 minutes, otherwise the session will end"
                )
                # raise PyNeviweb130Error("Session expired... Reconnecting...")
        return data

    def get_device_monthly_stats(self, device_id: str):
        """Get device power consumption (in Wh) for the last 24 months."""
        # Http requests
        try:
            raw_res = requests.get(
                DEVICE_DATA_URL + device_id + "/consumption/monthly",
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
        except OSError:
            raise PyNeviweb130Error("Cannot get device monthly stats...")
        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        # _LOGGER.debug("Monthly_stats data: %s", data)
        if "history" in data:
            return data["history"]
        else:
            _LOGGER.debug("Monthly stat error: %s", data)
            return None

    def get_device_daily_stats(self, device_id: str):
        """Get device power consumption (in Wh) for the last 30 days."""
        # Http requests
        try:
            raw_res = requests.get(
                DEVICE_DATA_URL + device_id + "/consumption/daily",
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
        except OSError:
            raise PyNeviweb130Error("Cannot get device daily stats...")
        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        # _LOGGER.debug("Daily_stats data: %s", data)
        if "history" in data:
            return data["history"]
        else:
            _LOGGER.debug("Daily stat error: %s", data)
            return None

    def get_device_hourly_stats(self, device_id: str):
        """Get device power consumption (in Wh) for the last 24 hours."""
        # Http requests
        try:
            raw_res = requests.get(
                DEVICE_DATA_URL + device_id + "/consumption/hourly",
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
        except OSError:
            raise PyNeviweb130Error("Cannot get device hourly stats...")
        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        # _LOGGER.debug("Hourly_stats data: %s", data)
        if "history" in data:
            return data["history"]
        else:
            _LOGGER.debug("Hourly stat error: %s", data)
            return None

    def get_weather(self):
        """Get Neviweb weather for my location."""
        if self._code is None:
            raise ValueError("self._code is None")
        try:
            raw_res = requests.get(
                NEVIWEB_WEATHER + self._code,
                headers=self._headers,
                cookies=self._cookies,
                timeout=self._timeout,
            )
        except OSError:
            raise PyNeviweb130Error("Cannot get Neviweb weather and icon...")
        # Update cookies
        if self._cookies is None:
            self._cookies = raw_res.cookies
        else:
            self._cookies.update(raw_res.cookies)
        # Prepare data
        data = raw_res.json()
        # _LOGGER.debug("weather data: %s", data)
        return data


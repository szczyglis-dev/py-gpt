#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.30 13:00:00                  #
# ================================================== #

import serial
import time
from PySide6.QtCore import Slot

from pygpt_net.plugin.base import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass  # add custom signals here


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        msg = None
        for item in self.cmds:
            try:
                if item["cmd"] in self.plugin.allowed_cmds and self.plugin.is_cmd_allowed(item["cmd"]):
                    request = {"cmd": item["cmd"]}  # prepare request item for result

                    # serial: send text command
                    if item["cmd"] == "serial_send":
                        port = self.plugin.get_option_value("serial_port")
                        speed = self.plugin.get_option_value("serial_bps")
                        timeout = self.plugin.get_option_value("timeout")
                        sleep = self.plugin.get_option_value("sleep")
                        self.log("Using serial port: {} @ {} bps".format(port, speed))
                        try:
                            msg = "Sending command to USB port: {}".format(
                                item["params"]['command'],
                            )
                            self.log(msg)
                            data = self.send_command(
                                port,
                                speed,
                                item["params"]['command'],
                                timeout=timeout,
                                sleep=sleep,
                            )
                            self.log("Response: {}".format(data))
                            response = {
                                "request": request,
                                "result": data,
                            }
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # serial: send raw bytes command
                    elif item["cmd"] == "serial_send_bytes":
                        port = self.plugin.get_option_value("serial_port")
                        speed = self.plugin.get_option_value("serial_bps")
                        timeout = self.plugin.get_option_value("timeout")
                        sleep = self.plugin.get_option_value("sleep")
                        self.log("Using serial port: {} @ {} bps".format(port, speed))
                        try:
                            msg = "Sending binary data to USB port: {}".format(
                                item["params"]['bytes'],
                            )
                            self.log(msg)
                            data = self.send_binary_data(
                                port,
                                speed,
                                int(item["params"]['bytes']),
                                timeout=timeout,
                                sleep=sleep,
                            )
                            self.log("Response: {}".format(data))
                            response = {
                                "request": request,
                                "result": data,
                            }
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

                    # serial: read data from USB port
                    elif item["cmd"] == "serial_read":
                        port = self.plugin.get_option_value("serial_port")
                        speed = self.plugin.get_option_value("serial_bps")
                        timeout = self.plugin.get_option_value("timeout")
                        duration = int(item["params"]['duration']) \
                            if "duration" in item["params"] else 3
                        self.log("Using serial port: {} @ {} bps".format(port, speed))
                        try:
                            msg = "Reading data from USB port..."
                            self.log(msg)
                            data = self.read_data(
                                port,
                                speed,
                                timeout=timeout,
                                duration=duration,
                            )
                            self.log("Response: {}".format(data))
                            response = {
                                "request": request,
                                "result": data,
                            }
                        except Exception as e:
                            response = {
                                "request": request,
                                "result": "Error: {}".format(e),
                            }
                            self.error(e)
                            self.log("Error: {}".format(e))
                        self.response(response)

            except Exception as e:
                self.response(
                    {
                        "request": item,
                        "result": "Error: {}".format(e),
                    }
                )
                self.error(e)
                self.log("Error: {}".format(e))

        if msg is not None:
            self.status(msg)

    def send_command(
            self,
            port: str,
            speed: int,
            command: str,
            timeout: int = 1,
            sleep: int = 2
    ) -> str:
        """
        Send command to USB port

        :param port: USB port name, e.g. /dev/ttyACM0
        :param speed: Port connection speed, in bps, default: 9600
        :param command: Command to send
        :param timeout: Timeout in seconds
        :param sleep: Sleep time in seconds
        :return: Response from USB port
        """
        ser = serial.Serial(port, speed, timeout=timeout)
        time.sleep(sleep)
        ser.write((command + '\n').encode())
        ser.flush()
        return ser.readline().decode().strip()

    def send_binary_data(
            self,
            port: str,
            speed: int,
            data: int,
            timeout: int = 1,
            sleep: int = 2
    ) -> str:
        """
        Send command to USB port

        :param port: USB port name, e.g. /dev/ttyACM0
        :param speed: Port connection speed, in bps, default: 9600
        :param data: Data to send
        :param timeout: Timeout in seconds
        :param sleep: Sleep time in seconds
        :return: Response from USB port
        """
        ser = serial.Serial(port, speed, timeout=timeout)
        time.sleep(sleep)
        ser.write(bytes(data))
        ser.flush()
        return ser.readline().decode().strip()

    def read_data(
            self,
            port: str,
            speed: int,
            timeout: int = 1,
            duration: int = 3
    ) -> str:
        """
        Read data from USB port

        :param port: USB port name, e.g. /dev/ttyACM0
        :param speed: Port connection speed, in bps, default: 9600
        :param timeout: Timeout in seconds
        :param duration: Duration in seconds
        :return: Response from USB port
        """
        data = ""
        ser = serial.Serial(port, speed, timeout=timeout)
        end_time = time.time() + duration
        while time.time() < end_time:
            if ser.in_waiting > 0:
                data += ser.readline().decode().strip()
        return data

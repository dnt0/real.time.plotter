from crccheck.crc import CrcXmodem, Crc32Base, Crc16Modbus
from numpy import number
from scipy.stats import norm
# from processing_py import App
import serial
import time
import struct
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import multiprocessing
import traceback
from .utilities import parse_properties_from_file, parse_default_data_stream_properties_from_file

import json
from random import randint
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

'''
Note on verbosity
The verbosity parameter is used to get insight into what is happening when a command is being run.
There are multiple "levels" of verbosity, the output  of information will increase as the level increases
    0 - Not verbose, i.e. no output
    1 - Outputs key information
    2 - Slightly verbose, outputs which functions are being run.
    3 - Moderately verbose, outputs pertinent information used in the function logic
    4 - Very verbose, outputs even more information
    5 - Very very verbose, outputs everything
'''


class Crc32_Best(Crc32Base):
    """https://users.ece.cmu.edu/~koopman/crc/index.html"""
    _names = ('Best',)
    _width = 32
    _poly = 0x973afb51
    _initvalue = 0x00000000
    _reflect_input = False
    _reflect_output = False
    _xor_output = 0x00000000
    _check_result = 0x678B6786
    _residue = 0x00000000


def calculate_modbus_crc(data):
    """
            Calculates and returns CRC16-MODBUS

        """
    crc_instance = Crc16Modbus()
    return crc_instance.calcbytes(data, byteorder="little")


def calculate_16bit_crc(data):
    """
        Calculates and returns CRC16-CCITT
        Crc16Ccitt() assumes initial value of 0x0000, use Crc16CcittFalse() for initial value of 0xFFFF
    :param data:
    :return:
    """
    crc_instance = CrcXmodem()
    return crc_instance.calcbytes(data, byteorder="big")


def calculate_32bit_crc(data):
    """
        Calculates and returns CRC16-CCITT
        Crc16Ccitt() assumes initial value of 0x0000, use Crc16CcittFalse() for initial value of 0xFFFF
    :param data:
    :return:
    """
    crc_instance = Crc32_Best()
    return crc_instance.calcbytes(data, byteorder="big")


class Property:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def print(self):
        if "fault" in self.name:
            print(self.name, bin(self.value), " | ", end="")
        elif "prpf" in self.name:
            print(self.name, "%.5f" % self.value, " | ", end="")
        else:
            print(self.name, self.value, " | ", end="")


class RealTimePlot:
    def __init__(self, fig, ax, x_axis_property, y_axis_property):
        self.fig = fig
        self.ax = ax
        self.x_axis_property = x_axis_property
        self.y_axis_property = y_axis_property
        # self.x = []
        # self.y = []

    def update(self, properties):
        x = None
        y = None
        for prp in properties:
            if prp.name == self.x_axis_property:
                x = prp.value
                # self.x.append(prp.value)
            if prp.name == self.y_axis_property:
                y = prp.value
                # self.y.append(prp.value)

        self.ax.plot(x, y, "r.")

        self.fig.canvas.draw()

        # self.ax.set_xlim(left=max(0, i - 50), right=i + 50)
        self.fig.show()
        plt.pause(0.0001)


class CommandConstants:
    byteEndianness = "big"
    GET = b'\xFE'
    SET = b'\xFD'
    END = b'\xFC'
    RESET = b'\xFB'
    START = b'\xFA'
    SUCCESS = b'\xF9'
    FAIL = b'\xF8'
    BEGIN_DATA_STREAM = b'\xF7'
    END_DATA_STREAM = b'\xF6'
    EVENT_DRIVEN_DATA_STREAM = b'\xF5'
    GET_STATUS = b'\xF4'
    WRITE_NONVOLATILE_PROPERTY = b'\xF3'


class CommandInterface:
    def __init__(self,
                 mcu_serial_port,
                 mcu_serial_baud,
                 mcu_serial_timeout,
                 plc_serial_port=None,
                 plc_serial_baud=None,
                 plc_serial_timeout=None,
                 modbus_serial_port=None,
                 modbus_serial_baud=None,
                 modbus_serial_timeout=None
                 ):
        self.mcu_serial_port = mcu_serial_port
        self.mcu_serial_baud = mcu_serial_baud
        self.mcu_serial_timeout = mcu_serial_timeout
        self.plc_serial_port = plc_serial_port
        self.plc_serial_baud = plc_serial_baud
        self.plc_serial_timeout = plc_serial_timeout
        self.modbus_serial_port = modbus_serial_port
        self.modbus_serial_baud = modbus_serial_baud
        self.modbus_serial_timeout = modbus_serial_timeout
        # self.is_modbus_position_control = False
        self.is_plc_logging = False
        if self.plc_serial_port is not None and self.plc_serial_baud is not None and self.plc_serial_timeout is not None:
            self.is_plc_logging = True
        self.properties_to_print = []
        self.properties_data = []
        manager = multiprocessing.Manager()
        self.plc_properties = manager.list()
        self.mcu_bytes_list = manager.list()
        self.mcu_bytes_backup = manager.list()
        self.plc_bytes_list = manager.list()
        self.plc_bytes_backup = manager.list()
        self.mcu_row_list = manager.list()
        self.plc_row_list = manager.list()
        self.is_saving_mcu_file = manager.Value("i", False)
        self.is_saving_plc_file = manager.Value("i", False)
        self.is_saving_data_backups = manager.Value("i", False)
        self.is_plc_ready = manager.Value("i", False)

        self.num_bytes_per_property = 4
        self.all_properties = parse_properties_from_file("../../source/property_management.h")
        self.default_data_stream_properties = parse_default_data_stream_properties_from_file("../../source/command_interface.c")

    def send_and_retry(self, bytes_to_send, num_retries=20, verbosity=0, serial_in=None):
        """
        Repeatedly send a message until it is received correctly
        """
        if serial_in is None:
            ser = serial.Serial(port=self.mcu_serial_port, baudrate=self.mcu_serial_baud, timeout=self.mcu_serial_timeout)
        else:
            ser = serial_in

        if verbosity >= 3:
            print("bytes_to_send: ", bytes_to_send.hex(":"))
        send_success = False
        retry_count = 0
        while not send_success and retry_count <= num_retries:
            if verbosity >= 3:
                print("sending...")
            ser.write(bytes_to_send)
            time.sleep(.2)

            response = ser.read(1)

            if response == CommandConstants.SUCCESS:
                if verbosity >= 3:
                    print("send success")
                send_success = True
            elif response == CommandConstants.FAIL and verbosity >= 3:
                print("send fail")
            elif verbosity >= 3:
                print("unexpected bytes in reply: ", response.hex())
            retry_count += 1
        if retry_count > num_retries and not send_success:
            raise Exception("Num retries exceeded")
        if serial_in is None:
            ser.close()

    def reset_command(self, verbosity=0):
        if verbosity >= 2:
            print("reset_command")
        bytes_to_send = CommandConstants.START
        bytes_to_send += CommandConstants.RESET
        bytes_to_send += calculate_16bit_crc(bytes_to_send)
        bytes_to_send += CommandConstants.END

        send_success = False
        fail_counter = 0
        while not send_success:
            try:
                self.send_and_retry(bytes_to_send, num_retries=0, verbosity=verbosity)
                ser = serial.Serial(port=self.mcu_serial_port, baudrate=self.mcu_serial_baud, timeout=0.1)
                b = ser.read()
                ser.close()
                if b == b'':
                    send_success = True
            except (KeyboardInterrupt, SystemExit):
                print("Exiting...")
                break
            except:
                if verbosity >= 3:
                    traceback.print_exc()
                fail_counter += 1
                if fail_counter > 100:
                    traceback.print_exc()
                    raise Exception("Error initializing serial connection")
                else:
                    continue

    def begin_plc_data_stream(self, verbosity=0):
        if verbosity >= 2:
            print("begin_plc_data_stream")

        ser = serial.Serial(port=self.plc_serial_port, baudrate=self.plc_serial_baud, timeout=self.plc_serial_timeout)
        ser.reset_input_buffer()

        print("Waiting for handshake from PLC")
        handshake_request = b'A'
        received_byte = b''
        while received_byte != handshake_request:
            received_byte = ser.read()
            print("received_byte", received_byte)

        if verbosity >= 2:
            print("Handshake received from PLC")

        handshake_response = b'C'

        if verbosity >= 2:
            print("Sending handshake response ", handshake_response)
        ser.write(handshake_response)
        # receive and parse the first row with column headers
        # if verbosity >= 2:
        #     print("Waiting for headers")
        # headers_bytes = ser.readline()
        # if headers_bytes == b'':
        #     raise Exception("Headers not received from PLC")
        # print("headers_bytes", headers_bytes)
        # headers_str = headers_bytes.decode(encoding="ascii", errors="ignore")
        # headers_list = headers_str.split(sep=" ")
        headers_list = ["time",
                        "valve_open",
                        "valve_status",
                        "plc_top_switch",
                        "plc_middle_switch",
                        "contactor",
                        "open_command",
                        "displacement",
                        "position_feedback",
                        "force",
                        "thermocouple_a",
                        "thermocouple_b",
                        "position_command",
                        "thermocouple_c",
                        "valve_position_modbus",
                        "position_command_modbus"]
        self.plc_properties.extend(headers_list)
        ser.close()

    def begin_data_stream_command(self, verbosity=0):
        if verbosity >= 2:
            print("begin_data_stream_command")
        bytes_to_send = CommandConstants.START
        bytes_to_send += CommandConstants.BEGIN_DATA_STREAM
        bytes_to_send += calculate_16bit_crc(bytes_to_send)
        bytes_to_send += CommandConstants.END

        self.send_and_retry(bytes_to_send, verbosity=verbosity)

    def end_data_stream_command(self, verbosity=0):

        if verbosity >= 2:
            print("end_data_stream_command")
        bytes_to_send = CommandConstants.START
        bytes_to_send += CommandConstants.END_DATA_STREAM
        bytes_to_send += CommandConstants.END

        ser = serial.Serial(port=self.mcu_serial_port, baudrate=self.mcu_serial_baud, timeout=self.mcu_serial_timeout)
        ser.write(bytes_to_send)
        ser.close()

    def event_driven_data_stream_command(self, verbosity=0):
        if verbosity >= 2:
            print("event_driven_data_stream_command")
        bytes_to_send = CommandConstants.START
        bytes_to_send += CommandConstants.EVENT_DRIVEN_DATA_STREAM
        bytes_to_send += calculate_16bit_crc(bytes_to_send)
        bytes_to_send += CommandConstants.END

        self.send_and_retry(bytes_to_send, verbosity=verbosity)

    def get_properties_command(self, properties_names, verbosity=0):
        if verbosity >= 2:
            print("get_properties_command start")

        # Make sure the list is empty
        while self.properties_to_print:
            self.properties_to_print.pop()

        # Send each get command
        for prp in properties_names:
            if verbosity >= 3:
                print("property:", prp)
            self.properties_to_print.append(prp)
            # Generate the message
            bytes_to_send = CommandConstants.START
            bytes_to_send += CommandConstants.GET
            bytes_to_send += self.all_properties.index(prp).to_bytes(1, byteorder="big")
            bytes_to_send += calculate_16bit_crc(bytes_to_send)
            bytes_to_send += CommandConstants.END
            self.send_and_retry(bytes_to_send, verbosity=verbosity)
        if verbosity >= 2:
            print("get_properties_command end")

    def set_property_command(self, property_name, property_value, verbosity=0):
        if verbosity >= 2:
            print("set_property_command start")
        if verbosity >= 3:
            print("property_name:", property_name, "property_value:", property_value)
        # Generate the message
        bytes_to_send = CommandConstants.START
        bytes_to_send += CommandConstants.SET
        bytes_to_send += self.all_properties.index(property_name).to_bytes(1, byteorder="big")
        if "prpf" in property_name:
            bytes_to_send += struct.pack(">f", property_value)
        else:
            bytes_to_send += property_value.to_bytes(4, byteorder="big")
        bytes_to_send += calculate_16bit_crc(bytes_to_send)
        bytes_to_send += CommandConstants.END
        self.send_and_retry(bytes_to_send, verbosity=verbosity)
        if verbosity >= 2:
            print("set_property_command end")

    def get_status_command(self, property_id, verbosity=0):
        if verbosity >= 2:
            print("get_status_command start")

        ser = serial.Serial(port=self.mcu_serial_port, baudrate=self.mcu_serial_baud, timeout=self.mcu_serial_timeout)

        # Generate the message
        bytes_to_send = CommandConstants.START
        bytes_to_send += CommandConstants.GET_STATUS
        bytes_to_send += self.all_properties.index(property_id).to_bytes(1, byteorder="big")
        bytes_to_send += calculate_16bit_crc(bytes_to_send)
        bytes_to_send += CommandConstants.END

        response_received = False
        while not response_received:

            # Send the message
            self.send_and_retry(bytes_to_send, verbosity=verbosity, serial_in=ser)

            # Receive the response
            response_length = 8

            received_bytes = ser.read(response_length)

            if not len(received_bytes) == response_length:
                if verbosity >= 3:
                    print("Incorrect response received, expected a response of ", response_length, "bytes, received", len(received_bytes))
                    print("bytes received", received_bytes.hex(":"))
                if verbosity >= 2:
                    print("Re-attempting...")
                continue
            # Check the CRC
            calculated_crc = calculate_16bit_crc(received_bytes[0: 5])
            if not calculated_crc == received_bytes[5: 7]:
                if verbosity >= 3:
                    print("Incorrect response received (CRC mismatch)")
                if verbosity >= 2:
                    print("Re-attempting...")
                break
            else:
                response_received = True
                if "prpf" in property_id:
                    [value] = struct.unpack('>f', received_bytes[1: 5])
                else:
                    value = int.from_bytes(received_bytes[1: 5],
                                           CommandConstants.byteEndianness,
                                           signed=False)
        if verbosity >= 2:
            print("Value:", value)

        if verbosity >= 2:
            print("get_status_command end")

        ser.close()

        return value

    def write_nonvolatile_property_command(self, property_id, verbosity=0):
        if verbosity >= 2:
            print("write_nonvolatile_property_command start")

        bytes_to_send = CommandConstants.START
        bytes_to_send += CommandConstants.WRITE_NONVOLATILE_PROPERTY
        bytes_to_send += self.all_properties.index(property_id).to_bytes(1, byteorder="big")
        bytes_to_send += calculate_16bit_crc(bytes_to_send)
        bytes_to_send += CommandConstants.END

        self.send_and_retry(bytes_to_send, verbosity=verbosity)

        if verbosity >= 2:
            print("write_nonvolatile_property_command end")

    def get_next_mcu_row(self, bytes_list_index, verbosity=0):
        crc_data_length = 1 + self.num_bytes_per_property * len(self.properties_to_print)
        row_length = crc_data_length + 4 + 1

        # check if the row is long enough
        if bytes_list_index + row_length > len(self.mcu_bytes_list):
            return None, None
        row_bytes = b''.join(self.mcu_bytes_list[bytes_list_index: bytes_list_index + row_length])
        index = 0

        # check the first and last bytes in the row
        row_first_byte = row_bytes[index:index + 1]
        row_last_byte = row_bytes[index + row_length - 1: index + row_length]
        if not (row_first_byte == CommandConstants.START and row_last_byte == CommandConstants.END):
            if verbosity == 4:
                print("Start and end bytes not found:")
                print("Start:", row_first_byte.hex(), "End:", row_last_byte.hex())
                print("Row data:", row_bytes[index: index + row_length].hex(" "))
            return bytes_list_index + 1, None

        # validate the CRC
        crc_received = row_bytes[index + crc_data_length: index + crc_data_length + 4]
        crc_calculated = calculate_32bit_crc(row_bytes[index: index + crc_data_length])
        if verbosity == 4:
            print("CRC bytes:", crc_received.hex("|"))
            print("Calculated CRC:", crc_calculated.hex("|"))
            print("Row data:", row_bytes[index: index + row_length].hex(" "))
        if not (crc_received == crc_calculated):
            if verbosity == 4:
                print("CRC check fail")
            bytes_list_index += 1
            if verbosity >= 1:
                print(bytes_list_index)
            return bytes_list_index, None
        else:
            if verbosity == 4:
                print("CRC check pass")

        # parse the properties
        index += 1  # go past the START byte
        row = []
        for property_name in self.properties_to_print:
            # parse floats
            if "prpf" in property_name:
                [float_value] = struct.unpack('>f', row_bytes[index: index + self.num_bytes_per_property])
                row.append(float_value)

                # check if properties that have a percentage value have a valid value
                if property_name in ["prpf_position_command",
                                     "prpf_valve_slew_target_position",
                                     "prpf_valve_slew_start_position",
                                     "prpf_valve_slew_end_position"]:
                    if not (110.0 >= float_value >= -10.0):
                        print(property_name, "has an invalid value: ", float_value)
                        return bytes_list_index + 1, None
            # parse unsigned ints
            else:
                int_value = int.from_bytes(
                    row_bytes[index: index + self.num_bytes_per_property],
                    CommandConstants.byteEndianness,
                    signed=False
                )
                row.append(int_value)

                # check validity of execution times, these values are limited by the hardware watchdog
                if property_name in ["prp_ADC_service_exec_time",
                                     "prp_sensors_service_exec_time",
                                     "prp_properties_service_exec_time",
                                     "prp_communications_service_exec_time",
                                     "prp_valve_service_exec_time",
                                     "prp_wire_bundle_service_exec_time",
                                     "prp_wire_bundle_physics_service_exec_time",
                                     "prp_motor_service_exec_time",
                                     "prp_body_temp_service_exec_time",
                                     "prp_command_interface_service_exec_time"]:
                    if not (1e4 >= int_value >= 0):
                        print("Execution time of", property_name, "is invalid:", int_value)
                        return bytes_list_index + 1, None

            index += self.num_bytes_per_property

        if verbosity >= 4:
            print(row)
        return bytes_list_index + row_length, row

    def get_next_plc_row(self, bytes_list_index, verbosity=0):
        if bytes_list_index >= len(self.plc_bytes_list):
            return None, None
        elif bytes_list_index == 0:
            if self.plc_bytes_list[0] == b"\n":
                self.plc_bytes_list.pop(0)
                return 0, None
            else:
                return 1, None
        elif self.plc_bytes_list[bytes_list_index] == b"\n":
            row_bytes = b''.join(self.plc_bytes_list[0: bytes_list_index])
            row_ascii = row_bytes.decode(encoding="ascii")
            row_list = row_ascii.split(sep=" ")
            row = []
            if verbosity >= 5:
                print("bytes_list_index:", bytes_list_index)
                print("self.plc_bytes_list[bytes_list_index]", self.plc_bytes_list[bytes_list_index])
                print("self.plc_bytes_list", self.plc_bytes_list)
                print("row_bytes", row_bytes)
                print("row_ascii:", row_ascii)
                print("row_list:", row_list)
            for r in row_list:
                if r == 'BB\r':
                    continue
                elif r != '':
                    try:
                        datum = int(r)
                    except:
                        raise Exception("Invalid data type, integer expected")
                    row.append(datum)
            if verbosity >= 4:
                print(row)
            return bytes_list_index, row
        elif bytes_list_index + 1 > len(self.plc_bytes_list):  # check if the row is long enough
            return None, None
        else:
            return bytes_list_index + 1, None

    def parse_mcu_bytes(self, read_time_seconds, filename_prefix, cyclic=False, verbosity=0):
        """
        Parse the list of bytes generated by read_mcu_data_stream.

        Repeatedly searches the bytes list for a row, parses the row values, and resets the list index
        """
        if self.is_plc_logging:
            while not self.is_plc_ready.get():
                time.sleep(0.1)

        bytes_list_index = 0
        while True:
            try:
                data = []
                start_time = datetime.now()
                read_time = timedelta(seconds=read_time_seconds)
                while datetime.now() - start_time < read_time:
                    bytes_list_index, row_data = self.get_next_mcu_row(bytes_list_index, verbosity=verbosity)
                    if row_data is not None:
                        for i in range(bytes_list_index):
                            self.mcu_bytes_list.pop(0)
                        bytes_list_index = 0
                        now = datetime.now()
                        timestamp = now.isoformat()
                        row_data.append(timestamp)
                        data.append(row_data)
                        self.mcu_row_list.append(row_data)
                    if bytes_list_index is None:  # Not enough bytes in the list, need to wait for more data from the MCU
                        wait_time = 0.001
                        if verbosity >= 4:
                            print("Waiting", wait_time, "seconds for more data...")
                        time.sleep(wait_time)
                        bytes_list_index = 0
                df = pd.DataFrame(data, columns=self.properties_to_print + ["timestamp"])
                date_time_obj = datetime.now()

                self.is_saving_mcu_file.set(True)  # other processes know to stop printing
                time.sleep(1)

                save_filename = filename_prefix + "[MCU][" + date_time_obj.strftime("%Y-%m-%d-%H.%M.%S") + "].csv"
                print("\n\n\n\nSaving", read_time_seconds, "seconds of MCU data to:", save_filename, "\n\n\n\n")
                df.to_csv(save_filename)

                time.sleep(1)
                self.is_saving_mcu_file.set(False)
                if not cyclic:
                    return
            except (KeyboardInterrupt, SystemExit):
                print("Exiting...")
                break
            except:
                traceback.print_exc()

    def parse_plc_bytes(self, read_time_seconds, filename_prefix, cyclic=False, verbosity=0):
        """
        Parse the list of bytes generated by read_mcu_data_stream.

        Repeatedly searches the bytes list for a row, parses the row values, and resets the list index
        """
        if self.is_plc_logging:
            while not self.is_plc_ready.get():
                time.sleep(0.1)

        bytes_list_index = 0
        while True:
            try:
                data = []
                start_time = datetime.now()
                read_time = timedelta(seconds=read_time_seconds)
                while datetime.now() - start_time < read_time:
                    bytes_list_index, row_data = self.get_next_plc_row(bytes_list_index, verbosity=verbosity)

                    if row_data is not None:
                        for i in range(bytes_list_index):
                            self.plc_bytes_list.pop(0)
                        bytes_list_index = 0
                        if len(row_data) == len(self.plc_properties):
                            now = datetime.now()
                            timestamp = now.isoformat()
                            row_data.append(timestamp)
                            data.append(row_data)
                            self.plc_row_list.append(row_data)
                    if bytes_list_index is None:  # Not enough bytes in the list, need to wait for more data from the MCU
                        wait_time = 0.001
                        if verbosity >= 4:
                            print("Waiting", wait_time, "seconds for more data...")
                        time.sleep(wait_time)
                        bytes_list_index = 0
                if self.plc_properties:
                    df = pd.DataFrame(data, columns=self.plc_properties + ["timestamp"])
                else:
                    df = pd.DataFrame(data)
                date_time_obj = datetime.now()

                self.is_saving_plc_file.set(True)  # other processes know to stop printing
                time.sleep(1)

                save_filename = filename_prefix + "[PLC][" + date_time_obj.strftime("%Y-%m-%d-%H.%M.%S") + "].csv"
                print("\n\n\n\nSaving", read_time_seconds, "seconds of PLC data to:", save_filename, "\n\n\n\n")
                df.to_csv(save_filename)

                time.sleep(1)
                self.is_saving_plc_file.set(False)
                if not cyclic:
                    return
            except (KeyboardInterrupt, SystemExit):
                print("Exiting...")
                break
            except:
                traceback.print_exc()

    def print_rows(self, read_time_seconds, print_period, cyclic=False, verbosity=0):
        """ Prints rows of properties data from a list of rows"""
        # TODO print data from PLC
        if verbosity >= 2:
            print("Start print_rows")
        while True:
            try:
                start_time = datetime.now()
                read_time = timedelta(seconds=read_time_seconds)
                while datetime.now() - start_time < read_time:
                    time.sleep(print_period)
                    if self.mcu_row_list:
                        row = self.mcu_row_list.pop(0)
                        while self.mcu_row_list:
                            self.mcu_row_list.pop()
                        for i, c in enumerate(row):
                            if i < len(self.properties_to_print):
                                if type(c) is float:
                                    print(self.properties_to_print[i] + ":", "%.5f" % c, end="\t")
                                else:
                                    print(self.properties_to_print[i] + ":", c, end="\t")
                            elif i == len(self.properties_to_print):
                                if type(c) is str:
                                    print("timestamp: ", c, end="\t")
                                else:
                                    raise Exception("ERROR, timestamp should be a string")
                            else:
                                raise Exception("ERROR, too many items in row data")
                        print()
                    while self.is_saving_mcu_file.get():
                        time.sleep(0.1)
                if not cyclic:
                    if verbosity >= 2:
                        print("End print_rows")
                    return
            except (KeyboardInterrupt, SystemExit):
                print("Exiting...")
                break
            except:
                traceback.print_exc()

    def read_mcu_data_stream(self, read_time_seconds, is_cyclic=False, verbosity=0):
        # wait until PLC has sent the handshake
        if self.is_plc_logging:
            while not self.is_plc_ready.get():
                time.sleep(0.1)

        """ Reads from a stream on a serial connection to a list of bytes. """
        ser = serial.Serial(port=self.mcu_serial_port, baudrate=self.mcu_serial_baud, timeout=self.mcu_serial_timeout)

        if verbosity >= 2:
            print("Start read_mcu_data_stream")
        bytes_backup = []
        while True:
            start_time = datetime.now()
            read_time = timedelta(seconds=read_time_seconds)
            while datetime.now() - start_time < read_time:
                try:
                    received_byte = ser.read()

                    if received_byte == b'':
                        if verbosity >= 1:
                            print("Timed out")
                        break
                    else:
                        if verbosity >= 4:
                            print(received_byte.hex())
                        self.mcu_bytes_list.append(received_byte)
                        bytes_backup.append(received_byte)
                        if not self.is_saving_data_backups.get():
                            self.mcu_bytes_backup.extend(bytes_backup)
                            bytes_backup.clear()
                except (KeyboardInterrupt, SystemExit):
                    print("Exiting...")
                    break
                except:
                    traceback.print_exc()

            if not is_cyclic:
                return

        ser.close()
        if verbosity >= 2:
            print("End read_mcu_data_stream")

    def read_plc_data_stream(self, read_time_seconds, is_cyclic=False, verbosity=0):
        self.begin_plc_data_stream(verbosity)
        self.is_plc_ready.set(True)

        """ Reads from a stream on a serial connection to a list of bytes. """
        ser = serial.Serial(port=self.plc_serial_port, baudrate=self.plc_serial_baud, timeout=self.plc_serial_timeout)

        if verbosity >= 2:
            print("Start read_plc_data_stream")
        bytes_backup = []
        while True:
            start_time = datetime.now()
            read_time = timedelta(seconds=read_time_seconds)
            while datetime.now() - start_time < read_time:
                try:
                    received_byte = ser.read()

                    if received_byte == b'':
                        if verbosity >= 1:
                            print("Timed out")
                        break
                    else:
                        if verbosity >= 4:
                            print(received_byte.hex())
                        self.plc_bytes_list.append(received_byte)
                        bytes_backup.append(received_byte)
                        if not self.is_saving_data_backups.get():
                            self.plc_bytes_backup.extend(bytes_backup)
                            bytes_backup.clear()
                except (KeyboardInterrupt, SystemExit):
                    print("Exiting...")
                    break
                except:
                    traceback.print_exc()

            if not is_cyclic:
                return

        ser.close()
        if verbosity >= 2:
            print("End read_plc_data_stream")

        # def real_time_plotting_update(self, app, verbosity=0):
        # app.image
        # app.text("TEMPERATURE A:", 100, 100)
        # app.text("TEMPERATURE B:", 100, 200)
        # app.text("TEMPERATURE C:", 100, 300)
        # app.text("DegC", 450, 100)
        # app.text("DegC", 450, 200)
        # app.text("DegC", 450, 300)

        app.strokeWeight(2)

        app.line(whitespace, height - whitespace, width - whitespace, height - whitespace)  # x-axis
        app.line(whitespace, 200, whitespace, height - whitespace)  # y-axis

        app.strokeWeight(1)
        for i in range(5):
            app.line(
                0,
                height - (linear_sensor_range - linear_sensor_home + i * 5 * displacement_sensitivity) / ystretch,
                width - 2 * whitespace,
                height - (linear_sensor_range - linear_sensor_home + i * 5 * displacement_sensitivity) / ystretch
            )

        app.strokeWeight(2)
        # app.scale(1,-1) # invert y
        # app.translate(whitespace,whitespace-height) 
        app.text("/", 1160, 410)  # 390 for 900px
        app.text("/", 1160, 540)  # 515 for 900px
        app.text("/", 1160, 670)  # 640 for 900px
        app.text("/", 1160, 800)  # 765 for 900px
        app.text("/", 1160, 930)  # 885 for 900px
        app.fill(0, 255, 0)
        app.text("20mm", 1060, 410)
        app.text("15mm", 1060, 540)
        app.text("10mm", 1060, 670)
        app.text("5mm", 1060, 800)
        app.text("0mm", 1060, 930)
        app.fill(0, 0, 255)
        app.text("4kN", 1180, 410)
        app.text("3kN", 1180, 540)
        app.text("2kN", 1180, 670)
        app.text("1kN", 1180, 800)
        app.text("0kN", 1180, 930)

        app.redraw()

    def real_time_plotting(self, verbosity=0):
        # Graphics
        whitespace = 50
        linear_sensor_home = 56164
        linear_sensor_range = 70000  # 68000         # ~1,500 more than linear_sensor_home
        displacement_sensitivity = 2580  # 2580.2 ADC/mm sensitivity of linear sensor
        force_offset = 1196  # force offset
        force_sensitivity = 8  # 7.73 ADC/N
        tune = 1
        height = 1024
        width = 1280

        ystretch = 100
        yFstretch = 72  # 600N : 4mm
        yFoffset = 137  # offset to 0mm line
        yPoffset = 72  # offset to 0mm line
        xstretch = 10 * 3  # use 3.1 for laptop screen and 2.5 with monitor set to 1600x900

        app = App(width, height)  # create window: width, height

        app.textSize(30)
        # app.imageMode
        # app.loadImage("KINITICS-SMALLCOLOR_200.jpg")
        app.background(255)
        app.fill(0)

        # self.real_time_plotting_update(app)
        # app.image
        # app.text("TEMPERATURE A:", 100, 100)
        # app.text("TEMPERATURE B:", 100, 200)
        # app.text("TEMPERATURE C:", 100, 300)
        # app.text("DegC", 450, 100)
        # app.text("DegC", 450, 200)
        # app.text("DegC", 450, 300)

        app.strokeWeight(2)

        app.line(whitespace, height - whitespace, width - whitespace, height - whitespace)  # x-axis
        app.line(whitespace, 200, whitespace, height - whitespace)  # y-axis

        app.strokeWeight(1)
        for i in range(5):
            app.line(
                0,
                height - (linear_sensor_range - linear_sensor_home + i * 5 * displacement_sensitivity) / ystretch,
                width - 2 * whitespace,
                height - (linear_sensor_range - linear_sensor_home + i * 5 * displacement_sensitivity) / ystretch
            )

        app.strokeWeight(2)
        # app.scale(1,-1) # invert y
        # app.translate(whitespace,whitespace-height)
        app.text("/", 1160, 410)  # 390 for 900px
        app.text("/", 1160, 540)  # 515 for 900px
        app.text("/", 1160, 670)  # 640 for 900px
        app.text("/", 1160, 800)  # 765 for 900px
        app.text("/", 1160, 930)  # 885 for 900px
        app.fill(0, 255, 0)
        app.text("20mm", 1060, 410)
        app.text("15mm", 1060, 540)
        app.text("10mm", 1060, 670)
        app.text("5mm", 1060, 800)
        app.text("0mm", 1060, 930)
        app.fill(0, 0, 255)
        app.text("4kN", 1180, 410)
        app.text("3kN", 1180, 540)
        app.text("2kN", 1180, 670)
        app.text("1kN", 1180, 800)
        app.text("0kN", 1180, 930)

        app.redraw()

        # wait until PLC has sent the handshake
        while not self.is_plc_ready.get():
            time.sleep(0.1)

        while True:
            try:
                if self.plc_row_list:
                    # get force ADC
                    force = self.plc_row_list[-1][9]
                    # get displacement ADC
                    displacement = self.plc_row_list[-1][7]
                    # get time
                    current_time = self.plc_row_list[-1][0]
                    start_time = self.plc_row_list[0][0]
                    # plot displacement
                    app.point((current_time - start_time) / xstretch, (linear_sensor_range - displacement) / ystretch + yPoffset)
                    # plot force
                    app.point((current_time - start_time) / xstretch, force / yFstretch + yFoffset)
                    app.redraw()
                    time.sleep(0.2)
            except (KeyboardInterrupt, SystemExit):
                print("Exiting...")
                break
            except:
                traceback.print_exc()

    def backup_data(self, verbosity=0):
        '''
        Backup the un-parsed byte data from the PLC and MCUs
        '''
        while True:
            try:
                time.sleep(10)  # Save to file every 10 seconds
                date_time_obj = datetime.now()
                self.is_saving_data_backups.set(True)
                if self.is_plc_logging:
                    plc_save_filename = "byte_data_backup/[PLC][" + date_time_obj.strftime("%Y-%m-%d-%H.00.00") + "].bin"
                    with open(plc_save_filename, "ab") as f:
                        f.write(b''.join(self.plc_bytes_backup[:]))
                    self.plc_bytes_backup[:] = []
                mcu_save_filename = "byte_data_backup/[MCU][" + date_time_obj.strftime("%Y-%m-%d-%H.00.00") + "].bin"
                with open(mcu_save_filename, "ab") as f:
                    f.write(b''.join(self.mcu_bytes_backup[:]))
                self.mcu_bytes_backup[:] = []
                self.is_saving_data_backups.set(False)

            except (KeyboardInterrupt, SystemExit):
                print("Exiting...")
                break
            except:
                traceback.print_exc()

    def modbus_controller(self, modbus_command_file, verbosity=0):
        assert self.modbus_serial_port
        assert self.modbus_serial_baud
        assert self.modbus_serial_timeout

        # load up the csv
        df = pd.read_csv(modbus_command_file)

        ser = serial.Serial(port=self.modbus_serial_port, baudrate=self.modbus_serial_baud, timeout=self.modbus_serial_timeout, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO)

        # wait until PLC has sent the handshake
        while not self.is_plc_ready.get():
            time.sleep(0.1)

        # get the current time
        start_time = datetime.now()
        # loop through the signal
        i = 0
        while i < len(df.index):
            now = datetime.now()
            time_elapsed = (now - start_time).total_seconds()
            if time_elapsed > df["time"][i]:
                # send the modbus command
                position_command = int(df["position_command"][i] * 10)
                message = b'\x01\x06\x00\x00'
                message += position_command.to_bytes(2, byteorder="big")
                message += calculate_modbus_crc(message)
                if verbosity >= 3:
                    print("Modbus message for position command of ", df["position_command"][i], ":", message.hex("|"))
                ser.write(message)
                i += 1
            time.sleep(0.001)

        # get the time delta in seconds
        # compare with the signal time

    def read_data(self, read_time_seconds, file_name_prefix, print_period, is_cyclic=False, real_time_plot=False, modbus_command_file=None, verbosity=0):
        if verbosity >= 2:
            print("Start read_data")

        if not self.properties_to_print:
            self.properties_to_print = self.default_data_stream_properties
            if verbosity >= 2:
                print("Using default properties:", self.properties_to_print)

        process1 = multiprocessing.Process(target=self.read_mcu_data_stream, args=(read_time_seconds, is_cyclic, verbosity))
        process2 = multiprocessing.Process(target=self.parse_mcu_bytes, args=(read_time_seconds, file_name_prefix, is_cyclic, verbosity))
        process3 = multiprocessing.Process(target=self.print_rows, args=(read_time_seconds, print_period, is_cyclic, verbosity))
        process4 = multiprocessing.Process(target=self.backup_data, args=(verbosity,))
        if self.is_plc_logging:
            process5 = multiprocessing.Process(target=self.read_plc_data_stream, args=(read_time_seconds, is_cyclic, verbosity))
            process6 = multiprocessing.Process(target=self.parse_plc_bytes, args=(read_time_seconds, file_name_prefix, is_cyclic, verbosity))
        if real_time_plot:
            process7 = multiprocessing.Process(target=self.real_time_plotting, args=(verbosity,))
        if modbus_command_file:
            process8 = multiprocessing.Process(target=self.modbus_controller, args=(modbus_command_file, verbosity))
        process9 = multiprocessing.Process(target=self.send_data_to_server)

        process1.start()
        process2.start()
        process3.start()
        process4.start()
        if self.is_plc_logging:
            process5.start()
            process6.start()
        if real_time_plot:
            process7.start()
        if modbus_command_file:
            process8.start()
        process9.start()


        process1.join()
        process2.join()
        process3.join()
        process4.join()
        if self.is_plc_logging:
            process5.join()
            process6.join()
        if real_time_plot:
            process7.join()
        if modbus_command_file:
            process8.join()
        process9.join()

    def send_data_to_server(self):
        channel_layer = get_channel_layer()
        mcu_valve_position = 0
        plc_displacement = 0
        plc_displacement_sensitivity = 2580.2       # ADC/mm
        plc_displacement_home = 58521
        plc_force = 0
        plc_force_sensitivity = 7.73                # ADC/N
        plc_force_home = 1196
        plc_timestamp = datetime.now().isoformat()
        mcu_timestamp = plc_timestamp

        while True:
            try:
                if len(self.mcu_row_list) > 0:
                    mcu_valve_position = self.mcu_row_list[-1][self.properties_to_print.index("prpf_valve_position")]
                    mcu_timestamp = self.mcu_row_list[-1][-1]

                # print(len(self.plc_row_list))

                if len(self.plc_row_list) > 0:
                    plc_displacement = self.plc_row_list[-1][self.plc_properties.index("displacement")]
                    plc_displacement = (plc_displacement_home-plc_displacement)/plc_displacement_sensitivity
                    plc_force = self.plc_row_list[-1][self.plc_properties.index("force")]
                    plc_force = (plc_force-plc_force_home)/plc_force_sensitivity
                    plc_timestamp = self.plc_row_list[-1][-1]

                # print(plc_displacement)

                message = json.dumps(
                    {'id': "MCU", 'value': mcu_valve_position, 'time': mcu_timestamp})

                async_to_sync(channel_layer.group_send)(
                    'gui',
                    {
                        'type': 'run_periodic_task',
                        'message': message
                    }
                )

                message = json.dumps(
                    {'id': "PLC", 'value': plc_displacement, 'time': plc_timestamp,
                     'force': plc_force})

                async_to_sync(channel_layer.group_send)(
                    'gui',
                    {
                        'type': 'run_periodic_task',
                        'message': message
                    }
                )

                time.sleep(0.5)
            except (KeyboardInterrupt, SystemExit):
                print("Exiting...")
                break
            except:
                traceback.print_exc()

                # headers_list = ["time",
                #                 "valve_open",
                #                 "valve_status",
                #                 "plc_top_switch",
                #                 "plc_middle_switch",
                #                 "contactor",
                #                 "open_command",
                #                 "displacement",
                #                 "position_feedback",
                #                 "force",
                #                 "thermocouple_a",
                #                 "thermocouple_b",
                #                 "position_command",
                #                 "thermocouple_c",
                #                 "valve_position_modbus",
                #                 "position_command_modbus"]
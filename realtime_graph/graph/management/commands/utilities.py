import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import interpolate
from datetime import datetime
import os
from tkinter import *
from tkinter import filedialog


def parse_properties_from_file(filename):
    file = open(filename, "r")
    lines = file.readlines()
    properties = []
    start_index = 0
    end_index = 0
    for i, line in enumerate(lines):
        if "typedef enum {" in line:
            start_index = i
        elif "} property_id;" in line:
            end_index = i
    assert(start_index != end_index)
    for i in range(start_index, end_index):
        if "prp" in lines[i]:
            line = lines[i].split(",")[0]
            line = line.strip()
            properties.append(line)
    return properties


def decode_prp_faults(df):
    if "prp_faults" in df.columns:
        properties = parse_properties_from_file("../source/property_management.h")
        start_index = properties.index("prp_fault_body_temperature_sensor_disconnect")
        end_index = properties.index("prp_fault_motor_lock_current_limit")
        bit_counter = 0
        for i in range(start_index, end_index + 1):
            column = []
            for j in range(len(df["prp_faults"])):
                column.append((df["prp_faults"][j] & (1 << bit_counter)) >> bit_counter)
                # if column[-1] > 0 :
                #     print(properties[i], bit_counter, bin(df["prp_faults"][j]), column[-1])
            df[properties[i]] = column
            bit_counter += 1
    return df


def parse_default_data_stream_properties_from_file(filename):
    file = open(filename, "r")
    lines = file.readlines()
    properties = []
    start_index = 0
    end_index = 0
    for i, line in enumerate(lines):
        if "property_id defaultPropertiesToPrint[] = {" in line:
            start_index = i
        elif "}; // defaultPropertiesToPrint" in line:
            end_index = i
    assert(start_index != end_index)
    for i in range(start_index, end_index):
        if "prp" in lines[i]:
            line = lines[i].split(",")[0]
            line = line.strip()
            properties.append(line)
    return properties


def combine_all_plc(directory_str):
    directory = os.fsencode(directory_str)
    # join filenames and directory
    file_list = [os.path.join(directory, i) for i in os.listdir(directory)]
    filtered_file_list = []
    for file in file_list:
        filename = os.fsdecode(file)
        if filename.endswith(".txt"):  # we assume that every bin file has a csv counterpart
            filtered_file_list.append(filename)
    # sort the files by creation data
    sorted_file_list = sorted(filtered_file_list, key=lambda f: datetime.strptime(f.split("Data_")[-1], "%Y-%m-%d_%H.%M.%S.txt"))

    plc_column_names = ["time", "valve_open", "valve_status", "plc_top_switch", "plc_middle_switch", "contactor",
                        "open_command", "displacement", "position_feedback", "force", "thermocouple_a",
                        "thermocouple_b", "position_command", "thermocouple_c"]

    data = []

    for file in sorted_file_list:
        filename = os.fsdecode(file)

        if filename.endswith(".txt"):
            with open(filename, "r") as file_in:
                print("Reading \"" + filename + "\"")
                for line in file_in:
                    row_data = line.split()

                    if len(row_data) == 14:
                        data.append(row_data)

    df = pd.DataFrame(data, columns=plc_column_names)
    save_filename = os.fsdecode(sorted_file_list[0])[0:-4] + " to " + os.fsdecode(sorted_file_list[-1])[-25:-4] + ".csv"
    print("Saving combined data to: \"" + save_filename + "\"")
    df.to_csv(save_filename)

    return save_filename


def combine_all_csv(directory_str, save_filename=None):
    print("Combining csv files.")
    # directory_str = "SYS.5 - 3.13 Long Stroke DC Position Tracking Stability Test/MCU Data/"
    directory = os.fsencode(directory_str)
    # join filenames and directory
    file_list = [os.path.join(directory, i) for i in os.listdir(directory)]
    filtered_file_list = []
    for file in file_list:
        filename = os.fsdecode(file)
        if filename.endswith(".csv"):  # we assume that every bin file has a csv counterpart
            filtered_file_list.append(filename)

    # sort the files by creation date
    sorted_file_list = sorted(filtered_file_list, key=lambda f: datetime.strptime(f[-24:-5], "%Y-%m-%d-%H.%M.%S"))

    df_list = []
    for filename in sorted_file_list:
        print(filename[:-4]+".csv")
        df = pd.read_csv(filename[:-4]+".csv")  # load the csv
        df["filename"] = [filename for i in range(len(df["prp_time"]))]
        df = decode_prp_faults(df)
        df_list.append(df)

    # join all dataframes
    all_df = pd.concat(df_list, ignore_index=True)

    print("Number of rows: ", len(all_df["prp_time"]))

    if save_filename is None:
        save_filename = os.fsdecode(sorted_file_list[0])[0:-4] + " to " + os.fsdecode(sorted_file_list[-1])[-25:-4] + ".csv"

    print("Saving parsed data to: \"" + save_filename + "\"")
    all_df.to_csv(save_filename)
    return save_filename


def combine_plc_and_mcu_data(MCU_data_filename, PLC_data_filename, plc_column_names=None, plc_start_index=None, plc_end_index=None, mcu_start_index=None, mcu_end_index=None, manual_index_finder=False):
    # load the two datasets
    if ".txt" in PLC_data_filename:
        if plc_column_names is None:
            plc_column_names = ["time", "valve_open", "valve_status", "plc_top_switch", "plc_middle_switch", "contactor",
                            "open_command", "displacement", "position_feedback", "force", "thermocouple_a",
                            "thermocouple_b", "position_command", "thermocouple_c"]
        plc_data = pd.read_csv(PLC_data_filename, names=plc_column_names, index_col=False, sep=" ")
    else:
        plc_data = pd.read_csv(PLC_data_filename)
    # print(plc_data)
    time_column = None
    for column in plc_data.columns:
        if "time" in column.lower():
            time_column = column
    if time_column is None:
        raise Exception("No time column name found in plc columns")
    plc_data[time_column] = plc_data[time_column] / 100
    plc_data[time_column] -= plc_data[time_column][0]

    mcu_data = pd.read_csv(MCU_data_filename)
    clock_ticks_per_second = 468750
    if "prpf_time_seconds" not in mcu_data.columns:
        mcu_data["prpf_time_seconds"] = (mcu_data["prp_time"] + 0xFFFFFFFF * mcu_data["prp_time_overflow_counter"]) / clock_ticks_per_second
        mcu_data["prpf_time_seconds"] -= mcu_data["prpf_time_seconds"][0]

    if manual_index_finder:
        fig, ax = plt.subplots()
        ax_twin = ax.twinx()

        ax.plot(mcu_data["prpf_time_seconds"], mcu_data["prpf_valve_position"], "+")
        ax_twin.plot(plc_data[time_column], plc_data["open_command"], "r")
        plt.show()

    if mcu_start_index is None:
        if "prpf_wire_bundle_pwm_gain" not in mcu_data.columns:
            raise Exception("Cannot sync datasets: prpf_wire_bundle_pwm_gain is missing from mcu data")

        # find the index in the mcu data where the gain becomes non-zero
        for i in range(len(mcu_data["prpf_time_seconds"])):
            if mcu_data["prpf_wire_bundle_pwm_gain"][i] > 0:
                mcu_start_index = i
                print("mcu_start_index", mcu_data["prpf_time_seconds"][mcu_start_index])
                break

    if mcu_end_index is None:
        if "prpf_wire_bundle_pwm_gain" not in mcu_data.columns:
            raise Exception("Cannot sync datasets: prpf_wire_bundle_pwm_gain is missing from mcu data")

        # find the index in the mcu data where the gain goes back to zero
        for i in reversed(range(len(mcu_data["prpf_time_seconds"]))):
            if mcu_data["prpf_wire_bundle_pwm_gain"][i] > 0:
                mcu_end_index = i
                print("mcu_end_index", mcu_data["prpf_time_seconds"][mcu_end_index])
                break

    if plc_start_index is None or plc_end_index is None:
        # we also want to know how the plc is commanding the controller, via position command or open command?
        # First find the columns name for position command
        position_command_column = None
        for column in plc_data.columns:
            if "position" in column.lower() and "command" in column.lower():
                position_command_column = column
        if position_command_column is None:
            raise Exception("Position command column not found in plc data column names")
        # Then find the column name for open command
        open_command_column = None
        for column in plc_data.columns:
            if "open" in column.lower() and "command" in column.lower():
                open_command_column = column
        if open_command_column is None:
            raise Exception("Open command column not found in plc data column names")

        if sum(plc_data[position_command_column] > 0) > 0:
            means_of_control = position_command_column
        elif sum(plc_data[open_command_column] > 0) > 0:
            means_of_control = open_command_column
        else:
            raise Exception("Problem determining the means of controlling the MCU")
        print("means_of_control", means_of_control)

    # for now we assume the plc start index is zero
    if plc_start_index is None:
        # find the index in the plc data where the open command becomes non-zero
        for i in range(len(plc_data[time_column])):
            if plc_data[means_of_control][i] > 0:
                plc_start_index = i
                print("plc_start_index: ", plc_data[time_column][plc_start_index], "seconds")
                break

    if plc_end_index is None:
        # find the plc end index
        for i in reversed(range(len(plc_data[time_column]))):
            if plc_data[means_of_control][i] > 0:
                plc_end_index = i
                print("plc_end_index: ", plc_data[time_column][plc_end_index], "seconds")
                break

    # now we have start indices and end indices for both datasets, which we now use to sync the times
    mcu_data["prpf_time_seconds"] -= mcu_data["prpf_time_seconds"][mcu_start_index]
    plc_data[time_column] -= plc_data[time_column][plc_start_index]
    time_scaling = plc_data[time_column][plc_end_index]/mcu_data["prpf_time_seconds"][mcu_end_index]
    print("time scaling:", time_scaling)
    mcu_data["prpf_time_seconds"] *= time_scaling
    mcu_data = mcu_data.drop(mcu_data.index[0:mcu_start_index])

    N = max([len(mcu_data["prpf_time_seconds"]), len(plc_data[time_column])])

    max_time = min(max(mcu_data["prpf_time_seconds"]), max(plc_data[time_column]))

    combined_data = pd.DataFrame()

    combined_data["time"] = np.linspace(0, max_time, N)

    # interpolate the MCU data columns
    for column in mcu_data.columns:
        if "filename" not in column:
            f = interpolate.interp1d(mcu_data["prpf_time_seconds"], mcu_data[column])
            combined_data[column] = f(combined_data["time"])

    # interpolate the PLC data columns
    for column in plc_data.columns:
        if "time" not in column:
            f = interpolate.interp1d(plc_data[time_column], plc_data[column])
            combined_data[column] = f(combined_data["time"])

    # fig, ax = plt.subplots()
    # ax.plot(combined_data["time"], combined_data["prpf_wire_bundle_displacement"])
    # ax.plot(combined_data["time"], combined_data["displacement"])
    # plt.show()

    # combined_data.to_csv(combined_data_filename)

    return combined_data


def open_filenames():
    root = Tk()
    root.withdraw()  # Hides the Tk window; root.deiconify() will make the window visible again

    filetypes = [
        ("data files", ".txt .csv"),
        ("all files", ".*")
    ]

    filenames = filedialog.askopenfilenames(initialdir="./", title="Select A File", filetypes=filetypes)
    root.destroy()
    return filenames


def open_dir():
    root = Tk()
    root.withdraw()

    directory = filedialog.askdirectory(initialdir="./", title="Select A Folder")
    root.destroy()
    return directory


def rmv_filepath(abs_filename):
    idx_startFilename = abs_filename.rfind('/') + 1

    if idx_startFilename == -1:
        idx_startFilename = 0            # If file path is not given then use the entire filename

    filename = abs_filename[idx_startFilename:]
    return filename



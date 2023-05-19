import multiprocessing
from django.core.management.base import BaseCommand

import json
from random import randint
from time import sleep
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from datetime import datetime, timedelta
from .command_interface import CommandInterface

def run_periodic_task_MCU():
    channel_layer = get_channel_layer()

    while True:
        message = json.dumps({'id': "MCU", 'value': randint(0, 100), 'time': (datetime.now().isoformat())})

        async_to_sync(channel_layer.group_send)(
            'gui',
            {
                'type': 'run_periodic_task',
                'message': message
            }
        )

        message = json.dumps({'id': "PLC", 'value': randint(0, 20), 'time': (datetime.now().isoformat()), 'force': 0})

        async_to_sync(channel_layer.group_send)(
            'gui',
            {
                'type': 'run_periodic_task',
                'message': message
            }
        )

        sleep(0.1)

def run_periodic_task_PLC():
    channel_layer = get_channel_layer()

    while True:
        message = json.dumps({'id': "PLC", 'value': randint(0, 20), 'time': (datetime.now().isoformat()), 'force': randint(0, 3800)})

        async_to_sync(channel_layer.group_send)(
            'gui',
            {
                'type': 'run_periodic_task',
                'message': message
            }
        )

        sleep(0.1)

class Command(BaseCommand):
    help = 'Command to start worker'

    def handle(self, *args, **kwargs):
        print("worker started")
        process1 = multiprocessing.Process(target=run_periodic_task_MCU)
        # process2 = multiprocessing.Process(target=run_periodic_task_PLC)
        process1.start()
        # process2.start()
        process1.join()
        # process2.join()

        # command = CommandInterface(
        #     mcu_serial_port='COM9',
        #     mcu_serial_baud=115200,
        #     mcu_serial_timeout=5,
        #     plc_serial_port="COM8",
        #     plc_serial_baud=57600,
        #     plc_serial_timeout=5,
        #     modbus_serial_port="COM4",
        #     modbus_serial_baud=9600,
        #     modbus_serial_timeout=5,
        # )
        #
        # verbosity = 0
        # read_time_seconds = 5 * 60
        # directory = "./"
        # file_name_prefix = directory + "System Test 3.10"  # "command_interface_test"
        # print_period = 0.5  # seconds
        # properties_to_print = [
        #     # "prp_run_count", #                   /**< Counts the number of times the application has started */
        #     # "prp_wdog_reset_count", #            /**< Counts the number of hardware watchdog resets */
        #     # "prp_factory_set_linear_sensor_ADC_min", #       /**< The ADC value on the linear sensor corresponding to 0% open that was set during the FAT*/
        #     # "prp_factory_set_linear_sensor_ADC_max", #       /**< The ADC value on the linear sensor corresponding to 100% open that was set during the FAT*/
        #     # "prp_home_position_offset_threshold", #			 /**< The allowable ADC threshold for the home position offset*/
        #     "prp_linear_sensor_ADC_min",  # /**< The ADC value on the linear sensor corresponding to 0% open*/
        #     "prp_linear_sensor_ADC_max",  # /**< The ADC value on the linear sensor corresponding to 100% open*/
        #     # "prp_position_command_ADC_min", #    /**< The ADC value of the position command corresponding to 4mA*/
        #     # "prp_position_command_ADC_max", #    /**< The ADC value of the position command corresponding to 20mA*/
        #     # "prp_position_output_DAC_min", #     /**< The DAC value corresponding to 0% open */
        #     # "prp_position_output_DAC_max", #     /**< The DAC value corresponding to 100% open */
        #     # "prpf_sma_resistance_min", #         /**< The minimum resistance (valve closed) */
        #     # "prpf_sma_resistance_max", #         /**< The maximum resistance (end-of-travel) */
        #     # "prp_modbus_address", #
        #     # "prp_modbus_baudrate", #
        #     # "prp_modbus_parity", #
        #     # "prp_modbus_stopbits", #
        #     # "prp_modbus_endianness", #
        #     # "prp_modbus_position_command_timeout", #
        #     # "prpf_resistance_sensor_scale", #
        #     # "prpf_resistance_sensor_offset", #
        #     "prp_time",  # /**< The global timer, makes use of the LPTMR peripheral */
        #     "prp_time_overflow_counter",
        #     # /**< Counts the number of times that prp_time, has passed the 32-bit integer limit */
        #     # "prp_sma_drive_time", #                  /**< Tracks the amount of time the SMA is powered on, in LPTMR ticks */
        #     # "prp_sma_drive_time_overflow_counter", # /**< 32-bit overflow counter for prp_sma_drive_time */
        #     # "prp_calibrate_pos_out_enable", #    /**< Set to 1 to enable position command calibration */
        #     # "prp_disable_body_temp_sensor", #   /**< Set to 1 to disable body temperature sensor, can then spoof the body temperature to test the fan response */
        #     # "prp_disable_motor_speed_control", # /**< Set to 1 to disable motor speed PID controller, motor speed can be set directly via prpf_motor_speed_gain */
        #     # "prp_disable_analog_position_command", # /**< Set to 1 to disable the conversion of the prp_ADC_position_command analog signal to the prpf_position_command */
        #     # "prp_is_modbus_frame_received", #    /**< 1 if a correctly formatted frame has been received, 0 otherwise */
        #     # "prp_valve_liftoff_predictor", #
        #     # "prpf_valve_liftoff_cooling_time", #
        #     # "prpf_valve_liftoff_energy_threshold", #
        #     "prp_calibration_state_machine",  #
        #     "prp_wire_bundle_state_machine",  #
        #     "prp_valve_state_machine",  #
        #     "prp_valve_open_command",  # /**< 1 if a drive command is being received, 0 otherwise */
        #     "prp_end_of_travel",  # /**< 1 if the end-of-travel switch has been triggered, 0 otherwise */
        #     "prp_calibrate_button",  # /**< 1 if the calibrate button has been pressed, 0 otherwise */
        #     # "prp_modbus_calibrate_command", #    /**< 1 if the calibrate command has been sent from the modbus principal, 0 otherwise */
        #     "prpf_analog_position_command",  # /**< Float. The input position command, in percent */
        #     "prpf_modbus_position_command",  # /**< Float. The position command, as received by a modbus command */
        #     # "prp_status_output", #               /**< 1 if system status is OK, 0 otherwise */
        #     # "prp_is_sampling", #                 /**< 1 if resistance is being sampled (and wire bundle is powered off), 0 otherwise */
        #     "prpf_valve_position",
        #     # /**< Float. The position, in percent, of the valve. 0% is completely closed and 100% is completely open */
        #     "prpf_valve_slew_target_position",
        #     # /**< Float. The target position for the wire bundle pid controller, in percent */
        #     # "prpf_valve_slew_start_position", #  /**< Float. The starting position used by the slew algorithm. prpf_valve_slew_target_position ramps from this value to prpf_valve_slew_end_position*/
        #     # "prpf_valve_slew_end_position", #    /**< Float. The end position used by the slew algorithm. */
        #     "prpf_wire_bundle_pwm_gain",
        #     # /**< Float. The pwm gain for the wire bundle, as output by the PID controller */
        #     # "prpf_wire_bundle_displacement", #   /**< Float. The displacement of the wire bundle, in Millimeters. */
        #     # "prpf_wire_bundle_speed", #          /**< Float. The time-derivative of the displacement in Millimeters per second */
        #     # "prpf_wire_bundle_strain", #         /**< Float. The strain of the wire bundle, in 1 / seconds */
        #     # "prpf_wire_bundle_resistance", #     /**< Float. The resistance of the wire bundle, in Ohms. */
        #     # "prpf_wire_bundle_temperature", #    /**< Float. The temperature of the wire bundle, in Celsius. */
        #     # "prpf_wire_bundle_current", #        /**< Float. The current of the wire bundle. */
        #     # "prpf_wire_bundle_voltage", #        /**< Float. The voltage of the wire bundle. */
        #     # "prpf_wire_bundle_powered_off_voltage", #/**< Float. The voltage of the wire bundle when not powered */
        #     # "prpf_wire_bundle_energy_in", #		 /**< Float. The energy input to the wire bundle for the current actuation, in Joules.  */
        #     "prpf_wire_bundle_gain_integral",  #
        #     "prp_internal_fan_power_on",  #
        #     "prpf_internal_fan_gain",  #
        #     # "prpf_motor_measured_speed", #       /**< Float. The measured speed of the motor, in rpm */
        #     # "prpf_motor_speed_target_rpm", #     /**< Float. The target speed for the motor, in rpm. */
        #     # "prpf_motor_speed_gain", #           /**< Float. The gain for the motor, in percent, output by the pid controller. To be sent to the DRV10983Z chip*/
        #     # "prpf_motor_speedcmd", #             /**< Float. The target gain for the motor, as reported by the DRV10983Z chip */
        #     # "prpf_motor_speedcmd_buffer", #      /**< Float. The actual gain being sent to the motor */
        #     # "prpf_motor_current", #              /**< Float. The measured current in the motor, in Amps */
        #     # "prpf_motor_voltage", #              /**< Float. The measured voltage at the motor, in Volts */
        #     # "prpf_motor_kt", #                   /**< Float. The motor velocity constant, in V/Hz. The BEMF constant, Kt, describes the motors phase-to-phase BEMF voltage as a function of the motor velocity.*/
        #     # "prp_motor_faultcode_register", #    /**< The faultCode register of the DRV10983 */
        #     # "prp_motor_status_register", #       /**< The status register of the DRV10983 */
        #     # "prp_mcf8315a_gate_driver_fault_status", #
        #     # "prp_mcf8315a_controller_fault_status", #
        #     # "prp_mcf8315a_state_machine", #
        #     "prpf_body_temperature",
        #     # /**< Float. The measured inside body temperature of actuator body, in Celsius */
        #     # "prpf_mosfet_temperature", #		 /**< Float. The measured temperature of the mostfets controlling the SMA, in Celsius */
        #     # "prpf_power_monitor_rms_voltage", #
        #     # "prpf_power_monitor_rms_current", #
        #     # "prpf_power_monitor_active_power", #
        #     # "prpf_power_monitor_reactive_power", #
        #     # "prpf_power_monitor_apparent_power", #
        #     # "prpf_power_monitor_power_factor", #
        #     # "prp_power_monitor_power_angle_sign", #
        #     # "prp_power_monitor_power_factor_sign", #
        #     # "prp_power_monitor_number_of_points_for_rms", #
        #     # "prpf_power_monitor_averagaed_rms_voltage_one_second", #
        #     # "prpf_power_monitor_averaged_rms_current_one_second", #
        #     # "prpf_power_monitor_averaged_rms_voltage_one_minute", #
        #     # "prpf_power_monitor_averaged_rms_current_one_minute", #
        #     # "prpf_power_monitor_averaged_active_power_one_second", #
        #     # "prpf_power_monitor_averaged_active_power_one_minute", #
        #     # "prpf_power_monitor_instantaneous_voltage", #
        #     # "prpf_power_monitor_instantaneous_current", #
        #     # "prpf_power_monitor_instantaneous_power", #
        #     # "prp_power_monitor_zero_cross_flag", #
        #     # "prp_power_monitor_current_fault_flag", #
        #     # "prp_power_monitor_current_fault_latched_flag", #
        #     # "prp_power_monitor_overvoltage_flag", #
        #     # "prp_power_monitor_undervoltage_flag", #
        #     # "prp_developer_mode", #				 /**< Set to 1 to enable developer mode for additional functionality. Set to 0 to disable developer mode.*/
        #     # "prp_fault_body_temperature_sensor_disconnect", #
        #     # "prp_fault_body_temperature_threshold_exceeded", #
        #     # "prp_fault_load_driver_temp_sensor_disconnect", #
        #     # "prp_fault_load_driver_temp_threshold_exceeded", #
        #     # "prp_fault_actuator_stuck_jammed_or_frozen", #
        #     # "prp_fault_loss_of_spring_closure_force", #
        #     # "prp_fault_wire_bundle_open_circuit", #
        #     # "prp_fault_over_travel", #
        #     # "prp_fault_linear_sensor_zero_displacement", #
        #     # "prp_fault_unsafe_wire_bundle_voltage", #
        #     # "prp_fault_motor_lock_detect", #
        #     # "prp_fault_motor_overcurrent", #
        #     # "prp_fault_motor_overtemp", #
        #     # "prp_fault_motor_no_motor_connected", #
        #     # "prp_fault_motor_lock_current_limit", #
        #     # "prp_fault_home_position_offset", #
        #     # "prp_error_count_write_protected_property", #
        #     # "prp_error_count_property_eeprom_write", #
        #     # "prp_error_count_property_eeprom_checksum", #
        #     # "prp_error_count_calibration_state_machine", #
        #     # "prp_error_count_wire_bundle_state_machine", #
        #     # "prp_error_count_resistance_sampling_state_machine", #
        #     # "prp_error_count_valve_state_machine", #
        #     # "prp_error_count_motor_i2c", #
        #     # "prp_error_count_body_temp_state_machine", #
        #     # "prp_error_count_body_temperature_sensor_disconnect", #
        #     # "prp_error_count_body_temperature_threshold_exceeded", #
        #     # "prp_error_count_load_driver_temp_sensor_disconnect", #
        #     # "prp_error_count_load_driver_temp_threshold_exceeded", #
        #     # "prp_error_count_actuator_stuck_jammed_or_frozen", #
        #     # "prp_error_count_loss_of_spring_closure_force", #
        #     # "prp_error_count_wire_bundle_open_circuit", #
        #     # "prp_error_count_over_travel", #
        #     # "prp_error_count_linear_sensor_zero_displacement", #
        #     # "prp_error_count_unsafe_wire_bundle_voltage", #
        #     # "prp_error_count_motor_fault_lock_detect", #
        #     # "prp_error_count_motor_fault_overcurrent", #
        #     # "prp_error_count_motor_fault_overtemp", #
        #     # "prp_error_count_motor_fault_no_motor_connected", #
        #     # "prp_error_count_motor_fault_lock_current_limit", #
        #     # "prp_error_count_home_position_offset", #
        #     # "prp_error_count_modbus_illegal_function", #
        #     # "prp_error_count_modbus_illegal_data_address", #
        #     # "prp_error_count_modbus_illegal_data_value", #
        #     # "prp_error_count_modbus_slave_device_failure", #
        #     # "prp_error_count_modbus_acknowledge", #
        #     # "prp_error_count_modbus_slave_device_busy", #
        #     # "prp_error_count_modbus_negative_acknowledge", #
        #     # "prp_error_count_modbus_memory_parity_error", #
        #     # "prp_error_count_test_task_timeout", #
        #     # "prp_error_count_ADC_service_timeout", #
        #     # "prp_error_count_internal_fan_service_timeout", #
        #     # "prp_error_count_sensors_service_timeout", #
        #     # "prp_error_count_properties_service_timeout", #
        #     # "prp_error_count_communications_service_timeout", #
        #     # "prp_error_count_valve_service_timeout", #
        #     # "prp_error_count_calibration_service_timeout", #
        #     # "prp_error_count_wire_bundle_service_timeout", #
        #     # "prp_error_count_wire_bundle_physics_service_timeout", #
        #     # "prp_error_count_motor_service_timeout", #
        #     # "prp_error_count_body_temp_service_timeout", #
        #     # "prp_error_count_modbus_agent_service_timeout", #
        #     # "prp_error_count_test_task_overdue", #
        #     # "prp_error_count_ADC_service_overdue", #
        #     # "prp_error_count_internal_fan_service_overdue", #
        #     # "prp_error_count_sensors_service_overdue", #
        #     # "prp_error_count_properties_service_overdue", #
        #     # "prp_error_count_communications_service_overdue", #
        #     # "prp_error_count_valve_service_overdue", #
        #     # "prp_error_count_calibration_service_overdue", #
        #     # "prp_error_count_wire_bundle_service_overdue", #
        #     # "prp_error_count_wire_bundle_physics_service_overdue", #
        #     # "prp_error_count_motor_service_overdue", #
        #     # "prp_error_count_body_temp_service_overdue", #
        #     # "prp_error_count_modbus_agent_service_overdue", #
        #     # "prp_test_task_exec_time", #
        #     # "prp_ADC_service_exec_time", #
        #     # "prp_internal_fan_service_exec_time", #
        #     # "prp_sensors_service_exec_time", #
        #     # "prp_properties_service_exec_time", #
        #     # "prp_communications_service_exec_time", #
        #     # "prp_valve_service_exec_time", #
        #     # "prp_calibration_service_exec_time", #
        #     # "prp_wire_bundle_service_exec_time", #
        #     # "prp_wire_bundle_physics_service_exec_time", #
        #     # "prp_motor_service_exec_time", #
        #     # "prp_body_temp_service_exec_time", #
        #     # "prp_modbus_agent_service_exec_time", #
        #     # "prp_DAC_value", #
        #     # "prp_ADC_wire_bundle_voltage", #
        #     # "prp_ADC_wire_bundle_resistance", #
        #     "prp_ADC_linear_sensor",  #
        #     # "prp_ADC_position_command", #
        #     # "prp_ADC_body_temperature", #
        #     # "prp_ADC_mosfet_temperature", #
        #     # "prp_ADC0_VREFL", #
        #     # "prp_ADC0_VREFH", #
        #     # "prp_faults", #
        #     # "prp_error_count_command_interface_service_timeout", #
        #     # "prp_error_count_command_interface_service_overdue", #
        #     # "prp_command_interface_service_exec_time", #
        #     # "prpf_time_seconds", #
        #     # "prp_data_streaming_period", #
        #     "prpf_sma_heating_control_pgain",  #
        #     "prpf_sma_heating_control_igain",  #
        #     "prpf_sma_heating_control_dgain",  #
        #     "prpf_sma_heating_control_iLimit",  #
        #     "prpf_sma_heating_control_max_sum_error",  #
        #     "prpf_sma_heating_control_min_sum_error",  #
        #     "prpf_sma_heating_control_pTerm",  #
        #     "prpf_sma_heating_control_iTerm",  #
        #     "prpf_sma_heating_control_dTerm",  #
        #     "prpf_sma_heating_control_error",  #
        #     "prpf_sma_heating_control_sum_error",  #
        #     "prpf_sma_cooling_control_pgain",  #
        #     "prpf_sma_cooling_control_igain",  #
        #     "prpf_sma_cooling_control_dgain",  #
        #     "prpf_sma_cooling_control_iLimit",  #
        #     "prpf_sma_cooling_control_max_sum_error",  #
        #     "prpf_sma_cooling_control_min_sum_error",  #
        #     "prpf_sma_cooling_control_pTerm",  #
        #     "prpf_sma_cooling_control_iTerm",  #
        #     "prpf_sma_cooling_control_dTerm",  #
        #     "prpf_sma_cooling_control_error",  #
        #     "prpf_sma_cooling_control_sum_error",  #
        # ]
        #
        # command.reset_command(verbosity=verbosity)
        # command.get_properties_command(properties_to_print, verbosity)
        #
        # command.begin_data_stream_command(verbosity)
        # command.read_data(
        #     read_time_seconds,
        #     file_name_prefix,
        #     print_period,
        #     is_cyclic=True,
        #     real_time_plot=False,
        #     modbus_command_file="wiggle_signal[1 percent noise].csv",
        #     verbosity=verbosity
        # )
        # command.end_data_stream_command()
        # # command.set_property_command("prpf_position_command", 0.0, verbosity=verbosity)
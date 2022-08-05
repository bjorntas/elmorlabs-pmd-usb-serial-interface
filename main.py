# Example code for real time plot of Elmor Labs PMD measurement readings through USB serial interface
# Real time plotting inspired by https://towardsdatascience.com/plotting-live-data-with-matplotlib-d871fac7500b
# Written by bjorntas

import serial
import serial.tools.list_ports
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.dates as mdates

# settings

pmd_settings = {
    'port':'COM9',
    'baudrate':115200,
    'bytesize':8,
    'stopbits':1,
    'timeout':1
}

list_all_windows_ports = True
save_to_csv = True
max_length = 1000


def check_connection():
    with serial.Serial(**pmd_settings) as ser:

        # b'\x00'   welcome message
        # b'\x01'   ID
        # b'\x02'   read sensors
        # b'\x03'   read values
        # b'\x04'   read config
        # b'\x06'   read ADC buffer

        # check welcome message
        ser.write(b'\x00')
        ser.flush()
        read_bytes = ser.read(18)
        assert read_bytes == b'ElmorLabs PMD-USB'

        # check sensor struct
        ser.write(b'\x02')
        ser.flush()
        read_bytes = ser.read(100)
        print('Struct: ', read_bytes)


def get_new_sensor_values(save_to_csv):

    with serial.Serial(**pmd_settings) as ser:
        command = b'\x03'
        ser.write(command)
        ser.flush()
        read_bytes = ser.read(16)

    df = pd.DataFrame()
    timestamp = pd.Timestamp(datetime.today())

    sensors = ['PCIE1', 'PCIE2', 'EPS1', 'EPS2']

    for i, name in enumerate(sensors):

        # convert bytes to float values
        voltage_value = int.from_bytes(read_bytes[i*4:i*4+2], byteorder='little')*0.01
        current_value = int.from_bytes(read_bytes[i*4+2:i*4+4], byteorder='little')*0.1
        power_value = voltage_value * current_value

        # save rows to dataframe
        voltage_row = pd.DataFrame([[timestamp, name, 'U', voltage_value]], columns = ['timestamp', 'id', 'unit', 'value'])
        current_row = pd.DataFrame([[timestamp, name, 'I', current_value]], columns = ['timestamp', 'id', 'unit', 'value'])
        power_row = pd.DataFrame([[timestamp, name, 'P', power_value]], columns = ['timestamp', 'id', 'unit', 'value'])
        df = pd.concat([df, voltage_row], ignore_index=True)
        df = pd.concat([df, current_row], ignore_index=True)
        df = pd.concat([df, power_row], ignore_index=True)

    if save_to_csv:
        df.to_csv('measurements.csv', mode='a', header=False, index=False)

    return df


def animation_update(i, *fargs):

    # unpack dataframe from input tuple
    df = fargs[0]

    # update data
    df_new_data = get_new_sensor_values(save_to_csv)

    # append new data to old data
    for _, row in df_new_data.iterrows():
        df.loc[df.index.max()+1] = row # pd.concat() does not work

    if df.shape[0] > max_length:
        for _ in range(len(df_new_data)):
            df.drop(df.index.min(), inplace=True)

    # pivot dataframe
    df_voltage_plot = df[df.unit == 'U'].pivot(columns=['id', 'unit'], index='timestamp')
    df_current_plot = df[df.unit == 'I'].pivot(columns=['id', 'unit'], index='timestamp')
    df_power_plot = df[df.unit == 'P'].pivot(columns=['id', 'unit'], index='timestamp')

    df_voltage_plot.columns = [col[1] for col in df_voltage_plot.columns]
    df_current_plot.columns = [col[1] for col in df_current_plot.columns]
    df_power_plot.columns = [col[1] for col in df_power_plot.columns]
                    
    # clear axis
    voltage_ax.cla()
    current_ax.cla()
    power_ax.cla()

    # plot voltage line
    df_voltage_plot.plot(ax=voltage_ax)
    df_current_plot.plot(ax=current_ax)
    df_power_plot.plot(ax=power_ax)

    # set titles
    voltage_ax.set_title('Voltage', fontsize=9, color='k')
    current_ax.set_title('Current', fontsize=9, color='k')
    power_ax.set_title('Power', fontsize=9, color='k')

    # set ylabels
    voltage_ax.set_ylabel('Voltage [V]', fontsize=9, color='k')
    current_ax.set_ylabel('Current [A]', fontsize=9, color='k')
    power_ax.set_ylabel('Power [W]', fontsize=9, color='k')
    
    # remove spines and ticks
    voltage_ax.spines['left'].set_visible(False)
    voltage_ax.spines['right'].set_visible(False)
    voltage_ax.spines['top'].set_visible(False)
    voltage_ax.spines['bottom'].set_visible(False)

    current_ax.spines['left'].set_visible(False)
    current_ax.spines['right'].set_visible(False)
    current_ax.spines['top'].set_visible(False)
    current_ax.spines['bottom'].set_visible(False)

    power_ax.spines['left'].set_visible(False)
    power_ax.spines['right'].set_visible(False)
    power_ax.spines['top'].set_visible(False)
    power_ax.spines['bottom'].set_visible(False)



if __name__ == '__main__':

    if list_all_windows_ports:
        ports = list(serial.tools.list_ports.comports())
        print('USB PORTS: ')
        for p in ports:
            print(p)
        print()

    check_connection()
    
    df = get_new_sensor_values(save_to_csv=False)

    if save_to_csv:
        df.to_csv('measurements.csv', index=False)

    plt.style.use('ggplot')

    # define and adjust figure
    fig, (voltage_ax, current_ax, power_ax) = plt.subplots(3, 1, figsize=(8, 7), facecolor='#707576')

    fig.suptitle('Elmor Labs PMD', fontsize=14)

    voltage_ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
    current_ax.xaxis.set_minor_formatter(mdates.DateFormatter("%H:%M:%S"))
    power_ax.xaxis.set_minor_formatter(mdates.DateFormatter("%H:%M:%S"))

    voltage_ax.tick_params(labelbottom=False)
    current_ax.tick_params(labelbottom=False)
    
    voltage_ax.xaxis.label.set_visible(False)
    current_ax.xaxis.label.set_visible(False)
    power_ax.xaxis.label.set_visible(False)

    # animate
    ani = FuncAnimation(fig, animation_update, fargs=(df,), interval=0)
    fig.tight_layout()
    fig.subplots_adjust(left=0.09)
    plt.show()

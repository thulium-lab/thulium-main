from serial import Serial
from serial.tools import list_ports
from time import sleep
from serial.serialutil import SerialException
from numpy import sign

""" TO DO
    Аккуратно пообрабатывать возможные случаи отвязывания и достижения границ"""


def connect_port_by_name(port, names, baudrate=9600, timeout=1, idn_message=b'*IDN?\r'):
    try:
        p = Serial(port, baudrate, timeout=timeout)
        p.write(idn_message)
        s = p.readline()
        s = s.decode().split(',')
        # print(s)
        if len(s) < len(names):
            p.close()
            return None
        else:
            status = True
            for i in range(len(names)):
                if s[i] != names[i]:
                    status = False
                    break
            if status:
                print('\n' + 'Divese ' + str(names) + ' connected on port ' + port + '\n')
                return p
            else:
                p.close()
                return None
    except SerialException as e:
        print(e)
        return None


def connect_port(names=['Stanford_Research_Systems', 'SIM960'], default_port='COM21', baudrate=9600):
    ports = [port.device for port in list(list_ports.comports())]
    if default_port in ports:
        srs = connect_port_by_name(default_port, names, baudrate)
        if srs != None:
            return srs
    for port in ports:
        srs = connect_port_by_name(port, names, baudrate)
        if srs != None:
            return srs
    print('\n' + "Couldn't connect " + str(names) + '\n')
    return None


def write_read_com(port, command):
    port.write(command)
    return port.readline().decode()


def get_sacher_offset(sacher):
    piezo_offset, suffix = (write_read_com(sacher, b'P:OFFS?\r')).split('\r')
    return float(piezo_offset)


def start_correction(srs, sacher, threshold_error=0.003, correction_limit=0.05):
    switched = True
    sacher_offset0 = 0
    while (True):
        sleep(1)
        is_lock_on = int(write_read_com(srs, b'AMAN?\r'))
        if switched and is_lock_on:
            # запомнить начальные параметры захера и сбросить байты привязки
            sacher_offset0 = get_sacher_offset(sacher)
            # очищаем INCR регистр статуса локбокса
            for i in range(4):
                write_read_com(srs, b'INSR? %i\r' % (i))
            switched = False
        if is_lock_on:
            ovld = int(write_read_com(srs, b'INSR? 0\r'))
            error = float(write_read_com(srs, b'OMON?\r'))
            if abs(error) > threshold_error:
                sacher_offset = get_sacher_offset(sacher)
                if abs(sacher_offset - sacher_offset0) >= correction_limit:
                    print('Correction limit of piezo is reached. System will switched to Manual mode')
                    write_read_com(srs, b'AMAN 0\r')
                    continue
                write_read_com(sacher, b'P:OFFS %.3fV\r' % (get_sacher_offset(sacher) + sign(error) * 1e-3))
                sacher_offset = get_sacher_offset(sacher)
                print("CORRECTION; total %.3f mV" % (abs(sacher_offset - sacher_offset0)))
            print('SRS output = %.3f mV ; Sacher offset = %.3f V ; overload = %i' % (
            1e3 * error, get_sacher_offset(sacher), ovld))
        if not is_lock_on:
            print('Lock is off')


if __name__ == '__main__':
    ports = [port.device for port in list(list_ports.comports())]
    print(ports)
    srs = connect_port(names=['Stanford_Research_Systems', 'SIM960'], default_port='COM21', baudrate=9600)
    if srs == None:
        #     srs.write(b'*IDN?\r')
        print('Exit...')
        exit(1)
    sacher = connect_port(names=['Sacher Lasertechnik', ' PilotPC 500', ' SN14098015'], default_port='COM19',
                          baudrate=57600)
    if sacher == None:
        #     sacher.write(b'*IDN?\r')
        print('Exit...')
        exit(1)
    print('Start correction')
    start_correction(srs, sacher)

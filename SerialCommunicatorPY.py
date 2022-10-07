from logging import error
import numpy as np
import serial
import serial.tools.list_ports
import time
import threading
import keyboard

def CRC_hash(data : list[int]):
    hash = 0
    for elem in data:
        highorder = ((hash & 0xf8000000) >> 27) & 0x0F8
        hash = hash << 5
        hash = hash ^ highorder
        hash = hash ^ (elem & 0xFF)

    res = [((hash>>i)&0xFF) for i in range(24, -1, -8)]

    return res

class Arduino_control:
    def __init__(self, func_hash : callable, size_hash : int):
        self.s = 0
        self.port = -1
        self.hash = func_hash
        self.size_hash = size_hash
        self.size_data_for_commands = [6, 6, 7, 17, 5]
        self.size_recieve_data_for_commands = [5, 6, 1, 1, 16]
        self.limit_waiting = 10
        self.limit_attempt = 3

    def start(self):
        print("Список доступных портов:")
        ports = []
        for elem in serial.tools.list_ports.comports():
            print(str(elem).split(' ')[0])
            ports += [str(elem).split(' ')[0]]

        port = "COM" + input("Выберите порт COM:")
        if port not in ports:
            error(f"Port {port} in not exists!")
            exit(-1)
            
        s = serial.Serial(port=port, baudrate=9600)
        if not s.is_open:
            error(f"Connection failure!")
            exit(-2)
        print("Connected!")

        self.port = port
        self.s = s

    def stop(self):
        self.s.close()

    def write(self, data):
        self.s.write(data.tobytes())
        
        safe_counter = 0
        while self.s.inWaiting() < 2:
            if safe_counter > self.limit_attempt:
                raise "\rattempt error!"
            if self.s.inWaiting() == 1:
                response = int(self.s.read(1)[0])
                if response == 2 or response == 1:
                    self.s.write(data.tobytes())
                    safe_counter += 1
                elif response == 0:
                    break
                else:
                    raise "\rIncorrect response!"

    def read(self, num_cmd):
        safe_counter = 0
        while self.s.inWaiting() < self.size_recieve_data_for_commands[num_cmd]:
            time.sleep(0.3)
            safe_counter += 1
            if safe_counter > self.limit_waiting:
                raise "\rTimeout error!"

        return self.s.read(self.size_recieve_data_for_commands[num_cmd])

    def get_block_data(self, pin : int, is_digital : bool = True):
        if is_digital and pin > 1 and pin < 14:
            num_cmd = 0x0
        elif not is_digital and pin >=0 and pin < 6:
            num_cmd = 0x1
        else:
            raise "Incorrect value for pin!"
        
        data = np.array(np.zeros(self.size_data_for_commands[num_cmd]), dtype='uint8')

        data[0] = num_cmd
        data[1] = pin
        data[-self.size_hash : ] = self.hash(data[:2])

        print("~ wait data...", end='')

        safe_counter = 0
        is_error = False
        while True:
            self.write(data)
            responce = [int(_byte) for _byte in self.s.read(self.size_recieve_data_for_commands[num_cmd])]
            safe_counter += 1
            if responce[-4:] == self.hash(responce[0:-4]) or safe_counter >= self.limit_attempt:
                if responce[-4:] != self.hash(responce[0:-4]):
                    is_error = True
                break

            print("\r~ rewait data (hash error)...", end='')

        if is_error:
            print(f"\rНе удалось получить значение (invalid hash)")
        elif num_cmd == 0x0:
            print(f"\rValue from pin ({pin}) === {responce[0]}")
        else:
            print(f"\rValue from pin (A{pin}) === {int(responce[0] << 8) + int(responce[1])}")

    def get_stream_data(self, pin : int, is_digital : bool = True):
        is_end : list[bool] = [False]
        thread = threading.Thread(target=self.__thread_for__stream, args=(is_end, pin, is_digital))
        print("!>> Введите любое значение для остановки поточного приема данных")
        thread.start()
        keyboard.read_key()
        is_end[0] = True
        thread.join()
        print("!>> Поточный прием данных остановлен!")

    def set_value(self, pin : int, value : int):
        num_cmd = 0x2

        if pin < 2 or pin > 13:
            raise "Incorrect value for pin!"

        data = np.array(np.zeros(self.size_data_for_commands[num_cmd]), dtype='uint8')

        data[0] = num_cmd
        data[1] = pin
        data[2] = bool(value)
        data[-self.size_hash : ] = self.hash(data[:3])
        
        print("~ wait data...", end='')

        self.write(data)

        print(f"\rЗначение установлено!")

    def set_values(self, values : list[bool]):
        num_cmd = 0x3

        if len(values) > 12:
            raise f"Слишком много значений для цифровых портов: {len(values)}. (max = 12)"

        values += [0] * (12 - len(values))

        values = [bool(elem) for elem in values]

        data = np.array(np.zeros(self.size_data_for_commands[num_cmd]), dtype='uint8')

        data[0] = num_cmd
        data[1:13] = values
        data[-self.size_hash : ] = self.hash(data[:13])

        print("~ wait data...", end='')

        self.write(data)

        print(f"\rЗначение установлено!")

    def get_values(self):
        num_cmd = 0x4

        data = np.array(np.zeros(self.size_data_for_commands[num_cmd]), dtype='uint8')

        data[0] = num_cmd
        data[-self.size_hash : ] = self.hash(data[ : 1])

        print("~ wait data...", end='')

        safe_counter = 0
        is_error = False
        while True:
            self.write(data)
            responce = [int(_byte) for _byte in self.s.read(self.size_recieve_data_for_commands[num_cmd])]
            safe_counter += 1
            if responce[-4:] == self.hash(responce[0:-4]) or safe_counter >= self.limit_attempt:
                if responce[-4:] != self.hash(responce[0:-4]):
                    is_error = True
                break

            print("\r~ rewait data (hash error)...", end='')

        if is_error:
            print(f"\rНе удалось получить значение (invalid hash)")
        else:
            print("\r")
            pin_data = responce[ : -self.size_hash]
            i = 2
            for value in pin_data:
                print(f"pin({i}) -> {value}")
                i += 1

    def set_PWM(self, pin : int, value : int):
        pass

    def info(self):
        print("---- info ----")
        if self.port != -1:
            print(f"Подключено к порту: {self.port}")
        else:
            print(f"Не подключено")

        print(f"Алгоритм хеширования данных при передаче: {str(self.hash)}")

    def __thread_for__stream(self, is_end : list[bool], pin : int, is_digital : bool):
        while not is_end[0]:
            self.get_block_data(pin, is_digital)

class Handler:
    def __init__(self, aduino_c : Arduino_control):
        self.aduino_c = aduino_c
        self.is_stream_data : bool = False
        self.exit : bool = False

    def input_handler(self, cmd : str):
        try:
            if "get d values" in cmd:
                self.aduino_c.get_values()
            elif "get a " in cmd:
                if self.is_stream_data:
                    self.aduino_c.get_stream_data(pin=int(cmd.split(' ')[2]), is_digital=False)
                else:
                    self.aduino_c.get_block_data(pin=int(cmd.split(' ')[2]), is_digital=False)
            elif "get d " in cmd:
                if self.is_stream_data:
                    self.aduino_c.get_stream_data(pin=int(cmd.split(' ')[2]), is_digital=True)
                else:
                    self.aduino_c.get_block_data(pin=int(cmd.split(' ')[2]), is_digital=True)
            elif "set d values " in cmd:
                values = list(map(int, list(cmd.split('set d values ')[1].replace(' ', ''))))
                self.aduino_c.set_values(values=values)
            elif "set d " in cmd:
                self.aduino_c.set_value(pin=int(cmd.split(' ')[2]), value=int(cmd.split(' ')[3]))
            elif "set" in cmd and "data" in cmd:
                if "stream" in cmd.split('=')[1]:
                    self.is_stream_data = True
                elif "block" in cmd.split('=')[1]:
                    self.is_stream_data = False
                else:
                    print(f"Неверный синтаксис комманды! {cmd}")
            elif cmd == "serial info" or cmd == "s i" or cmd == "si":
                self.aduino_c.info()
                print("Type transfer data: ", end='')
                if self.is_stream_data: print("stream")
                else: print("block")
            elif cmd == "h" or cmd == "help":
                self.help()
            elif cmd == "e" or cmd == "exit":
                self.exit = True
            else:
                print("Команда не распознана")
        except Exception as e:
            print(f"Неверный синтаксис комманды! Описание: {e}")

    def help(self):
        print("""---- help ----
        Арргументы для команд указаны в []
        get a [0] <---> Получить данные с [0] аналового пина ([0] = номер пина)
        get d [0] <---> Получить данные с [0] цифрового пина ([0] = номер пина)
        get d values <---> Получить данные со всех цифровых пинов
        set d [0] [1] <---> Установить значение для цифрового пина с номером [0] на значение [1] (тип boolean)
        set d values [2 3 4 5 6 7 8 9 10 11 12 13] <---> Установить ряд значений для цифровых пинов -> индексация со 2 пинана значение типа boolean, указывать всю последовательность не обязательно
        set data=stream <---> Установить способ получения данных от МК на потоковый
        set data=block <---> Установить способ получения данных от МК на блочный
        e OR exit <---> Выход
        serial info OR s i <---> выввод информации о состоянии подключения с COM портом
        """)

if __name__ == "__main__":
    print("Welcome to << SerialCommunicator >> programm\n")
    
    arduino_c = Arduino_control(CRC_hash, 4)
    arduino_c.start()

    h = Handler(arduino_c)

    cmd : str = ""

    while not h.exit:
        cmd = input(">> ")
        h.input_handler(cmd)
        
    arduino_c.stop()
    print("Программа завершена!")
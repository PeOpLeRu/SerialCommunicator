from logging import error
import numpy as np
import serial
import serial.tools.list_ports
import time

def CRC_hash(data : list[int]):
    hash = 0
    for elem in data:
        highorder = hash & 0xf8000000
        hash = hash << 5
        hash = hash ^ (highorder >> 27)
        hash = hash ^ (elem & 0xFF)

    res = [((hash>>i)&0xFF) for i in range(24, -1, -8)]

    return res

class Arduino_control:
    def __init__(self, func_hash : callable, size_hash : int):
        self.s = 0
        self.port = -1
        self.hash = func_hash
        self.size_hash = size_hash
        self.size_data_for_commands = [6, 6]
        self.size_recieve_data_for_commands = [5, 6]
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

    def write(self, data):
        self.s.write(data.tobytes())
        
        safe_counter = 0
        while self.s.inWaiting() < 2:
            if safe_counter > self.limit_attempt:
                raise "\rattempt error!"
            if self.s.inWaiting() == 1:
                if int(self.s.read(1)) == 1:
                    self.s.write(data.tobytes())
                    safe_counter += 1
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
        data[-4:] = self.hash(data[:2])

        print("~ wait data...", end='')

        safe_counter = 0
        while True:
            self.write(data)
            responce = [int(_byte) for _byte in self.read(num_cmd)]
            safe_counter += 1
            if responce[-4:] == self.hash(responce[0:-4]) or safe_counter >= self.limit_attempt:
                break

            print("\r~ rewait data (hash error)...", end='')

        if num_cmd == 0x0:
            print(f"\rValue from pin ({pin}) === {responce[0]}")
        else:
            print(f"\rValue from pin (A{pin}) === {int(responce[0] << 8) + int(responce[1])}")

    def get_stream_data(self, pin : int, is_digital : bool = True):
        pass

    def set_data(self, pin : int, value : int):
        pass

    def set_data(self, values : list[bool]):
        pass

    def info(self):
        print("---- info ----")
        if self.port != -1:
            print(f"Подключено к порту: {self.port}")
        else:
            print(f"Не подключено")

        print(f"Алгоритм хеширования данных при передаче: {str(self.hash)}")

class Handler:
    def __init__(self, aduino_c : Arduino_control):
        self.aduino_c = aduino_c
        self.is_stream_data : bool = False
        self.exit : bool = False

    def input_handler(self, cmd : str):
        try:
            if "get a " in cmd:
                self.aduino_c.get_block_data(pin=int(cmd.split(' ')[2]), is_digital=False)
            elif "get d " in cmd:
                self.aduino_c.get_block_data(pin=int(cmd.split(' ')[2]), is_digital=True)
            elif "set" in cmd and "data" in cmd:
                if "stream" in cmd.split('=')[1]:
                    self.is_stream_data = True
                elif "block" in cmd.split('=')[1]:
                    self.is_stream_data = False
                else:
                    print(f"Неверный синтаксис комманды! {cmd}")
            elif cmd == "serial info" or cmd == "s i" or cmd == "si":
                self.aduino_c.info()
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
        set data=stream <---> Установить способ получения данных от МК на потоковый
        set data=block <---> Установить способ получения данных от МК на блочный
        e OR exit <---> Выход
        serial info OR s i <---> выввод информации о состоянии подключения с COM портом
        """)

    def end(self):
        self.aduino_c.s.close()

if __name__ == "__main__":
    print("Welcome to << SerialCommunicator >> programm\n")
    
    arduino_c = Arduino_control(CRC_hash, 4)
    arduino_c.start()

    h = Handler(arduino_c)

    cmd : str = ""

    while not h.exit:
        cmd = input(">> ")
        h.input_handler(cmd)
        
    h.end()
    print("Программа завершена!")
from logging import error
import numpy as np
import serial
import serial.tools.list_ports
import time

def CRC_hash(data : list[int]):
    hash : int = 0
    for elem in data:
        highorder = hash & 0xf8000000
        hash = (hash << 5) & 0xFFFFFFFF
        hash = hash ^ (highorder >> 27)
        hash = hash ^ (elem & 0xFF)

    res = [((hash>>i)&0xFF) for i in range(24, -1, -8)]

    return res

cmd = input("values: ")

values = list(map(int, list(cmd.replace(' ', ''))))
print(CRC_hash(values))

values += [0] * (12 - len(values))

values = [bool(elem) for elem in values]

values = [3] + values

print(CRC_hash(values))
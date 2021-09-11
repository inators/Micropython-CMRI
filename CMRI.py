""" CMRI Micropython port by David Whipple 2021
    CMRI reference at
    https://www.nmra.org/sites/default/files/standards/sandrp/Other_Specifications/lcs-9.10.1_cmrinet_v1.1.pdf

    CMRI - a small library for Arduino to interface with the C/MRI
    computer control system for model railroads
    Copyright (C) 2012 Michael Adams (www.michael.net.nz)
    All rights reserved.

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included
    in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

    """


from machine import Pin, UART
import time
import math


mode = "Preamble 1"
address = 0
receivePosition = 0


# Sets up the receive and transmit buffers.  These are fixed lengths that are agreed
# upon between JMRI and our script.  Default is SMINI 24 inputs (8*3), 48 outputs (8*6)
def CMRI(receiveBytes=6, transmitBytes=3, UARTnum=0, tx=Pin(0), rx=Pin(1),
        baudrate=9600, add=1, txEnablePin=3, debug=0):
    global receiveBuffer, transmitBuffer, lenReceive, lenTransmit, uart, \
        address, txEnable, debugme
    receiveBuffer = [0] * receiveBytes
    transmitBuffer = [0] * transmitBytes
    lenReceive = receiveBytes
    lenTransmit = transmitBytes
    uart = UART(UARTnum, baudrate, tx=tx, rx=rx, stop=2)
    txEnable = Pin(txEnablePin, Pin.OUT)
    txEnable.value(0)
    address = add
    debugme = debug
    transmit()

# sets the address we listen to
def set_address(add):
    global address
    address = add


# When called it will attempt to process the input
def process():
    data = uart.read(64)
    output = [data]
    if debugme == 1 and data is not None:
        print(output)
    if data is not None:
        for char in data:
            process_char(char)
    return output

# Puts together a data packet and transmits it.
# A packet is 0xFF,0xFF,STX (0x02), Address, R for receive , the data, ETX (0x03)
def transmit():
    global txEnable
    global transmitBuffer
    dataList = (
        [0xFF, 0xFF, 0x02, (ord("A") + address), ord("R")]
    )
    for char in transmitBuffer:
        dataList.append(char)    
    dataList.append(0x03)
    if debugme == 1:
        print(dataList)

    data = bytearray(dataList)
    txEnable.value(1)
    uart.write(data)
    time.sleep(0.01)
    txEnable.value(0)


# Get the byte from our receive buffer and return the bit we are asking for
def get_bit(position):
    byte = get_byte(math.floor(position / 8))
    return (byte >> (position % 8)) & 0x01


def get_byte(position):
    global receiveBuffer
    return receiveBuffer[position]


# Set the bit/byte into our transmit buffer so it is ready to send_report
def set_bit(position, value):
    global transmitBuffer
    # Make sure we are not out of bounds
    if math.floor((position + 7) / 8) > lenTransmit:
        return False
    index = math.floor(position / 8)
    if value == 1:
        # or the particular bit into place
        transmitBuffer[index] |= (1 << (position % 8))
    else:
        # NAND (not and) the bit into place to remove it
        transmitBuffer[index] &= ~(1 << (position % 8))
    return True


def set_byte(position, byte):
    if position > lenTransmit:
        return False
    transmitBuffer[position] = byte
    return True


# Go through the data stream and figure out if we care or what to do
# Data has 3 preambles bytes, an address, a command. data, and an ending
def process_char(char):
    global mode, receiveBuffer, receivePosition, lenReceive, address
    #char = ord(char)
    if mode == "Preamble 1":
        receivePosition = 0
        if char == 0xFF:
            mode = "Preamble 2"
    elif mode == "Preamble 2":
        if char == 0xFF:
            mode = "Preamble 3"
        else:
            mode = "Preamble 1"
    elif mode == "Preamble 3":
        if char == 0x02:  # STX - Start Transmission
            mode = "Address"
        else:
            mode = "Preamble 1"
    elif mode == "Address":
        tempAddress = char - ord("A")  # Address is the address plus the ascii for "A"
        if address == tempAddress:
            mode = "Decode Command"
        else:
            mode = "Ignore Command"
    elif mode == "Decode Command":
        if char == ord("T"):  # Transmit or set or whatever you want to call it
            mode = "Decode Data"
        elif char == ord("P"):  # Poll data - They want our info
            mode = "Preamble 1"
            transmit()
        else:
            mode = "Postamble Other"
    elif mode == "Ignore Command":
        mode = "Ignore Data"
    elif mode == "Decode Data":
        if char == 0x10:  # Escape character
            mode = "Decode Esc Data"
        # ETX - End Transmission but only when we have it all
        # Note - if the pattern is 0x03 then it will have the escape char sent first
        elif char == 0x03:
            mode = "Preamble 1"
        elif receivePosition >= lenReceive:
            pass
        else:
            receiveBuffer[receivePosition] = char
            receivePosition += 1
    elif mode == "Decode Esc Data":
        if receivePosition >= lenReceive:
            pass
        else:
            receiveBuffer[receivePosition] = char
            receivePosition += 1
        mode = "Decode Data"
    elif mode == "Ignore Data":
        if char == 0x10:  # Escape character
            mode = "Ignore Esc Data"
        if char == 0x03:  # ETX - End Transmission
            mode = "Preamble 1"
    elif mode == "Ignore Esc Data":
        mode = "Ignore Data"
    elif mode == "Postamble Other":
        mode = "Preamble 1"

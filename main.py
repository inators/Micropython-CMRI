import CMRI
from machine import Pin


# Call the CMRI function first.  
CMRI.CMRI(add=1, baudrate=115200, debug=1, txEnablePin=3, tx=Pin(12), rx=Pin(13))


led = Pin(25, Pin.OUT)


while True:
    data = CMRI.process()

   
    led.value(CMRI.get_bit(0))

    CMRI.set_bit(0, 1)
    CMRI.set_bit(1, 0)
    CMRI.set_bit(2, 1)
    CMRI.set_bit(3, 1)

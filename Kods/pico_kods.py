# !!! Sis MicroPython kods ir izmantojams tikai uz Raspberry Pi Pico 2 W !!!

import machine
import time
import sys
import select

measuring = False
t0 = time.ticks_us() # sakuma laika atskaites punkts

class HallKey:
    def __init__(self, pin_id, name):
        self.adc = machine.ADC(pin_id) # uzsak ADC (analog-to-digital converter)
        self.name = name
        
        # kalibracijas vertibas
        self.min_val = 0
        self.max_val = 65535
        
        # filtra mainigie
        self.raw_filtered = 65535
        self.alpha = 0.15

    def update(self):
        # nolasa sensora vertibu, piemero tai EMA (exponential moving average) filtru, lai samazinatu signala troksni
        raw = self.adc.read_u16()
        self.raw_filtered = (1 - self.alpha) * self.raw_filtered + self.alpha * raw
        return self.raw_filtered

    def get_depth(self): # parvers sensora vertibu normalizeta dziluma (0-1) 
        amplitude = self.max_val - self.min_val
        if abs(amplitude) < 500: return 0.0 # aizsardziba pret kludainu kalibraciju
        depth = (self.max_val - self.raw_filtered) / amplitude # aprekina relativo poziciju
        return max(0.0, min(1.0, depth))

# konfiguracija
key_pins = [26, 27, 28]
keys = [HallKey(pin, f"K{i}") for i, pin in enumerate(key_pins)]

def calibrate_keys(): # nosaka sensoru maksimālās (atlaists) un minimālās (nospiests) vērtības
    print("\n--- KALIBRACIJA SAKTA ---")
    print("Atlaidiet visus taustinus un gaidiet...")
    time.sleep(2)
    
    for k in keys:
        samples = [k.adc.read_u16() for _ in range(100)]
        k.max_val = sum(samples) / len(samples) # videjais no 100 paraugiem miera stavokli
        k.raw_filtered = k.max_val
    
    for k in keys:
        print("Nospiediet " + k.name + " lidz galam un TURIET (3s)")
        time.sleep(1)
        
        tmp_min = 65535
        start = time.ticks_ms()
        # 3 sekundes meklejam zemako iespejamo vertibu (maksimali nospiests)
        while time.ticks_diff(time.ticks_ms(), start) < 3000:
            v = k.adc.read_u16()
            if v < tmp_min: tmp_min = v
        k.min_val = tmp_min
        print("   " + k.name + " vertibas saglabatas!")

    print("--- KALIBRACIJA PABEIGTA ---\n")

# parbauda vai nav ienakosi noradijumi caur usb
def check_serial():
    global measuring, t0
    if select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline().strip().upper()
        if not line: return

        if line == "CAL":
            measuring = False
            calibrate_keys()
        elif line == "START":
            measuring = True
            t0 = time.ticks_us() # sakam laika atskaiti no jauna
            print("Merisana sakta")
        elif line == "STOP":
            measuring = False
            print("Merisana aptureta")

# Sakuma zinojums
print("Gatavs darbam!")

while True:
    check_serial()
    
    if measuring:
        t = time.ticks_diff(time.ticks_us(), t0) # aprekina laiku, kas pagajis kops sakuma (mikrosekundes)
        depths = []
        for k in keys:
            k.update() # iegust pasreizejo sensora vertibu
            depths.append("{:.4f}".format(k.get_depth())) # dati ar 4 vertibam aiz komata
        
        print(str(t) + "," + ",".join(depths)) # nosuta datus uz datoru CSV formata
        time.sleep_ms(5) # ~200Hz
    else:
        time.sleep_ms(20) # ja nekas netiek merits, standby

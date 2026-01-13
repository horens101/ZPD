import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial, serial.tools.list_ports, threading, os, csv, queue

class HallSensorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Datu ieguves programma")
        self.root.geometry("850x600")

        # Mainīgo inicializācija
        self.serial_port = None
        self.is_connected = self.is_recording = self.is_calibrating = False
        self.current_user_id = 1
        self.data_queue = queue.Queue()

        if not os.path.exists("data"): os.makedirs("data") # Izveido mapi datiem, ja tā neeksistē

        self.setup_ui()
        self.scan_ports()
        self.scan_users()
        self.root.after(100, self.process_queue) # Apstrādā komandu rindu ik pēc 100 ms

    def setup_ui(self):
        # Savienojums ar Raspberry Pi Pico
        f1 = ttk.LabelFrame(self.root, text="Savienojums"); f1.pack(fill="x", padx=10, pady=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(f1, textvariable=self.port_var, width=35, state="readonly")
        self.port_combo.pack(side="left", padx=5, pady=5)
        
        ttk.Button(f1, text="↻", width=3, command=self.scan_ports).pack(side="left")
        self.btn_connect = ttk.Button(f1, text="Izveidot savienojumu", command=self.toggle_connection)
        self.btn_connect.pack(side="left", padx=5)
        
        # Kontroles panelis (satur visas darbības)
        ctrl = ttk.Frame(self.root); ctrl.pack(fill="x", padx=10, pady=5)

        # Lietotāja izveide un izvēle
        u_frame = ttk.LabelFrame(ctrl, text="Lietotājs"); u_frame.pack(side="left", expand=True, fill="both")
        self.user_combo = ttk.Combobox(u_frame, state="readonly"); self.user_combo.pack(fill="x", padx=5, pady=5)
        self.user_combo.bind("<<ComboboxSelected>>", lambda e: setattr(self, 'current_user_id', int(self.user_combo.get().split('_')[1])))
        ttk.Button(u_frame, text="+ Jauns lietotājs", command=self.create_new_user).pack(fill="x", padx=5)

        # Darbību pogas
        a_frame = ttk.LabelFrame(ctrl, text="Darbības"); a_frame.pack(side="right", expand=True, fill="both")
        self.btn_cal = ttk.Button(a_frame, text="KALIBRĒT", command=self.send_calibrate, state="disabled")
        self.btn_start = ttk.Button(a_frame, text="IERAKSTĪT", command=self.start_recording, state="disabled")
        self.btn_stop = ttk.Button(a_frame, text="BEIGT IERAKSTĪT", command=self.stop_recording, state="disabled")
        for b in [self.btn_cal, self.btn_start, self.btn_stop]: b.pack(side="left", expand=True, fill="both", padx=2, pady=5)

        # Konsole datu izvadei
        self.console = scrolledtext.ScrolledText(self.root, state='disabled', bg="#1e1e1e", fg="#ffffff")
        self.console.pack(fill="both", expand=True, padx=10, pady=10)
        for tag, col in [("tx", "#00d4ff"), ("rx", "#00ff00"), ("instr", "#ffaa00"), ("data", "#888888")]:
            self.console.tag_config(tag, foreground=col)

    def scan_ports(self): # Meklē pieejamos serial portus
        ports = serial.tools.list_ports.comports()
        self.port_combo['values'] = [f"{p.device} ({p.description})" for p in ports]
        if ports: self.port_combo.current(0)

    def scan_users(self): # Atrod visus lietotājus
        users = sorted([int(d.split('_')[1]) for d in os.listdir("data") if d.startswith("user_")])
        if not users: os.makedirs("data/user_1"); users = [1]
        self.user_combo['values'] = [f"user_{u}" for u in users]
        self.user_combo.set(f"user_{users[-1]}"); self.current_user_id = users[-1]

    def create_new_user(self): # Izveido jaunu lietotāju
        new_id = max([int(v.split('_')[1]) for v in self.user_combo['values']]) + 1
        os.makedirs(f"data/user_{new_id}"); self.scan_users(); self.log(f"Lietotājs {new_id} izveidots", "tx")

    def toggle_connection(self): # Savieno vai atvieno no serial porta
        if not self.is_connected:
            try:
                self.serial_port = serial.Serial(self.port_var.get().split(" ")[0], 115200, timeout=0.1)
                self.is_connected = True; self.btn_connect.config(text="Atvienoties")
                threading.Thread(target=self.read_serial, daemon=True).start()
            except Exception as e: messagebox.showerror("Kļūda", str(e))
        else:
            self.is_connected = False; self.serial_port.close()
            self.btn_connect.config(text="Savienoties")
        self.update_buttons()

    def read_serial(self): # Nolasa datus no serial porta
        while self.is_connected:
            try:
                line = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                if line: self.data_queue.put(line)
            except: break

    def process_queue(self): # Procesu rinda
        while not self.data_queue.empty():
            line = self.data_queue.get()
            if "," in line and line[0].isdigit(): # Ja tie ir dati CSV formātā
                if self.is_recording: self.csv_writer.writerow(line.split(","))
                self.log(line, "data")
            elif any(x in line for x in ["SAKTA", "Nospiediet", "gaidiet"]):
                self.is_calibrating = True; self.log(line, "instr")
            elif "PABEIGTA" in line:
                self.is_calibrating = False; self.log(line, "rx"); messagebox.showinfo("Info", "Kalibrācija pabeigta!")
            else: self.log(line, "rx")
        self.update_buttons(); self.root.after(20, self.process_queue)

    def log(self, msg, tag): # Izveido ierakstu konsolē
        self.console.config(state='normal'); self.console.insert(tk.END, msg + "\n", tag)
        self.console.see(tk.END); self.console.config(state='disabled')

    def send_calibrate(self): # Nosūtu Pico kalibrācijas norādi
        if messagebox.askyesno("Kalibrācija", "Sākt?"): self.serial_port.write(b"CAL\n")

    def start_recording(self): # Izveido jaunu CSV un sāk ierakstīt
        path = f"data/user_{self.current_user_id}"
        att = len([f for f in os.listdir(path) if f.endswith(".csv")]) + 1
        self.f_out = open(f"{path}/attempt_{att}.csv", "w", newline="")
        self.csv_writer = csv.writer(self.f_out)
        self.csv_writer.writerow(["Time_us", "K1", "K2", "K3"])
        self.is_recording = True; self.serial_port.write(b"START\n")

    def stop_recording(self): # Pārtrauc ierakstīšanu un aizver CSV
        self.is_recording = False; self.serial_port.write(b"STOP\n")
        if hasattr(self, 'f_out'): self.f_out.close()

    def update_buttons(self):
        st = "normal" if self.is_connected and not self.is_calibrating else "disabled"
        self.btn_cal.config(state=st if not self.is_recording else "disabled")
        self.btn_start.config(state=st if not self.is_recording else "disabled")
        self.btn_stop.config(state="normal" if self.is_recording else "disabled")
        self.user_combo.config(state="readonly" if not (self.is_recording or self.is_calibrating) else "disabled")

if __name__ == "__main__":
    root = tk.Tk()
    HallSensorApp(root)
    root.mainloop()

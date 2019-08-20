import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
import pandas as pd
import re
from glob import glob
import os
# from tempest import *
from docx_generator import DocxGenerator
from presenter import SiPresenter


class FieldStrengthCalculator:
    def __init__(self):
        self.meas = pd.DataFrame(columns=["f", "cn", "n", "p"])
        self.ftak = .0
        self.imp = .0

    def set_imp(self):  # Расчёт длительности импульса в секундах
        self.imp = 1 / (self.ftak * 2 * 10 ** 6) if self.ftak > 0 else 0


INITIALDIR = '/home/kruglov/PycharmProjects/siCalculator/'


class SiCalculator(tk.Tk):
    def __init__(self):
        super().__init__()

        self.presenter = SiPresenter(self)

        self.file_loaded = False

        self.fsc = FieldStrengthCalculator()

        self.docx = DocxGenerator()

        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label='Файл', menu=self.file_menu)
        self.file_menu.add_command(label='Открыть файл с измерениями...', command=self.measurements_file_open,
                                   accelerator='Ctrl+O')
        self.file_menu.add_separator()
        self.file_menu.add_command(label='Выйти...', command=self.exit_sicalc,
                                   accelerator='Alt+F4')

        self.canvas = tk.Canvas(self, borderwidth=0)
        self.table = InputTable(self.canvas)

        self.canvas.create_window((0, 0), window=self.table, anchor=tk.NW)
        self.canvas.grid(row=0, column=0, sticky="nswe")

        self.y_scroll = tk.Scrollbar(self, orient=tk.VERTICAL)
        self.y_scroll.grid(row=0, column=1, sticky='ns')

        self.canvas.config(yscrollcommand=self.y_scroll.set)
        self.canvas.configure(scrollregion=self.canvas.bbox(tk.ALL))
        self.y_scroll.configure(command=self.canvas.yview)

        self.params = ParamsFrame(self, self.presenter, self.docx)
        self.params.grid(row=0, column=2, sticky="ns")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.wm_maxsize(width=720, height=500)
        self.wm_minsize(width=720, height=300)

        self.table.bind('<Configure>', self.on_table_configure)

        self.main()

    def on_table_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox(tk.ALL))

    def measurements_file_open(self, event=None):
        filepath = filedialog.askopenfilename(initialdir=INITIALDIR,
                                              title="Выберите файл...",
                                              filetypes=[("Текстовый файл", '*.txt')])
        if bool(filepath):
            self.presenter.load_meas_df(filepath)

    def main(self):
        self.bind("<Control-o>", self.measurements_file_open)
        self.bind("<Control-O>", self.measurements_file_open)

    def exit_sicalc(self, event=None):
        self.destroy()


class InputTable(tk.Frame):
    def __init__(self, parent, rows=1, columns=4):
        super().__init__(parent)
        header_text_list = [
            'F, МГц',
            'U сш, дБмкВ',
            'U с, дБмкВ'
        ]

        opts = {
            'sticky': 'we',
            'pady': 1,
            'padx': 1
        }

        self.header = [tk.Label(self, text=i) for i in header_text_list]
        for i in range(len(self.header)):
            self.header[i].grid(row=0, column=i, **opts)

        self.widgets = None
        self.values = None
        self.reset(rows=rows, columns=columns, state=tk.DISABLED)

    def reset(self, rows, columns, state):
        self.widgets = []
        self.values = []

        opts = {
            'pady': 1,
            'padx': 1
        }

        for r in range(rows):
            current_widgets_row = []
            current_values_row = []
            for c in range(columns):
                value = tk.StringVar()
                current_values_row.append(value)

                entry = tk.Entry(self, textvariable=value, borderwidth=0, width=10, state=state)

                entry.grid(row=r + 1, column=c, sticky='nsew', **opts)
                current_widgets_row.append(entry)

            self.widgets.append(current_widgets_row)
            self.values.append(current_values_row)

        for c in range(columns):
            self.grid_columnconfigure(c, weight=1)

    def set(self, row, column, value):
        # widget = self.widgets[row][column]
        # widget.config(text=value)
        # widget = self.widgets[row][column]
        # widget.delete(0, tk.END)
        # widget.insert(0, value)
        self.values[row][column].set(value)

    def update_table(self, values):
        rows = values.shape[0]
        cols = values.shape[1]
        self.reset(rows=rows, columns=cols, state=tk.NORMAL)
        for r in range(rows):
            for c in range(cols):
                self.set(r, c, values[r, c])


class ParamsFrame(tk.Frame):
    def __init__(self, parent, presenter, docx):
        super().__init__(parent)

        self.parent = parent
        self.presenter = presenter
        self.docx = docx

        self.e_var = tk.IntVar()
        self.e_var.trace("w", self.check_e)
        self.e_lbl = tk.Label(self, text="E")
        self.e_chk = tk.Checkbutton(self, text="Электрическая антенна", variable=self.e_var)
        self.e_chk.configure(state="disabled")

        e_antenna_list = self.get_antenna_list(0)
        self.e_antenna_var = tk.StringVar()
        self.e_antenna_var.set(e_antenna_list[0])
        self.e_antenna_var.trace("w", self.change_e)
        self.e_antenna_drop = tk.OptionMenu(self, self.e_antenna_var,
                                            *e_antenna_list)
        self.e_antenna_drop.configure(state="disabled")

        self.h_var = tk.IntVar()
        self.h_var.trace("w", self.check_h)
        self.h_lbl = tk.Label(self, text="H")
        self.h_chk = tk.Checkbutton(self, text="Магнитная антенна", variable=self.h_var)
        self.h_chk.configure(state="disabled")

        h_antenna_list = self.get_antenna_list(1)
        self.h_antenna_var = tk.StringVar()
        self.h_antenna_var.set(h_antenna_list[0])
        self.h_antenna_var.trace("w", self.change_h)
        self.h_antenna_drop = tk.OptionMenu(self, self.h_antenna_var,
                                            *h_antenna_list)
        self.h_antenna_drop.configure(state="disabled")

        self.frequency_lbl = tk.Label(self, text="Тактовая частота")
        vmcd = (self.register(self.validate_frequency), "%i", "%P", "%s")
        self.frequency_entry = tk.Entry(self, validate='key', validatecommand=vmcd)
        self.frequency_entry.configure(state="disabled")

        self.impulse_duration_var = tk.StringVar()
        self.impulse_duration_lbl = tk.Label(self, text="Длительность импульса")
        self.impulse_duration_entry = tk.Entry(self,
                                               textvariable=self.impulse_duration_var,
                                               state="disabled")

        self.cat_2_lbl = tk.Label(self, text="Cat. A")
        self.cat_2_entry = tk.Entry(self, show="*")
        self.cat_2_entry.configure(state="disabled")

        self.cat_3_lbl = tk.Label(self, text="Cat. B")
        self.cat_3_entry = tk.Entry(self, show="*")
        self.cat_3_entry.configure(state="disabled")

        self.calc_btn = tk.Button(self, text="Сформировать!", command=self.calculate)
        self.calc_btn.configure(state="disabled")

        opts = {
            'pady': 7,
            'padx': 7
        }

        # self.e_lbl.grid(row=0, column=0, sticky=tk.W, **opts)
        self.e_chk.grid(row=0, column=0, sticky=tk.W, **opts)
        self.e_antenna_drop.grid(row=0, column=1, sticky='we', **opts)

        # self.h_lbl.grid(row=1, column=0, sticky=tk.W, **opts)
        self.h_chk.grid(row=1, column=0, sticky=tk.W, **opts)
        self.h_antenna_drop.grid(row=1, column=1, sticky='we', **opts)

        self.frequency_lbl.grid(row=2, column=0, sticky=tk.W, **opts)
        self.frequency_entry.grid(row=2, column=1, sticky='we', **opts)

        self.impulse_duration_lbl.grid(row=3, column=0, sticky=tk.W, **opts)
        self.impulse_duration_entry.grid(row=3, column=1, sticky='we', **opts)

        self.cat_2_lbl.grid(row=4, column=0, sticky=tk.W, **opts)
        self.cat_2_entry.grid(row=4, column=1, sticky='we', **opts)

        self.cat_3_lbl.grid(row=5, column=0, sticky=tk.W, **opts)
        self.cat_3_entry.grid(row=5, column=1, sticky='we', **opts)

        self.calc_btn.grid(row=6, column=0, columnspan=2, sticky='we', **opts)

    def enable_widgets(self):
        self.e_chk.configure(state="normal")
        self.h_chk.configure(state="normal")
        self.frequency_entry.configure(state="normal")
        self.cat_2_entry.configure(state="normal")
        self.cat_3_entry.configure(state="normal")


    def get_antenna_list(self, mode=0):  # 0 for e, 1 for h
        ant_file_list = glob('./antennas/*.txt')
        antennas = [i.split('/')[-1].split('.')[0] for i in ant_file_list]
        # TODO antenna types
        return antennas

    def check_e(self, *args):
        if self.e_var.get() == 1:
            state = "normal"
        else:
            state = "disabled"
        self.e_antenna_drop.configure(state=state)

    def change_e(self, *args):
        antenna = self.e_antenna_var.get()
        ant_df = self.load_antenna(antenna)
        self.presenter.set_ant_df(ant_df, 'e')

    def check_h(self, *args):
        if self.h_var.get() == 1:
            state = "normal"
        else:
            state = "disabled"
        self.h_antenna_drop.configure(state=state)

    def change_h(self, *args):
        antenna = self.e_antenna_var.get()
        ant_df = self.load_antenna(antenna)
        self.presenter.set_ant_df(ant_df, 'h')

    def load_antenna(self, antenna):
        ant_df = pd.read_csv(os.path.join('./antennas/', antenna + '.txt'),
                             sep='\t', index_col=None, header=None,
                             names=['f', 'k'])
        return ant_df

    def validate_frequency(self, index, f, before):
        if len(f) == 0:
            return False
        pattern = re.compile("^\d*\.?\d*$")
        if pattern.match(f) is not None:
            ftak = float(f)
            self.parent.presenter.set_ftak(ftak)
            self.parent.presenter.get_imp()
            self.frequency_entry.config(background='white')
            return True
        else:
            self.frequency_entry.config(background='pink')
            return False

    def calculate(self, *args):
        self.presenter.calculate()
        # print(self.fsc.meas)
        # self.fsc.db_to_mkv()
        # print(self.fsc.E)
        # self.fsc.kalibr()
        # print(self.fsc.meas.values)
        self.docx.create_table(self.parent.presenter.get_values())
        self.docx.save_docx()


if __name__ == "__main__":
    app = SiCalculator()
    app.mainloop()

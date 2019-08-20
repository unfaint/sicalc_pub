import pandas as pd
from model import *
from docx_generator import DocxGenerator


class SiPresenter(object):
    def __init__(self, view):
        self.model = SiModel(self)
        self.view = view

    def load_meas_df(self, filepath):
        df = pd.read_csv(filepath_or_buffer=filepath, sep="\t", index_col=None, header=None)
        columns = ["f", "cn", "n"]
        values = df.values[:, :3]
        meas = pd.DataFrame(columns=columns, data=values)
        self.model.set_meas_h(meas)
        self.view.table.update_table(values)
        self.view.params.enable_widgets()

    def set_ant_df(self, ant_df, ant_type):
        self.model.meas_h.set_ant_df(ant_df, ant_type)

    def set_ftak(self, ftak):
        self.model.set_ftak(ftak)

    def get_imp(self):
        imp = self.model.get_imp()
        if imp is not None:
            self.view.params.impulse_duration_var.set(imp)

    def set_ready(self):
        self.view.params.calc_btn.configure(state="normal")

    def calculate(self):
        self.model.calculate()

    def get_values(self):
        return self.model.get_meas_values()


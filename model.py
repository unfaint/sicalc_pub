import pandas as pd
import numpy as np
from sympy import *
import math

# speed of light
C_CONST = 299792458
# ranges
R1 = np.arange(0.1, 1000.1, 0.1)
# distance between equipment and antenna
D = 1.
# antena types
ANTENNA_TYPES = 'eh'


def gc_to_kgc(x):
    return x * (10 ** 3)


def gc_to_mgc(x):
    return x * (10 ** 6)


def db_to_mkv(x):
    return 10 ** (x / 20)


def mkv_to_db(x):
    return 20 * math.log(x, 10)


def i_for_kgc(x, imp):
    return int(1 + 10 ** 3 * x * imp)


def kz_for_r(la, d):
    kz = np.ones(R1.shape)
    if d <= (la / (2 * math.pi)):

        ixs = np.logical_and(R1 > 0, R1 <= (la / (2 * math.pi)))
        kz[ixs] = (R1[ixs] / d) ** 3

        ixs = np.logical_and(R1 > (la / (2 * math.pi)), R1 <= (6 * la))
        kz[ixs] = (la * (R1[ixs] ** 2)) / (2 * math.pi * (d ** 3))

        ixs = R1 > (6 * la)
        kz[ixs] = (6 * (la ** 2) * R1[ixs]) / (2 * math.pi * (d ** 3))

    elif (d > (la / (2 * math.pi))) and (d <= (6 * la)):

        ixs = np.logical_and(R1 > 0, R1 <= (la / (2 * math.pi)))
        kz[ixs] = (2 * math.pi * (R1[ixs] ** 3)) / (la * (d ** 2))

        ixs = np.logical_and(R1 > (la / (2 * math.pi)), R1 <= (6 * la))
        kz[ixs] = (R1[ixs] / d) ** 2

        ixs = R1 > (6 * la)
        kz[ixs] = (6 * la * R1[ixs]) / (d ** 2)

    else:

        ixs = np.logical_and(R1 > 0, R1 <= (la / (2 * math.pi)))
        kz[ixs] = (2 * math.pi * (R1[ixs] ** 3)) / (6 * (la ** 2) * d)

        ixs = np.logical_and(R1 > (la / (2 * math.pi)), R1 <= (6 * la))
        kz[ixs] = (R1[ixs] ** 2) / (6 * la * d)

        ixs = R1[ixs] > (6 * la)
        kz[ixs] = R1[ixs] / d

    return kz


def calculate_ka(antenna, series):
    if len(antenna[antenna.f == series.f]) == 0:  # нет совпадения с измеренной частотой
        min_row = antenna[antenna.f < series.f].sort_values('f', ascending=False).iloc[0]
        max_row = antenna[antenna.f > series.f].sort_values('f', ascending=True).iloc[0]
        k_min = float(min_row['k_mkv'])
        f_min = float(min_row['f'])
        k_max = float(max_row['k_mkv'])
        f_max = float(max_row['f'])
        return k_min + ((series.f - f_min) / (f_max - f_min)) * (k_max - k_min)
    else:
        return float(antenna[antenna.f == series.f]['k_mkv'])


class MeasHandler(object):
    def __init__(self, meas, ant_e=None, ant_h=None):
        assert meas.shape[0] > 0
        self.meas = meas.copy()
        self.ant_e = ant_e
        self.ant_h = ant_h
        self.ftak = None
        self.imp = None
        self.meas['f_kgc'] = self.meas['f'].apply(gc_to_kgc)
        self.meas['f_mgc'] = self.meas['f'].apply(gc_to_mgc)
        self.meas['lam'] = C_CONST / self.meas['f_mgc']
        self.meas['cn_mkv'] = self.meas['cn'].apply(db_to_mkv)
        self.meas['n_mkv'] = self.meas['n'].apply(db_to_mkv)
        self.meas['uc_mkv'] = (self.meas['cn_mkv'] ** 2 - self.meas['n_mkv'] ** 2) ** 0.5
        self.meas['Kz'] = self.meas['lam'].apply(lambda x: kz_for_r(x, D))
        self.ready = False

    def set_ant_df(self, ant_df, ant_type):
        assert ant_type in ANTENNA_TYPES
        ant_df = ant_df.copy()
        if ant_type == 'e':
            self.ant_e = ant_df
            self.ant_e['k_mkv'] = 10 ** (ant_df['k'] / 20)
        else:
            self.ant_h = ant_df
            self.ant_h['k_mkv'] = 10 ** (ant_df['k'] / 20)

        self.calibrate(ant_type)

        if ant_type == 'e':
            self.meas['Es_mkv'] = self.meas['uc_mkv'] * self.meas['Ek_mkv']
            self.meas['Es'] = 20 * np.log10(self.meas['Es_mkv'])
        else:
            self.meas['Hs_mkv'] = 377 * self.meas['uc_mkv'] * self.meas['Hk_mkv']
            self.meas['Hs'] = 20 * np.log10(self.meas['Hs_mkv'])

    def calibrate(self, ant_type):
        name = ant_type.upper() + 'k'
        if ant_type == 'e':
            antenna = self.ant_e.copy()
        else:
            antenna = self.ant_h.copy()

        self.meas[name + '_mkv'] = self.meas.apply(lambda x: calculate_ka(antenna=antenna, series=x), axis=1)
        self.meas[name] = self.meas[name + '_mkv'].apply(lambda x: 20 * math.log(x, 10))

    def set_ftak(self, ftak):
        self.ftak = ftak
        if ftak == 0:
            self.imp = 0
        else:
            self.imp = 1 / (2 * ftak * (10 ** 6))

    def set_i(self):
        self.meas['i'] = self.meas['f_kgc'].apply(lambda x: i_for_kgc(x, self.imp))
        self.ready = True

    def get_i_list(self):
        return self.meas['i'].unique()


def fup_for_i(i, imp):
    return (10 ** (-3) * i) / imp


def fdown_for_i(i, imp):
    return 0.1 if i == 1 else (((10 ** (-3)) * (i-1)) / imp) + 0.001


class IntervHandler(object):
    def __init__(self, i_list, imp):
        self.interv = pd.DataFrame()
        self.interv['i'] = i_list
        self.imp = imp
        self.x = Symbol('x')
        self.poms = self.get_poms()
        self.interv['fdown'] = self.interv['i'].apply(lambda x: fdown_for_i(x, self.imp))
        self.interv['fup'] = self.interv['i'].apply(lambda x: fup_for_i(x, self.imp))

        self.integral_poms = {}
        self.integral_ind_pom = {
            30000: self.integrate(self.poms['ind_pom'], fup=30000),
            300000: self.integrate(self.poms['ind_pom'], fup=300000)
        }

        self.integral_poms.update({
            'stac': self.integrate(self.poms['stac']),
            'voz': self.integrate(self.poms['voz']),
            'nos': self.integrate(self.poms['nos'])
        })
        a = 1
        # for key, value in self.poms.items():
        #     # TODO f_up если нет частот, то...
        #     self.integral_poms.update({
        #         key: self.integrate(self.poms[key])
        #     })

    def get_poms(self):
        poms = {}
        poms.update(
            {
                """
                replace with real values
                """
            }
        )
        return poms

    def calculate_integral(self, series):
        return integrate(series['func'] ** 2, (self.x, series['fdown'], (series['fup']))).evalf()

    def integrate_intervals(self, series, pom):
        fdown = series.fdown
        fup = series.fup

        pom_interv = pom[(pom['fup'] >= fdown) & (pom['fdown'] < fup)].copy()
        pom_interv.index = list(range(len(pom_interv)))
        pom_interv.loc[0, 'fdown'] = fdown
        pom_interv.loc[len(pom_interv) - 1, 'fup'] = fup
        integrals = pom_interv.apply(lambda x: self.calculate_integral(x), axis=1)

        integrals_sum = integrals.sum()

        return integrals_sum

    def integrate(self, pom, fdown=0, fup=10**10):
        # pom = pom[(pom['fup'] >= fdown) & (pom['fdown'] < fup)].copy()
        # if len(pom) == 0:
        #     return None

        temp_interv = self.interv[self.interv['fdown'] < fup].copy()
        if len(temp_interv) == 0:
            print('Empty intervals list!')
            return None

        if (temp_interv.iloc[-1:]['fup'] > fup).bool():
            temp_interv.iloc[-1:]['fup'] = fup

        return temp_interv.apply(lambda x: self.integrate_intervals(x, pom), axis=1)


class SiModel(object):
    def __init__(self, presenter):
        self.presenter = presenter
        self.meas_h = None
        self.interv_h = None

    def set_meas_h(self, meas):
        self.meas_h = MeasHandler(meas)

    def set_ftak(self, ftak):
        self.meas_h.set_ftak(ftak)
        self.meas_h.set_i()
        if self.meas_h.ready:
            self.presenter.set_ready()
        # self.set_interv_h()

    def get_imp(self):
        return self.meas_h.imp

    def calculate(self):
        self.set_interv_h()

    def set_interv_h(self):
        print('Setting intervals handler...')
        if self.meas_h is not None:
            if self.meas_h.ready:
                i_list = self.meas_h.get_i_list()
                imp = self.meas_h.imp
                self.interv_h = IntervHandler(i_list, imp)

    def get_meas_values(self):
        return self.meas_h.meas.values
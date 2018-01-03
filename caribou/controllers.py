import numpy as np
import scipy
from scipy.linalg import sqrtm
from numpy.random import multivariate_normal
from numpy.random import rand
"""Controllers."""


class Controller:
    def __init__(self):
        pass


class LocalController(Controller):
    id_generator = 0

    def __init__(self, agentgroup, globalcontroller):
        super().__init__()
        self.agentgroup = agentgroup
        self.globalcontroller = globalcontroller

    def generate_random_pv_gen(self):
        raise NotImplementedError

    def run_local_optim(self, globalcontroller_variables):
        x_result, f_result = self.local_solve(globalcontroller_variables)
        return x_result, f_result

    def local_solve(self, globalcontroller_variables):
        raise NotImplementedError


class TravaccaEtAl2017LocalController(LocalController):
    def __init__(self, agentgroup, globalcontroller):
        super().__init__(agentgroup, globalcontroller)
        self.identity = self.id_generator
        self.id_generator += 1

    def local_solve(self, globalcontroller_variables):
        mu, nu, fq = globalcontroller_variables

    def load_e_max(self):
        return np.genfromtxt('data/travacca_et_al_2017/dam_e_max.csv', delimiter=',')[self.identity]

    def load_e_min(self):
        return np.genfromtxt('data/travacca_et_al_2017/dam_e_min.csv', delimiter=',')[self.identity]

    def load_ev_max(self):
        return np.genfromtxt('data/travacca_et_al_2017/dam_ev_max.csv', delimiter=',')[self.identity]

    def load_ev_min(self):
        return np.genfromtxt('data/travacca_et_al_2017/dam_ev_min.csv', delimiter=',')[self.identity]

    def generate_random_pv_gen(self):
        data_pv = self.globalcontroller.load_pv_gen()
        return data_pv + data_pv * (rand(self.globalcontroller.time_horizon * 24)-0.5)


class GlobalController(Controller):
    def __init__(self):
        super().__init__()
        self.list_localcontrollers = []

    def set_list_localcontrollers(self, list_localcontrollers):
        self.list_localcontrollers = list_localcontrollers

    def get_list_localcontrollers(self):
        return self.list_localcontrollers

    def run_global_optim(self):
        self.global_solve()

    def global_solve(self):
        raise NotImplementedError


class TravaccaEtAl2017GlobalController(GlobalController):
    def __init__(self, start_day=2, time_horizon=1):  # time_horizon in days
        super().__init__()
        self.start_day = start_day
        self.time_horizon = time_horizon
        self.data_main = np.genfromtxt(
            'data/travacca_et_al_2017/main.csv', delimiter=',')

    def load_pv_gen(self):
        start = self.start_day * 4 * 24
        stop = self.start_day * 4 * 24 + self.time_horizon * 24 * 4 - 1
        scale_pv = 10
        return self.data_main[start:stop:4, 16] / scale_pv

    def load_e_max_agg(self):
        return np.genfromtxt('data/travacca_et_al_2017/dam_e_max_agg.csv', delimiter=',')

    def load_e_min_agg(self):
        return np.genfromtxt('data/travacca_et_al_2017/dam_e_min_agg.csv', delimiter=',')

    def load_ev_max_agg(self):
        return np.genfromtxt('data/travacca_et_al_2017/dam_ev_max_agg.csv', delimiter=',')

    def load_ev_min_agg(self):
        return np.genfromtxt('data/travacca_et_al_2017/dam_ev_min_agg.csv', delimiter=',')

    def load_b_matrix(self):
        return np.genfromtxt('data/travacca_et_al_2017/b.csv', delimiter=',')

    def load_dam_price(self):
        start = self.start_day * 4 * 24
        stop = self.start_day * 4 * 24 + self.time_horizon * 24 * 4 - 1
        scale_price = 1000
        return self.data_main[start:stop:4, 11] / scale_price

    def load_cov_dam_price(self):
        return np.genfromtxt(
            'data/travacca_et_al_2017/covariance.csv', delimiter=',')

    def predict_dam_price(self):
        cov_dam_price = self.load_cov_dam_price()
        dam_price = self.load_dam_price()
        dam_predict_price = np.zeros((24, self.time_horizon))
        for day in range(self.time_horizon):
            product_matrix = np.reshape(np.dot(
                    sqrtm(cov_dam_price),
                    multivariate_normal(np.zeros((24,)), np.eye(24))), (24, 1))
            matrix_dam_price = np.reshape(dam_price[24 * (
                day - 1):24 * (day + 1)], (24, 1))
            dam_predict_price[24 * day:24 * (day + 1), :] = matrix_dam_price + product_matrix
        return dam_predict_price


    def global_solve(self, num_iter=50):
        mu, nu, ev_sol, g_sol, local_optimal_cost = self.initialize_gradient_accent(
            self)
        for _ in range(num_iter):
            mu, nu, ev_sol, g_sol, local_optimal_cost = self.next_step_gradiant_accent(
                mu, nu)

    def initialize_gradient_accent(self):
        size = len(self.list_localcontrollers)
        return 0, 0, np.zeros((24, size)), np.zeros((24, size)), np.zeros(
            (size, 1))

    def next_step_gradient_accent(self, mu, nu):
        b = self.load_b_matrix()
        dam_predict_price = self.predict_dam_price()
        fq = np.array(dam_predict_price - nu, np.dot(b, mu))
        globalcontroller_variables = (mu, nu, fq)
        for localcontroller in self.list_localcontrollers:
            localcontroller.run_local_optim(globalcontroller_variables)

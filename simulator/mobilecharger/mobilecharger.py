from scipy.spatial import distance

from simulator.mobilecharger.utils import get_location, charging
from simulator.network import parameter as para


class MobileCharger:
    def __init__(self, id,  energy=None, e_move=None, start=para.depot, end=para.depot, velocity=None,
                 e_self_charge=None, capacity=None):
        self.id = id
        self.is_stand = False  # is true if mc stand and charge
        self.is_self_charge = False  # is true if mc is charged
        self.is_active = False

        self.start = start  # from location
        self.end = end  # to location
        self.current = start  # location now
        self.end_time = -1

        self.energy = energy  # energy now
        self.capacity = capacity  # capacity of mc
        self.e_move = e_move  # energy for moving
        self.e_self_charge = e_self_charge  # energy receive per second
        self.velocity = velocity  # velocity of mc

    def get_status(self):
        if not self.is_active:
            return "deactivated"
        if not self.is_stand:
            return "moving"
        if not self.is_self_charge:
            return "charging"
        return "self_charging" 

    def update_location(self, func=get_location):
        self.current = func(self)
        self.energy -= self.e_move

    def charge(self, net=None, node=None, func=charging):
        func(self, net, node)

    def self_charge(self):
        self.energy = min(self.energy + self.e_self_charge, self.capacity)

    def check_state(self):
        if distance.euclidean(self.current, self.end) < 1:
            self.is_stand = True
            self.current = self.end
        else:
            self.is_stand = False
        if distance.euclidean(para.depot, self.end) < 10 ** -3:
            self.is_self_charge = True
        else:
            self.is_self_charge = False

    def get_next_location(self, network, time_stem, optimizer=None):
        next_location, charging_time = optimizer.update(self, network, time_stem)
        self.start = self.current
        self.end = next_location
        moving_time = distance.euclidean(self.start, self.end) / self.velocity
        self.end_time = time_stem + moving_time + charging_time

    def run(self, network, time_stem, net=None, optimizer=None):
        # print(self.energy, self.start, self.end, self.current)
        if ((not self.is_active) and optimizer.list_request) or abs(time_stem - self.end_time) < 1:
            self.is_active = True
            new_list_request = []
            for request in optimizer.list_request:
                if net.node[request["id"]].energy < net.node[request["id"]].energy_thresh:
                    new_list_request.append(request)
                else:
                    net.node[request["id"]].is_request = False
            optimizer.list_request = new_list_request
            if not optimizer.list_request:
                self.is_active = False
            self.get_next_location(network=network, time_stem=time_stem, optimizer=optimizer)
        else:
            if self.is_active:
                if not self.is_stand:
                    # print("moving")
                    self.update_location()
                elif not self.is_self_charge:
                    # print("charging")
                    self.charge(net)
                else:
                    # print("self charging")
                    self.self_charge()
        if self.energy < para.E_mc_thresh and not self.is_self_charge and self.end != para.depot:
            self.start = self.current
            self.end = para.depot
            self.is_stand = False
            charging_time = self.capacity / self.e_self_charge
            moving_time = distance.euclidean(self.start, self.end) / self.velocity
            self.end_time = time_stem + moving_time + charging_time
        self.check_state()

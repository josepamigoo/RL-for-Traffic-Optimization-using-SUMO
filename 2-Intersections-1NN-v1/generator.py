import numpy as np
import math
from memory import Memory

class TrafficGenerator:
    def __init__(self,Memory, max_steps, n_cars_generated):
        self._Memory = Memory
        self._n_cars_generated = n_cars_generated  # how many cars per episode
        self._max_steps = max_steps
        self._distribution_store=[]

    def generate_routefile(self, seed):
        """
        Generation of the route of every car for one episode
        """
        np.random.seed(seed)  # make tests reproducible

        # the generation of cars is distributed according to two gaussian distributiins
        timings1 = np.random.normal(loc=1920, scale=600,size=int(self._n_cars_generated/2))
        timings2 = np.random.normal(loc=3800, scale=350,size=int(self._n_cars_generated/2))
        timings=np.concatenate((timings1,timings2))
        timings = np.sort(timings)

        # flip negative values just in case
        car_gen_steps = []
        for value in timings:
            car_gen_steps=np.append(car_gen_steps,np.sign(value)*value)

        car_gen_steps = np.sort(car_gen_steps)
        car_gen_steps = np.rint(car_gen_steps)  # round every value to int -> effective steps when a car will be generated
        self._distribution_store=(car_gen_steps.tolist())

        # produce the file for cars generation, one car per line
        with open("intersection/episode_routes.rou.xml", "w") as routes:
            print("""<routes>
            <vType accel="1.0" decel="4.5" id="standard_car" length="5.0" minGap="2.5" maxSpeed="25" sigma="0.5" />

            <route id="W_N1" edges="W2TL TL2N"/>
            <route id="W_S1" edges="W2TL TL2S"/>
            <route id="W_E" edges="W2TL TL2E E0"/>
            <route id="W_N2" edges="W2TL TL2E E3"/>
            <route id="W_S2" edges="W2TL TL2E E4"/>
                  
            <route id="N1_W" edges="N2TL TL2W"/>
            <route id="N1_E" edges="N2TL TL2E E0"/>
            <route id="N1_S1" edges="N2TL TL2S"/>
            <route id="N1_S2" edges="N2TL TL2E E4"/>  
            <route id="N1_N2" edges="N2TL TL2E E3"/>

            <route id="S1_W" edges="S2TL TL2W"/>
            <route id="S1_N1" edges="S2TL TL2N"/>
            <route id="S1_E" edges="S2TL TL2E E0"/>
            <route id="S1_N2" edges="S2TL TL2E E3"/>
            <route id="S1_S2" edges="S2TL TL2E E4"/>
        
            <route id="E_W" edges="-E0 E2TL TL2W"/>
            <route id="E_N1" edges="-E0 E2TL TL2N"/>
            <route id="E_S1" edges="-E0 E2TL TL2S"/>
            <route id="E_N2" edges="-E0 E3"/>
            <route id="E_S2" edges="-E0 E4"/>
  
            <route id="N2_W" edges="-E3 E2TL TL2W"/>
            <route id="N2_E" edges="-E3 E0"/>
            <route id="N2_S1" edges="-E3 E2TL TL2S"/>
            <route id="N2_S2" edges="-E3 E4"/>  
            <route id="N2_N1" edges="-E3 E2TL TL2N"/>
              
            <route id="S2_W" edges="-E4 E2TL TL2W"/>
            <route id="S2_N1" edges="-E4 E2TL TL2N"/>
            <route id="S2_E" edges="-E4 E0"/>
            <route id="S2_N2" edges="-E4 E3"/>
            <route id="S2_S1" edges="-E4 E2TL TL2S"/> """, file=routes)

            for car_counter, step in enumerate(car_gen_steps):
                straight_or_turn = np.random.uniform()

                if straight_or_turn < 0.60:  # choose direction: straight or turn - 60% of times the car goes straight

                    route_straight = np.random.randint(1, 7)  # choose a random source & destination
                    if route_straight == 1:
                        print('    <vehicle id="W_E_%i" type="standard_car" route="W_E" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_straight == 2:
                        print('    <vehicle id="E_W_%i" type="standard_car" route="E_W" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_straight == 3:
                        print('    <vehicle id="N1_S1_%i" type="standard_car" route="N1_S1" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_straight == 4:
                        print('    <vehicle id="S1_N1_%i" type="standard_car" route="S1_N1" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_straight == 5:
                        print('    <vehicle id="S2_N2_%i" type="standard_car" route="S2_N2" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_straight == 6:
                        print('    <vehicle id="N2_S2_%i" type="standard_car" route="N2_S2" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)

                else:  # car that turn -40% of the time the car turns

                    route_turn = np.random.randint(1, 16)  # choose random source source & destination
                    if route_turn == 1:
                        print('    <vehicle id="W_N1_%i" type="standard_car" route="W_N1" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 2:
                        print('    <vehicle id="W_S1_%i" type="standard_car" route="W_S1" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 3:
                        print('    <vehicle id="N1_W_%i" type="standard_car" route="N1_W" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 4:
                        print('    <vehicle id="N1_E_%i" type="standard_car" route="N1_E" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 5:
                        print('    <vehicle id="E_N1_%i" type="standard_car" route="E_N1" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 6:
                        print('    <vehicle id="E_S1_%i" type="standard_car" route="E_S1" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 7:
                        print('    <vehicle id="S1_W_%i" type="standard_car" route="S1_W" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 8:
                        print('    <vehicle id="S1_E_%i" type="standard_car" route="S1_E" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 9:
                        print('    <vehicle id="W_N2_%i" type="standard_car" route="W_N2" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 10:
                        print('    <vehicle id="W_S2_%i" type="standard_car" route="W_S2" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 11:
                        print('    <vehicle id="N2_W_%i" type="standard_car" route="N2_W" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 12:
                        print('    <vehicle id="N2_E_%i" type="standard_car" route="N2_E" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 13:
                        print('    <vehicle id="E_N2_%i" type="standard_car" route="E_N2" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 14:
                        print('    <vehicle id="E_S2_%i" type="standard_car" route="E_S2" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 15:
                        print('    <vehicle id="S2_W_%i" type="standard_car" route="S2_W" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 16:
                        print('    <vehicle id="S2_E_%i" type="standard_car" route="S2_E" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 17:
                        print('    <vehicle id="S2_S1_%i" type="standard_car" route="S2_S1" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 18:
                        print('    <vehicle id="S1_S2_%i" type="standard_car" route="S1_S2" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 19:
                        print('    <vehicle id="N1_N2_%i" type="standard_car" route="N1_N2" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    elif route_turn == 20:
                        print('    <vehicle id="N2_N1_%i" type="standard_car" route="N2_N1" depart="%s" departLane="random" departSpeed="10" />' % (car_counter, step), file=routes)
                    
            print("</routes>", file=routes)

    @property
    def distribution_store(self):
        return self._distribution_store
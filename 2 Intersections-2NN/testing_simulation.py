import traci
import numpy as np
import random
import timeit
import os

# phase codes based on environment.net.xml
PHASE_NS_GREEN = 0  # action 0 code 00
PHASE_NS_YELLOW = 1
PHASE_NSL_GREEN = 2  # action 1 code 01
PHASE_NSL_YELLOW = 3
PHASE_EW_GREEN = 4  # action 2 code 10
PHASE_EW_YELLOW = 5
PHASE_EWL_GREEN = 6  # action 3 code 11
PHASE_EWL_YELLOW = 7



class Simulation:
    def __init__(self, Model, TrafficGen, sumo_cmd, max_steps, green_duration, yellow_duration, num_states, num_actions,reward):
        self._Model = Model
        self._TrafficGen = TrafficGen
        self._step = 0
        self._sumo_cmd = sumo_cmd
        self._max_steps = max_steps
        self._green_duration = green_duration
        self._yellow_duration = yellow_duration
        self._num_states = num_states
        self._num_actions = num_actions
        self._reward= reward
        self._reward1_episode = []
        self._reward2_episode = []
        self._queue1_length_episode = []
        self._queue2_length_episode = []
        self._queue_total_length_episode =[]
        self._store_action1=[]
        self._store_action2=[]


    def run(self, episode):
        """
        Runs the testing simulation
        """
        start_time = timeit.default_timer()

        # first, generate the route file for this simulation and set up sumo
        self._TrafficGen.generate_routefile(seed=episode)
        traci.start(self._sumo_cmd)
        print("Simulating...")

        # inits
        self._step = 0
        self._waiting_times1 = {}
        self._waiting_times2 = {}
        old_total_wait1 = 0
        old_total_wait2 = 0
        old_action1 = -1
        old_action2 = -1 
        time1 = 10
        time2 = 10
        yellow1 = False
        yellow2 = False


        while self._step < self._max_steps:

            # Check if phase change is needed for Intersection 1 (TL)
            if time1 >= self._green_duration and not yellow1:

                current_state1=self._get_state(1)
                reward1, reward2, current_total_wait1, current_total_wait2 = self._calculate_reward(old_total_wait1,old_total_wait2,old_action1,old_action2)             
                action1=self._choose_action(current_state1,1)
                time1=0

                if  old_action1 != action1:
                    self._set_yellow_phase(old_action1, "TL")
                    yellow1=True
                    time1=0

            # After yellow light 1 has finnished, implement the triggering action 1
            if yellow1 and time1 >= self._yellow_duration:
                self._set_green_phase(action1, "TL")  
                time1=0
                yellow1=False

            # Check if phase change is needed for Intersection 2 (DE)
            if time2 >= self._green_duration and not yellow2:

                current_state2=self._get_state(2)
                reward1, reward2, current_total_wait1, current_total_wait2 = self._calculate_reward(old_total_wait1, old_total_wait2, old_action1, old_action2)
                action2=self._choose_action(current_state2,2)
                time2=0  

                if  old_action2 != action2:
                    self._set_yellow_phase(old_action1, "DE")
                    yellow2=True
                    time2=0

            # After yellow light 2 has finnished, implement the triggering action 2
            if yellow2 and time2  >= self._yellow_duration:

                self._set_green_phase(action2, "DE")  
                time2=0
                yellow2=False

            # update timers and advance 2 steps in the simulation
            time1+=2
            time2+=2
            self._simulate(2)

            # saving variables for later & accumulate reward
            self._store_action1=np.append(self._store_action1,action1)
            self._store_action2=np.append(self._store_action2,action2)
            old_action1 = action1
            old_action2 = action2
            old_total_wait1 = current_total_wait1
            old_total_wait2 = current_total_wait2

            self._reward1_episode.append(reward1)
            self._reward2_episode.append(reward2)

        #print("Total reward:", np.sum(self._reward_episode))
        traci.close()
        simulation_time = round(timeit.default_timer() - start_time, 1)

        return simulation_time


    def _simulate(self, steps_to_do):
        """
        Proceed with the simulation in sumo
        """
        while steps_to_do > 0 :
            traci.simulationStep()  # simulate 1 step in sumo
            self._step += 1 # update the step counter
            steps_to_do += -1
            queue_length1, queue_length2 = self._get_queue_length() # get number of cars for each incoming lane 
            self._queue1_length_episode.append(queue_length1)
            self._queue2_length_episode.append(queue_length2)
            self._queue_total_length_episode.append(queue_length1 + queue_length2)


    def _collect_waiting_times(self, agent_id):
        """
        Retrieve the waiting time of every car in the incoming roads of the corresponding intersection
        """
        if agent_id == 1:
            incoming_roads = ["E2TL", "N2TL", "W2TL", "S2TL"]
        if agent_id == 2:
           incoming_roads = ["TL2E","-E0","-E3","-E4"]

        car_list=[]
        for lane_id in incoming_roads:
              car_list =np.append(car_list, traci.edge.getLastStepVehicleIDs(lane_id)) 
        
        for car_id in car_list:
            wait_time = traci.vehicle.getAccumulatedWaitingTime(car_id)
            road_id = traci.vehicle.getRoadID(car_id)  # get the road id where the car is located

            if road_id in incoming_roads:   # consider waiting times for the selected intersection 
                if agent_id ==1:
                    self._waiting_times1[car_id] = wait_time
                elif agent_id ==2:
                    self._waiting_times2[car_id] = wait_time
            else:
                    if car_id in self._waiting_times1 and agent_id == 1: # a car that was tracked has cleared the intersection 1
                        del self._waiting_times1[car_id] 
                    if car_id in self._waiting_times2 and agent_id == 2: # a car that was tracked has cleared the intersection 2
                        del self._waiting_times2[car_id] 
        if agent_id==1:
                  total_waiting_time = sum(self._waiting_times1.values())
        if agent_id==2:
                  total_waiting_time = sum(self._waiting_times2.values())
      
        return total_waiting_time


    def _choose_action(self, state, agent_id):
        """
        Pick the best action known based on the current state of the env
        """
        action = np.argmax(self._Model.predict_one(state,agent_id))
  
        return action


    def _set_yellow_phase(self, old_action, intersection_id):
        """
        Activate the correct yellow light combination in sumo
        """
        if old_action>=0 and old_action<=3:
         yellow_phase_code = old_action * 2 + 1
         traci.trafficlight.setPhase(intersection_id, yellow_phase_code)



    def _set_green_phase(self, action_number, intersection_id):
        """
        Activate the correct green light combination in sumo for the selected intersection
        """

        if action_number == 0:
            traci.trafficlight.setPhase(intersection_id, PHASE_NS_GREEN)  # straight
        elif action_number == 1:
            traci.trafficlight.setPhase(intersection_id, PHASE_NSL_GREEN)  # turn left
        elif action_number == 2:
            traci.trafficlight.setPhase(intersection_id, PHASE_EW_GREEN)  # straight
        elif action_number == 3:
            traci.trafficlight.setPhase(intersection_id, PHASE_EWL_GREEN)  # turn left

    def _get_queue_length(self):
        """
        Retrieve the number of cars with speed = 0 in every incoming lane of both intersecions
        """
         # incoming cars intersection 1
        halt_N1 = traci.edge.getLastStepHaltingNumber("N2TL")
        halt_S1 = traci.edge.getLastStepHaltingNumber("S2TL")
        halt_E1 = traci.edge.getLastStepHaltingNumber("E2TL")
        halt_W1 = traci.edge.getLastStepHaltingNumber("W2TL")
         # incoming cars intersection 2
        halt_N2 = traci.edge.getLastStepHaltingNumber("-E3")
        halt_S2 = traci.edge.getLastStepHaltingNumber("-E4")
        halt_E2 = traci.edge.getLastStepHaltingNumber("-E0")
        halt_W2 = traci.edge.getLastStepHaltingNumber("TL2E")

        queue_length1 = halt_N1 + halt_S1 + halt_E1 + halt_W1
        queue_length2 = halt_N2 + halt_S2 + halt_E2 + halt_W2

        return queue_length1, queue_length2


    def _get_state(self, agent_id):
        """
        Retrieve the state of the intersection from sumo, in the form of cell occupancy
        """
        state = np.zeros(self._num_states)
        car_list=[]
        # selecting the lanes of the given intersection and agent
        if agent_id == 1:
            lanes = ["E2TL", "N2TL", "W2TL", "S2TL"]
        if agent_id == 2:
           lanes = ["TL2E","-E0","-E3","-E4"]

        for lane_id in lanes:
              car_list =np.append(car_list, traci.edge.getLastStepVehicleIDs(lane_id) )

        for car_id in car_list:
            lane_pos = traci.vehicle.getLanePosition(car_id)
            lane_id = traci.vehicle.getLaneID(car_id)
            lane_pos = 750 - lane_pos  # inversion of lane pos, so if the car is close to the traffic light -> lane_pos = 0 --- 750 = max len of a road
    
          
            # distance in meters from the traffic light -> mapping into cells
            if lane_id == 'E2TL' or lane_id == 'TL2E': #special case for roads in the middle
              if lane_pos < 7:
                  lane_cell = 0
              elif lane_pos < 20:
                  lane_cell = 1
              elif lane_pos < 40:
                  lane_cell = 2
              elif lane_pos < 100:
                  lane_cell = 3
              elif lane_pos < 200:
                  lane_cell = 4
              elif lane_pos < 400:
                  lane_cell = 5
              elif lane_pos < 600:
                  lane_cell = 6
              elif lane_pos < 700:
                  lane_cell = 7
              elif lane_pos < 730:
                  lane_cell = 8
              elif lane_pos <= 750:
                  lane_cell = 9

            else :           
              if lane_pos < 7:
                  lane_cell = 0
              elif lane_pos < 14:
                  lane_cell = 1
              elif lane_pos < 21:
                  lane_cell = 2
              elif lane_pos < 28:
                  lane_cell = 3
              elif lane_pos < 40:
                  lane_cell = 4
              elif lane_pos < 60:
                  lane_cell = 5
              elif lane_pos < 100:
                  lane_cell = 6
              elif lane_pos < 160:
                  lane_cell = 7
              elif lane_pos < 400:
                  lane_cell = 8
              elif lane_pos <= 750:
                  lane_cell = 9
                
            if agent_id==1:
                if lane_id == "W2TL_0" or lane_id == "W2TL_1" or lane_id == "W2TL_2":
                    lane_group = 0
                elif lane_id == "W2TL_3":
                    lane_group = 1
                elif lane_id == "N2TL_0" or lane_id == "N2TL_1" or lane_id == "N2TL_2":
                    lane_group = 2
                elif lane_id == "N2TL_3":
                    lane_group = 3
                elif lane_id == "E2TL_0" or lane_id == "E2TL_1" or lane_id == "E2TL_2":
                    lane_group = 4
                elif lane_id == "E2TL_3":
                    lane_group = 5
                elif lane_id == "S2TL_0" or lane_id == "S2TL_1" or lane_id == "S2TL_2":
                    lane_group = 6
                elif lane_id == "S2TL_3":
                    lane_group = 7
                else:
                    lane_group = -1   

            if agent_id==2:        

                if lane_id == "-E0_0" or lane_id == "-E0_1" or lane_id == "-E0_2":
                    lane_group = 0 
                elif lane_id == "-E0_3":
                    lane_group = 1 
                elif lane_id == "-E3_0" or lane_id == "-E3_1" or lane_id == "-E3_2":
                    lane_group = 2  
                elif lane_id == "-E3_3":
                    lane_group = 3
                elif lane_id == "-E4_0" or lane_id == "-E4_1" or lane_id == "-E4_2":
                    lane_group = 4
                elif lane_id == "-E4_3":
                    lane_group = 5
                elif lane_id == "TL2E_0" or lane_id == "TL2E_1" or lane_id == "TL2E_2":
                    lane_group = 6  
                elif lane_id == "TL2E_3":
                    lane_group = 7                         
                else:
                    lane_group = -1
            
            if lane_group >= 1 and lane_group <= 7:
                car_position = int(str(lane_group) + str(lane_cell))  # composition of the two postion ID to create a number in interval 0-79
                valid_car = True
            elif lane_group == 0:
                car_position = lane_cell
                valid_car = True
            else:
                valid_car = False  # flag for not detecting cars crossing the intersection or driving away from it
            if valid_car:
                if car_position>=0 and car_position<= (self._num_states-1) :
                   state[car_position] = 1  # write the position of the car car_id in the state array in the form of "cell occupied"

        return state
        
    
    def _calculate_reward(self,old_total_wait1, old_total_wait2,action1,action2):
        """
        Computes the chosen reward
        """  
        # computes waiting times for each intersection
        current_total_wait1 = self._collect_waiting_times(1)
        current_total_wait2 = self._collect_waiting_times(2)
        
        # boolean parameter to choose reward
        if self._reward == 0:
            r1 = old_total_wait1 - current_total_wait1
            r2 = old_total_wait2 - current_total_wait2

        elif self._reward == 1:
            r1 = -current_total_wait1
            r2 = -current_total_wait2

        elif self._reward == 2:
            rold1 =  old_total_wait1 - current_total_wait1   
            rold2 = old_total_wait2 - current_total_wait2
            bonus1, bonus2 = self._coordination_bonus(action1, action2, rold1, rold2, 1)
            r1 = rold1 +bonus1
            r2 = rold2 +bonus2
            
        elif self._reward == 3:        
            rold1 =  old_total_wait1 - current_total_wait1  
            rold2 = old_total_wait2 - current_total_wait2 
            bonus1, bonus2 = self._coordination_bonus(action1, action2, rold1, rold2, 2)   
            r1 = rold1 +bonus1
            r2 = rold2 +bonus2
            
        elif self._reward == 4:
            r1old = old_total_wait1 - current_total_wait1
            r2old = old_total_wait2 - current_total_wait2
            r1=0.8*r1old+0.2*r2old
            r2=0.8*r2old+0.2*r1old
        else:
            print("Reward still to be defined")

        return r1, r2, current_total_wait1, current_total_wait2
    
    def _coordination_bonus(self, action1, action2, rold1, rold2, type):
        """
        Assigns a prize when light are synchronised
        """ 
        bonus1 = 0
        bonus2 = 0

        if type == 1 :  # perpendicular
            if (action1 == 0 and action2 == 2) or (action1 == 2 and action2 == 0):
                bonus1 = -0.25*rold1
                bonus2 = -0.25*rold2
        elif type == 2 : # parallel
            if (action1 == 0 and action2 == 0) or (action1 == 2 and action2 == 2):
                bonus1 = -0.25*rold1   
                bonus2 = -0.25*rold2     
        return bonus1, bonus2
    
    @property
    def queue1_length_episode(self):
        return self._queue1_length_episode
    
    @property
    def queue2_length_episode(self):
        return self._queue2_length_episode
    
    @property
    def queue_total_length_episode(self):
        return self._queue_total_length_episode


    @property
    def reward1_episode(self):
        return self._reward1_episode
    
    @property
    def reward2_episode(self):
        return self._reward2_episode

    @property
    def store_action1(self):
        return self._store_action1

    @property
    def store_action2(self):
        return self._store_action2


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

PHASE2_NS_GREEN = 0  # action 0 code 00
PHASE2_NS_YELLOW = 1
PHASE2_NSL_GREEN = 2 # action 1 code 01
PHASE2_NSL_YELLOW = 3
PHASE2_EW_GREEN = 4  # action 2 code 10
PHASE2_EW_YELLOW = 5
PHASE2_EWL_GREEN = 6  # action 3 code 11
PHASE2_EWL_YELLOW = 7

class Simulation:
    def __init__(self, Model, Memory, TrafficGen, sumo_cmd, gamma, max_steps, green_duration, yellow_duration, num_states, num_actions, training_epochs,mode,reward):
        self._Model = Model
        self._Memory = Memory
        self._TrafficGen = TrafficGen
        self._gamma = gamma
        self._step = 0
        self._sumo_cmd = sumo_cmd
        self._max_steps = max_steps
        self._green_duration = green_duration
        self._yellow_duration = yellow_duration
        self._num_states = num_states
        self._num_actions = num_actions
        self._reward_store = []
        self._cumulative_wait_store = []
        self._avg_queue_length_store = []
        self._training_epochs = training_epochs
        self._mode = mode
        self._reward= reward
        self._fixed_phase_duration=80


    def run(self, episode, epsilon):
        """
        Runs an episode of simulation, then starts a training session
        """
        start_time = timeit.default_timer()

        # first, generate the route file for this simulation and set up sumo
        self._TrafficGen.generate_routefile(seed=episode)
        traci.start(self._sumo_cmd)
        print("Simulating...")

        # inits
        self._step = 0
        self._waiting_times = {}
        self._sum_neg_reward = 0
        self._sum_queue_length = 0
        self._sum_waiting_time = 0
        old_total_wait = 0
        old_state = -1
        old_action = -1
        training_time = 0

        while self._step < self._max_steps:

            # get current state of the intersection
            current_state = self._get_state()

            # waiting time = seconds waited by a car since the spawn in the environment, cumulated for every car in incoming lanes
            current_total_wait = self._collect_waiting_times()

            # calculate reward of previous action: (change in cumulative waiting time between actions)
            reward=self._calculate_reward(old_total_wait,current_total_wait)

            # saving the data into the memory
            if self._step != 0:
                self._Memory.add_sample((old_state, old_action, reward, current_state))

            # choose the light phase to activate, based on the current state of the intersection
            action = self._choose_action(current_state, epsilon)

            # if the chosen phase is different from the last phase, activate the yellow phase
            if self._step != 0 and old_action != action:
                self._set_yellow_phase(old_action)
                self._simulate(self._yellow_duration)

            # execute the phase selected before
            self._set_green_phase(action)
            self._simulate(self._green_duration)

            # saving variables for later & accumulate reward
            old_state = current_state
            old_action = action
            old_total_wait = current_total_wait

            # saving only the meaningful reward to better see if the agent is behaving correctly
            if reward < 0:
                self._sum_neg_reward += reward

        self._save_episode_stats()
        print("Total reward:", self._sum_neg_reward, "- Epsilon:", round(epsilon, 2))
        traci.close()
        simulation_time = round(timeit.default_timer() - start_time, 1)
        
        if self._mode == 0: # only if in training mode
         print("Training...")
         start_time = timeit.default_timer()
         for _ in range(self._training_epochs):
            self._replay()
         training_time = round(timeit.default_timer() - start_time, 1)

        return simulation_time, training_time


    def _simulate(self, steps_todo):
        """
        Execute steps in sumo while gathering statistics
        """
        if (self._step + steps_todo) >= self._max_steps:  # do not do more steps than the maximum allowed number of steps
            steps_todo = self._max_steps - self._step

        while steps_todo > 0:
            traci.simulationStep()  # simulate 1 step in sumo
            self._step += 1 # update the step counter
            steps_todo -= 1
            queue_length = self._get_queue_length() # get number of cars for each incoming lane
            self._sum_queue_length += queue_length
            self._sum_waiting_time += queue_length # 1 step while wating in queue means 1 second waited, for each car, therefore queue_lenght == waited_seconds


    def _collect_waiting_times(self):
        """
        Retrieve the waiting time of every car in the incoming roads
        """
        # roads from both intersections
        incoming_roads = ["E2TL", "N2TL", "W2TL", "S2TL","TL2E","-E0","-E3","-E4"]  # roads from both intersections
        car_list = traci.vehicle.getIDList()

        for car_id in car_list:
            wait_time = traci.vehicle.getAccumulatedWaitingTime(car_id)
            road_id = traci.vehicle.getRoadID(car_id)  # get the road id where the car is located

            if road_id in incoming_roads:  # consider only the waiting times of cars in incoming roads
                self._waiting_times[car_id] = wait_time
            else:
                if car_id in self._waiting_times: # a car that was tracked has cleared the intersection
                    del self._waiting_times[car_id] 

        total_waiting_time = sum(self._waiting_times.values())
        return total_waiting_time


    def _choose_action(self, state, epsilon):
        """
        Decide wheter to perform an explorative or exploitative action, according to an epsilon-greedy policy
        """
        if self._mode == 0:  # training mode w/ epsilon-greedy policy
          if random.random() < epsilon:  
            return random.randint(0, self._num_actions - 1) # random action
          else:
            return np.argmax(self._Model.predict_one(state)) # the best action given the current state
          
        elif self._mode == 1: # baseline stochastic
            return random.randint(0, self._num_actions - 1) # random action
        
        elif self._mode == 2:  # baseline deterministic
            return (self._step // self._fixed_phase_duration) % self._num_actions # alternate actions sequentially

    def _set_yellow_phase(self, old_action):
        """
        Activate the correct yellow light combination in sumo
        """
        # actions for intersection 1
        if old_action>=0 and old_action<=3:
         yellow_phase_code = old_action * 2 + 1  # obtain the yellow phase code, based on the old action
         traci.trafficlight.setPhase("TL", yellow_phase_code)

        # actions for intersection 2
        if old_action>=4 and old_action<=7:
          yellow_phase_code = (old_action-4) * 2 + 1 # substract the offset and obtain the yellow phase code, based on the old action
          traci.trafficlight.setPhase("DE", yellow_phase_code)
         


    def _set_green_phase(self, action_number):
        """
        Activate the correct green light combination in sumo for each intersection
        """
        # Acions belong to: [0,3] Intersection 1; [4,7] Intersection 2
        if action_number == 0:
            traci.trafficlight.setPhase("TL", PHASE_NS_GREEN)   # straight
        elif action_number == 1:
            traci.trafficlight.setPhase("TL", PHASE_NSL_GREEN)  # turn left
        elif action_number == 2:
            traci.trafficlight.setPhase("TL", PHASE_EW_GREEN)   # straight
        elif action_number == 3:
            traci.trafficlight.setPhase("TL", PHASE_EWL_GREEN)  # turn left
        elif action_number == 4: 
            traci.trafficlight.setPhase("DE", PHASE2_NS_GREEN)  # straight
        elif action_number == 5:
            traci.trafficlight.setPhase("DE", PHASE2_NSL_GREEN) # turn left
        elif action_number == 6:
            traci.trafficlight.setPhase("DE", PHASE2_EW_GREEN)  # straight
        elif action_number == 7:
            traci.trafficlight.setPhase("DE", PHASE2_EWL_GREEN) # turn left
 
        

    def _get_queue_length(self):
        """
        Retrieve the number of cars with speed = 0 in every incoming lane in both intersections
        """
        halt_N1 = traci.edge.getLastStepHaltingNumber("N2TL")
        halt_S1 = traci.edge.getLastStepHaltingNumber("S2TL")
        halt_E1 = traci.edge.getLastStepHaltingNumber("E2TL")
        halt_W1 = traci.edge.getLastStepHaltingNumber("W2TL")
        halt_N2 = traci.edge.getLastStepHaltingNumber("-E3")
        halt_S2 = traci.edge.getLastStepHaltingNumber("-E4")
        halt_E2 = traci.edge.getLastStepHaltingNumber("-E0")
        halt_W2 = traci.edge.getLastStepHaltingNumber("TL2E")
        queue_length = halt_N1 + halt_S1 + halt_E1 + halt_W1+halt_N2 + halt_S2 + halt_E2 + halt_W2
        return queue_length


    def _get_state(self):
        """
        Retrieve the state of the intersection from sumo, in the form of cell occupancy
        """
        state = np.zeros(self._num_states)
        car_list = traci.vehicle.getIDList()

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

            # finding the lane where the car is located 
            # x2TL_3 and xEX_3 are the "turn left only" lanes
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
            elif lane_id == "-E0_0" or lane_id == "-E0_1" or lane_id == "-E0_2":
                lane_group = 8 
            elif lane_id == "-E0_3":
                lane_group = 9  
            elif lane_id == "-E3_0" or lane_id == "-E3_1" or lane_id == "-E3_2":
                lane_group = 10  
            elif lane_id == "-E3_3":
                lane_group = 11
            elif lane_id == "-E4_0" or lane_id == "-E4_1" or lane_id == "-E4_2":
                lane_group = 12
            elif lane_id == "-E4_3":
                lane_group = 13
            elif lane_id == "TL2E_0" or lane_id == "TL2E_1" or lane_id == "TL2E_2":
                lane_group = 14  
            elif lane_id == "TL2E_3":
                lane_group = 15                         
            else:
                lane_group = -1

            if lane_group >= 1 and lane_group <= 15:
                car_position = int(str(lane_group) + str(lane_cell))  # composition of the two postion ID to create a number in interval 0-159
                valid_car = True
            elif lane_group == 0:
                car_position = lane_cell
                valid_car = True
            else:
                valid_car = False  # flag for not detecting cars crossing the intersection or driving away from it

            if valid_car:
                state[car_position] = 1  # write the position of the car car_id in the state array in the form of "cell occupied"

        return state


    def _replay(self):
        """
        Retrieve a group of samples from the memory and for each of them update the learning equation, then train
        """
        batch = self._Memory.get_samples(self._Model.batch_size)
    

        if len(batch) > 0:  # if the memory is full enough
            states = np.array([val[0] for val in batch])  # extract states from the batch
            next_states = np.array([val[3] for val in batch])  # extract next states from the batch

            # prediction
            q_s_a = self._Model.predict_batch(states)  # predict Q(state), for every sample
            q_s_a_d = self._Model.predict_batch(next_states)  # predict Q(next_state), for every sample

            # setup training arrays
            x = np.zeros((len(batch), self._num_states))
            y = np.zeros((len(batch), self._num_actions))

            for i, b in enumerate(batch):
                state, action, reward, _ = b[0], b[1], b[2], b[3]  # extract data from one sample
                current_q = q_s_a[i]  # get the Q(state) predicted before
                current_q[action] = reward + self._gamma * np.amax(q_s_a_d[i])  # update Q(state, action)
                x[i] = state
                y[i] = current_q  # Q(state) that includes the updated action value

            self._Model.train_batch(x, y)  # train the NN


    def _save_episode_stats(self):
        """
        Save the stats of the episode to plot the graphs at the end of the session
        """
        self._reward_store.append(self._sum_neg_reward)  # how much negative reward in this episode
        self._cumulative_wait_store.append(self._sum_waiting_time)  # total number of seconds waited by cars in this episode
        self._avg_queue_length_store.append(self._sum_queue_length / self._max_steps)  # average number of queued cars per step, in this episode

    def _calculate_reward(self,old_total_wait,current_total_wait):
        """
        Computes the chosen reward
        """      
        # boolean parameter to choose reward
        if self._reward == 0:
            r = old_total_wait - current_total_wait
        elif self._reward == 1:
            r = -current_total_wait
        elif self._reward == 2:
            rold = old_total_wait - current_total_wait 
            r= rold + self._coordination_bonus(1, rold)
        elif self._reward == 3:
            rold = old_total_wait - current_total_wait 
            r = rold + self._coordination_bonus(2, rold)
        else:
            print("Reward still to be defined")

        return r
    
    def _coordination_bonus(self, type, rold):
        """
        Assigns a prize when light are synchronised
        """      
        bonus = 0
        light_1=traci.trafficlight.getPhase('TL')
        light_2=traci.trafficlight.getPhase('DE')

        if type == 1 :  # perpendicular
            if (light_1 == 0 and light_2 == 4) or (light_1 == 4 and light_2 == 0):
                bonus = -0.25*rold       
        elif type == 2 : # parallel
            if (light_1 == 0 and light_2 == 0) or (light_1 == 4 and light_2 == 4):
                bonus = -0.25*rold    

        return bonus


    @property
    def reward_store(self):
        return self._reward_store


    @property
    def cumulative_wait_store(self):
        return self._cumulative_wait_store


    @property
    def avg_queue_length_store(self):
        return self._avg_queue_length_store


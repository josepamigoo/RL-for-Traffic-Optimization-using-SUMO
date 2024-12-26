import traci
import sumolib
import sys
import os
import configparser
from sumolib import checkBinary

# configure simulation 
gui="False"    # SUMO simulation no visible
sumocfg_file_name="sumo_config.sumocfg"   
max_steps=5400   #simulation length  

if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
else:
        sys.exit("please declare environment variable 'SUMO_HOME'")

# setting the cmd mode or the visual mode    
if gui == False:
        sumoBinary = checkBinary('sumo')
else:
        sumoBinary = checkBinary('sumo-gui')
 
# setting the cmd command to run sumo at simulation time
sumo_cmd = [sumoBinary, "-c", os.path.join('intersection', sumocfg_file_name), "--no-step-log", "true", "--waiting-time-memory", str(max_steps)]

# Starting mx config file
try:
    traci.start(sumo_cmd)

except Exception as e:
    print(f"Error when starting SUMO: {e}")
    sys.exit()

#  Run simulation and extract data
step = 0
max_steps = 5000

while step < max_steps:
    traci.simulationStep()  # simulation step
    traffic_light_ids = traci.trafficlight.getIDList() 
    print(f"IDclears de semáforos disponibles: {traffic_light_ids}")
    
    # extract vehicle position
    vehicle_ids = traci.vehicle.getIDList()

    if not vehicle_ids: 
        print(f"Step: {step}, No cars in simulation")
    else:
        for veh_id in vehicle_ids:
            position = traci.vehicle.getPosition(veh_id)
            speed = traci.vehicle.getSpeed(veh_id)

    step += 1

# close connexion
traci.close()

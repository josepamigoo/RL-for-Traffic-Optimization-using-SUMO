import traci
import sumolib
import sys
import os
import configparser
from sumolib import checkBinary

gui="False"
sumocfg_file_name="sumo_config.sumocfg"
max_steps=1000

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
# Iniciar SUMO amx arxiu de configuració
try:
    traci.start(sumo_cmd)

except Exception as e:
    print(f"Error al iniciar SUMO: {e}")
    sys.exit()

# Ejecutar la simulació i extreure dades
step = 0
max_steps = 5000

while step < max_steps:
    traci.simulationStep()  # Avança la simulació
    traffic_light_ids = traci.trafficlight.getIDList() 
    print(f"IDclears de semáforos disponibles: {traffic_light_ids}")

    current_state = traci.trafficlight.getRedYellowGreenState(
        traffic_light_ids[1])
    
    print(f"Estat del semàfor: {current_state}")
    current_state = traci.trafficlight.getRedYellowGreenState(
        traffic_light_ids[1])
    print(f"Estat del semàfor: {current_state}" )
    
    # Extreure dades: posició dels vehícles
    vehicle_ids = traci.vehicle.getIDList()

    if not vehicle_ids:  # Si no hi ha vehículos, imprimir missatge
        print(f"Step: {step}, No hi ha vehícules en la simulació.")
    else:
        for veh_id in vehicle_ids:
            position = traci.vehicle.getPosition(veh_id)
            speed = traci.vehicle.getSpeed(veh_id)
            #print(f"Step: {step}, Vehicle: {veh_id},Position: {position}, Speed: {speed}")

    step += 1

# tancar la connexió
traci.close()

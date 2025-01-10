
import clr
clr.AddReference("MissionPlanner")
import MissionPlanner

def get_altitude():
    altitude = cs.alt
    print("Current Altitude:", altitude)
    return altitude

while True:
    altitude = get_altitude()

    Script.Sleep(1000)
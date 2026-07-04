import clr
import json
clr.AddReference("System")
clr.AddReference("System.IO")
clr.AddReference("MissionPlanner")
import MissionPlanner
from System import IO, Text
from System.Net import HttpWebRequest, WebResponse

def post_request(url, data):
    request = HttpWebRequest.Create(url)
    request.Method = "POST"
    request.ContentType = "application/json"
    print("ini data kirim",data)
    
    json_data = json.dumps(data)    
    byte_data = Text.Encoding.UTF8.GetBytes(json_data)
    
    request.ContentLength = byte_data.Length
    request_stream = request.GetRequestStream()
    request_stream.Write(byte_data, 0, byte_data.Length)
    request_stream.Close()
    
    response = request.GetResponse()
    response_stream = response.GetResponseStream()
    
    reader = IO.StreamReader(response_stream)
    response_text = reader.ReadToEnd()
    
    reader.Close()
    response.Close()
    
    return response_text

def get_request(url):
    request = HttpWebRequest.Create(url)
    request.Method = "GET"
    request.ContentType = "application/json"    
    
    response = request.GetResponse()
    response_stream = response.GetResponseStream()
    
    reader = IO.StreamReader(response_stream)
    response_text = reader.ReadToEnd()
    
    reader.Close()
    response.Close()
    
    return response_text

def fly(altitude, latitude, longitude):
    """
    Fungsi untuk memindahkan drone ke titik koordinat tertentu
    Args:
        altitude: ketinggian dalam meter
        latitude: garis lintang dalam derajat
        longitude: garis bujur dalam derajat
    """
    try:
        altitude = float(altitude)
        latitude = float(latitude)
        longitude = float(longitude)

        # Pastikan drone dalam mode GUIDED
        Script.ChangeMode("GUIDED")
        
        # Tunggu sampai mode berubah
        while cs.mode != "GUIDED":
            print("Menunggu mode GUIDED...")
            Script.Sleep(1000)
        
        # Perintah untuk terbang ke titik yang ditentukan
        item = MissionPlanner.Utilities.Locationwp()
        MissionPlanner.Utilities.Locationwp.lat.SetValue(item, float(latitude))
        MissionPlanner.Utilities.Locationwp.lng.SetValue(item, float(longitude))
        MissionPlanner.Utilities.Locationwp.alt.SetValue(item, float(altitude))
        
        # Kirim perintah ke drone
        MAV.setGuidedModeWP(item)
        
        print(f"Terbang ke koordinat: LAT={latitude}, LON={longitude}, ALT={altitude}m")
        
        # Monitor progress
        while True:
            # Hitung jarak ke target
            current_lat = cs.lat
            current_lon = cs.lng
            current_alt = cs.alt
            
            # Hitung jarak horizontal ke target (dalam meter)
            dist_to_target = MissionPlanner.Utilities.Coords.GetDistance(
                current_lat, current_lon,
                latitude, longitude
            )
            
            # Hitung selisih ketinggian
            alt_diff = abs(current_alt - altitude)
            
            print(f"Jarak ke target: {dist_to_target:.1f}m, Selisih ketinggian: {alt_diff:.1f}m")
            
            # Cek apakah sudah sampai (dalam radius 1 meter)
            if dist_to_target < 1 and alt_diff < 1:
                print("Sampai di titik target!")
                break
                
            Script.Sleep(1000)  # Update setiap 1 detik
            
    except Exception as e:
        print(f"Error: {e}")
        return False
        
    return True

def arm_drone():
    try:
        MAV.doARM(True)
        print("Drone armed")
        return True
    except Exception as e:
        print(f"Failed to arm drone: {e}")
        return False

def disarm_drone():
    try:
        MAV.doARM(False)
        print("Drone disarmed")
        return True
    except Exception as e:
        print(f"Failed to disarm drone: {e}")
        return False

def test_motor(motor_number, power):
    try:
        # MAV_CMD_DO_MOTOR_TEST = 209
        # params: motor, throttle type, throttle %, timeout, motor count, test order, empty
        MAV.doCommand(209, int(motor_number), 0, float(power), 3, 0, 0, 0)
        print(f"Testing motor {motor_number} at {power}%")
        return True
    except Exception as e:
        print(f"Failed to test motor {motor_number}: {e}")
        return False

def fetch_command():
    try:
        response_text = get_request(urlget)
        data = json.loads(response_text)
        return data.get("command")
    except Exception as e:
        print(f"Failed to fetch command: {e}")
        return None

def execute_command(command):
    if not command:
        return

    command = command.strip()
    print(f"Received command: {command}")

    alias_commands = {
        "cw1": "testmotor,1,15",
        "ccw1": "testmotor,2,15",
        "ccw2": "testmotor,3,15",
        "cw2": "testmotor,4,15",
    }
    command = alias_commands.get(command, command)

    parts = [part.strip() for part in command.split(",")]
    command_name = parts[0].lower()

    if command_name == "arm":
        arm_drone()
    elif command_name == "disarm":
        disarm_drone()
    elif command_name == "testmotor" and len(parts) == 3:
        test_motor(parts[1], parts[2])
    elif command_name == "goto" and len(parts) == 4:
        fly(parts[1], parts[2], parts[3])
    else:
        print(f"Unknown command: {command}")

urlpost = "http://127.0.0.1:5000/data"
urlget = "http://127.0.0.1:5000/command"
while True:
    current_altitude = str(cs.alt)
    current_latitude = str(cs.lat)
    current_longitude = str(cs.lng)
    current_roll = str(cs.roll)        
    current_groundspeed = str(cs.groundspeed) 
    current_verticalspeed = str(cs.verticalspeed) # verticalspeed dari index 5
    current_yaw = str(cs.yaw)         # yaw dari index 6
    current_satcount = str(cs.satcount)    # satcount dari index 7
    current_wp_dist = str(cs.wp_dist)  
    data = {
    'altitude': current_altitude,
    'latitude': current_latitude,
    'longitude': current_longitude,
    'roll': current_roll,
    'groundspeed': current_groundspeed,
    'verticalspeed': current_verticalspeed,
    'yaw': current_yaw,
    'satcount': current_satcount,
    'wp_dist': current_wp_dist
}

    response_text = post_request(urlpost, data)
    command = fetch_command()
    execute_command(command)
    Script.Sleep(1000)
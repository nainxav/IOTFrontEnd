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
    # command = get_request(urlget)    
    Script.Sleep(1000)
import json
import math

import clr

clr.AddReference("System")
clr.AddReference("System.IO")
clr.AddReference("MissionPlanner")
clr.AddReference("MAVLink")

import MissionPlanner
from MAVLink import MAV_CMD
from System import IO, Text
from System.Net import HttpWebRequest, WebResponse

EARTH_RADIUS_M = 6378137.0


def post_request(url, data):
    request = HttpWebRequest.Create(url)
    request.Method = "POST"
    request.ContentType = "application/json"
    print("ini data kirim", data)

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


def resolve_mav_cmd(names, fallback_value):
    """Resolve a MAV_CMD enum member across differing MAVLink binding naming
    conventions (some keep the full MAV_CMD_ prefix, some strip it).

    Tries each name in `names` as an attribute of MAV_CMD, and if none exist,
    falls back to casting the raw integer command id into the MAV_CMD enum
    type (works for .NET enums under IronPython).
    """
    for name in names:
        if hasattr(MAV_CMD, name):
            return getattr(MAV_CMD, name)
    return MAV_CMD(fallback_value)


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

        if not ensure_guided_mode():
            print("Gagal masuk mode GUIDED, batalkan fly()")
            return False

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
            if check_cancel():
                print("Perintah goto/followtarget dibatalkan oleh pengguna.")
                return False

            # Hitung jarak ke target
            current_lat = cs.lat
            current_lon = cs.lng
            current_alt = cs.alt

            # Hitung jarak horizontal ke target (dalam meter)
            dist_to_target = MissionPlanner.Utilities.Coords.GetDistance(
                current_lat, current_lon, latitude, longitude
            )

            # Hitung selisih ketinggian
            alt_diff = abs(current_alt - altitude)

            print(
                f"Jarak ke target: {dist_to_target:.1f}m, Selisih ketinggian: {alt_diff:.1f}m"
            )

            # Cek apakah sudah sampai (dalam radius 1 meter)
            if dist_to_target < 1 and alt_diff < 1:
                print("Sampai di titik target!")
                break

            Script.Sleep(1000)  # Update setiap 1 detik

    except Exception as e:
        print(f"Error: {e}")
        return False

    return True


def offset_latlon(lat, lon, north_m, east_m):
    """Offset a lat/lon point by north_m/east_m meters (equirectangular approx)."""
    d_lat = north_m / EARTH_RADIUS_M
    d_lon = east_m / (EARTH_RADIUS_M * math.cos(math.pi * lat / 180.0))
    new_lat = lat + (d_lat * 180.0 / math.pi)
    new_lon = lon + (d_lon * 180.0 / math.pi)
    return new_lat, new_lon


def move_relative(x, y, z):
    """Move relative to the drone's current position/heading (body-frame).

    x: forward distance in meters (along current heading), + = forward
    y: right distance in meters (perpendicular to heading), + = right
    z: altitude change in meters, + = up
    """
    try:
        x = float(x)
        y = float(y)
        z = float(z)

        if not ensure_guided_mode():
            print("Gagal masuk mode GUIDED, batalkan forward")
            return False

        current_lat = cs.lat
        current_lon = cs.lng
        current_alt = cs.alt
        heading_rad = math.radians(cs.yaw)

        # Rotate body-frame (x=forward, y=right) into earth-frame (north, east)
        north = x * math.cos(heading_rad) - y * math.sin(heading_rad)
        east = x * math.sin(heading_rad) + y * math.cos(heading_rad)

        new_lat, new_lon = offset_latlon(current_lat, current_lon, north, east)
        new_alt = current_alt + z

        item = MissionPlanner.Utilities.Locationwp()
        MissionPlanner.Utilities.Locationwp.lat.SetValue(item, new_lat)
        MissionPlanner.Utilities.Locationwp.lng.SetValue(item, new_lon)
        MissionPlanner.Utilities.Locationwp.alt.SetValue(item, new_alt)

        MAV.setGuidedModeWP(item)

        print(
            f"Bergerak relatif: forward={x}m right={y}m alt_change={z}m -> "
            f"LAT={new_lat}, LON={new_lon}, ALT={new_alt}m"
        )
        return True
    except Exception as e:
        print(f"Failed forward move: {e}")
        return False


def ensure_guided_mode(timeout_s=10):
    """Try to switch to GUIDED mode, waiting up to timeout_s seconds.

    Returns True if GUIDED mode was reached, False otherwise (e.g. vehicle
    refuses GUIDED because it isn't armed/has no GPS fix/etc).
    """
    Script.ChangeMode("GUIDED")

    waited = 0
    while cs.mode.upper() != "GUIDED":
        if check_cancel():
            print("Dibatalkan oleh pengguna saat menunggu mode GUIDED.")
            return False
        print("Menunggu mode GUIDED...")
        Script.Sleep(1000)
        waited += 1
        if waited >= timeout_s:
            print(
                f"Timeout menunggu mode GUIDED setelah {timeout_s}s (mode saat ini: {cs.mode})"
            )
            return False

    return True


def takeoff_drone(altitude):
    try:
        altitude = float(altitude)

        if not cs.armed:
            if not arm_drone():
                print("Gagal arm drone, batalkan takeoff")
                return False

        if not ensure_guided_mode():
            print("Gagal masuk mode GUIDED, batalkan takeoff")
            return False

        takeoff_cmd = resolve_mav_cmd(["NAV_TAKEOFF", "MAV_CMD_NAV_TAKEOFF"], 22)
        MAV.doCommand(takeoff_cmd, 0, 0, 0, 0, 0, 0, altitude)
        print(f"Takeoff ke ketinggian {altitude}m")
        return True
    except Exception as e:
        print(f"Failed to takeoff: {e}")
        return False


def land_drone():
    try:
        Script.ChangeMode("LAND")
        print("Drone landing")
        return True
    except Exception as e:
        print(f"Failed to land drone: {e}")
        return False


def rtl_drone():
    try:
        Script.ChangeMode("RTL")
        print("Drone returning to launch")
        return True
    except Exception as e:
        print(f"Failed to RTL drone: {e}")
        return False


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
        # params: motor, throttle type, throttle %, timeout, motor count, test order, empty
        motor_test_cmd = resolve_mav_cmd(
            ["DO_MOTOR_TEST", "MAV_CMD_DO_MOTOR_TEST"], 209
        )
        MAV.doCommand(motor_test_cmd, int(motor_number), 0, float(power), 3, 0, 0, 0)
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


def check_cancel():
    """Poll the server's cancel flag. Returns True if a cancel was requested.

    The server clears the flag once it's read, so this should only be
    called from inside blocking wait loops (ensure_guided_mode, fly) to
    detect a user-triggered cancel/reset.
    """
    try:
        response_text = get_request(urlcancel)
        data = json.loads(response_text)
        return bool(data.get("cancel"))
    except Exception as e:
        print(f"Failed to check cancel flag: {e}")
        return False


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
    elif command_name == "followtarget" and len(parts) == 4:
        fly(parts[1], parts[2], parts[3])
    elif command_name == "takeoff" and len(parts) == 2:
        takeoff_drone(parts[1])
    elif command_name == "land":
        land_drone()
    elif command_name == "rtl":
        rtl_drone()
    elif command_name == "forward" and len(parts) == 2:
        move_relative(parts[1], 0, 0)
    elif command_name == "forward" and len(parts) == 4:
        move_relative(parts[1], parts[2], parts[3])
    else:
        print(f"Unknown command: {command}")


urlpost = "http://127.0.0.1:5000/data"
urlget = "http://127.0.0.1:5000/command"
urlcancel = "http://127.0.0.1:5000/command/cancel"
while True:
    current_altitude = str(cs.alt)
    current_latitude = str(cs.lat)
    current_longitude = str(cs.lng)
    current_roll = str(cs.roll)
    current_groundspeed = str(cs.groundspeed)
    current_verticalspeed = str(cs.verticalspeed)  # verticalspeed dari index 5
    current_yaw = str(cs.yaw)  # yaw dari index 6
    current_satcount = str(cs.satcount)  # satcount dari index 7
    current_wp_dist = str(cs.wp_dist)
    data = {
        "altitude": current_altitude,
        "latitude": current_latitude,
        "longitude": current_longitude,
        "roll": current_roll,
        "groundspeed": current_groundspeed,
        "verticalspeed": current_verticalspeed,
        "yaw": current_yaw,
        "satcount": current_satcount,
        "wp_dist": current_wp_dist,
    }

    response_text = post_request(urlpost, data)
    command = fetch_command()
    execute_command(command)
    Script.Sleep(1000)

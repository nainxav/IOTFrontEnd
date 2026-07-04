"""
Control-focused server for drone telemetry and commands.

- Flask REST API for telemetry (/data), recent telemetry (/recent), follow target (/follow), and commands (/command)
- MySQL initialization and insertion
- Command validation for arm/disarm/land/rtl/takeoff/goto/followtarget/testmotor/forward

Dependencies:
- flask, flask_cors
- mysql-connector-python

Usage:
- Ensure MySQL server is running or adjust DB_CONFIG
- Run: python serverWithForwardV2.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import mysql.connector
import threading
import logging

# Try to import MissionPlanner / MAVLink for command execution (optional)
try:
    import clr
    clr.AddReference("MissionPlanner")
    clr.AddReference("MAVLink")
    from MAVLink import MAV_CMD
    import MissionPlanner
    HAS_MISSIONPLANNER = True
except Exception:
    HAS_MISSIONPLANNER = False

# ============================================================
# CONFIG
# ============================================================
DB_CONFIG = {"host": "localhost", "user": "root", "password": "", "database": "drone"}

# Command safety limits (tuned for indoor test scale)
MAX_COMMAND_LENGTH = 120
FORWARD_XY_LIMIT = 20.0
FORWARD_Z_LIMIT = 10.0

# ============================================================
# LOGGER
# ============================================================
logger = logging.getLogger("follow_logger")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("follow.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# ============================================================
# DATABASE HELPERS
# ============================================================

def initiate_database():
    try:
        conn = mysql.connector.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'])
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS drone")
        cursor.execute("USE drone")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drone_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                altitude FLOAT,
                latitude FLOAT,
                longitude FLOAT,
                roll FLOAT,
                groundspeed FLOAT,
                verticalspeed FLOAT,
                yaw FLOAT,
                satcount INT,
                wp_dist FLOAT
            )
        """)
        logger.info("Database initialized")
    except Exception as e:
        logger.exception("Failed to init database: %s", e)
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


def connect_database():
    return mysql.connector.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'], database=DB_CONFIG['database'])

# ============================================================
# FLASK APP + ROUTES
# ============================================================

app = Flask(__name__)
CORS(app)

current_command = {"command": ""}
command_lock = threading.Lock()

droneData = {'altitude': None, 'latitude': None, 'longitude': None,
             'roll': None, 'groundspeed': None, 'verticalspeed': None,
             'yaw': None, 'satcount': None, 'wp_dist': None}


@app.route("/command/schema", methods=["GET"])
def command_schema():
    """Expose command formats/ranges so client can validate before sending."""
    return jsonify({
        "supported_commands": {
            "arm": "arm",
            "disarm": "disarm",
            "land": "land",
            "rtl": "rtl",
            "takeoff": "takeoff,<altitude_m>",
            "goto": "goto,<altitude_m>,<latitude>,<longitude>",
            "followtarget": "followtarget,<altitude_m>,<latitude>,<longitude>",
            "testmotor": "testmotor,<motor_number_1_to_8>,<throttle_0_to_100>",
            "forward_distance": "forward,<meters_forward_from_current_heading>",
            "forward_vector": "forward,<x_m>,<y_m>,<z_m>"
        },
        "limits": {
            "forward": {"x_min": -20, "x_max": 20, "y_min": -20, "y_max": 20, "z_min": -10, "z_max": 10},
            "takeoff_altitude_min": 0,
            "testmotor_throttle_min": 0,
            "testmotor_throttle_max": 100
        }
    }), 200



@app.route('/data', methods=['GET', 'POST'])
def data_route():
    global droneData

    if request.method == 'GET':
        try:
            conn = connect_database()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM drone_data")
            rows = cursor.fetchall()
            return jsonify(rows), 200
        except Exception as e:
            logger.exception("/data GET error: %s", e)
            return jsonify({'error': str(e)}), 500
        finally:
            try:
                cursor.close(); conn.close()
            except Exception:
                pass

    # POST
    try:
        data = request.get_json(force=True)
        droneData.update(data)

        # Insert to DB (convert strings to floats when possible)
        conn = connect_database()
        cursor = conn.cursor()

        insert_query = (
            "INSERT INTO drone_data "
            "(altitude, latitude, longitude, roll, groundspeed, verticalspeed, yaw, satcount, wp_dist, timestamp) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        )

        def _to_float(v):
            try:
                return float(v) if v not in (None, "", "None") else None
            except Exception:
                return None

        data_tuple = (
            _to_float(data.get('altitude')),
            _to_float(data.get('latitude')),
            _to_float(data.get('longitude')),
            _to_float(data.get('roll')),
            _to_float(data.get('groundspeed')),
            _to_float(data.get('verticalspeed')),
            _to_float(data.get('yaw')),
            int(float(data.get('satcount'))) if data.get('satcount') not in (None, "", "None") else None,
            _to_float(data.get('wp_dist')),
            datetime.now()
        )

        cursor.execute(insert_query, data_tuple)
        conn.commit()

        return jsonify({
            'message': 'Data saved'
        }), 200

    except Exception as e:
        logger.exception("/data POST error: %s", e)
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except Exception:
            pass

@app.route('/recent', methods=['GET'])
def recent_route():
    try:
        conn = connect_database()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM drone_data ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return jsonify({'data': row}), 200
        else:
            return jsonify({'data': None}), 404
    except Exception as e:
        logger.exception("/recent error: %s", e)
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            cursor.close(); conn.close()
        except Exception:
            pass


@app.route('/follow', methods=['GET', 'POST'])
def follow_route():
    global target
    if request.method == 'GET':
        if target.get('latitude') is not None and target.get('longitude') is not None:
            return jsonify({'target': target}), 200
        return jsonify({'message': 'no target'}), 404

    # POST
    data = request.get_json()
    if not all(k in data for k in ('altitude', 'latitude', 'longitude')):
        return jsonify({'error': 'missing params'}), 400
    target.update(data)
    logger.info("New follow target: %s", target)
    return jsonify({'message': 'target updated', 'target': target}), 200


@app.route('/command', methods=['GET', 'POST'])
def command_route():
    global current_command
    if request.method == 'GET':
        with command_lock:
            return jsonify(current_command)

    # POST
    try:
        payload = request.json
        if not payload or 'command' not in payload:
            return jsonify({'error': 'invalid format'}), 400
        
        command = payload['command'].lower().strip()
        if not command:
            return jsonify({"error": "command cannot be empty"}), 400
        if len(command) > MAX_COMMAND_LENGTH:
            return jsonify({"error": f"command too long (max {MAX_COMMAND_LENGTH})"}), 400

        if command.startswith('testmotor'):
            parts = command.split(',')
            if len(parts) != 3:
                return jsonify({"error": "Invalid testmotor command format"}), 400
            try:                    
                motor_num = int(parts[1])
                throttle = float(parts[2])
                if not (1 <= motor_num <= 8 and 0 <= throttle <= 100):
                    return jsonify({"error": "Invalid motor number or throttle value"}), 400
            except ValueError:
                return jsonify({"error": "Invalid testmotor parameters"}), 400
        
        elif command.startswith('forward'):
            parts = command.split(',')
            try:
                # Support both:
                # - forward,10      -> move +X 10m from current heading
                # - forward,x,y,z   -> local/body-style vector move in meters
                if len(parts) == 2:
                    x = float(parts[1])
                    y = 0.0
                    z = 0.0
                elif len(parts) == 4:
                    x = float(parts[1])
                    y = float(parts[2])
                    z = float(parts[3])
                else:
                    return jsonify({"error": "Invalid forward command format. Use forward,<distance> or forward,<x>,<y>,<z>"}), 400

                if not (-FORWARD_XY_LIMIT <= x <= FORWARD_XY_LIMIT and
                        -FORWARD_XY_LIMIT <= y <= FORWARD_XY_LIMIT and
                        -FORWARD_Z_LIMIT <= z <= FORWARD_Z_LIMIT):
                    return jsonify({"error": f"Invalid forward value. Allowed: x/y in [-{FORWARD_XY_LIMIT}, {FORWARD_XY_LIMIT}], z in [-{FORWARD_Z_LIMIT}, {FORWARD_Z_LIMIT}]"}), 400
            except ValueError:
                return jsonify({"error": "Invalid forward parameters"}), 400
            
        elif command.startswith('goto'):
            parts = command.split(',')
            if len(parts) != 4:
                return jsonify({"error": "Invalid followtarget command format"}), 400
            try:
                altitude = float(parts[1])
                latitude = float(parts[2])
                longitude = float(parts[3])
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and 0 <= altitude <= 200):
                    return jsonify({"error": "Invalid GPS or altitude values"}), 400
            except ValueError:
                return jsonify({"error": "Invalid followtarget parameters"}), 400
            
        elif command.startswith('followtarget'):
            parts = command.split(',')
            if len(parts) != 4:
                return jsonify({"error": "Invalid followtarget command format"}), 400
            try:
                altitude = float(parts[1])
                latitude = float(parts[2])
                longitude = float(parts[3])
                if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and 0 <= altitude <= 200):
                    return jsonify({"error": "Invalid GPS or altitude values"}), 400
            except ValueError:
                return jsonify({"error": "Invalid followtarget parameters"}), 400

        elif command.startswith('takeoff'):
            parts = command.split(',')
            if len(parts) != 2:
                return jsonify({"error": "Invalid takeoff command format"}), 400
            try:
                altitude = float(parts[1])
                if not (1 <= altitude <= 100):
                    return jsonify({"error": "Invalid takeoff altitude. Allowed 1..100m"}), 400
            except ValueError:
                return jsonify({"error": "Invalid takeoff parameters"}), 400

        elif command in ('arm', 'disarm', 'land', 'rtl'):
            pass
        else:
            return jsonify({"error": "Unsupported command"}), 400

        # # Basic validation for complex commands (testmotor,goto,followtarget)
        # if cmd.startswith('testmotor'):
        #     parts = cmd.split(',')
        #     if len(parts) != 3:
        #         return jsonify({'error': 'invalid testmotor format'}), 400
        # elif cmd.startswith('goto') or cmd.startswith('followtarget'):
        #     parts = cmd.split(',')
        #     if len(parts) != 4:
        #         return jsonify({'error': 'invalid goto/followtarget format'}), 400
        #     try:
        #         float(parts[1]); float(parts[2]); float(parts[3])
        #     except Exception:
        #         return jsonify({'error': 'invalid numeric parameters'}), 400

        with command_lock:
            current_command = payload

        return jsonify({'message': 'command updated', 'command': command}), 200

    except Exception as e:
        logger.exception("/command error: %s", e)
        return jsonify({'error': str(e)}), 500


# ============================================================
# COMMAND EXECUTOR (optional MissionPlanner integration)
# ============================================================

def execute_command_on_vehicle(command_str):
    """Execute command on vehicle. If MissionPlanner not available, we log only."""
    logger.info("Executing command: %s", command_str)
    if not HAS_MISSIONPLANNER:
        logger.warning("MissionPlanner not available; skipping actual execution")
        return False

    # Minimal example: parse and call relevant MissionPlanner functions
    try:
        cmd = command_str.lower().strip()
        if cmd == 'arm':
            # Example: this depends on your MissionPlanner environment
            MAV.doARM(True)
            return True
        if cmd == 'disarm':
            MAV.doARM(False)
            return True
        if cmd.startswith('takeoff'):
            parts = cmd.split(',')
            if len(parts) == 2:
                alt = float(parts[1])
                MAV.doCommand(MAV_CMD.TAKEOFF, 0, 0, 0, 0, 0, 0, alt)
                return True
        if cmd.startswith('goto') or cmd.startswith('followtarget'):
            parts = cmd.split(',')
            if len(parts) == 4:
                alt = float(parts[1]); lat = float(parts[2]); lon = float(parts[3])
                # Implement your flight function here (fly/fly2)
                logger.info("(MissionPlanner) would fly to: %s", (lat, lon, alt))
                return True
        # Add more handlers as needed
    except Exception as e:
        logger.exception("Failed to execute on vehicle: %s", e)
        return False

    return False

# ============================================================
# MAIN
# ============================================================

target = {'altitude': None, 'latitude': None, 'longitude': None}

if __name__ == '__main__':
    # Initialize DB
    initiate_database()

    # Run Flask
    app.run(host='0.0.0.0', port=5000)

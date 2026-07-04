from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)

# bagian sini samain sama mySQL anata ya aibou
dbconfig = {"host": "localhost", "user":"root", "password":""}

droneData = {'altitude':None, 'latitude':None, 'longitude':None, 
             "roll":None,"groundspeed":None,"verticalspeed":None,"yaw":None,
             "satcount":None,"wp_dist":None}

def initiateDatabase():
    try:        
        conn = mysql.connector.connect(
            host=dbconfig["host"],
            user=dbconfig["user"],
            password=dbconfig['password']
        )
        cursor = conn.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS drone")
                
        cursor.execute("USE drone")
                
        query = """
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
        """
        cursor.execute(query)

        print("berhasil anjai")        
        
    except mysql.connector.Error as err:
        print(err)
        
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def connectDatabase():
    return mysql.connector.connect(
        host=dbconfig['host'],
        user=dbconfig['user'],
        password=dbconfig['password'],
        database='drone'
    )

@app.route('/data', methods=['GET','POST'])
def get_altitude():    
    global droneData
    if request.method == 'GET':
        try:
            conn = connectDatabase()        
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM drone_data"
            cursor.execute(query)
            data = cursor.fetchall()
            print(data)
            return data
        except mysql.connector.errors as e:
            print(e)
        except Exception as e:
            print(e)
    elif request.method == "POST":
        try:            
            data = request.get_json()                                
            conn = connectDatabase()
            cursor = conn.cursor()                        
            insert_query = """
                INSERT INTO drone_data 
                (altitude, latitude, longitude, roll, groundspeed, 
                verticalspeed, yaw, satcount, wp_dist)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Data yang akan diinsert
            data_tuple = (                
                data.get('altitude'),
                data.get('latitude'),
                data.get('longitude'),
                data.get('roll'),
                data.get('groundspeed'),
                data.get('verticalspeed'),
                data.get('yaw'),
                data.get('satcount'),
                data.get('wp_dist')
            )
                        
            cursor.execute(insert_query, data_tuple)
                        
            conn.commit()
                        
            droneData.update(data)

            cursor.close()
            conn.close()
            
            return jsonify({
                'message': 'Data successfully saved',                
                'data': data
            }), 200
            
        except mysql.connector.Error as e:
            return jsonify({
                'error': f'Database error: {str(e)}'
            }), 500
            
        except Exception as e:
            return jsonify({
                'error': f'Error: {str(e)}'
            }), 500
            


target = {'altitude':None, 'latitude':None, 'longitude':None}
commands = []

def get_request_command():
    data = request.get_json(silent=True) or {}
    command_value = data.get('command') or request.form.get('command')
    if command_value:
        return command_value.strip()

    altitude = request.form.get("altitude") or data.get("altitude")
    latitude = request.form.get("latitude") or data.get("latitude")
    longitude = request.form.get("longitude") or data.get("longitude")
    if altitude and latitude and longitude:
        return f"goto,{altitude},{latitude},{longitude}"

    return None

def changedata(data):
    global droneData
    if 'altitude' in data:
        altitude = data['altitude']
        return jsonify({'altitude': altitude}), 200
    else:
        return jsonify({'error': 'No altitude provided'}), 400

@app.route('/changealt', methods=['POST'])
def changealt():   
    global droneData 
    data = request.get_json()
    # if 'altitude' in data:
    #     altitude = data['altitude']
    #     return jsonify({'altitude': altitude}), 200
    # else:
    #     return jsonify({'error': 'No altitude provided'}), 400
    if 'altitude' and 'latitude' and 'longitude' in data:
        droneData = data
        return jsonify(droneData), 200
    else:
        return jsonify({'error': 'No altitude provided'}), 400
    
@app.route('/command', methods=['GET','POST'])
def command():
    global commands
    if request.method == 'GET':
        if commands:
            return jsonify({'command': commands.pop(0), 'remaining': len(commands)}), 200
        return jsonify({'command': None, 'remaining': 0}), 200
    elif request.method == 'POST':   
        command_value = get_request_command()
        if not command_value:
            return jsonify({'error': 'No command provided'}), 400

        commands.append(command_value)
        return jsonify({'message': 'Command queued', 'command': command_value, 'remaining': len(commands)}), 200

if __name__ == '__main__':
    initiateDatabase()
    app.run(host="0.0.0.0",debug=True)
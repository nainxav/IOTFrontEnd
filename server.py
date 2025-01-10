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
        pass
    elif request.method == 'POST':   
        altitude = request.form.get("altitude") if request.form.get("altitude") else None
        latitude = request.form.get("latitude") if request.form.get("latitude") else None
        longitude = request.form.get("longitude") if request.form.get("longitude") else None
        commands.append({'altitude':altitude, 'latitude':latitude, 'longitude':longitude})
        return 200

if __name__ == '__main__':
    initiateDatabase()
    app.run(host="0.0.0.0",debug=True)
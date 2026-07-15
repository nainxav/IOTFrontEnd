import json
import sys
import urllib.error
import urllib.request
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

DEFAULT_SERVER_URL = "http://127.0.0.1:5000"


class DroneApiClient:
    def __init__(self, server_url):
        self.server_url = server_url.rstrip("/")

    def get_data(self):
        return self._request("GET", "/data")

    def get_recent(self):
        return self._request("GET", "/recent")

    def send_command(self, command):
        return self._request("POST", "/command", {"command": command})

    def cancel_command(self):
        return self._request("POST", "/command/cancel", {})

    def _request(self, method, path, payload=None):
        url = f"{self.server_url}{path}"
        body = None
        headers = {}

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                response_body = response.read().decode("utf-8")
                if not response_body:
                    return {}
                return json.loads(response_body)
        except urllib.error.HTTPError as error:
            message = error.read().decode("utf-8") or str(error)
            raise RuntimeError(message) from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"Cannot connect to {url}: {error.reason}") from error


class DroneControlWindow(QMainWindow):
    telemetry_fields = [
        "altitude",
        "latitude",
        "longitude",
        "roll",
        "groundspeed",
        "verticalspeed",
        "yaw",
        "satcount",
        "wp_dist",
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone Control System")
        self.resize(1050, 760)

        self.server_input = QLineEdit(DEFAULT_SERVER_URL)
        self.telemetry_labels = {}
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(3000)
        self.poll_timer.timeout.connect(self.refresh_telemetry)

        self._build_ui()
        self.poll_timer.start()
        self.refresh_telemetry()

    @property
    def api(self):
        return DroneApiClient(self.server_input.text().strip() or DEFAULT_SERVER_URL)

    def _build_ui(self):
        root = QWidget()
        layout = QVBoxLayout(root)

        layout.addWidget(self._build_connection_panel())

        content_layout = QHBoxLayout()
        content_layout.addWidget(self._build_control_panel(), 2)
        content_layout.addWidget(self._build_telemetry_panel(), 1)
        layout.addLayout(content_layout)

        layout.addWidget(self._build_log_panel())

        self.setCentralWidget(root)

    def _build_connection_panel(self):
        group = QGroupBox("Server")
        layout = QHBoxLayout(group)

        refresh_button = QPushButton("Refresh Telemetry")
        refresh_button.clicked.connect(self.refresh_telemetry)

        layout.addWidget(QLabel("Backend URL:"))
        layout.addWidget(self.server_input, 1)
        layout.addWidget(refresh_button)

        return group

    def _build_control_panel(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)

        arm_layout = QHBoxLayout()
        arm_button = QPushButton("ARM")
        arm_button.setStyleSheet(
            "font-weight: bold; color: white; background-color: #16a34a; padding: 10px;"
        )
        arm_button.clicked.connect(lambda: self.send_command("arm"))

        disarm_button = QPushButton("DISARM")
        disarm_button.setStyleSheet(
            "font-weight: bold; color: white; background-color: #dc2626; padding: 10px;"
        )
        disarm_button.clicked.connect(lambda: self.send_command("disarm"))

        arm_layout.addWidget(arm_button)
        arm_layout.addWidget(disarm_button)
        layout.addLayout(arm_layout)

        cancel_button = QPushButton("CANCEL / RESET COMMAND")
        cancel_button.setStyleSheet(
            "font-weight: bold; color: white; background-color: #ea580c; padding: 10px;"
        )
        cancel_button.clicked.connect(self.send_cancel)
        layout.addWidget(cancel_button)

        mode_layout = QHBoxLayout()
        land_button = QPushButton("LAND")
        land_button.setStyleSheet("font-weight: bold; padding: 10px;")
        land_button.clicked.connect(lambda: self.send_command("land"))

        rtl_button = QPushButton("RTL")
        rtl_button.setStyleSheet("font-weight: bold; padding: 10px;")
        rtl_button.clicked.connect(lambda: self.send_command("rtl"))

        mode_layout.addWidget(land_button)
        mode_layout.addWidget(rtl_button)
        layout.addLayout(mode_layout)

        layout.addWidget(self._build_takeoff_panel())
        layout.addWidget(self._build_motor_panel())
        layout.addWidget(self._build_waypoint_panel())
        layout.addWidget(self._build_follow_target_panel())
        layout.addWidget(self._build_forward_panel())
        layout.addWidget(self._build_manual_control_panel())
        layout.addStretch()

        scroll.setWidget(container)
        return scroll

    def _build_takeoff_panel(self):
        group = QGroupBox("Takeoff")
        layout = QHBoxLayout(group)

        self.takeoff_altitude = QDoubleSpinBox()
        self.takeoff_altitude.setRange(0.1, 100)
        self.takeoff_altitude.setDecimals(2)
        self.takeoff_altitude.setSingleStep(0.1)
        self.takeoff_altitude.setSuffix(" m")
        self.takeoff_altitude.setValue(10)

        button = QPushButton("TAKEOFF")
        button.clicked.connect(self.send_takeoff)

        layout.addWidget(QLabel("Altitude:"))
        layout.addWidget(self.takeoff_altitude)
        layout.addWidget(button)

        return group

    def _build_motor_panel(self):
        group = QGroupBox("Motor Test")
        layout = QVBoxLayout(group)

        power_layout = QHBoxLayout()
        self.motor_power = QSpinBox()
        self.motor_power.setRange(1, 100)
        self.motor_power.setValue(15)
        self.motor_power.setSuffix("%")
        power_layout.addWidget(QLabel("Power:"))
        power_layout.addWidget(self.motor_power)
        power_layout.addStretch()
        layout.addLayout(power_layout)

        motor_grid = QGridLayout()
        for index in range(1, 9):
            button = QPushButton(f"Test Motor {index}")
            button.clicked.connect(lambda _, motor=index: self.send_motor_test(motor))
            motor_grid.addWidget(button, (index - 1) // 4, (index - 1) % 4)
        layout.addLayout(motor_grid)

        return group

    def _build_waypoint_panel(self):
        group = QGroupBox("GPS Waypoint")
        form = QFormLayout(group)

        self.latitude_input = QDoubleSpinBox()
        self.latitude_input.setRange(-90, 90)
        self.latitude_input.setDecimals(8)
        self.latitude_input.setValue(-6.89586546)

        self.longitude_input = QDoubleSpinBox()
        self.longitude_input.setRange(-180, 180)
        self.longitude_input.setDecimals(8)
        self.longitude_input.setValue(107.76433421)

        self.altitude_input = QDoubleSpinBox()
        self.altitude_input.setRange(0, 200)
        self.altitude_input.setDecimals(2)
        self.altitude_input.setSuffix(" m")
        self.altitude_input.setValue(20)

        send_button = QPushButton("Fly To Waypoint")
        send_button.setStyleSheet("font-weight: bold; padding: 8px;")
        send_button.clicked.connect(self.send_waypoint)

        form.addRow("Latitude:", self.latitude_input)
        form.addRow("Longitude:", self.longitude_input)
        form.addRow("Altitude:", self.altitude_input)
        form.addRow(send_button)

        return group

    def _build_follow_target_panel(self):
        group = QGroupBox("Follow Target")
        form = QFormLayout(group)

        self.follow_latitude_input = QDoubleSpinBox()
        self.follow_latitude_input.setRange(-90, 90)
        self.follow_latitude_input.setDecimals(8)
        self.follow_latitude_input.setValue(-6.89586546)

        self.follow_longitude_input = QDoubleSpinBox()
        self.follow_longitude_input.setRange(-180, 180)
        self.follow_longitude_input.setDecimals(8)
        self.follow_longitude_input.setValue(107.76433421)

        self.follow_altitude_input = QDoubleSpinBox()
        self.follow_altitude_input.setRange(0, 200)
        self.follow_altitude_input.setDecimals(2)
        self.follow_altitude_input.setSuffix(" m")
        self.follow_altitude_input.setValue(20)

        send_button = QPushButton("FOLLOW TARGET")
        send_button.setStyleSheet("font-weight: bold; padding: 8px;")
        send_button.clicked.connect(self.send_follow_target)

        form.addRow("Latitude:", self.follow_latitude_input)
        form.addRow("Longitude:", self.follow_longitude_input)
        form.addRow("Altitude:", self.follow_altitude_input)
        form.addRow(send_button)

        return group

    def _build_forward_panel(self):
        group = QGroupBox("Forward Movement")
        layout = QVBoxLayout(group)

        distance_layout = QHBoxLayout()
        self.forward_distance_input = QDoubleSpinBox()
        self.forward_distance_input.setRange(-20, 20)
        self.forward_distance_input.setDecimals(2)
        self.forward_distance_input.setSuffix(" m")
        self.forward_distance_input.setValue(5)

        distance_button = QPushButton("FORWARD BY DISTANCE")
        distance_button.clicked.connect(self.send_forward_distance)

        distance_layout.addWidget(QLabel("Distance:"))
        distance_layout.addWidget(self.forward_distance_input)
        distance_layout.addWidget(distance_button)
        layout.addLayout(distance_layout)

        vector_form = QFormLayout()
        self.forward_x_input = QDoubleSpinBox()
        self.forward_x_input.setRange(-20, 20)
        self.forward_x_input.setDecimals(2)
        self.forward_x_input.setSuffix(" m")
        self.forward_x_input.setValue(5)

        self.forward_y_input = QDoubleSpinBox()
        self.forward_y_input.setRange(-20, 20)
        self.forward_y_input.setDecimals(2)
        self.forward_y_input.setSuffix(" m")

        self.forward_z_input = QDoubleSpinBox()
        self.forward_z_input.setRange(-10, 10)
        self.forward_z_input.setDecimals(2)
        self.forward_z_input.setSuffix(" m")

        vector_button = QPushButton("FORWARD VECTOR")
        vector_button.clicked.connect(self.send_forward_vector)

        vector_form.addRow("X:", self.forward_x_input)
        vector_form.addRow("Y:", self.forward_y_input)
        vector_form.addRow("Z:", self.forward_z_input)
        vector_form.addRow(vector_button)
        layout.addLayout(vector_form)

        return group

    def _build_manual_control_panel(self):
        group = QGroupBox("Manual Control (Remote-Style)")
        layout = QVBoxLayout(group)

        step_layout = QHBoxLayout()
        self.manual_move_step_input = QDoubleSpinBox()
        self.manual_move_step_input.setRange(0.1, 20)
        self.manual_move_step_input.setDecimals(1)
        self.manual_move_step_input.setSuffix(" m")
        self.manual_move_step_input.setValue(1.0)

        self.manual_alt_step_input = QDoubleSpinBox()
        self.manual_alt_step_input.setRange(0.1, 10)
        self.manual_alt_step_input.setDecimals(1)
        self.manual_alt_step_input.setSuffix(" m")
        self.manual_alt_step_input.setValue(0.5)

        step_layout.addWidget(QLabel("Move step:"))
        step_layout.addWidget(self.manual_move_step_input)
        step_layout.addWidget(QLabel("Altitude step:"))
        step_layout.addWidget(self.manual_alt_step_input)
        layout.addLayout(step_layout)

        dpad_grid = QGridLayout()

        forward_button = QPushButton("Forward")
        forward_button.clicked.connect(lambda: self.send_manual_move(1, 0, 0))

        backward_button = QPushButton("Backward")
        backward_button.clicked.connect(lambda: self.send_manual_move(-1, 0, 0))

        left_button = QPushButton("Left")
        left_button.clicked.connect(lambda: self.send_manual_move(0, -1, 0))

        right_button = QPushButton("Right")
        right_button.clicked.connect(lambda: self.send_manual_move(0, 1, 0))

        up_button = QPushButton("Alt Up")
        up_button.clicked.connect(lambda: self.send_manual_altitude(1))

        down_button = QPushButton("Alt Down")
        down_button.clicked.connect(lambda: self.send_manual_altitude(-1))

        for button in (
            forward_button,
            backward_button,
            left_button,
            right_button,
            up_button,
            down_button,
        ):
            button.setStyleSheet("font-weight: bold; padding: 12px;")

        dpad_grid.addWidget(forward_button, 0, 1)
        dpad_grid.addWidget(left_button, 1, 0)
        dpad_grid.addWidget(right_button, 1, 2)
        dpad_grid.addWidget(backward_button, 2, 1)
        dpad_grid.addWidget(up_button, 0, 2)
        dpad_grid.addWidget(down_button, 2, 0)

        layout.addLayout(dpad_grid)

        return group

    def _build_telemetry_panel(self):
        group = QGroupBox("Latest Telemetry")
        form = QFormLayout(group)

        for field in self.telemetry_fields:
            label = QLabel("-")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.telemetry_labels[field] = label
            form.addRow(f"{field}:", label)

        return group

    def _build_log_panel(self):
        group = QGroupBox("Command Log")
        layout = QVBoxLayout(group)
        layout.addWidget(self.log_output)
        return group

    def send_motor_test(self, motor_number):
        power = self.motor_power.value()
        self.send_command(f"testmotor,{motor_number},{power}")

    def send_takeoff(self):
        altitude = self.takeoff_altitude.value()
        self.send_command(f"takeoff,{altitude}")

    def send_waypoint(self):
        altitude = self.altitude_input.value()
        latitude = self.latitude_input.value()
        longitude = self.longitude_input.value()
        self.send_command(f"goto,{altitude},{latitude},{longitude}")

    def send_follow_target(self):
        altitude = self.follow_altitude_input.value()
        latitude = self.follow_latitude_input.value()
        longitude = self.follow_longitude_input.value()
        self.send_command(f"followtarget,{altitude},{latitude},{longitude}")

    def send_forward_distance(self):
        distance = self.forward_distance_input.value()
        self.send_command(f"forward,{distance}")

    def send_forward_vector(self):
        x = self.forward_x_input.value()
        y = self.forward_y_input.value()
        z = self.forward_z_input.value()
        self.send_command(f"forward,{x},{y},{z}")

    def send_manual_move(self, x_dir, y_dir, z_dir):
        step = self.manual_move_step_input.value()
        x = x_dir * step
        y = y_dir * step
        z = z_dir * step
        self.send_command(f"forward,{x},{y},{z}")

    def send_manual_altitude(self, z_dir):
        step = self.manual_alt_step_input.value()
        z = z_dir * step
        self.send_command(f"forward,0,0,{z}")

    def send_command(self, command):
        try:
            response = self.api.send_command(command)
            self.write_log(f"Sent: {command} | {response.get('message', 'queued')}")
        except RuntimeError as error:
            self.write_log(f"Failed: {command} | {error}")
            QMessageBox.critical(self, "Command Failed", str(error))

    def send_cancel(self):
        try:
            response = self.api.cancel_command()
            self.write_log(f"Cancel/reset requested | {response.get('message', 'ok')}")
        except RuntimeError as error:
            self.write_log(f"Cancel failed | {error}")
            QMessageBox.critical(self, "Cancel Failed", str(error))

    def refresh_telemetry(self):
        try:
            recent = self.api.get_recent()
            latest = recent.get("data")
            if latest is None:
                data = self.api.get_data()
                latest = data[-1] if data else None
        except RuntimeError as error:
            self.write_log(f"Telemetry refresh failed: {error}")
            return

        if not latest:
            self.write_log("Telemetry refresh returned no data.")
            return

        for field, label in self.telemetry_labels.items():
            label.setText(str(latest.get(field, "-")))

    def write_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{timestamp}] {message}")


def main():
    app = QApplication(sys.argv)
    window = DroneControlWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

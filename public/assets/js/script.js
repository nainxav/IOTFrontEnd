var [x, y] = [-6.190529999829426, 106.82151147617375];

const server = "http://127.0.0.1:5000";

var map = L.map("map", {
  crs: L.CRS.EPSG3857,
  center: [x, y],
  zoom: 13,
  maxZoom: 20,
  minZoom: 6,
}).setView([x, y], 13);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  crs: L.CRS.EPSG3857,
  attribution:
    '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

const behaviorConfig = {
  coordinatePrecision: 6,
  mode: "polygon",
  pointerDistance: 10,
  project: (coords) => {
    return map.latLngToLayerPoint(L.latLng(coords.lat, coords.lng));
  },
  projection: L.CRS.EPSG3857,
  store: "GeoJSONStore",
  unproject: (point) => {
    return map.layerPointToLatLng(L.point(point.x, point.y));
  },
};

let draw = new terraDraw.TerraDraw({
  adapter: new terraDraw.TerraDrawLeafletAdapter({
    lib: L,
    map: map,
  }),
  behaviorConfig: behaviorConfig,
  modes: [
    new terraDraw.TerraDrawSelectMode({
      allowManualDeselection: true,

      flags: {
        point: {
          feature: {
            draggable: true,
          },
        },

        polygon: {
          feature: {
            draggable: true,
            coordinates: {
              midpoints: true,
              draggable: true,
              deletable: true,
            },
          },
        },

        linestring: {
          feature: {
            draggable: true,
            coordinates: {
              midpoints: true,
              draggable: true,
              deletable: true,
            },
          },
        },

        freehand: {
          feature: {
            draggable: true,
            coordinates: {
              midpoints: true,
              draggable: true,
              deletable: true,
            },
          },
        },

        circle: {
          feature: {
            draggable: true,
            coordinates: {
              midpoints: true,
              draggable: true,
              deletable: true,
            },
          },
        },

        rectangle: {
          feature: {
            draggable: true,
            coordinates: {
              midpoints: true,
              draggable: true,
              deletable: true,
            },
          },
        },
      },
    }),
    new terraDraw.TerraDrawPointMode(),
    new terraDraw.TerraDrawLineStringMode(),
    new terraDraw.TerraDrawRectangleMode(),
    new terraDraw.TerraDrawPolygonMode({
      styles: {
        fillOpacity: 0.6,
        // fillColor: ({ id }) => {
        //   if (!colorCache[id]) {
        //     colorCache[id] = getRandomColor();
        //   }
        //   return colorCache[id];
        // },

        fillColor: ({ id }) => {
          return findLayerIndexByTerraId(layer, id)
            ? findLayerIndexByTerraId(layer, id)
            : activatedLayer[0].color;
        },
        // fillColor: "#ff0a0a",
      },
    }),
    new terraDraw.TerraDrawFreehandMode(),
    new terraDraw.TerraDrawCircleMode(),
  ],
});

draw.start();

// async function fetchAltitude() {
//   try {
//     const response = await fetch('http://192.168.1.145:5000/altitude');
//     const contentType = response.headers.get("content-type");

//     if (!response.ok) {
//       throw new Error(`HTTP error! Status: ${response.status}`);
//     }

//     // Check if the response is JSON
//     if (contentType && contentType.includes("application/json")) {
//       const data = await response.json();
//       console.log(data.altitude);
//       const button = document.getElementById('altitudeValue');
//       button.textContent = `Altitude: ${data.altitude}`;
//     } else {
//       const responseText = await response.text();
//       console.error("Response was not JSON:", responseText);
//     }
//   } catch (error) {
//     console.error('Error fetching altitude:', error);
//   }
// }

// window.addEventListener('DOMContentLoaded', () => {
//   setInterval(fetchAltitude, 1000);
// });

async function fetchData() {
  try {
    console.log("anjai");
    // const response = await fetch('http://192.168.105.193:5000/data');
    const response = await fetch(`${server}/data`);
    const contentType = response.headers.get("content-type");

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    if (contentType && contentType.includes("application/json")) {
      const data = await response.json();

      const altitude = document.getElementById("altitudeValue");
      altitude.textContent = `Altitude: ${data[data.length - 1].altitude}`;

      const latitude = document.getElementById("latitudeValue");
      latitude.textContent = `Latitude: ${data[data.length - 1].latitude}`;

      const longitude = document.getElementById("longitudeValue");
      longitude.textContent = `Longitude: ${data[data.length - 1].longitude}`;

      // const yaw = document.getElementById('yawValue');
      // yaw.textContent = `Yaw: ${data[data.length-1].yaw}`;

      // const roll = document.getElementById('rollValue');
      // roll.textContent = `Roll: ${data[data.length-1].roll}`;

      // const groundSpeed = document.getElementById('groundSpeedValue');
      // groundSpeed.textContent = `Ground Speed: ${data[data.length-1].groundspeed}`;

      // const verticalSpeed = document.getElementById('verticalSpeedValue');
      // verticalSpeed.textContent = `Vertical Speed: ${data[data.length-1].verticalspeed}`;

      // const satCount = document.getElementById('satCountValue');
      // satCount.textContent = `Sat Count: ${data[data.length-1].satcount}`;

      // const wpDist = document.getElementById('wp_distValue');
      // wpDist.textContent = `WP Distance: ${data[data.length-1].wp_dist}`;
      const element = [
        {
          id: draw.getFeatureId(),
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [
              data[data.length - 1].longitude,
              data[data.length - 1].latitude,
            ],
          },
          properties: {
            mode: "point",
          },
          properties2: {
            d: "sd",
          },
        },
      ];
      console.log(element[0].geometry.coordinates);
      const bounds = L.GeoJSON.coordsToLatLngs([
        element[0].geometry.coordinates,
        [107.609, -6.91357],
      ]);
      const bound = L.GeoJSON.coordsToLatLng(element[0].geometry.coordinates);
      // console.log(bound);
      // map.fitBounds(bound);
      map.setView(bound, 19);
      draw.clear();
      draw.addFeatures(element);
    } else {
      const responseText = await response.text();
      console.error("Response was not JSON:", responseText);
    }
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

async function command(command) {
  console.log(`${server}/command`);
  const response = await fetch(`${server}/command`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ command: command }),
  });
  console.log(response);
}

const armButton = document.querySelector("#armButton");
armButton.addEventListener("click", () => command("arm"));
const disarm = document.querySelector("#disarmButton");
disarm.addEventListener("click", () => command("disarm"));

const motor1Button = document.querySelector("#motor1Button");
motor1Button.addEventListener("click", () => command("testmotor,1,15"));
const motor2Button = document.querySelector("#motor2Button");
motor2Button.addEventListener("click", () => command("testmotor,2,15"));
const motor3Button = document.querySelector("#motor3Button");
motor3Button.addEventListener("click", () => command("testmotor,3,15"));
const motor4Button = document.querySelector("#motor4Button");
motor4Button.addEventListener("click", () => command("testmotor,4,15"));

window.addEventListener("DOMContentLoaded", () => {
  setInterval(fetchData, 3000);
});

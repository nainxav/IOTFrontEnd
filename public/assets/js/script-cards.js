async function fetchData() {
    try {
    // const response = await fetch('http://192.168.105.193:5000/data');
      const response = await fetch('http://192.168.105.45:5000/data');
      const contentType = response.headers.get("content-type");
  
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
  
      if (contentType && contentType.includes("application/json")) {
        const data = await response.json();
  
        const latitude = document.getElementById('latitudeValue');
        latitude.textContent = `${data[data.length-1].latitude}`;
  
        const longitude = document.getElementById('longitudeValue');
        longitude.textContent = `${data[data.length-1].longitude}`;
  
        const yaw = document.getElementById('yawValue');
        yaw.textContent = `${data[data.length-1].yaw}`;
  
        const roll = document.getElementById('rollValue');
        roll.textContent = `${data[data.length-1].roll}`;
  
        const groundSpeed = document.getElementById('groundSpeedValue');
        groundSpeed.textContent = `${data[data.length-1].groundspeed}`;
  
        const verticalSpeed = document.getElementById('verticalSpeedValue');
        verticalSpeed.textContent = `${data[data.length-1].verticalspeed}`;
  
        const satCount = document.getElementById('satCountValue');
        satCount.textContent = `${data[data.length-1].satcount}`;
  
        const wpDist = document.getElementById('wp_distValue');
        wpDist.textContent = `${data[data.length-1].wp_dist}`;
      } else {
        const responseText = await response.text();
        console.error("Response was not JSON:", responseText);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  }
  
  window.addEventListener('DOMContentLoaded', () => {
    setInterval(fetchData, 1000);
  });
  
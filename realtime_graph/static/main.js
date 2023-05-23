
const ctx = document.getElementById('myChart');

var graphData = {
type: 'scatter',
data: {
  datasets: [
      {
        label: 'MCU',
        data: [],
        backgroundColor: [
            'rgba(73, 198, 230, 1)',
        ],
        borderColor: [
            'rgba(73, 198, 230, 1)',
        ],
        borderWidth: 1,
        showLine: true,
        yAxisID: 'y',

      },
      {
        label: 'PLC_Displacement',
        data: [],
        backgroundColor: [
            'rgba(255, 0, 0, 0.5)',
        ],
        borderColor: [
            'rgba(255, 0, 0, 0.5)',
        ],
        borderWidth: 1,
        showLine: true,
        yAxisID: 'y2',
      },
      {
        label: 'PLC_Force',
        data: [],
        backgroundColor: [
            'rgba(0, 0, 255, 0.5)',
        ],
        borderColor: [
            'rgba(0, 0, 255, 0.5)',
        ],
        borderWidth: 1,
        showLine: true,
        yAxisID: 'y1',
      },
  ]
},
options: {
    animation: false,
	interaction: {
		mode: 'nearest',
		intersect: false,
	},
    scales: {
        x: {
            type: 'time',
            time: {
                unit: 'second',
                displayFormats: {
                    second: 'HH:mm:ss',
                },
            },
            title:{
                display: true,
                text: 'Time'
            },
			ticks: {
				autoSkip: false,
				minRotation: 30,
				callback: function(value, index, values) {
					if (index <= 1) {
						return null;
					}

					var dateTime = new Date(value);
					var dateTimeString = ("0" + dateTime.getHours().toString()).slice(-2) + "." +
										 ("0" + dateTime.getMinutes().toString()).slice(-2) + ":" +
										 ("0" + dateTime.getSeconds().toString()).slice(-2);
					return dateTime.getSeconds() % 5 == 0 ? dateTimeString : null;
				},
			}
        },
        y: {
            type: 'linear',
            min: -10,
            max: 110,
            title:{
                display: true,
                text: 'Position [%]',
                color: 'blue'
            },
            position: 'left',
        },
        y1: {
            type: 'linear',
            min: -500,
            max: 5500,
            title:{
                display: true,
                text: 'Force'
            },
            position: 'right',
        },
        y2: {
            type: 'linear',
            min: -2.5,
            max: 27.5,
            title:{
                display: true,
                text: 'Position [mm]',
                color: 'red'
            },
            position: 'left',
        },
    }
}
}

var myChart = new Chart(ctx, graphData);

var socket = new WebSocket('ws://localhost:8000/ws/graph/')

var panCounter = 0;
var mcuDataMessage = null;
var plcDataMessage = null;

socket.onmessage = function(e){
    var djangoData = JSON.parse(e.data);

    if (djangoData.id == "MCU") {
		mcuDataMessage = djangoData;
    } else {
		plcDataMessage = djangoData;
    }
};

setInterval(function() {
    // console.log(socket.bufferedAmount);

    if (mcuDataMessage != null) {
        var newGraphData = graphData.data.datasets[0].data;

        if (panCounter > 1000) {
            newGraphData.shift();
        } else {
            panCounter++;
        }

        newGraphData.push({x: mcuDataMessage.time, y: mcuDataMessage.value});

        graphData.data.datasets[0].data = newGraphData;

		mcuDataMessage = null;
    } 
	
	if (plcDataMessage != null) {
        var newGraphData = graphData.data.datasets[1].data;
        var newGraphData2 = graphData.data.datasets[2].data;

        if (panCounter > 1000) {
            newGraphData.shift();
            newGraphData2.shift();
        } else {
            panCounter++;
        }

        newGraphData.push({x: plcDataMessage.time, y: plcDataMessage.value});
        newGraphData2.push({x: plcDataMessage.time, y: plcDataMessage.force});

        graphData.data.datasets[1].data = newGraphData;
        graphData.data.datasets[2].data = newGraphData2;

		plcDataMessage = null;
    }

    myChart.update();

}, 10);

socket.onopen = function(e) {
//  alert("[open] Connection established");
    console.log("WebSocket onopen: ", e);
 };

socket.onclose = function(e) {
    if (event.wasClean) {
//        alert(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
        console.log("WebSocket onclose clean: ", e);
    } else {
//        alert('[close] Connection died');
        console.log("WebSocket onclose unclean: ", e);
    }
};

socket.onerror = function(e) {
    console.log("WebSocket onerror: ", e);
};

socket.addEventListener("error", (event) => {
    console.log("WebSocket error: ", event);
});

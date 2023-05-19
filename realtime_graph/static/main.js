
const ctx = document.getElementById('myChart');

var graphData = {
type: 'scatter',
data: {
//  labels: ['jan', 'feb', 'mar', 'apr', 'may', 'jun'],
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
    scales: {
        x: {
            type: 'time',
            time: {
//                parser: 'yyyy-MM-ddTHH:mm:ss.SSSSSS',
                unit: 'second',
                displayFormats: {
                    second: 'HH:mm:ss',
                },
            },
            title:{
                display: true,
                text: 'Time'
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

socket.onmessage = function(e){
    var djangoData = JSON.parse(e.data);

//    var date = new Date(djangoData.time);

//    console.log(date.valueOf());
//    console.log(djangoData.time);

    if (djangoData.id == "MCU") {
        var newGraphData = graphData.data.datasets[0].data;

        if (panCounter > 1000) {
            newGraphData.shift();
        } else {
            panCounter++;
        }

        newGraphData.push({x: djangoData.time, y: djangoData.value});

        graphData.data.datasets[0].data = newGraphData;
    } else {
        var newGraphData = graphData.data.datasets[1].data;
        var newGraphData2 = graphData.data.datasets[2].data;

        if (panCounter > 1000) {
            newGraphData.shift();
            newGraphData2.shift();
        } else {
            panCounter++;
        }

        newGraphData.push({x: djangoData.time, y: djangoData.value});
        newGraphData2.push({x: djangoData.time, y: djangoData.force});

        graphData.data.datasets[1].data = newGraphData;
        graphData.data.datasets[2].data = newGraphData2;
    }


//    var newGraphData = graphData.data.datasets[0].data;
//    newGraphData.shift();
//    newGraphData.push(djangoData.value);
//
//    graphData.data.datasets[0].data = newGraphData;
    myChart.update();

//    document.querySelector('#app').innerText = djangoData.value;
};

setInterval(function() {
    socket.send(JSON.stringify({"signal": "heartbeat"}));
    console.log(socket.bufferedAmount);
}, 1000);

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



      // Load the Visualization API and the piechart package.
      google.load('visualization', '1.0', {'packages':['corechart']});

      // Set a callback to run when the Google Visualization API is loaded.
      //google.setOnLoadCallback(drawChart);


      
      
      // Callback that creates and populates a data table,
      // instantiates the pie chart, passes in the data and
      // draws it.
      function drawChart() {

        // Create the data table.
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Answer');
        data.addColumn('number', 'Votes');
        
        var theData = JSON.parse($('#results_data').attr("data-votes"));
        var arr = Array()
         for (i in theData) {arr.push([i,theData[i] ]);}
        
        console.log(arr);
        
        data.addRows(arr);

        // Set chart options
        var options = {
                       'width':400,
                       'height':300,
                       'left': 0,
                       'top':0};
        
         //options = {'chartArea': '{title: "blah2", left:0,top:0,width:0,height:0}'};
                // Instantiate and draw our chart, passing in some options.
        var chart = new google.visualization.PieChart(document.getElementById('results_chart'));
        chart.draw(data, options);
      }
    
function setCookie(cookieName, cookieValue, nDays) {		
    var today = new Date();
    var expire = new Date();
    if (!nDays) 
        nDays=1;
    expire.setTime(today.getTime() + 3600000*24*nDays);
    document.cookie = cookieName+"="+escape(cookieValue) + ";expires="+expire.toGMTString();
}	

function getCookie(name) {
  var nameEQ = name + "=";
  var ca = document.cookie.split(';');
  for(var i = 0; i < ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == ' ') c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
  }
  return null;
}

(function($) {

$(document).ready(function () {
    $("#players").tablesorter({
        sortList: [[0,0],[2,0]],
        textExtraction: { 
            2: function(node, table, cellIndex) { return $(node).find("i").data("order"); }, 
        }
    });
    $(".class_stat").tablesorter({
        sortList: [[12,1]],
        sortInitialOrder: "desc",
        textExtraction: { 
            2: function(node, table, cellIndex) { return $(node).find("i").data("order"); }, 
        }	 		 	
    });
    $(".healsort").tablesorter({
        sortList: [[2,1]],
        sortInitialOrder: "desc",
        textExtraction: { 
            1: function(node, table, cellIndex) { return $(node).find("i").data("order"); }, 
        }	 			
    });
    $(".roundtable").tablesorter({sortList: [[2,1]]});
    $(".classicon").popover({
        html: true,
        trigger: 'hover',
        placement: 'top',
        animation: false,
        delay: { show: 100, hide: 1 }	
    });
    $('body').tooltip({
        selector: '.tip'
    });
    $('.round_row').click(function() {
        $(this).next().toggle();				
        $(this).toggleClass('expanded');
    });	
    $('#players td, .class_stat td').filter(function(){return $(this).html() == "0";}).addClass('zero');
    

    var forced_sort = getCookie('forceteamsort');
    if (forced_sort == 'true') {
        $('#players').data('tablesorter').sortForce = [[0,0]];
        $('#force_team_sort').prop('checked', true);    	
    } else {
        $('#players').data('tablesorter').sortForce = [];
        $('#force_team_sort').prop('checked', false);	
    }
    $("#force_team_sort").change(function() {		
        if(this.checked) {
            $('#players').data('tablesorter').sortForce = [[0,0]];
            setCookie('forceteamsort', 'true', 365);
        } else {
            $('#players').data('tablesorter').sortForce = [];
            setCookie('forceteamsort', 'false', 365);
        }
    });	    

    // Remember saved sorting order
    var sortselect = $('#sortselect');
    var selected_sort = getCookie('tablesort');
    sortselect.val(selected_sort);	
    switch(selected_sort) {
        case 'da':    		
            $("#players").trigger("sorton",[[[6,1]]]);
            break;
        case 'tda':    		
            $("#players").trigger("sorton",[[[0,0],[6,1]]]);
            break;    		
        case 'k':    		
            $("#players").trigger("sorton",[[[3,1]]]);
            break;    		
        case 'kad':    		
            $("#players").trigger("sorton",[[[8,1]]]);
            break;    		
        case 'kd':    		
            $("#players").trigger("sorton",[[[9,1]]]);
            break; 
        default:
            sortselect.val('default');
            break;
    }

    // Highlight
    var hash = window.location.hash;
    var highlight = hash.substring(1);
    if (highlight) {
        $("#player_" + highlight).addClass("highlight");
    }
});

})($);
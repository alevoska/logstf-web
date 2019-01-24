(function($) {

$(document).ready(function () {
    $("[rel=tooltip]").tooltip();
    $(".tip").tooltip();
    $(".datefield").each(function () {						
        var datevalue = parseInt($(this).data('timestamp'));
        var date = moment.unix(datevalue);
        $(this).html(date.format('lll'));
    });
});

})($);
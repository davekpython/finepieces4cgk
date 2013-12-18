$(document).ready(function() {
	
	$('#edit-artist input').hide();
	$('#edit-artist').click(function() {
		$('#edit-artist input').show();
		$('#edit-artist span').hide();
		var value = $("#edit-artist span").text();
		$("#edit-artist input").val(value);
	});
	$('#edit-subject input').hide();
	$('#edit-subject').click(function() {
		$('#edit-subject input').show();
		$('#edit-subject span').hide();
		var value = $("#edit-subject span").text();
		$("#edit-subject input").val(value);
	});	
	
	$('#edit-title input').hide();
	$('#edit-title').click(function() {
		$('#edit-title input').show();
		$('#edit-title span').hide();
		var value = $("#edit-title span").text();
		$("#edit-title input").val(value);
	});	
		
	$('#edit-medium input').hide();
	$('#edit-medium').click(function() {
		$('#edit-medium input').show();
		$('#edit-medium span').hide();
		var value = $("#edit-medium span").text();
		$("#edit-medium input").val(value);
	});	
	
	$('#edit-ob_date input').hide();
	$('#edit-ob_date').click(function() {
		$('#edit-ob_date input').show();
		$('#edit-ob_date span').hide();
		var value = $("#edit-ob_date span").text();
		$("#edit-ob_date input").val(value);
	});		

	$('#edit-provenance input').hide();
	$('#edit-provenance').click(function() {
		$('#edit-provenance input').show();
		$('#edit-provenance span').hide();
		var value = $("#edit-provenance span").text();
		$("#edit-provenance input").val(value);
	});		

	$('#edit-valuation input').hide();
	$('#edit-valuation').click(function() {
		$('#edit-valuation input').show();
		$('#edit-valuation span').hide();
		var value = $("#edit-valuation span").text();
		$("#edit-valuation input").val(value);
	});		

	
	$('#text_remark').hide();
	$('#edit-remark').click(function() {
		$('#edit-remark').show();
		$('#edit-remark span').hide();
		var value = $("edit-remark span").text();
		$('#text_remark').val(value);
		$('#text_remark').show();
	});
	
	$('#update-object').hide();
	$('#edit-object').click(function() {
		$('#update-object').show()
	});
	
	$('#objectperm').click(function() {
		$('#objectperm').css('width', function(_,cur) {
			return cur=== '870px'
			});
		});
	
var flag = true;
	$('#objectperm').click(function(e){
		if(flag)
			$(e.target).animate({width:'1024px', height:'768px' }, 150, function(){
            //do stuff after animation
			});

		else
        $(e.target).animate({width:'512px', height: '384px'}, 150, function(){
            //do stuff after animation
        });
    flag=!flag;
});

	
	// $('#objectperm').click(function() {
		// $('#objectperm').toggle(500);
		// {$(this).css('width', function(_, cur){
		// return cur === '512px' ? '100%' : '870px'
		// });
	// });
	// });
	// $('#objectperm').click(function ()
	// {$(this).css('height', function(_, cur){
		// return cur === '384px' ? '100%' : '652px'
		// });
	// });
});


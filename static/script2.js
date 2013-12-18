$(document).ready(function() {
	$('#update-artist').hide();
	$('.arts').click(function() {
	$('.arts .stuff').replaceWith('<input type="text" size=5 name="updateartist" value="" placeholder={{ post.artist }}>');
	});
	$('#update-note').hide();
	$('#edit-note').click(function() {
	$('#update-note').show();
	});
	$('#update-object').hide();
	$('#edit-object').click(function() {
	$('#update-object').show()
	});
});
(function($) {

$(document).ready(function () {
	var uploader = new qq.FineUploaderBasic({
		button: $('#fileuploader')[0],	
		autoUpload: false,			
		request: {
			endpoint: '/upload',
			forceMultipart: true,
			inputName: 'logfile',
		},
		validation: {
			allowedExtensions: ['log'],
			sizeLimit: 12582912,
			minSizeLimit: 51200
		},
		debug: false,  
		maxConnections: 1,        
		callbacks: {
			onSubmit: function(id, fileName) {								
				$('#files tbody').append('<tr id="file-'+id+'"><td>'+fileName+'</td><td><input type="text" class="input-medium" name="title" placeholder="(Optional)"></td><td><input type="text" class="input-medium" name="map" placeholder="(Optional)"></td><td class="filestatus">Waiting</td></tr>');	
				$('#uploader-table').show();
				$('#uploadfiles').removeAttr('disabled').addClass('btn-primary');			
				$('#resetfiles').removeAttr('disabled');
			},
			onUpload: function(id, fileName) {	
				$('#file-'+id+' .filestatus').html('Initializing upload');
				this.setParams({					
					title: $('#file-'+id+' input[name=title]').val(),
					map: $('#file-'+id+' input[name=map]').val()
				}, id);
			},					
			onProgress: function(id, fileName, loaded, total) {
				if (loaded < total) {
					var progress = Math.round(loaded / total * 100);
					$('#file-'+id+' .filestatus').html('Uploading ('+progress+'%)');
				} else {
					$('#file-'+id+' .filestatus').html('Processing log');
				}
			},
			onComplete: function(id, fileName, res) {
				if (res.success) {
					var link = '<a href="'+res.url+'">View log</a>';
					$('#file-'+id+' .filestatus').html(link);
					$('#file-'+id).addClass('upload-success');
				} else {
					$('#file-'+id+' .filestatus').html('Error: '+res.error);
					$('#file-'+id).addClass('upload-error');
				}
			},
			onError: function(id, fileName, error) {				
				// $('#files').append('<div class="alert alert-upload"><button type="button" class="close" data-dismiss="alert">×</button>'+error+'</div>');
				// $('#file-'+id).addClass('upload-error');
			}
		}
	});
$('#resetfiles').click(function(e) {
	e.preventDefault();
	uploader.reset();	
	$('#files tbody').empty();
	$('#uploadfiles').attr('disabled', 'disabled').removeClass('btn-primary');			
	$('#resetfiles').attr('disabled', 'disabled');	
	fileNum = 0;
});
$('#uploadfiles').click(function(e) {
	e.preventDefault();
	uploader.uploadStoredFiles();
});

$(document).bind('drop dragover', function (e) {
	e.preventDefault();
});

$("body").bind('drop', function (e) {
	console.log('Drop');
	uploader.addFiles(e.originalEvent.dataTransfer.files);
});
});

})($);

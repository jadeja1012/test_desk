$(document).ready(async function(){
    if($('#hotel_select')){
        $.ajax({
            url: '/search_hotel', // URL of the server-side script or API
            type: 'POST',
            dataType: 'json',
            beforeSend: function (xhr) { xhr.setRequestHeader('Content-Type', 'application/json'); },
            data: JSON.stringify({ jsonrpc: '2.0' }),
            success: function(response) {
                $('#hotel_select').empty()
                for(var i=0;i<response.result.length;i++){
                    $('#hotel_select').append('<option value='+response.result[i].id+'>'+response.result[i].name+'</option')
                }
                console.log(response);
            },

})
    }
})
!function ($) {
    $("#id_from_date").datepicker({onSelect:function(dateText,inst){
        $("#id_to_date").datepicker("option","minDate",dateText);
      }
    });

    $("#id_to_date").datepicker({onSelect:function(dateText,inst){
        $("#id_from_date").datepicker("option","maxDate",dateText);
      }
    });

    $('.reply .wrap-reply:last').addClass("last");

    // Hit the top
    function gotoTop(min_height){
      $("#goTop").click(
        function(){ $('html,body').animate({scrollTop:0},700);
      });

      // Fetch the min height of the page, default is 300px
      min_height ? min_height = min_height : min_height = 300;
      $(window).scroll(function(){
        // Fetch the vertical height of scroll bar
        var s = $(window).scrollTop();
        // Fading in the Hittop icon if s greater than min_height 
        if( s > min_height){
          $("#goTop").fadeIn(100);
        }else{
          $("#goTop").fadeOut(200);
        };
      });
    };
    gotoTop();

    // Fold back the long comment
    $(function(){
      var slideHeight = 68;
      $('.comment').each(function(){
        var defHeight = $(this).height();
        if(defHeight >= slideHeight){
          $(this).css('height' , slideHeight + 'px');
          $(this).next('.read-more').append('<a href="#">Read More</a>');
          $(this).next('.read-more').children('a').click(function(){
            var curHeight = $(this).parent().prev().height();
            if(curHeight == slideHeight){
              $(this).parent().prev().animate({
                height: defHeight
              }, "normal");
              $(this).html('Close');
            }else{
              $(this).parent().prev().animate({
                height: slideHeight
              }, "normal");
              $(this).html('Read More');
            }
            return false;
          });   
        }
      });
    });

}(window.jQuery);
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

  // Dynamically add form to package formset
  // Update 'id' and 'for' attrs to new form
  function updateElementIndex(el, prefix, ndx) {
    var id_regex = new RegExp('(' + prefix + '-\\d+-)');
    var replacement = prefix + '-' + ndx + '-';
    if ($(el).attr("for")) {
      $(el).attr("for", $(el).attr("for").replace(id_regex, replacement));
    }
    if (el.id) {
      el.id = el.id.replace(id_regex, replacement);
    }
    if (el.name)  {
      el.name = el.name.replace(id_regex, replacement);
    }
  }

  function addForm(btn, prefix) {
    var formCount = parseInt($('#id_' + prefix + '-TOTAL_FORMS').val());
    // You can only submit a maximum of 10 items 
    if (formCount < 10) {
      // Clone a form (without event handlers) from the first form
      var row = $(".well:first").clone(false).get(0);
      // Insert it after the last form
      $(row).removeAttr('id').hide().insertAfter(".well:last").slideDown(300);

      // Remove the bits we don't want in the new row/form
      $(".errorlist", row).remove();
      $(row).children('.row').removeClass("error");

      // Relabel or rename all the relevant bits
      $(row).children('.row').find('label,input,textarea').each(function () {
        updateElementIndex(this, prefix, formCount);
        $(this).val("");
      });

      // Add an event handler for the delete item/form link 
      $(row).find(".del-pack").click(function () {
        return deleteForm(this, prefix);
      });
      // Update the total form count
      $("#id_" + prefix + "-TOTAL_FORMS").val(formCount + 1);
    }
    else {
      alert("Sorry, you can only enter a maximum of ten items.");
    }
    return false;
  }
  function deleteForm(btn, prefix) {
    var formCount = parseInt($('#id_' + prefix + '-TOTAL_FORMS').val());
    if (formCount > 1) {
      // Delete the item/form
      $(btn).parents('.well').remove();
      var forms = $('.well'); // Get all the forms  
      // Update the total number of forms (1 less than before)
      $('#id_' + prefix + '-TOTAL_FORMS').val(forms.length);
      var i = 0;
      // Go through the forms and set their indices, names and IDs
      for (formCount = forms.length; i < formCount; i++) {
        $(forms.get(i)).children('.row').find('label,input,textarea').each(function () {
          updateElementIndex(this, prefix, i);
        });
      }
    }
    else {
      alert("You have to enter at least one package!");
    }
    return false;
  }
  // Register the click event handlers
  $("#add-pack").click(function () {
    return addForm(this, "form");
  });
  $(".del-pack").click(function () {
    return deleteForm(this, "form");
  });
}(window.jQuery);
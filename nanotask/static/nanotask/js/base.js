var hrefSplit = window.location.href.split("/");
PROJECT_NAME = hrefSplit[hrefSplit.length-2];

MTURK_WORKER_ID = turkGetParam("workerId", "TEST_WORKER");
MTURK_ASSIGNMENT_ID = turkGetParam("assignmentId", "ASSIGNMENT_ID_NOT_AVAILABLE");
MTURK_HIT_ID = turkGetParam("hitId", "TEST_DUMMY_HIT");

TEST_MODE = MTURK_ASSIGNMENT_ID=="test" ? true : false;

BASE_URL = window.location.origin+"/";

nanotasksPerHIT = -1;
submittedNanotasks = 0;

timeNanotaskStarted = null;

var randomSeed = function(){
    var l = 16;
    var c = "abcdefghijklmnopqrstuvwxyz0123456789";
    var cl = c.length;
    var r = "";
    for(var i=0; i<l; i++) r += c[Math.floor(Math.random()*cl)];
    return r;
};

var loadPreviewNanotask = function() {
    $.ajax({
        type: "GET",
        url: BASE_URL + "nanotask/nanotask/"+PROJECT_NAME+"/?preview=1",
        success: function(nanotask){
            $("#base-nanotask").html(nanotask.html);
        }
    });
};

var loadNanotask = function() {
    var afterNanotaskLoadHandler = function(nanotask){
        if(!nanotask.info) afterNanotaskLoadErrorHandler();
        $("#base-submitted-num-box>span.submitted-num").text(submittedNanotasks+1);
        $("#base-nanotask").html(nanotask.html);
        $("#base-nanotask").fadeIn("normal");
        timeNanotaskStarted = new Date();
        var idsAllInputVal = $("#nano-ids-all").val();
        if(idsAllInputVal=="") idsAll = [];
        else idsAll = JSON.parse(idsAllInputVal);
    
        $(".nano-submit").on("click", function(){
            var secsElapsed = (new Date() - timeNanotaskStarted)/1000;
            $("#base-nanotask").fadeOut("fast");
            //var answersJSON = {};
	    var answersJSON = [];  // FIXME hacked

            if($(this).attr("name")){
                var name = $(this).attr("name");
                var value = $(this).val();
                answersJSON[name] = value;
            } else {
                //$answers = $(".nano-answer[type=radio]:checked,.nano-answer[type=text]");

                /* for(var i in $answers){
		 *     var $answer = $answers.eq(i);
		 *     var name = $answer.attr("name");
		 *     var value = $answer.val();
		 *     //answersJSON[name] = value;
		   if(name in answersJSON)
		   answersJSON[name].push(value);
		   else
		   answersJSON[name] = [value];
		 * }
		 */

		$(".image_box").each(function(idx, elem) {
		    var id = $(elem).parent().find("input").attr("value");
		    var type = $(elem).parent().find("input").attr("name");
		    var class_names = $(elem).find("img").attr("class").split(" ");
		    var ans;

		    console.log(id);
		    console.log(type);
		    alert("hello");

		    if (class_names.indexOf("checked") > 0) {
			ans = "yes";
		    } else {
			ans = "no";
		    }
		    answersJSON.push({"id":id, "type":type, "ans":ans});
		});
            }
            idsAll.push(nanotask.info.id);
            $("#nano-ids-all").val(JSON.stringify(idsAll));
            submittedNanotasks += 1;
            sessionStorage.setItem("submittedNanotasks", submittedNanotasks);
            data = {
                "id": nanotask.info.id,
                "sec": secsElapsed,
                "answer": answersJSON,
                "project_name": PROJECT_NAME
            };
            submitNanotask(data, function(){
                if(submittedNanotasks >= nanotasksPerHIT) submitHIT();
                else loadNanotask();
            }, function(){
                alert("We're sorry, an error occured on sending data --- no worries, this HIT will be submitted now and you will be paid for this :) Thank you for your cooperation!");
		submitHIT();
            });
        });
    };
    
    var afterNanotaskLoadErrorHandler = function(){
        if(submittedNanotasks==0){
            noTaskAlert();
        } else {
            noMoreTaskAlert(submitHIT);
        }
    };

    $.ajax({
        type: "POST",
        url: BASE_URL + "nanotask/nanotask/"+PROJECT_NAME+"/",
        data: JSON.stringify({
            "mturk_worker_id": MTURK_WORKER_ID,
            "session_tab_id": sessionStorage.tabID,
            "user_agent": window.navigator.userAgent
        }),
        success: afterNanotaskLoadHandler,
        error: afterNanotaskLoadErrorHandler
    });
};

var submitHIT = function(){
    data["mturk_assignment_id"] = MTURK_ASSIGNMENT_ID;
    data["mturk_worker_id"] = MTURK_WORKER_ID;
    data["mturk_hit_id"] = MTURK_HIT_ID;
    data["project_name"] = PROJECT_NAME;
    data["ids"] = JSON.parse($("#nano-ids-all").val());
    $("#base-nanotask-submitted").show();
    $.ajax({
        type: "POST",
        url: BASE_URL + "nanotask/assignment/save/",
        data: JSON.stringify(data),
        success: function(){
            sessionStorage.removeItem("submittedNanotasks");
            if(TEST_MODE) { setTimeout(function(){ window.location.reload(); }, 500); }
            else $("#mturk_form").submit();
        },
        error: function(){
            console.log("submit hit error");
            $("#mturk_form").submit();
        }
    });
};

var submitNanotask = function(data, success, error){
    data["mturk_worker_id"] = MTURK_WORKER_ID;
    $.ajax({
        type: "POST",
        url: BASE_URL + "nanotask/answer/save/",
        dataType: "json",
        data: JSON.stringify(data),
        success: success,
        error: error
    });
}

var noMoreTaskAlert = function(callback){
    alert("Well done! There are no more tasks available -- this HIT will be automatically submitted. Thank you for your help! :)");
    callback();
};

var noTaskAlert = function(){
    alert("We're sorry but there are currently no tasks available :( Please try again later. Thank you!");
};


$("#base-instruction-button").on("click", function(){
    $("#base-instruction-shadow").fadeIn("normal");
    $("#base-instruction").animate({"marginTop":"+=200px", "display": "block"});
    $("#base-instruction").show();
    $(this).prop("disabled", true);
});
$("#base-instruction-shadow").on("click", function(){
    $("#base-instruction").animate({"marginTop":"-=200px", "display": "none"});
    $(this).fadeOut("normal");
    $("#base-instruction-button").prop("disabled", false);
});
$("#base-instruction").on("click", function(e){
    e.stopPropagation();
});


$(function(){
    nanotasksPerHIT = $("#nanotasks-per-hit").val();
    if(MTURK_ASSIGNMENT_ID=="ASSIGNMENT_ID_NOT_AVAILABLE") {
        loadPreviewNanotask();
        $("#base-instruction-button").click();
    } else { 
        $("#base-submitted-num-box").show();
        var sessionSubmittedNanotasks = sessionStorage.getItem("submittedNanotasks");
        if(sessionSubmittedNanotasks) submittedNanotasks = parseInt(sessionSubmittedNanotasks);
        if(!sessionStorage.tabID) sessionStorage.tabID = randomSeed();
        loadNanotask();
    }
});


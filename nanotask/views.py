import os
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.db import transaction, connection
from django.utils import timezone
from .models import *

from django import http
from django.views.generic.base import View

import json
import secrets


@xframe_options_exempt
def load_base(request, project_name):
    project_settings = json.load(open("/root/DynamicCrowd/settings/projects/{}.json".format(project_name)))
    context = {
        "base_title": project_settings["DynamicCrowd"]["Title"],
        "base_instruction": loader.get_template("./{}/instruction.html".format(project_name)).render({}, request),
        "nanotasks_per_hit": project_settings["DynamicCrowd"]["NanotasksPerHIT"],
        "min_height": project_settings["AMT"]["FrameHeight"]
    }
    ret = render(request, "base.html", context=context)
    return ret


@csrf_exempt
def load_static_template(request, project_name, template_name):
    template_path = "./{}/{}.html".format(project_name,template_name)
    return render(request, template_path)


@csrf_exempt
def load_nanotask(request, project_name):
    if "preview" in request.GET:
        template_path = "./{}/preview.html".format(project_name)
        template = loader.get_template(template_path)
        response = {
            "info": {"id": None, "project_name": project_name, "template_name": "__preview__" },
            "html": template.render({}, request)
        } 
        return JsonResponse(response)

    else:
        request_json = json.loads(request.body)
        mturk_worker_id = request_json["mturk_worker_id"]
        session_tab_id = request_json["session_tab_id"]
        user_agent = request_json["user_agent"]
        nanotask = Nanotask.objects.using(project_name).filter(answer__mturk_worker_id=mturk_worker_id, answer__session_tab_id=session_tab_id, answer__value=None, project_name=project_name).order_by('id').first();
        if not nanotask:
            sql = "update {4}.nanotask_answer set mturk_worker_id='{0}', session_tab_id='{2}', user_agent='{3}', time_assigned='{5}' where mturk_worker_id is null and nanotask_id not in ( select nanotask_id from ( select distinct nanotask_id from {4}.nanotask_answer as a inner join {4}.nanotask_nanotask as n on a.nanotask_id=n.id where (a.mturk_worker_id='{0}' and n.project_name='{1}') or n.project_name<>'{1}') as tmp) order by nanotask_id asc, mturk_worker_id desc limit 1;".format(mturk_worker_id,project_name, session_tab_id, user_agent, project_name, timezone.now())
            with connection.cursor() as cursor:
                cursor.execute(sql)
            connection.close()
            nanotask = Nanotask.objects.using(project_name).filter(answer__mturk_worker_id=mturk_worker_id, answer__session_tab_id=session_tab_id, answer__value=None, project_name=project_name).order_by('id').first();
    
        if nanotask:
            media_data = json.loads(nanotask.media_data)
            template_path = "./{}/{}.html".format(project_name, nanotask.template_name)
            template = loader.get_template(template_path)

#            import pdb; pdb.set_trace()
            response = {
                "info": {"id": nanotask.id, "project_name": nanotask.project_name, "template_name": nanotask.template_name },
                "html": template.render(media_data, request)
            } 
            ret = JsonResponse(response)
        else:
            ret = JsonResponse({"info": None, "html": None}) 
        return ret


@csrf_exempt
def save_answer(request):
    request_json = json.loads(request.body)
    id = request_json["id"]
    sec = request_json["sec"]
    ans = request_json["answer"]
    mturk_worker_id = request_json["mturk_worker_id"]
    project_name = request_json["project_name"]

    with transaction.atomic():
        answer = Answer.objects.using(project_name).filter(nanotask_id=id, mturk_worker_id=mturk_worker_id).first()
        answer.value = json.dumps(ans)
        answer.time_submitted = timezone.now()
        answer.secs_elapsed = sec
        answer.save(using=project_name)

#    setting.notify_answer_listener(ans)
    return JsonResponse({})


@csrf_exempt
def save_assignment(request):
    request_json = json.loads(request.body)
    ids = request_json["ids"]
    mturk_assignment_id = request_json["mturk_assignment_id"]
    mturk_hit_id = request_json["mturk_hit_id"]
    mturk_worker_id = request_json["mturk_worker_id"]
    project_name = request_json["project_name"]
    amt_assignment = AMTAssignment(mturk_assignment_id = mturk_assignment_id,
                                   mturk_hit_id = mturk_hit_id,
                                   mturk_worker_id = mturk_worker_id)
    amt_assignment.save(using=project_name)
    sql = "UPDATE {0}.nanotask_answer SET amt_assignment_id='{1}' WHERE nanotask_id IN ({2}) AND mturk_worker_id='{3}';".format(project_name, amt_assignment.id, ",".join(map(str,ids)),  mturk_worker_id)
    with connection.cursor() as cursor:
        cursor.execute(sql)
    connection.close()
    return JsonResponse({})


# @csrf_exempt
# def create_nanotask(request, project_name, template_name):
#     project_settings = json.load(open("/root/DynamicCrowd/settings/projects/{}.json".format(project_name)))

#     request_json = json.loads(request.body)
#     create_id = secrets.token_hex(8)

#     with transaction.atomic():
#         print(request_json)

#         for row in request_json:
#             nanotask = Nanotask(project_name=project_name,
#                                 template_name=template_name,
#                                 media_data=json.dumps(row),
#                                 create_id=create_id)
#             print(nanotask)
#             nanotask.save(using=project_name)
#             for i in range(project_settings["DynamicCrowd"]["AnswersPerNanotask"]):
#                 answer = Answer(nanotask=nanotask)
#                 answer.save(using=project_name)


#     return JsonResponse({"nanotask_id":create_id})

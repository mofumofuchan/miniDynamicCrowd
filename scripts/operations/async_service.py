import os
import csv
import sys
import random
from datetime import datetime, timedelta
from tqdm import tqdm

import asyncio
from aiohttp import web, WSMsgType
import aiofiles
import concurrent

from urllib.parse import urlparse, parse_qs
import json
from io import StringIO
from io import BytesIO

from functools import reduce

import time
from datetime import datetime

from django.db import transaction
from django.forms.models import model_to_dict

import nanotask.models



class Server(object):

    API_ROOT = '/plugins/api/v1'
    STATIC_ROOT = '/plugins/static'

    def __init__(self, context):
        self.context = context
        self.args = context.parser.parse_args()
        #self.template_name = args.template_name
        self.last_time_id = int(time.time()*1000)
        self.retrial_images_queue = []
        self.last_update = datetime.min

    def next_time_id(self):
        now = int(time.time()*1000)
        if self.last_time_id < now:
            self.last_time_id = now
            return now
        else:
            self.last_time_id += 1

            return self.last_time_id

    def run_forever(self):
        self.loop = asyncio.get_event_loop()
        self.recogexec = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        #def process():
        #    self.recognizer = self.Recognizer()
        #future =  self.loop.run_in_executor(self.recogexec, process)
        #sqlexec = concurrent.futures.ThreadPoolExecutor()
        app = web.Application(loop=self.loop)
        #app.router.add_post(self.API_ROOT, self.post_url)
        #app.router.add_get('/ws/store/{name}', self.websocket_handler)
        #app.router.add_get('/ws/query_upload', self.websocket_query_upload)

        #app.router.add_get(self.API_ROOT+'/post_and_wait', self.websocket_handler)
        #app.router.add_get(self.API_ROOT+'/{prefix}/{box}/input.jpg', self.get_box)
        app.router.add_post(self.API_ROOT+'/cropped_images', self.append_cropped_images)
        app.router.add_post(self.API_ROOT+'/fetch_results', self.fetch_crowdsourced_results)
        app.router.add_static(self.STATIC_ROOT, './', show_index = True)

        handler = app.make_handler()
        #f = self.loop.create_server(handler, self.config.httpd_addr, self.config.httpd_port)
        f = self.loop.create_server(handler, '0.0.0.0', 8888)
        srv = self.loop.run_until_complete(f)
        #self.config.logger.notice('serving on [{}]'.format(srv.sockets[0].getsockname()))

        print('serving on [{}]'.format(srv.sockets[0].getsockname()))
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            srv.close()
            self.loop.run_until_complete(srv.wait_closed())
            self.loop.run_until_complete(app.shutdown())
            self.loop.run_until_complete(handler.shutdown(60.0))
            self.loop.run_until_complete(app.cleanup())
            self.loop.close()

    async def append_cropped_images(self, request):
        request_json = await request.json()
        response_json = []

        # FIXME TODO check json format

        for row in request_json:
            row['time_id'] = self.next_time_id()

        #[{'img_url': 'http://okimoto.r9n.net/images/40_cropped-test-images/181024_cropped-images/20170603/2017060310/20170603103021_0.jpg', 'posterior': 0.1483979970216751, 'cropped_id': '20170603103021_0'},
        # {'img_url': 'http://okimoto.r9n.net/images/40_cropped-test-images/181024_cropped-images/20170603/2017060310/20170603103021_1.jpg', 'posterior': 0.034577783197164536, 'cropped_id': '20170603103021_1'}]

        with transaction.atomic():
            for row in request_json:
                attrs = {"time_id":row["time_id"],
                         "image_url":row["img_url"],
                         "posterior":row["posterior"]}
                img = nanotask.models.CroppedImage(**attrs)
                print("saving: {}".format(attrs))  # FIXME debug
                img.save(using=self.context.project_name)

                response_json.append({"cropped_id":row["cropped_id"], "time_id":row["time_id"]})

        return web.json_response(response_json)

    async def fetch_crowdsourced_results(self, request):
        request_json = await request.json()

        try:
            since_time = datetime.strptime(request_json["since_time"], "%Y-%m-%d %H:%M:%S.%f")
        except (KeyError, ValueError) as e:
            print(e)
            response_json = {"status":"failed", "message":"invalid since_time format; '%Y-%m-%d %H:%M:%S.%f'"}
            return web.json_response(response_json)

        # Fetch answers which submitted time are later than self.last_update
        db_results = nanotask.models.CroppedImage.objects.using(self.context.project_name).raw("""
        SELECT id, time_id, valid_all_count, valid_yes_count, invalid_all_count, invalid_yes_count
        FROM nanotask_croppedimage
        WHERE
          time_finished > '{0}';
        """.format(since_time.strftime("%Y-%m-%d %H:%M:%S.%f")))
        db_results = list(db_results)

        # return finished time of processing
        results_json = [{"time_id":item["time_id"],
                         "valid_all_count":item["valid_all_count"],
                         "valid_yes_count":item["valid_yes_count"],
                         "invalid_all_count":item["invalid_all_count"],
                         "invalid_yes_count":item["invalid_yes_count"]} \
                        for item in db_results]

        return web.json_response(results_json)


def run(context):
    server = Server(context)
    server.run_forever()

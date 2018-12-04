import os
import csv
import sys
sys.path.append("/root/DynamicCrowd")
import argparse
from tqdm import tqdm

import asyncio
from aiohttp import web, WSMsgType
import aiofiles
import concurrent

from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import json
from io import StringIO
from io import BytesIO

from functools import reduce

import time
from datetime import datetime

from django.db import transaction
from django.forms.models import model_to_dict

import nanotask.models


class TimeIDGenerator(object):
    def __init__(self):
        self.last_time_id = int(time.time()*1000)

    def next_time_id(self):
        now = int(time.time()*1000)
        if self.last_time_id < now:
            self.last_time_id = now
            return now
        else:
            self.last_time_id += 1

            return self.last_time_id


def run(context):
    #IMG_LIST = "scripts/operations/tmp_cow_labeled_images/cats.list"
    IMG_LIST = "scripts/operations/tmp_cow_labeled_images/5a_1_selected_selected.list"
    #IMAGE_ROOT_URL = "http://okimoto.r9n.net/images/40_cropped-test-images/cats"
    IMAGE_ROOT_URL = "http://okimoto.r9n.net/images/40_cropped-test-images/180522_anomaly-list_24h-9days_5a/1"
    PRIORITY = 0
    #PRIORITY = -10

    time_id_generator = TimeIDGenerator()

    # Add images to CroppedImage
    with open(IMG_LIST) as f:
        fnames = [line.strip() for line in f.readlines()]

    print("saving images")
    with transaction.atomic():
        for fname in tqdm(fnames):
            img_url = IMAGE_ROOT_URL + "/" + fname

            cropped_image = nanotask.models.CroppedImage()

            cropped_image.time_id = time_id_generator.next_time_id()
            cropped_image.image_url = img_url
            #cropped_image.priority = -10
            cropped_image.priority = PRIORITY
            cropped_image.save(using=context.project_name)

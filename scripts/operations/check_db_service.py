import os
import csv
import sys
import random
from datetime import datetime, timedelta
from tqdm import tqdm
import pdb

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

NORMAL_PRIORITY = 0
LOW_PRIORITY = -10

NUM_CROPPED_IMAGES_IN_BAG = 10
NUM_LABELED_IMAGES_YES = 1
NUM_LABELED_IMAGES_NO = 1

NUM_LEAST_NANOTASKS = 10


class Periodic(object):
    def __init__(self, context, template_name):
        self.context = context
        self.args = context.parser.parse_args()
        self.template_name = template_name
        self.last_time_id = int(time.time()*1000)
        self.retrial_images_queue = []
        self.last_update = datetime.min
        self.period_time = 40

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

        task = self.loop.create_task(self.update_db())

        print('starting checking db')
        try:
            self.loop.run_until_complete(task)
        except KeyboardInterrupt:
            pass
        finally:
            print("KeybordInterrupt; finish")

    async def update_db(self):
        while True:
            print("update db!")
            self.read_answers()
            self.create_nanotask()
            await asyncio.sleep(self.period_time)

    def read_answers(self):
        YES_TOKEN = "yes_labeled"
        NO_TOKEN = "no_labeled"
        TAGGING_TOKEN = "tagging"

        context = self.context

        # Fetch answers which submitted time are later than self.last_update

        update_time_new = datetime.now()
        answers = nanotask.models.Answer.objects.using(context.project_name).raw("""
        SELECT id, value FROM nanotask_answer
        WHERE (time_submitted > '{0}') AND (time_submitted < '{1}')
        """.format(self.last_update.strftime("%Y-%m-%d %H:%M:%S.%f"),
                   update_time_new.strftime("%Y-%m-%d %H:%M:%S.%f")))
        answers = list(answers)
        self.last_update = update_time_new

        # Pick up spammer
        valid_answers = []
        invalid_answers = []
        for answer in answers:
            answer_values = json.loads(answer.value)
            count_yes_labeled = len([item for item in answer_values if item["type"] == YES_TOKEN])
            count_no_labeled = len([item for item in answer_values if item["type"] == NO_TOKEN])

            if count_yes_labeled == NUM_LABELED_IMAGES_YES and count_no_labeled == 0:
                valid_answers.append(answer_values)
            else:
                invalid_answers.append(answer_values)

        #for invalid_answer in invalid_answers:
        with transaction.atomic():
            cropped_img_ids = []

            for invalid_answer in tqdm(invalid_answers):
                for img_info in invalid_answer:
                    if img_info["type"] != TAGGING_TOKEN:
                        continue

                    nano_nanotask = nanotask.models.NanoNanotask.objects.\
                                    using(self.context.project_name).\
                                    filter(time_id=img_info["id"]).first()

                    nano_nanotask.is_spam = True

                    if img_info["ans"] == "yes":
                        nano_nanotask.answer = 1
                    elif img_info["ans"] == "no":
                        nano_nanotask.answer = 0
                    nano_nanotask.time_finished = datetime.now()
                    nano_nanotask.save()

                    cropped_id = nano_nanotask.cropped_id
                    cropped_image = nanotask.models.CroppedImage.objects.\
                                    using(self.context.project_name).\
                                    filter(id=cropped_id).first()

                    if cropped_image.invalid_all_count is None:
                        cropped_image.invalid_all_count = 1
                        cropped_image.invalid_yes_count = 0
                    else:
                        cropped_image.invalid_all_count += 1
                    if img_info["ans"] == "yes":
                        cropped_image.invalid_yes_count += 1
                    cropped_image.save()

                    cropped_img_ids.extend(sorted(set(nano_nanotask.cropped_id), key=nano_nanotask.cropped_id.index))

            #pdb.set_trace()

            self.retrial_images_queue.extend(cropped_img_ids)
            self.retrial_images_queue = sorted(set(self.retrial_images_queue), key=self.retrial_images_queue.index)

            # update cropped_images table
            for valid_answer in tqdm(valid_answers):
                for img_info in valid_answer:
                    if img_info["type"] != TAGGING_TOKEN:
                        continue

                    nano_nanotask = nanotask.models.NanoNanotask.objects.\
                                    using(self.context.project_name).\
                                    filter(time_id=img_info["id"]).first()

                    nano_nanotask.is_spam = False
                    nano_nanotask.time_finished = datetime.now()
                    nano_nanotask.answer = img_info["ans"]

                    if img_info["ans"] == "yes":
                        nano_nanotask.answer = 1
                    elif img_info["ans"] == "no":
                        nano_nanotask.answer = 0
                    nano_nanotask.time_finished = datetime.now()
                    nano_nanotask.save()

                    cropped_id = nano_nanotask.cropped_id
                    cropped_image = nanotask.models.CroppedImage.objects.\
                                    using(self.context.project_name).\
                                    filter(id=cropped_id).first()

                    pdb.set_trace()

                    if cropped_image.valid_all_count is None:
                        cropped_image.valid_all_count = 1
                        cropped_image.valid_yes_count = 0
                    else:
                        cropped_image.valid_all_count += 1
                    if img_info["ans"] == "yes":
                        cropped_image.valid_yes_count += 1
                    cropped_image.save()

    def create_nanotask(self):
        template_name = self.template_name

        not_issued_images = nanotask.models.CroppedImage.objects.raw("""
        SELECT * FROM {0}.nanotask_croppedimage
        WHERE nanotask_issued = 0 AND priority = {1};
        """.format(self.context.project_name, NORMAL_PRIORITY))
        not_issued_images = list(not_issued_images)

        # get images for retrial
        if len(self.retrial_images_queue) > 0:
            retrial_images = nanotask.models.CroppedImage.objects.using(self.context.project_name).raw("""
            SELECT * FROM nanotask_croppedimage
            WHERE id IN ({0});
            """.format(",".join(self.retrial_images_queue)))
            retrial_images = list(retrial_images)
            self.retrial_images_queue = []

            not_issued_images.extend(retrial_images)

        asked_images = not_issued_images

        # generate nano_nanotask

        # If there are only less than the # of images, fill the bag with low-priority images
        # fill more nanotasks if there are too few nanotasks
        if len(asked_images) % NUM_CROPPED_IMAGES_IN_BAG == 0:
            num_remained_images = NUM_LEAST_NANOTASKS - (len(asked_images) // NUM_CROPPED_IMAGES_IN_BAG)
        else:
            num_remained_images = NUM_CROPPED_IMAGES_IN_BAG - \
                              (len(asked_images) % NUM_CROPPED_IMAGES_IN_BAG)
            n_nanotasks = NUM_LEAST_NANOTASKS - ((len(asked_images) // NUM_CROPPED_IMAGES_IN_BAG) + 1)
            num_remained_images += n_nanotasks * NUM_CROPPED_IMAGES_IN_BAG

        if num_remained_images > 0:
            # # Fetch low-priority images
            low_priority_images = nanotask.models.CroppedImage.objects.raw("""
            SELECT * FROM {0}.nanotask_croppedimage
            WHERE priority = {1}
            ORDER BY time_created
            LIMIT {2}
            """.format(self.context.project_name, LOW_PRIORITY, num_remained_images))

            low_priority_images = list(low_priority_images)
            asked_images.extend(low_priority_images)

        # Split images to each N images
        split_asked_images = [asked_images[i:i+NUM_CROPPED_IMAGES_IN_BAG] for i in \
                              range(0, len(asked_images), NUM_CROPPED_IMAGES_IN_BAG)]

        # Add two labeled images to each images sets.
        for bag in split_asked_images:
            yes_imgs = nanotask.models.YesLabeledImage.objects.raw('''
            SELECT * FROM {0}.nanotask_yeslabeledimage
            '''.format(self.context.project_name))
            yes_imgs = list(yes_imgs)
            random.shuffle(yes_imgs)
            yes_selected_images = yes_imgs[:NUM_LABELED_IMAGES_YES]

            no_imgs = nanotask.models.NoLabeledImage.objects.raw('''
            SELECT * FROM {0}.nanotask_nolabeledimage
            '''.format(self.context.project_name))
            no_imgs = list(no_imgs)
            random.shuffle(no_imgs)
            no_selected_images = no_imgs[:NUM_LABELED_IMAGES_NO]

            bag.extend(yes_selected_images)
            bag.extend(no_selected_images)
            random.shuffle(bag)

        # create nanotask and nano_nanotasks
        nanotasks = []

        for bag in split_asked_images:
            nano_nanotask_records = []
            nanotask_dict = {}

            for i, item in enumerate(bag):
                nano_nanotask = nanotask.models.NanoNanotask()
                time_id = self.next_time_id()

                nanotask_dict["image_url{}".format(i)] = item.image_url
                nanotask_dict["id{}".format(i)] = time_id
                nano_nanotask.time_id = time_id
                if type(item) == nanotask.models.CroppedImage:
                    nano_nanotask.cropped_id = item.id
                    nanotask_dict["type{}".format(i)] = "tagging"
                elif type(item) == nanotask.models.YesLabeledImage:
                    nano_nanotask.yes_labeled_image_id = item.id
                    nanotask_dict["type{}".format(i)] = "yes_labeled"
                elif type(item) == nanotask.models.NoLabeledImage:
                    nano_nanotask.no_labeled_image_id = item.id
                    nanotask_dict["type{}".format(i)] = "no_labeled"
                else:
                    raise RuntimeError

                nano_nanotask_records.append(nano_nanotask)

            def generate():
                yield nanotask_dict

            # create nanotasks and answers
            with transaction.atomic():
                nanotask_id = self.context.save_nanotasks(template_name=template_name,
                                                          generator=generate())

                print(nanotask_id)
                for nano_nanotask in nano_nanotask_records:
                    nano_nanotask.nanotask_id = nanotask_id
                    if nano_nanotask.cropped_id is not None:
                        cropped_image = nanotask.models.CroppedImage.objects.\
                                        using(self.context.project_name).\
                                        filter(id=nano_nanotask.cropped_id).first()
                        cropped_image.nanotask_issued += 1
                        cropped_image.save()
                    nano_nanotask.save(using=self.context.project_name)

        print("DONE")


def run(context):
    TEMPLATE_NAME = "okimoto_balloon"

    periodic = Periodic(context, TEMPLATE_NAME)
    periodic.run_forever()

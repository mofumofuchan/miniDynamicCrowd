import os
import csv
import sys
sys.path.append("/root/DynamicCrowd")

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

import argparse

from tqdm import tqdm


def run(context):
    YES_LIST = "scripts/operations/tmp_cow_labeled_images/yes.list"
    NO_LIST = "scripts/operations/tmp_cow_labeled_images/no.list"

    # Add images to YesLabeledImage
    YES_IMAGE_ROOT_URL = "http://okimoto.r9n.net/images/40_cropped-test-images/180129_balllon_test-new/yes"
    with open(YES_LIST) as f:
        fnames = [line.strip() for line in f.readlines()]

    print("saving yes images")
    with transaction.atomic():
        for fname in tqdm(fnames):
            img_url = YES_IMAGE_ROOT_URL + "/" + fname
            yes_labeled_image = nanotask.models.YesLabeledImage(image_url=img_url)
            yes_labeled_image.save(using=context.project_name)

    # Add images to NoLabeledImage
    NO_IMAGE_ROOT_URL = "http://okimoto.r9n.net/images/40_cropped-test-images/180129_balllon_test-new/no"
    with open(NO_LIST) as f:
        fnames = [line.strip() for line in f.readlines()]

    print("saving no images")
    with transaction.atomic():
        for fname in tqdm(fnames):
            img_url = NO_IMAGE_ROOT_URL + "/" + fname
            no_labeled_image = nanotask.models.NoLabeledImage(image_url=img_url)
            no_labeled_image.save(using=context.project_name)

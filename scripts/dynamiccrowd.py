#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import django
import csv
import sys
import json
import concurrent.futures
import boto3
import argparse
import secrets
sys.path.append(".")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DynamicCrowd.settings')
django.setup()
from nanotask.models import *
from django.db import transaction
from django.forms.models import model_to_dict

from tqdm import tqdm

class Context:

    def __init__(self, setting):
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("operation", help="DynamicCrowd operation (put \"operations.\" before operation name)")
        self.parser.add_argument("project_name", help="Project name")
        self.operation = sys.argv[1]
        self.project_name = sys.argv[2]

        with open(setting) as f:
            self.settings = json.load(f)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    
    def get_mturk_client(self, is_sandbox):
        if is_sandbox:
            endpoint_url = "https://mturk-requester-sandbox.us-east-1.amazonaws.com"
        else:
            endpoint_url = "https://mturk-requester.us-east-1.amazonaws.com"
        
        return boto3.client('mturk',
                    aws_access_key_id = self.settings["AMT"]["Credentials"]["AWSAccessKeyId"],
                    aws_secret_access_key = self.settings["AMT"]["Credentials"]["AWSSecretAccessKey"],
                    region_name = "us-east-1",
                    endpoint_url = endpoint_url
        )
    
    def save_nanotasks(self, template_name, generator, total=0):
        create_id = secrets.token_hex(8)
        with open("/root/DynamicCrowd/settings/projects/{}.json".format(self.project_name)) as f:
            settings = json.load(f)
        with transaction.atomic():
            for row in tqdm(generator, total=total):
                nanotask = Nanotask(project_name=self.project_name, template_name=template_name, media_data=json.dumps(row), create_id=create_id)
                nanotask.save(using=self.project_name)
                for i in range(settings["DynamicCrowd"]["AnswersPerNanotask"]):
                    answer = Answer(nanotask=nanotask)
                    answer.save(using=self.project_name)

        return create_id

    def export_answers(self, callback):
        for row in Answer.objects.using(self.project_name).filter(nanotask__project_name=self.project_name):
            callback(model_to_dict(row), model_to_dict(row.nanotask))


def main():
    context = Context("/root/DynamicCrowd/settings/global.json")
    mod = __import__(context.operation, fromlist=["run"])
    run = getattr(mod,"run")
    run(context)


if __name__=="__main__":
    main()

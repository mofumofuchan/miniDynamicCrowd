from django.db import models

# Create your models here.

class AMTAssignment(models.Model):
    mturk_assignment_id = models.CharField(max_length=255)
    mturk_hit_id = models.CharField(max_length=255, blank=True, null=True)  # allow blank for testing
    mturk_worker_id = models.CharField(max_length=255, blank=True, null=True)  # allow blank for testing
    bonus_amount = models.FloatField(default=0.0)
    time_created = models.DateTimeField(auto_now_add=True)
    time_bonus_sent = models.DateTimeField(blank=True, null=True)


class HIT(models.Model):
    mturk_hit_id = models.CharField(max_length=255)
    project_name = models.CharField(max_length=255)
    is_sandbox = models.IntegerField()
    time_created = models.DateTimeField(auto_now_add=True)
    time_expired = models.DateTimeField(blank=True, null=True)


class Nanotask(models.Model):
    project_name = models.TextField(max_length=255)
    template_name = models.TextField(max_length=255)
    media_data = models.TextField(blank=True, default="{}")
    create_id = models.CharField(max_length=100)
    time_created = models.DateTimeField(auto_now_add=True)


class Answer(models.Model):
    nanotask = models.ForeignKey(Nanotask, on_delete=models.CASCADE)
    amt_assignment = models.ForeignKey(AMTAssignment, on_delete=models.CASCADE, blank=True, null=True)
    mturk_worker_id = models.CharField(max_length=255, blank=True, null=True)
    session_tab_id = models.CharField(max_length=32)
    value = models.TextField(blank=True, null=True)
    time_created = models.DateTimeField(auto_now_add=True)
    time_assigned = models.DateTimeField(blank=True, null=True)
    time_submitted = models.DateTimeField(blank=True, null=True)
    secs_elapsed = models.FloatField(default=0.0)
    user_agent = models.CharField(max_length=255)


class CroppedImage(models.Model):
    time_id = models.CharField(blank=False, max_length=15)
    image_url = models.TextField(blank=True, default="")
    posterior = models.FloatField(default=0.0)
    priority = models.IntegerField(default=0)
    time_created = models.DateTimeField(auto_now_add=True)
    nanotask_issued = models.IntegerField(default=0)
    valid_all_count = models.IntegerField(blank=True, null=True)
    valid_yes_count = models.IntegerField(blank=True, null=True)
    invalid_all_count = models.IntegerField(blank=True, null=True)
    invalid_yes_count = models.IntegerField(blank=True, null=True)
    time_finished = models.DateTimeField(blank=True, null=True)


class YesLabeledImage(models.Model):
    image_url = models.TextField(blank=True, default="")
    time_created = models.DateTimeField(auto_now_add=True)


class NoLabeledImage(models.Model):
    image_url = models.TextField(blank=True, default="")
    time_created = models.DateTimeField(auto_now_add=True)


class NanoNanotask(models.Model):
    time_id = models.CharField(blank=False, null=False, max_length=15)
    nanotask_id = models.CharField(max_length=100, null=False)
    cropped_id = models.CharField(max_length=32, blank=True, null=True)
    yes_labeled_image_id = models.CharField(max_length=32, blank=True, null=True)
    no_labeled_image_id = models.CharField(max_length=32)
    is_spam = models.NullBooleanField(blank=True, null=True)
    answer = models.IntegerField(blank=True, null=True)
    time_created = models.DateTimeField(auto_now_add=True)
    time_finished = models.DateTimeField(blank=True, null=True)

"""
Script to send events to SQS for review scraping
"""

import os

import boto3

SQS_ADDRESS = os.environ.get('SQS_ADDRESS')

sqs = boto3.client('sqs')

with open(os.path.join('scrape','missing_pages.txt')) as f:
    urls = f.read().split('\n')

for url in urls:
    sqs.send_message(
        QueueUrl=SQS_ADDRESS,
        MessageBody=url
    )
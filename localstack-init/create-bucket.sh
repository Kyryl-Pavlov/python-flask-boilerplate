#!/bin/sh
awslocal s3 mb s3://media-bucket
echo "Bucket media-bucket created"

awslocal sqs create-queue --queue-name events-queue
echo "Queue events-queue created"

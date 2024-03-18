import boto3
import time
from botocore.exceptions import ClientError  # Import ClientError for error handling
from decouple import config  # For loading AWS credentials from environment variables
import logging

# Load AWS credentials from environment variables
aws_access_key_id = config('AWS_ACCESS_KEY_ID')
aws_secret_access_key = config('AWS_SECRET_ACCESS_KEY')
ami_id = "ami-016e727b2dd2d09b4"
key_pair_name = 'my_key_pair'

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQS and EC2 clients
sqs_req_client = boto3.client('sqs', region_name='us-east-1', 
                          aws_access_key_id=aws_access_key_id, 
                          aws_secret_access_key=aws_secret_access_key)
ec2_app_client = boto3.client('ec2', region_name='us-east-1', 
                          aws_access_key_id=aws_access_key_id, 
                          aws_secret_access_key=aws_secret_access_key)

# SQS queue URLs
req_queue_url = 'https://sqs.us-east-1.amazonaws.com/905418105068/1229729529-req-queue'
resp_queue_url = 'https://sqs.us-east-1.amazonaws.com/905418105068/1229729529-resp-queue'

# Define thresholds
max_instances = 20

instance_ids = []

def get_queue_size(queue_url):
    response = sqs_req_client.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(response['Attributes']['ApproximateNumberOfMessages'])

def launch_ec2_instances(count):
    # Launch 'count' number of EC2 instances
    instance_ids = []
    for i in range(count):
        value = 'app-tier-instance-' + str(i+1)
        response = ec2_app_client.run_instances(
            ImageId=ami_id,
            InstanceType="t2.micro",
            KeyName=key_pair_name,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': value}]
                }]
            # Add any other parameters you need
        )
        instance_ids.append(response['Instances'][0]['InstanceId'])
        # instance_ids = [instance['InstanceId'] for instance in response['Instances']]
    return instance_ids

def terminate_ec2_instances(instance_ids):
    # Terminate EC2 instances
    ec2_app_client.terminate_instances(InstanceIds=instance_ids)

def auto_scale():
    while True:
        consecutive_message_counts = 0
        last_req_queue_size = -1
        global instance_ids
        instance_ids = []
        req_queue_size = get_queue_size(req_queue_url)
        
        if req_queue_size == 0:
            continue
        else:
            while True:
                req_queue_size = get_queue_size(req_queue_url)
                if req_queue_size > 10:
                    instance_ids = launch_ec2_instances(20)
                    break
                if req_queue_size == last_req_queue_size:
                    consecutive_message_counts += 1
                else:
                    consecutive_message_counts = 0
                    
                if consecutive_message_counts == 3:
                    if req_queue_size == 10:
                        instance_ids = launch_ec2_instances(10)
                        break
                last_req_queue_size = req_queue_size
                    
        # after scaling up and when the req_queue size becomes zero, we need to scale down
        consecutive_message_counts = 0
        last_req_queue_size = -1
        while True:
            req_queue_size = get_queue_size(req_queue_url)
            if req_queue_size == 0 and last_req_queue_size == 0:
                consecutive_message_counts += 1 
            else:
                consecutive_message_counts = 0
                
            if consecutive_message_counts == 3 and req_queue_size == 0:
                terminate_ec2_instances(instance_ids)
                break
            last_req_queue_size = req_queue_size 
        sqs_req_client.purge_queue(QueueUrl=resp_queue_url)
            

if __name__ == "__main__":
    auto_scale()

from flask import Flask, request, jsonify
import pandas as pd
import boto3
from botocore.exceptions import ClientError  # Import ClientError for error handling
from decouple import config  # For loading AWS credentials from environment variables
import logging


app = Flask(__name__)

# Load AWS credentials from environment variables
aws_access_key_id = config('AWS_ACCESS_KEY_ID')
aws_secret_access_key = config('AWS_SECRET_ACCESS_KEY')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
    
def msg_to_sqs_req(filename):
    try:
        # Send the image file name to sqs_req_queue
        sqs_req_queue = boto3.client('sqs', region_name='us-east-1',
                                     aws_access_key_id=aws_access_key_id, 
                                     aws_secret_access_key=aws_secret_access_key) # initialize sqs_req_queue
        req_queue_url = 'https://sqs.us-east-1.amazonaws.com/905418105068/1229729529-req-queue'   # URL of SQS queue
        msg_body = filename

        # Sending msg body to queue
        response = sqs_req_queue.send_message(
            QueueUrl=req_queue_url,
            MessageBody=msg_body
        )

        # Log successful message
        logger.info("Message sent successfully. MessageId: %s", response['MessageId'])

    except Exception as e:
        # Log error
        logger.error("An error occurred while sending message: %s", str(e))



def check_message(message,filename):
    # Get the message body
    message_body = message['Body']
    
    # Extract image name and classification from the message body
    message_name, classification = message_body.split(':')
    
    #image_name from filename.jpg
    image_name = filename.split('.')[0]

    # Check if the image name is relevant to the current consumer
    if message_name.strip() == image_name:
        # If relevant, you can perform further actions here if needed
        logger.info(f"Received relevant message for image: {image_name}, classification: {classification.strip()}")
        return True
    else:
        # If not relevant, continue polling
        # logger.info(f"Ignore message for image: {image_name.strip()}, continue polling...")
        return False

    

def msg_from_sqs_resp(filename):
    try:
        while True:
            sqs_resp_queue = boto3.client('sqs', region_name='us-east-1',
                                          aws_access_key_id=aws_access_key_id, 
                                          aws_secret_access_key=aws_secret_access_key) # initialize sqs_resp_queue
            resp_queue_url = 'https://sqs.us-east-1.amazonaws.com/905418105068/1229729529-resp-queue'   # URL of SQS queue
            # Receive message from SQS queue
            response = sqs_resp_queue.receive_message(
                QueueUrl=resp_queue_url,
                MaxNumberOfMessages=1,
                VisibilityTimeout=0  # Message will be immediately visible to other consumers
            )

            if 'Messages' in response:
                message = response['Messages'][0]
                
                
                # Process the received message
                if check_message(message, filename):
                    # If message is relevant, delete it from the queue
                    receipt_handle = message['ReceiptHandle']
                    sqs_resp_queue.delete_message(
                        QueueUrl=resp_queue_url,
                        ReceiptHandle=receipt_handle
                    )
                    logger.info("Message processed and deleted from the queue.")
                    result = message['Body']
                    return result
                # else:
                #     logger.info("Continuing to poll the queue.")
            # else:
            #     logger.info("No messages available in the queue. Continuing to poll.")
    except Exception as e:
        # Handle any unexpected exceptions
        logger.error(f"An error occurred: {str(e)}")
        
def s3_msg_store(image_file):
    try:
        image_name = image_file.filename
        bucket_name = '1229729529-in-bucket'
        s3 = boto3.client('s3', region_name='us-east-1',
                          aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        s3.put_object(Bucket=bucket_name, Key=image_name, Body=image_file)
        logger.info(f"Uploaded {image_name} to bucket {bucket_name}")
        return True
    except Exception as e:
        logger.error(f"Error uploading {image_name} to bucket {bucket_name}: {e}")
        return False
        
        
@app.route('/', methods=['POST'])
def web_tier():
    # Get the image file from the request
    image_file = request.files['inputFile']
    filename = image_file.filename
    s3_msg_store(image_file)
    msg_to_sqs_req(filename)
    return msg_from_sqs_resp(filename)
    
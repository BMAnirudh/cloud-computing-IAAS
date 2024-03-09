import boto3
from botocore.exceptions import ClientError  # Import ClientError for error handling
from decouple import config  # For loading AWS credentials from environment variables

# Initialize Boto3 session with provided AWS credentials
ec2_resource = boto3.resource(
    'ec2', 
    region_name='us-east-1',  
    aws_access_key_id=config('AWS_ACCESS_KEY_ID'), 
    aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY')
)

# AMI ID
ami_id = "ami-00ddb0e5626798373"

# Define tags for the instance
tags = [{'Key': 'Name', 'Value': 'web-instance'}]

# Specify the name of the key pair
key_pair_name = 'my_key_pair'

# Check if any instance exists
instances = list(ec2_resource.instances.filter(Filters=[
    {'Name' : 'instance-state-name', 'Values': ['running','stopped']}
]))

try:
    if instances:
        # If instance(s) already exist(s), run the first instance found
        existing_instance = instances[0]
        if existing_instance.state['Name'] == 'stopped':
            ec2_resource.instances.filter(InstanceIds=[existing_instance.id]).start()
            print("Instance already exists. Starting the existing instance with ID:", existing_instance.id)
        elif existing_instance.state['Name'] == 'running':
            print("Instance already exists and is already running. Instance ID:", existing_instance.id)
    else:
        # If no instance exists, create a new instance and run it
        print("No instance exists. Creating a new instance...")
        
        # Launch EC2 instance
        new_instance = ec2_resource.create_instances(
            ImageId=ami_id,
            MinCount=1,
            MaxCount=1,
            InstanceType="t2.micro",
            KeyName=key_pair_name,
            TagSpecifications=[{
                'ResourceType': 'instance',
                'Tags': tags
            }]
        )[0]  # Get the first instance in the list

        # Start the instance
        new_instance.start()

        # Output instance ID
        print("webTier instance ID:", new_instance.id)
        print("API call was successful.")


except ClientError as e:
    print("An error occurred:", e)
    print("API call was not successful.")
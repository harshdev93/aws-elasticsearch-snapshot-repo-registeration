import boto3
import time
import json
import sys
import uuid
import requests
import datetime

es_arn = raw_input("Enter your ES cluster ARN: ")

def createBucket(s3_bucket_name, es_region):

    s3_client = boto3.client('s3')

    if es_region == "us-east-1":
        s3_create_bucket_response = s3_client.create_bucket(
            Bucket=s3_bucket_name)
    else:
        s3_create_bucket_response = s3_client.create_bucket(
            Bucket=s3_bucket_name,
            CreateBucketConfiguration={'LocationConstraint': es_region}
        )

def get_es_arn(es_domain, es_region):
    es_client = boto3.client('es', region_name=es_region)

    es_response = es_client.describe_elasticsearch_domain(
        DomainName=es_domain
    )

    return es_response

def get_instance_profile_arn():

    res = requests.get("http://169.254.169.254/latest/meta-data/instance-id")
    instance_id = str(res.text)

    client = boto3.client('ec2', region_name=es_region)

    response = client.describe_iam_instance_profile_associations(
        Filters=[
            {
                'Name': 'instance-id',
                'Values': [instance_id]
            }
        ]
    )

    inst_profile_arn = response["IamInstanceProfileAssociations"][0]["IamInstanceProfile"]["Arn"]
    inst_profile_arn = inst_profile_arn.split("/")[1]
    return inst_profile_arn

def del_iam_role(snapshot_role_name):

    client = boto3.client('iam')

    response = client.delete_role(RoleName=snapshot_role_name)


def del_iam_policy(policy_name, role_name):

    client = boto3.client('iam')
    response = client.detach_role_policy(
    RoleName=role_name,
    PolicyArn=policy_name)

    time.sleep(2)

    response = client.delete_policy(PolicyArn=policy_name)

try:
    es_domain = es_arn.split("/")[1]
    es_region = es_arn.split(":")[3]

    s3_bucket_name = es_domain + "-es-repo-bucket-" + str(uuid.uuid4()).split("-")[0]
    createBucket(s3_bucket_name, es_region)
except:
    print("Please enter a valid ARN.. exiting")
    sys.exit()

snapshot_role_name = "TheSnapshotRole-"+ str(uuid.uuid4()).split("-")[0]
snapshot_policy_name = "TheSnapshotPolicy-"+ str(uuid.uuid4()).split("-")[0]
instance_profile_policy = "TheSnapshotInstanceProfilePolicy-"+ str(uuid.uuid4()).split("-")[0]

trust_relationship = {
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "",
    "Effect": "Allow",
    "Principal": {
      "Service": "es.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}

role_policy = {
  "Version": "2012-10-17",
  "Statement": [{
      "Action": [
        "s3:ListBucket"
      ],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::"+s3_bucket_name
      ]
    },
    {
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Effect": "Allow",
      "Resource": [
        "arn:aws:s3:::"+s3_bucket_name+"/*"
      ]
    }
  ]
}

iam_client = boto3.client('iam')

policy_response = iam_client.create_policy(
        PolicyName=snapshot_policy_name,
    PolicyDocument=json.dumps(role_policy)
)

get_policy_arn = policy_response["Policy"]["Arn"]

time.sleep(2)

role_response = iam_client.create_role(
    RoleName=snapshot_role_name,
    AssumeRolePolicyDocument=json.dumps(trust_relationship)
)

get_role_arn = role_response["Role"]["Arn"]

attach_role_policy_response = iam_client.attach_role_policy(
    RoleName=snapshot_role_name,
    PolicyArn=get_policy_arn
)

es_domain_arn = get_es_arn(es_domain,es_region)["DomainStatus"]["ARN"]  
es_endpoint = get_es_arn(es_domain,es_region)
if "VPCOptions" in es_endpoint["DomainStatus"]:
    es_endpoint = get_es_arn(es_domain,es_region)["DomainStatus"]["Endpoints"]["vpc"]
else:
    es_endpoint = get_es_arn(es_domain,es_region)["DomainStatus"]["Endpoint"]
user_pol = {
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": get_role_arn
    },
    {
      "Effect": "Allow",
      "Action": "es:ESHttpPut",
      "Resource": es_domain_arn+"/*"
    }
  ]
}

["vpc"]

policy_response_2 = iam_client.create_policy(
    PolicyName=instance_profile_policy,
    PolicyDocument=json.dumps(user_pol)
)

instance_profile_role_name = get_instance_profile_arn()
attach_role_policy_response = iam_client.attach_role_policy(
    RoleName=instance_profile_role_name,
    PolicyArn=policy_response_2["Policy"]["Arn"]
)

print("Starting the snapshot repository registeration...")

time.sleep(15)

###############################################
# Registering the repository
###############################################

from requests_aws4auth import AWS4Auth

host = "https://" + es_endpoint + "/" 
region = es_region
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

# Register repository

now = datetime.datetime.today()
# str_now = now.isoformat()
repo_name = "snapshot-repo-" + es_domain
snapshot_name = "snapshot-" + str(now.year) + '-' + str(now.month) + '-' + str(now.day)

path = '_snapshot/'+repo_name  # snapshot path
url = host + path

payload = {
  "type": "s3",
  "settings": {
    "bucket": s3_bucket_name,
    "region": es_region,
    "role_arn": get_role_arn
  }
}

headers = {"Content-Type": "application/json"}

rep = requests.put(url, auth=awsauth, json=payload, headers=headers)

print("Registering Repository in progress for host:", host)
print(rep.status_code)
print(rep.text)

# Take snapshot

path = '_snapshot/'+repo_name+'/'+snapshot_name
url = host + path

snap = requests.put(url, auth=awsauth)

print("Taking snapshot....")
print(snap.text)

time.sleep(5)

# Deleting the IAM role/policies created
del_iam_policy(get_policy_arn,snapshot_role_name)
del_iam_policy(policy_response_2["Policy"]["Arn"],instance_profile_role_name)
del_iam_role(snapshot_role_name)

if int(rep.status_code) == 200 and int(snap.status_code) == 200:
  print("------------DETAILS------------")
  print("Snapshot S3 Bucket Name: ", s3_bucket_name)
  print("Repository name: ", repo_name)
  print("Snapshot Name: ", snapshot_name)

print("Fin..")

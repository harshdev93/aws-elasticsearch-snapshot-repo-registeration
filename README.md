# Overview

This script makes it easy to register a snapshot repository/take snapshot. It handles the creation of AWS resources such as of IAM Roles/Policies which is required when registering a repository.The only input it takes is the cluster ARN.

## Prerequisites:

1) EC2 instance and an IAM role attached to it as an instance profile role.

### Steps:


1) Create an EC2 instance with Amazon Linux 2 AMI
2) Create an IAM Role with EC2 as the service (Allows EC2 instances to call AWS services on your behalf) and attach the following managed policies:
- IAMFullAccess
- AmazonS3FullAccess
- AmazonESReadOnlyAccess
AmazonEC2ReadOnlyAccess
3) Attach this role as an Instance profile role to the EC2 instance. This you can do by going to the EC2 console, select the EC2, click on Actions -> Instance settings -> Attach/Replace IAM role and select the role you created above and attach it.
4) SSH to the EC2 instance.
5) Install pip
$ sudo yum -y install python-pip

6) Install the following python dependencies:
$ sudo pip install boto3
$ sudo pip install requests-aws4auth

7) Copy the script below and save it to a file with .py extension
$ sudo vim snap-repo.py

8) Save and run it
python snap-repo.py

9) Provide the ES domain ARN as input for the domain you would like to register/take snapshot.
10) If the script runs successfully, you would get the details such as the name of the S3 bucket in your account containing the repository/ snapshot data, repository and snapshot name. You can save these details for future requirements.
11) All the IAM resources created by the script for the the snapshot registration process are deleted in the end.


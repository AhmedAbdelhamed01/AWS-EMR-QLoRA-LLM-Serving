# Terraform — AWS Infrastructure

All AWS resources for this project are provisioned using Terraform, ensuring full reproducibility and clean teardown.

## Resources Provisioned

| File | Resources |
|------|-----------|
| `main.tf` | AWS provider configuration (`~> 5.0`, `>= 1.5.0`) |
| `variables.tf` | `netid` (25nsfb), `region` (ca-central-1), `key_pair_name` |
| `vpc.tf` | VPC, public/private subnets, IGW, route tables, security groups, S3 bucket |
| `emr.tf` | EMR cluster (emr-6.15.0, Spark 3.4.1), IAM roles, instance groups |
| `ec2.tf` | EC2 `t3.xlarge`, Ubuntu 22.04, 60 GB gp3 root volume |
| `outputs.tf` | `ec2_public_ip`, `s3_bucket_name`, `emr_cluster_id` |

## Network Architecture

```
VPC: 10.0.0.0/16
├── Public Subnet:  10.0.1.0/24  →  EC2 (model server)
├── Private Subnet: 10.0.2.0/24  →  EMR (data processing)
└── Internet Gateway: 25nsfb-igw →  Public subnet only
```

## Usage

```bash
# Initialise Terraform
terraform init

# Preview all resources
terraform plan

# Provision VPC + S3 (no compute cost)
terraform apply \
  -target=aws_vpc.main \
  -target=aws_subnet.public \
  -target=aws_subnet.private \
  -target=aws_internet_gateway.igw \
  -target=aws_route_table.public_rt \
  -target=aws_route_table_association.public_assoc \
  -target=aws_security_group.ec2_sg \
  -target=aws_security_group.emr_master_sg \
  -target=aws_security_group.emr_slave_sg \
  -target=aws_s3_bucket.project_bucket \
  -target=aws_s3_bucket_ownership_controls.bucket_ownership

# Provision EMR cluster (billing starts here)
terraform apply -target=aws_emr_cluster.spark_cluster

# Provision EC2 model server
terraform apply -target=aws_instance.model_server -target=data.aws_ami.ubuntu

# Destroy everything when done
terraform destroy
```

## Security Notes

- Ollama API port `11434` restricted to VPC CIDR `10.0.0.0/16` (not publicly accessible)
- EMR cluster runs in private subnet with no internet-facing ingress
- All resource names prefixed with `25nsfb-` via `var.netid`
- SSH key and Terraform state files excluded from version control via `.gitignore`

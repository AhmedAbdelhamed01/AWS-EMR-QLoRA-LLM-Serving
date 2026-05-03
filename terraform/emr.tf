# -----------------------------------------------------------------------------
# IAM — EMR Service Role (AWS managed policy satisfies the SCP)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "emr_service_role" {
  name = "${var.netid}-emr-service-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "elasticmapreduce.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "emr_service_managed" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

# -----------------------------------------------------------------------------
# EMR Classic Cluster
# -----------------------------------------------------------------------------
resource "aws_emr_cluster" "spark_cluster" {
  name          = "${var.netid}-emr-cluster"
  release_label = "emr-6.15.0"
  applications  = ["Hadoop", "Spark"]

  # Use the pre-existing university role here
  service_role = "EMR_DefaultRole"

  ec2_attributes {
    subnet_id                         = aws_subnet.public.id
    emr_managed_master_security_group = aws_security_group.emr_master_sg.id
    emr_managed_slave_security_group  = aws_security_group.emr_slave_sg.id
    key_name                          = var.key_pair_name

    # Use the pre-existing university profile here
    instance_profile = "EMR_EC2_DefaultRole"
  }

  master_instance_group {
    instance_type = "m5.xlarge"
  }

  core_instance_group {
    instance_count = 2
    instance_type  = "m5.xlarge"
  }

  # v4 bucket is correct if currently deployed in Canada (ca-central-1)
  log_uri = "s3://${var.netid}-cisc886-project-v4/emr-logs/"

  auto_termination_policy {
    idle_timeout = 3600
  }

  step_concurrency_level = 1
  visible_to_all_users   = true

  tags = {
    Name = "${var.netid}-emr-cluster"
  }
}

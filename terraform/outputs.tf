output "s3_bucket_name" {
  description = "S3 bucket name for all project data"
  value       = aws_s3_bucket.project_bucket.bucket
}

output "emr_cluster_id" {
  description = "EMR Classic Cluster ID"
  value       = aws_emr_cluster.spark_cluster.id
}

output "ec2_public_ip" {
  description = "Public IP address of the model server"
  value       = aws_instance.model_server.public_ip
}

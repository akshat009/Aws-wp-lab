output "instance_id" {
  description = "ID of the provisioned WordPress EC2 instance"
  value       = aws_instance.wp.id
}

output "instance_public_ip" {
  description = "Public IPv4 address of the WordPress server"
  value       = aws_instance.wp.public_ip
}

output "instance_public_dns" {
  description = "Public DNS hostname of the WordPress server"
  value       = aws_instance.wp.public_dns
}

output "website_url" {
  description = "HTTP URL to access WordPress"
  value       = "http://${aws_instance.wp.public_ip}"
}


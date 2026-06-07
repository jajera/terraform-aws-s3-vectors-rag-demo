resource "aws_s3vectors_vector_bucket" "this" {
  vector_bucket_name = local.vector_bucket_name
}

resource "aws_s3vectors_index" "this" {
  vector_bucket_name = aws_s3vectors_vector_bucket.this.vector_bucket_name
  index_name         = var.vector_index_name

  dimension       = var.vector_dimension
  distance_metric = var.vector_distance_metric
  data_type       = "float32"
}

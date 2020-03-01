Remove-Item ./get_reviews_lambda.zip;
7z u ./get_reviews_lambda.zip ./get_reviews_lambda/lambda_function.py;
7z u ./get_reviews_lambda.zip ./get_reviews_lambda/package/*;
aws s3 cp ./get_reviews_lambda.zip s3://site-reviews/get_site_reviews.zip; 
aws lambda update-function-code --function-name get_site_reviews --s3-bucket site-reviews --s3-key get_site_reviews.zip
import os
import json
import boto3
import sys
import time
import subprocess
import tempfile
import re
import argparse
import logging

logger = logging.getLogger(__name__)

def check_kerberos_ticket(test_url=None):
    """
    Check if Kerberos ticket is valid and attempt to renew it if expired
       
    Parameters:
    test_url (str): Optional URL to test authentication against
    
    Returns:
    bool: True if ticket is valid or was successfully renewed, False otherwise
    """
    try:
        # Check if ticket exists and is valid
        result = subprocess.run(["klist", "-s"], capture_output=True)
        if result.returncode == 0:
            logger.info("Kerberos ticket is valid")
            
            # If a test URL is provided, check if we can access it
            if test_url:
                logger.info(f"Testing authentication against {test_url}...")

                test_cmd = [
                    "curl", "-s", "-I", "-L", "-k", "--negotiate", "-u", ":",
                    "--delegation", "always",
                    test_url
                ]
                test_result = subprocess.run(test_cmd, capture_output=True, text=True)
                
                # Check if we got a successful response
                if "HTTP/1.1 200" in test_result.stdout or "HTTP/2 200" in test_result.stdout:
                    logger.info("Authentication test successful")
                    return True
                else:
                    logger.warning("Authentication test failed. Attempting to renew ticket...")
    
            else:
                return True
        
        logger.warning("Kerberos ticket is expired or not found. Attempting to renew...")
        
        # Try to renew ticket with kinit
        logger.info("Please enter your Kerberos password when prompted:")
        renew_result = subprocess.run(["kinit"], text=True)
        if renew_result.returncode == 0:
            logger.info("Successfully renewed Kerberos ticket")
            return True
        else:
            logger.error(f"Failed to renew Kerberos ticket")
            return False
    except Exception as e:
        logger.error(f"Error checking Kerberos ticket: {e}")
        return False

def upload_wiki_url(wiki_url, bucket_name, folder_prefix="wiki-content", output_file="wiki_content.html"):
    """
    Save a wiki URL as HTML to an S3 bucket
    
    Parameters:
    wiki_url (str): URL of the wiki page
    bucket_name (str): Name of the S3 bucket
    folder_prefix (str): Folder path within the bucket
    output_file (str): Name of the output file
    
    Returns:
    bool: True if URL was saved to S3, else False
    """
    try:

            
        # Create a temporary file to store the HTML content
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as temp_file:
            temp_path = temp_file.name

        # Use curl to fetch the HTML content with stronger authentication options
        cmd = [
            "curl", "-v", "-L", "-k", "--negotiate", "-u", ":",
            "--delegation", "always",
            "--location-trusted",
            "-c", "/tmp/cookies.txt", "-b", "/tmp/cookies.txt",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml",
            "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "-o", temp_path, wiki_url
        ]
        logger.info(f"Fetching HTML from: {wiki_url}")
        env = os.environ.copy()
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)

        if result.returncode != 0:
            logger.error(f"Error getting wiki content: {result.stderr}")
            return False

        # Check if the file has content
        file_size = os.path.getsize(temp_path)
        logger.info(f"Downloaded file size: {file_size} bytes")

        if file_size == 0:
            logger.warning("Downloaded file is empty")
            return False
            
        # Check if the content contains authentication error
        with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if "You've failed to authenticate" in content or "Unauthorized" in content:
                logger.error("Authentication failed. The downloaded content contains an error message.")
                logger.error("Please ensure your Kerberos ticket is valid by running 'kinit' and try again.")
                return False

        # Validate content before proceeding
        if not content or len(content.strip()) == 0:
            logger.error("Downloaded content is empty or invalid")
            return False

        # Copy the temp file to the output file
        with open(output_file, 'w', encoding='utf-8') as dest_file:
            dest_file.write(content)

        # Clean up the temp file
        os.unlink(temp_path)
        
        logger.info(f"Wiki HTML saved to {output_file}")
        
        # Upload to S3
        logger.info(f"Uploading to S3 bucket: {bucket_name}/{folder_prefix}")
        session = boto3.Session()
        s3_client = session.client('s3')
        
        # Ensure folder prefix ends with a slash
        if folder_prefix and not folder_prefix.endswith('/'):
            folder_prefix += '/'
            
        # Extract wiki page path from URL for consistent object naming
        # Use the full path after /bin/view/ to ensure unique naming
        if '/bin/view/' in wiki_url:
            path_part = wiki_url.split('/bin/view/')[-1]
            # Replace slashes with underscores for valid S3 key
            page_name = path_part.replace('/', '_')
        else:
            page_name = wiki_url.split('/')[-1] if '/' in wiki_url else 'default'
        object_key = f"{folder_prefix}{page_name}.html"
        
        # Validate file exists and has content before upload
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            logger.error(f"Output file {output_file} is empty or does not exist")
            return False
            
        try:
            s3_client.upload_file(
                output_file,
                bucket_name,
                object_key,
                ExtraArgs={
                    'ContentType': 'text/html',
                    'ACL': 'public-read'
                }
            )
            
            # Generate a public URL for the uploaded file
            s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
            logger.info(f"Public URL: {s3_url}")
            
        except Exception as e:
            if "AccessControlListNotSupported" in str(e):
                logger.warning("Bucket does not support ACLs. Uploading without ACL...")

                s3_client.upload_file(
                    output_file,
                    bucket_name,
                    object_key,
                    ExtraArgs={
                        'ContentType': 'text/html'
                    }
                )
                logger.info(f"File uploaded successfully without public access.")
                logger.info(f"Access the file through the S3 console or use a pre-signed URL.")
            else:

                raise
        
        logger.info(f"Upload successful to s3://{bucket_name}/{object_key}")
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return False
def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="Download a wiki page and upload it to S3")
    parser.add_argument("--url", required=True, help="URL of the wiki page")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--folder", default="wiki-content", help="Folder prefix in S3 bucket")
    parser.add_argument("--output", help="Output filename (optional)")
    
    args = parser.parse_args()
    
    # Generate output filename from URL if not provided
    if not args.output:
        if '/bin/view/' in args.url:
            path_part = args.url.split('/bin/view/')[-1]
            args.output = path_part.replace('/', '_') + '.html'
        else:
            args.output = 'wiki_content.html'
    
    logger.info(f"URL: {args.url}")
    logger.info(f"Bucket: {args.bucket}")
    logger.info(f"Folder: {args.folder}")
    logger.info(f"Output: {args.output}")

    try:
        # Check Kerberos ticket before proceeding, testing against the target URL
        if not check_kerberos_ticket(args.url):
            logger.error("Cannot proceed without a valid Kerberos ticket.")
            logger.error("Please run 'kinit' manually to authenticate and try again.")
            return 1
            
        # Upload the wiki URL to S3
        if upload_wiki_url(args.url, args.bucket, args.folder, args.output):
            logger.info("Wiki URL successfully uploaded to S3")
            return 0
        else:
            logger.error("Failed to upload wiki URL to S3")
            return 1
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
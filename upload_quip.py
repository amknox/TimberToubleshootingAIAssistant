import argparse
import boto3
import requests
from bs4 import BeautifulSoup
import re
import os
import logging

logger = logging.getLogger(__name__)

def download_quip_document(url, token, base_url='https://platform.quip-amazon.com'):
    """
    Download a Quip document using the provided URL and token.
    
    Args:
        url: URL of the Quip document
        token: Quip API access token
        base_url: Base URL for Quip API (default: 'https://platform.quip-amazon.com')
        
    Returns:
        HTML content if successful, None otherwise
    """
    try:
        # Extract thread ID from URL
        thread_id = None
        if url.startswith('http') and 'quip-amazon.com' in url:
            # Extract the thread ID from URL
            parts = url.split('/')
            if len(parts) >= 4:
                # Get thread ID from URL path
                thread_id = parts[3]
        else:
            # Assume the URL is already a thread ID
            thread_id = url
        
        if not thread_id:
            logger.error(f"Could not extract thread ID from URL: {url}")
            return None
            
        logger.info(f"Using thread ID: {thread_id}")
        
        # Set up API request
        api_url = f"{base_url}/1/threads/{thread_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        logger.info(f"Requesting document from API: {api_url}")
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        # Get HTML content
        thread_data = response.json()
        if 'html' in thread_data:
            html_content = thread_data['html']
            # Wrap in basic HTML structure
            full_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{thread_data.get('thread', {}).get('title', 'Quip Document')}</title>
</head>
<body>
    {html_content}
</body>
</html>"""
            return full_html.encode('utf-8')
        else:
            logger.error(f"No HTML content found in API response: {thread_data}")
            return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed for Quip document: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading Quip document: {str(e)}")
        return None

def sanitize_title(title):
    """
    Sanitize page title for filesystem use.
    
    Args:
        title: Original title
        
    Returns:
        Sanitized title
    """
    title = re.sub(r'[<>:"/\\|?*]', '_', title)
    title = title.strip()
    return title

def upload_to_s3(content, bucket, output_name=None, thread_id=None):
    """
    Upload content to S3 bucket.
    
    Args:
        content: HTML content to upload
        bucket: S3 bucket name
        output_name: Custom filename (without extension)
        thread_id: Quip thread ID for consistent naming
        
    Returns:
        S3 URL for user confirmation and potential future integrations, None if upload fails
    """
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Check if bucket has versioning enabled
        try:
            versioning = s3_client.get_bucket_versioning(Bucket=bucket)
            if versioning.get('Status') != 'Enabled':
                print("Warning: Bucket versioning is not enabled. Enabling versioning...")
                try:
                    s3_client.put_bucket_versioning(
                        Bucket=bucket,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )
                    print("Bucket versioning enabled successfully")
                except Exception as e:
                    print(f"Could not enable bucket versioning: {e}")
        except Exception as e:
            print(f"Could not check bucket versioning: {e}")
        
        # Parse HTML to extract title if no output name provided
        if not output_name:
            soup = BeautifulSoup(content, 'html.parser')
            title_tag = soup.find('title')
            output_name = title_tag.string.strip() if title_tag and title_tag.string else "Quip_Document"
            output_name = sanitize_title(output_name)
        
        # Always use thread_id for consistent naming to enable proper versioning
        if thread_id:
            s3_key = f"quip-content/{thread_id}.html"
        else:
            # Fallback to sanitized output name if thread_id not available
            s3_key = f"quip-content/{output_name}.html"
            
        # Validate content before upload
        if not content:
            logger.error("Cannot upload empty content to S3")
            return None
            
        logger.info(f"Uploading to bucket: {bucket}, key: {s3_key}")
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=content,
            ContentType='text/html'
        )
        
        # Generate S3 URL
        s3_url = f"https://{bucket}.s3.amazonaws.com/{s3_key}"
        logger.info(f"Successfully uploaded to S3: {s3_url}")
        
        return s3_url
        
    except Exception as e:
        logger.error(f"Failed to upload to S3 bucket '{bucket}': {str(e)}")
        return None

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description="Download a Quip document and upload it to S3")
    parser.add_argument("--url", required=True, help="URL of the Quip document")
    parser.add_argument("--token", required=True, help="Quip API access token")
    parser.add_argument("--bucket", required=True, help="S3 bucket name")
    parser.add_argument("--output", help="Output filename (without extension)")
    parser.add_argument("--region", help="AWS region for S3 bucket")
    parser.add_argument("--base-url", default="https://platform.quip-amazon.com", 
                      help="Base URL for Quip API (default: https://platform.quip-amazon.com)")
    
    args = parser.parse_args()
    
    # Set AWS region if provided
    if args.region:
        logger.info(f"Setting AWS region to {args.region}")
        boto3.setup_default_session(region_name=args.region)
    
    # Extract thread ID from URL
    thread_id = None
    if args.url.startswith('http') and 'quip-amazon.com' in args.url:
        parts = args.url.split('/')
        if len(parts) >= 4:
            thread_id = parts[3]
    else:
        thread_id = args.url
    
    # Download Quip document
    logger.info(f"Downloading Quip document from {args.url}")
    content = download_quip_document(args.url, args.token, args.base_url)
    if not content:
        logger.error("Failed to download Quip document")
        return 1
    
    logger.info(f"Successfully downloaded document, size: {len(content)} bytes")
    
    # Upload to S3 with thread_id for consistent naming
    # S3 URL is returned for user confirmation and potential future automation
    s3_url = upload_to_s3(content, args.bucket, args.output, thread_id)
    if not s3_url:
        logger.error("Failed to upload to S3")
        return 1
    
    logger.info(f"Process completed successfully. Document available at: {s3_url}")
    return 0

if __name__ == "__main__":
    main()
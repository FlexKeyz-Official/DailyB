#!/usr/bin/env python3
"""
Standalone earnings cron script for Replit Scheduled Deployments
This script runs the daily earnings processing independently without the full Flask app.
"""
import os
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_earnings_cron():
    """Execute the daily earnings processing"""
    try:
        logger.info("Starting daily earnings processing...")
        
        # The earnings URL with token
        earnings_url = "https://dailybred.ct.ws/crons/cron_earnings.php?token=adminFlex01"
        
        # Headers to simulate a legitimate request from Replit
        headers = {
            'User-Agent': 'Replit-Scheduled-Task/1.0 (+https://replit.com)',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Connection': 'keep-alive'
        }
        
        # Make the request with a longer timeout
        logger.info(f"Making request to {earnings_url}")
        response = requests.get(earnings_url, headers=headers, timeout=60)
        
        # Log the results
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        # Check if we got the actual earnings response or protection page
        response_text = response.text
        if "Cookies are not enabled" in response_text:
            logger.warning("Hit InfinityFree cookie protection page")
            print("❌ InfinityFree protection blocked the request")
            return False
        elif "aes.js" in response_text:
            logger.warning("Hit InfinityFree anti-bot protection")
            print("❌ InfinityFree anti-bot protection active")
            return False
        elif response.status_code == 200:
            logger.info("Successfully reached earnings endpoint")
            logger.info(f"Response content: {response_text[:200]}...")
            
            # Try to parse as JSON (expected success response)
            try:
                import json
                result = json.loads(response_text)
                if result.get('success'):
                    credited = result.get('credited', 0)
                    print(f"✅ Success! {credited} users received their daily earnings")
                    logger.info(f"Earnings processed successfully: {credited} users credited")
                    return True
                else:
                    print(f"⚠️  Earnings script responded but reported: {result.get('message', 'Unknown error')}")
                    return False
            except json.JSONDecodeError:
                # Not JSON, but 200 status might still be success
                if len(response_text) < 1000 and "success" in response_text.lower():
                    print("✅ Earnings processing completed (non-JSON response)")
                    logger.info("Earnings processing completed")
                    return True
                else:
                    print("⚠️  Received unexpected response format")
                    logger.warning(f"Unexpected response: {response_text[:100]}...")
                    return False
        else:
            logger.error(f"HTTP error: {response.status_code}")
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        print("❌ Request timed out - server may be slow")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Connection error")
        print("❌ Connection error - check internet connectivity")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Error: {e}")
        return False

def main():
    """Main entry point"""
    print("🚀 DailyBred Earnings Cron Job Starting...")
    print(f"⏰ Execution time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    success = run_earnings_cron()
    
    if success:
        print("✨ Daily earnings cron job completed successfully!")
    else:
        print("💥 Daily earnings cron job failed!")
        exit(1)

if __name__ == "__main__":
    main()
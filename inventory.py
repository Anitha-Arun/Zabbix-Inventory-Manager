import csv
import requests
import logging
import json
import pandas as pd
from datetime import datetime
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=f'inventory_manager_{datetime.now().strftime("%Y%m%d")}.log'
)
logger = logging.getLogger(__name__)

def clean_csv(input_file, output_file):
    """
    Clean and preprocess the input CSV file
    
    Args:
        input_file (str): Path to the input CSV file
        output_file (str): Path to save the cleaned CSV file
    
    Returns:
        pd.DataFrame or None: Cleaned DataFrame if successful, None otherwise
    """
    try:
        # Read the file manually to understand its structure
        with open(input_file, 'r') as file:
            # Peek at the first few lines
            logger.info("First few lines of the file:")
            for _ in range(5):
                logger.info(file.readline().strip())
            file.seek(0)  # Reset file pointer 
        
        # Use csv reader to handle problematic lines
        with open(input_file, 'r') as file:
            csv_reader = csv.reader(file)
            cleaned_rows = []
            
            for row in csv_reader:
                # Filter out completely empty rows
                if any(cell.strip() for cell in row):
                    # Trim whitespace from each cell
                    cleaned_row = [cell.strip() for cell in row]
                    # Take only first 8 columns
                    cleaned_row = cleaned_row[:8]
                    cleaned_rows.append(cleaned_row)
            
            # Convert to DataFrame
            df = pd.DataFrame(cleaned_rows[1:], columns=cleaned_rows[0][:8])
            
            # Additional cleaning
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            
            # Remove rows with all empty values
            df = df.dropna(how='all')
            
            # Save cleaned CSV
            df.to_csv(output_file, index=False)
            
            logger.info(f"Cleaned CSV contains {len(df)} rows")
            logger.info("First few rows of cleaned CSV:")
            logger.info(str(df.head()))
            
            return df
    
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")
        return None

class ZabbixInventoryManager:
    def __init__(self, zabbix_url='zabbix url', username='Admin', password='zabbix_password'):
        self.api_url = f"{zabbix_url}/api_jsonrpc.php"
        self.headers = {"Content-Type": "application/json-rpc"}
        self.auth_token = self.get_zabbix_token(username, password)
        self.counter = 1  # Initialize counter for devices without S/N and MAC
        self.hostname_counters = {}  # Track hostname counts for duplicates

    def generate_unique_hostname(self, base_hostname):
        """Generate a unique hostname by adding a number suffix if needed"""
        if base_hostname not in self.hostname_counters:
            self.hostname_counters[base_hostname] = 1
            return base_hostname
        else:
            count = self.hostname_counters[base_hostname]
            self.hostname_counters[base_hostname] += 1
            return f"{base_hostname}-{count}"

    def get_zabbix_token(self, username, password):
        """Authenticate and get Zabbix API token"""
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "username": username,
                "password": password
            },
            "id": 1
        }
        
        try:
            response = requests.post(
                self.api_url,
                data=json.dumps(payload),
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    logger.info("Successfully authenticated with Zabbix API")
                    return result['result']
            
            logger.error(f"Authentication failed: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting Zabbix token: {e}")
            return None

    def read_inventory_csv(self, file_path):
        """Read and clean inventory CSV file with enhanced space and data handling"""
        try:
            # Read CSV with pandas, specifying only the first 8 columns
            df = pd.read_csv(file_path, usecols=range(8), dtype=str)
            
            # Clean column names
            df.columns = ['Sl.no', 'Team', 'Device model', 'S/N', 'MAC ID', 'Condition', 'Assigned to', 'Owner']
            
            # Enhanced cleaning function
            def clean_value(value):
                """Clean and validate individual values"""
                if pd.isna(value):
                    return ''
                # Remove all types of whitespace and normalize
                cleaned = ' '.join(str(value).split())
                return cleaned if cleaned else ''
            
            # Apply cleaning to all columns
            for col in df.columns:
                df[col] = df[col].apply(clean_value)
            
            # Specific handling for critical fields
            df['Device model'] = df['Device model'].apply(lambda x: x if x else 'Unknown Device')
            df['S/N'] = df['S/N'].apply(lambda x: x if x else 'UNKNOWN')
            df['MAC ID'] = df['MAC ID'].apply(lambda x: x if x else 'UNKNOWN')
            
            # Fill remaining empty values with defaults
            defaults = {
                'Owner': 'Unassigned',
                'Team': 'Inventory',
                'Condition': 'Unknown',
                'Assigned to': 'Unassigned'
            }
            
            for col, default in defaults.items():
                df[col] = df[col].apply(lambda x: x if x else default)
            
            # Remove rows that are completely empty after cleaning
            df = df[df.apply(lambda row: any(row.str.strip() != ''), axis=1)]

            logger.info(f"Successfully read {len(df)} devices from CSV")
            return df

        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            return None

    def get_group_id(self, group_name):
        """Get or create host group"""
        payload = {
            "jsonrpc": "2.0",
            "method": "hostgroup.get",
            "params": {
                "filter": {"name": group_name}
            },
            "auth": self.auth_token,
            "id": 1
        }
        
        try:
            response = requests.post(
                self.api_url,
                data=json.dumps(payload),
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    group_id = result['result'][0]['groupid']
                    logger.info(f"Found existing group '{group_name}' with ID {group_id}")
                    return group_id
                else:
                    # Create group if it doesn't exist
                    return self.create_group(group_name)
            
            logger.error(f"Failed to get group ID for {group_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting group ID: {e}")
            return None

    def create_group(self, group_name):
        """Create a new host group"""
        payload = {
            "jsonrpc": "2.0",
            "method": "hostgroup.create",
            "params": {
                "name": group_name
            },
            "auth": self.auth_token,
            "id": 1
        }
        
        try:
            response = requests.post(
                self.api_url,
                data=json.dumps(payload),
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    group_id = result['result']['groupids'][0]
                    logger.info(f"Created new group '{group_name}' with ID {group_id}")
                    return group_id
            
            logger.error(f"Failed to create group {group_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return None

    def create_or_update_host(self, host_data):
        """Create new host in Zabbix"""
        try:
            # Generate identifier
            identifier = self.generate_identifier(host_data['S/N'], host_data['MAC ID'])
            base_hostname = f"{str(host_data['Device model']).replace(' ', '-')}-{identifier}"
            # Ensure hostname is valid (remove special characters)
            base_hostname = ''.join(c for c in base_hostname if c.isalnum() or c in '-_.')
            
            # Generate unique hostname
            hostname = self.generate_unique_hostname(base_hostname)
            
            group_id = self.get_group_id(str(host_data['Team']).strip())
            
            if not group_id:
                logger.error(f"Failed to get/create group for {host_data['Team']}")
                return False
            
            # Create new host (don't check for existing)
            payload = {
                "jsonrpc": "2.0",
                "method": "host.create",
                "params": {
                    "host": hostname,
                    "groups": [{"groupid": group_id}],
                    "inventory_mode": 1,
                    "inventory": {
                        "type": str(host_data['Device model']),
                        "serialno_a": str(host_data['S/N']),
                        "macaddress_a": str(host_data['MAC ID']),
                        "location": str(host_data['Assigned to']),
                        "notes": str(host_data['Condition']),
                        "site_notes": str(host_data['Team']),
                        "contact": str(host_data['Owner'])
                    }
                },
                "auth": self.auth_token,
                "id": 1
            }
            
            response = requests.post(
                self.api_url,
                data=json.dumps(payload),
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'result' in result:
                    logger.info(f"Successfully created host {hostname}")
                    return True
                else:
                    logger.error(f"Failed to create host {hostname}: {result.get('error', 'Unknown error')}")
                    return False
            
            logger.error(f"Failed to create host {hostname}: {response.text}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating host: {e}")
            return False

    def generate_identifier(self, serial_number, mac_address):
        """Generate a unique identifier for the device"""
        if serial_number and serial_number != 'UNKNOWN':
            return f"SN{str(serial_number).strip()[-4:]}"
        elif mac_address and mac_address != 'UNKNOWN':
            return f"MC{str(mac_address).strip()[-4:]}"
        else:
            # Use counter for devices without S/N and MAC
            identifier = f"DEV{str(self.counter).zfill(4)}"
            self.counter += 1
            return identifier
        
    def get_host(self, hostname):
        """Check if host exists and return hostid if it does"""
        payload = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "filter": {"host": hostname}
            },
            "auth": self.auth_token,
            "id": 1
        }
        
        try:
            response = requests.post(
                self.api_url,
                data=json.dumps(payload),
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('result'):
                    return result['result'][0]['hostid']
            return None
            
        except Exception as e:
            logger.error(f"Error checking host existence: {e}")
            return None

def main():
    try:
        # Clean the input CSV first
        cleaned_csv_path = 'cleaned_sending.csv' # u can change this as u want 
        raw_csv_path = 'sending.csv' # enter the correct csv where u have the details 
        
        # Clean the CSV
        cleaned_df = clean_csv(raw_csv_path, cleaned_csv_path)
        
        if cleaned_df is None:
            logger.error("Failed to clean CSV file")
            return
        
        # Initialize the inventory manager
        manager = ZabbixInventoryManager()
        
        if not manager.auth_token:
            logger.error("Failed to authenticate with Zabbix")
            return
        
        # Read inventory data from cleaned CSV
        inventory_data = manager.read_inventory_csv(cleaned_csv_path)
        if inventory_data is None:
            logger.error("Failed to read inventory data")
            return
        
        success_count = 0
        failed_count = 0
        total_count = len(inventory_data)
        
        # Process each device
        for _, row in inventory_data.iterrows():
            if manager.create_or_update_host(row):
                success_count += 1
            else:
                failed_count += 1
                
        logger.info(f"Processing complete. Successfully processed {success_count} out of {total_count} devices")
        if failed_count > 0:
            logger.warning(f"Failed to process {failed_count} devices. Check logs for details.")
        
        # Optionally, remove the cleaned CSV after processing
        import os
        os.remove(cleaned_csv_path)
            
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        logger.exception("Detailed error information:")

if __name__ == "__main__":
    main()
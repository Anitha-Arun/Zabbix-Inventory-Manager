# Zabbix-Inventory-Manager
 It clearly reflects the purpose of the script, which is managing inventory within Zabbix.
 
 This Python script automates the process of cleaning inventory data from a CSV file and syncing it with the Zabbix monitoring system. The core functionality includes data cleaning, host creation/updating in Zabbix, and error handling for each step.

#Main Features
CSV Cleaning:

The clean_csv function reads a raw CSV file, trims whitespace, handles empty rows, and ensures only the first 8 columns are considered.
It handles problematic lines, normalizes text (e.g., removes extra spaces), and drops rows with empty values.
The cleaned CSV is saved for further use in Zabbix integration.
Zabbix Integration:

The ZabbixInventoryManager class interacts with the Zabbix API for creating and updating hosts.
It handles authentication, retrieves group IDs, creates new groups if necessary, and manages host data like device model, serial number (S/N), MAC address, and more.
The script generates a unique hostname for each device and ensures that Zabbix entries follow the correct format.
Host creation ensures that the device information is properly assigned to the correct group in Zabbix.
Error Handling & Logging:

Detailed logging is implemented for every operation (authentication, host creation, CSV cleaning, etc.) to help debug any issues.
Errors are logged in a dedicated log file, which is useful for tracking down failures.
Device Identifier Generation:

A unique identifier is generated for each device based on its serial number, MAC address, or a counter if both are missing.

#CSV File Processing:

The script reads a cleaned CSV file, processes each device entry, and either creates a new host in Zabbix or updates an existing one.
The main function orchestrates the workflow, from cleaning the CSV to updating the Zabbix system.

#How to Use
Prepare your input CSV file (e.g., sending.csv) containing inventory details with columns for device model, serial number, MAC address, etc.
Run the script. It will clean the CSV and attempt to update the Zabbix system with the inventory data.
The cleaned CSV will be saved as cleaned_sending.csv (or another name of your choice).
Successful and failed updates are logged in a file named inventory_manager_<current_date>.log.

#Dependencies

requests: Used for interacting with the Zabbix API.
pandas: Used for reading, cleaning, and processing the CSV data.
logging: Used for logging all actions performed by the script.
json: Used to send and receive data in JSON format to/from the Zabbix API.

#Important Notes

Ensure the Zabbix API URL and credentials (username, password) are correctly set in the script before running it.
The script uses the first 8 columns of the input CSV. Modify the column settings if your CSV structure changes.
The Zabbix system must be configured to accept API requests and have the necessary permissions for creating or updating hosts and groups.

#Author
This is a Python script written and maintained by Anitha.Damarla. The script is designed to clean inventory data from a CSV file and interact with the Zabbix monitoring system to create or update hosts..
for Doubts please contant :Anithadamarla0313@gmail.com

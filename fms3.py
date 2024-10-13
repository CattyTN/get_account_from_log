import paramiko
from pymongo import MongoClient
import datetime
from sshtunnel import SSHTunnelForwarder
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
import os
import time
import tkinter as tk
from tkinter import ttk

formatted_date = ''

today = datetime.now()
today = today.replace(hour = 0, minute = 0, second = 0, microsecond=0)
print(today.date())
tomorrow = today.replace(day=today.day+1)
query = {"dateCreated": {"$gte": today, "$lt": tomorrow}}

tunnel = None

excel_path = 'log_ngay_' + str(today.date()) + '.xlsx'



def get_mongo_data(ssh_host, ssh_port, ssh_user, ssh_password, mongo_host, mongo_port, mongo_db, mongo_collection, filter, sample_size=10):
	print('in 1')
	with SSHTunnelForwarder((ssh_host, ssh_port),
	ssh_username=ssh_user,
	ssh_password=ssh_password,
	remote_bind_address=(mongo_host, mongo_port)
	) as tunnel:
		client = MongoClient('127.0.0.1', tunnel.local_bind_port)
		db = client[mongo_db]
		collection = db[mongo_collection]
		#result = list(collection.aggregate([{"$sample": {"size": sample_size}}]))
		result = list(collection.find(filter).limit(10000))
		#result = list(collection.aggregate([{"$match":{"created_at":{"$regex":'2024-03-01'}}},{"$sample": {"size": 10}}]))
		#result = list(collection.aggregate([{"$match":{"created_at":{"$regex":'2024-04-13'}}},{"$sample": {"size": 10}}]))	
	print('done 1')
	return result

def raw_to_df(result):
	data = {'mac': [],'ip': [],'unit_name': [],'user_name': [],'unit_full_name': [],'alert_type': [],'alert_level_id': [], 'time_receive': [],'description': []}
	for record in result:
		data['mac'].append(str(record['mac']))
		data['ip'].append(str(record['ip']))
		data['unit_name'].append(str(record['unit_full_name']))
		data['user_name'].append(str('Chua dinh danh'))
		data['unit_full_name'].append(str(record['unit_full_name']))
		data['alert_type'].append(str(record['alert_type']))
		data['alert_level_id'].append(str(record['alert_level_id']))
		data['time_receive'].append(str(record['time_receive']))
		data['description'].append(str(record.get('alert_info', {}).get('description', 'No description available')))
	df = pd.DataFrame(data)
	return df

def df_to_df(df):
	df_gray_domain = df[df['alert_type'].str.contains('Gray_domain', na=False)]
	df_gray_ip = df[df['alert_type'].str.contains('Gray_ip', na=False)]
	df_dll = df[df['description'].str.contains('dll', na=False)]
	return df_gray_domain, df_gray_ip, df_dll

def create_file(file_name):
	exists_1 = os.path.exists(file_name)
	if exists_1:
		return
	else:
		wb = Workbook()
		ws = wb.active
		wb.save(excel_path)
		return


def get_output_path(date):
	df_gray_domain_path = str(date) + '-gray_domain'
	df_gray_ip_path = str(date) + '-gray_ip'
	df_dll_path = str(date) + '-dll'
	return df_gray_domain_path, df_gray_ip_path, df_dll_path

def append_data_to_excel(excel_path, new_data):
	create_file(excel_path)
	df_xlsx = pd.read_excel(excel_path)
	new_data = pd.DataFrame(new_data)
	if len(new_data) > 0:
		cols = ['mac','ip','unit_name','user_name','unit_full_name','alert_type','alert_level_id', 'time_receive','description']
		df_xlsx_ = pd.concat([df_xlsx, new_data[cols]], ignore_index=True)   
		open(excel_path, 'w').close()
		df_xlsx_.to_excel(excel_path, index=False, sheet_name="Sheet1")
	return len(new_data)


def create_date_picker():
    def get_date():
        global formatted_date  # Sử dụng biến toàn cục để lưu giá trị
        day = day_combobox.get()
        month = month_combobox.get()
        year = year_combobox.get()
        formatted_date = f"{year}-{int(month):02d}-{int(day):02d}"
        root.quit()  # Đóng cửa sổ sau khi giá trị đã được lưu

    root = tk.Tk()
    root.title("Chọn Ngày Tháng Năm")

    frame = ttk.Frame(root, padding="10")
    frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    days = list(range(1, 32))
    months = list(range(1, 13))
    years = list(range(2023, 2025))

    day_label = ttk.Label(frame, text="Ngày:")
    day_label.grid(row=0, column=0, padx=5, pady=5)
    day_combobox = ttk.Combobox(frame, values=days, width=5)
    day_combobox.grid(row=0, column=1, padx=5, pady=5)
    day_combobox.set(days[0])  

    month_label = ttk.Label(frame, text="Tháng:")
    month_label.grid(row=0, column=2, padx=5, pady=5)
    month_combobox = ttk.Combobox(frame, values=months, width=5)
    month_combobox.grid(row=0, column=3, padx=5, pady=5)
    month_combobox.set(months[0])  

    year_label = ttk.Label(frame, text="Năm:")
    year_label.grid(row=0, column=4, padx=5, pady=5)
    year_combobox = ttk.Combobox(frame, values=years, width=10)
    year_combobox.grid(row=0, column=5, padx=5, pady=5)
    year_combobox.set(years[0]) 

    submit_button = ttk.Button(frame, text="Xác nhận", command=get_date)
    submit_button.grid(row=1, column=0, columnspan=6, pady=10)

    result_label = ttk.Label(frame, text="")
    result_label.grid(row=2, column=0, columnspan=6)

    root.mainloop()

def main():
	start_time = time.time()
	ssh_host = "86.64.60.71"
	ssh_port = 22
	ssh_user = 'root'
	ssh_password = 'P52abc@123456'

	mongo_host = 'localhost.localdomain'
	mongo_port = 27017
	mongo_db = 'fms_v3'
	mongo_collection = 'events'

	create_date_picker()
	filter = {'time_receive': {'$gte': formatted_date}}
	result1 = get_mongo_data(ssh_host, ssh_port, ssh_user, ssh_password, mongo_host, mongo_port, mongo_db, mongo_collection, filter, sample_size=10)
	df = raw_to_df(result1)
	df = pd.DataFrame(df)
	df_gray_domain, df_gray_ip, df_dll = df_to_df(df)
	
	df_gray_domain_path, df_gray_ip_path, df_dll_path = get_output_path(formatted_date)

	append_data_to_excel(df_gray_domain_path,df_gray_domain)
	append_data_to_excel(df_gray_ip_path,df_gray_ip)
	append_data_to_excel(df_dll_path,df_dll)

	end_time = time.time()
	exe_time = end_time - start_time
	print('thoi gian thuc hien: ' + str(exe_time))


	







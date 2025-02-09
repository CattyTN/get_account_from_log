import pandas as pd
import re
import os
from openpyxl import Workbook
def filter_and_save_excel(file_path, file_path_2, keywords):
    try:
        df = pd.read_excel(file_path)

        if not all(col in df.columns for col in ['URL', 'Username', 'Password']):
            print("File không chứa đầy đủ các cột URL, Username, Password.")
            return

        def contains_keyword(value):
            if pd.isna(value):
                return False, None
            for keyword in keywords:
                if keyword in str(value):
                    return True, keyword
            return False, None

        def has_consecutive_digits(value):
            if pd.isna(value):
                return False
            return bool(re.search(r'\d{9,10}', str(value)))

        matched_rows = []

        for index, row in df.iterrows():
            username_contains, username_keyword = contains_keyword(row['Username'])
            password_contains, password_keyword = contains_keyword(row['Password'])

            username_has_digits = has_consecutive_digits(row['Username'])
            password_has_digits = has_consecutive_digits(row['Password'])

            if (username_contains and password_has_digits) or (password_contains and username_has_digits):
                matched_rows.append({
                    'URL': row['URL'],
                    'Username': row['Username'],
                    'Password': row['Password'],
                    'Matched Keyword': username_keyword if username_contains else password_keyword
                })

        filtered_df = pd.DataFrame(matched_rows)

        if not filtered_df.empty:
            print("Các dòng khớp với yêu cầu:")
            print(filtered_df[['URL', 'Username', 'Password', 'Matched Keyword']])

            filtered_df.to_excel(file_path_2, index=False)
            print(f"Dữ liệu đã được ghi vào file: {file_path_2}")
        else:
            print("Không có dòng nào khớp với yêu cầu.")

    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")

def create_output():
    exists_1 = os.path.exists(file_path_2)
    if exists_1:
        return
    else:
        wb = Workbook()
        ws = wb.active
        wb.save(file_path_2)
        return

a= 'C:\\Users\\PC\\Documents\\broject\\database\\2025-02-06'
file_path = a + '.xlsx' 
file_path_2 = a + '-2.xlsx'





keywords = ['linh', 'minhanh', 'ngoc','huyen', 'huong', 'nhi', 'thao', 'khanhly', 'anhthu', 'thuha', 'tram', 'baoanh', 'vananh', 'chau', "vy"]
create_output()
filter_and_save_excel(file_path, file_path_2, keywords)
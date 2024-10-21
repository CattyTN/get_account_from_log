import pandas as pd
import re

def filter_and_save_excel(file_path, file_path_2, keywords):
    try:
        df = pd.read_excel(file_path)

        if not all(col in df.columns for col in ['URL', 'Username', 'Password']):
            print("File không chứa đầy đủ các cột A, B, C.")
            return

        def contains_keyword(value):
            if pd.isna(value):
                return False
            return any(keyword in str(value) for keyword in keywords)

        def has_consecutive_digits(value):
            if pd.isna(value):
                return False
            return bool(re.search(r'\d{9,10}', str(value)))

        filtered_df = df[
            (df['Username'].apply(contains_keyword) & df['Password'].apply(has_consecutive_digits)) |
            (df['Password'].apply(contains_keyword) & df['Username'].apply(has_consecutive_digits))
        ]

        filtered_df.to_excel(file_path_2, index=False)
        print(f"Dữ liệu đã được ghi vào file: {file_path_2}")

    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")

file_path = 'C:\\Users\\PC\\Documents\\broject\\database\\2024-10-21.xlsx' 
file_path_2 = 'C:\\Users\\PC\\Documents\\broject\\database\\2024-10-21_2.xlsx'
keywords = ['linh', 'minhanh', 'ngoc','huyen', 'huong', 'nhi', 'thao', 'khanhly', 'anhthu', 'thuha', 'tram', 'baoanh', 'vananh']

filter_and_save_excel(file_path, file_path_2, keywords)
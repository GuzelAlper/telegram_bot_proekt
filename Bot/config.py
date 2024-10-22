import mysql.connector
from mysql.connector import Error

def create_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            password=user_password,
            database=db_name
        )
        print("MySQL bağlantısı başarılı!")
    except Error as e:
        print(f"Hata: '{e}'")

    return connection

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Sorgu başarılı!")
    except Error as e:
        print(f"Hata: '{e}'")

def fetch_query(connection, query):
    cursor = connection.cursor(dictionary=True)  # Sonuçları sözlük formatında almak için
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Error as e:
        print(f"Hata: '{e}'")
        return []

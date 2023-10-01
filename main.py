from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.label import Label
from kivy.uix.camera import Camera
from kivy.uix.relativelayout import RelativeLayout
import requests
import io
import cv2
from pyzbar.pyzbar import decode
import numpy as np
import io
import base64
import mysql.connector


class InformationMessageBox(ModalView):
    def __init__(self, message, **kwargs):
        super(InformationMessageBox, self).__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (400, 150)
        self.auto_dismiss = False  # Prevent the modal from being automatically dismissed
        #layout = BoxLayout(orientation='vertical', spacing=10)
        layout = RelativeLayout()
        # Create a label with the provided message
        self.message_label = Label(text=message, size_hint=(None, None), height=100, pos_hint={'center_x' : 0.5, 'top' : 1.5})
        layout.add_widget(self.message_label)
        self.close_button = Button(text="OK", size_hint=(0.4, 0.4), size=(100, 30), pos_hint={'center_x' : 0.5, 'top' : 0.2})
        self.close_button.bind(on_release=self.dismiss)
        layout.add_widget(self.close_button)
        # Add widgets to the modal
        #self.add_widget(self.message_label)
        #self.add_widget(self.close_button)
        self.add_widget(layout)
class ErrorMessageBox(ModalView):
    def __init__(self, message, **kwargs):
        super(ErrorMessageBox, self).__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (300, 150)
        self.auto_dismiss = False  # Prevent the modal from being automatically dismissed
        layout = RelativeLayout()
        #layout = BoxLayout(orientation='vertical', spacing=10)
        self.message_label = Label(text=message, size_hint=(None, None), height=100, pos_hint={'center_x': 0.5, 'top':1.5})
        layout.add_widget(self.message_label)
        self.close_button = Button(text="OK", size_hint=(0.4, 0.4), size=(100, 30), pos_hint={'center_x':0.5,'y':0.2})
        self.close_button.bind(on_release=self.dismiss)
        layout.add_widget(self.close_button)  # Adjust the y position as needed
        # Add widgets to the modal
        self.add_widget(layout)
        #self.add_widget(self.message_label)
        #self.add_widget(self.close_button)

class CameraApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')
        self.camera = Camera(resolution=(640, 480), play=True)
        layout.add_widget(self.camera)

        button = Button(text="Capture Photo")
        button.bind(on_press=self.capture)
        layout.add_widget(button)

        return layout

    def capture(self, instance):
        self.camera.export_to_png("captured_image.png")


        # Send the captured image to your ESP32 server
        image_file = "captured_image.png"

        # MySQL server configuration
        db_config = {
            "host": "localhost",
            "user": "root",
            "password": "22052000",
        }

        # Connect to MySQL server
        try:
            # Connect to MySQL server
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()

            # Create the INTERNSHIP database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS INTERNSHIP")

            # Close the connection to the MySQL server
            cursor.close()
            connection.close()

            # Reconnect to the MySQL server with the INTERNSHIP database selected
            db_config["database"] = "INTERNSHIP"
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor()
            # Create the MACHINE table if it doesn't exist
            create_table_query = """
            CREATE TABLE IF NOT EXISTS MACHINE (
                BARCODE VARCHAR(255) PRIMARY KEY,
                COUNTER INT,
                STATUS VARCHAR(255)
            )
            """
            cursor.execute(create_table_query)
        except mysql.connector.Error as err:
            print("Error:", err)
            message = "DataBase Error: "+ err
            error_box = ErrorMessageBox(message)
            error_box.open()

        # Establish a MySQL database connection
        db_connection = mysql.connector.connect(**db_config)
        db_cursor = db_connection.cursor()
        # read the image in numpy array using cv2
        img = cv2.imread(image_file)
        
        # Decode the barcode image
        detectedBarcodes = decode(img)

        # If not detected then return an error message
        if not detectedBarcodes:
            message = "Barcode Not Detected or your barcode is blank/corrupted!"
            error_box = ErrorMessageBox(message)
            error_box.open()
        else:
            # List to store barcode content
            barcode_contents = []

            # Traverse through all the detected barcodes in the image
            for barcode in detectedBarcodes:
                # Get the content of the barcode
                barcode_content = barcode.data.decode('utf-8')

                # Append the content to the list
                barcode_contents.append(barcode_content)

                 # If not detected then return an error message
        if not detectedBarcodes:
            message = "Barcode Not Detected or your barcode is blank/corrupted!"
            error_box = ErrorMessageBox(message)
            error_box.open()
        else:
            # List to store barcode content
            barcode_contents = []

            # Traverse through all the detected barcodes in the image
            for barcode in detectedBarcodes:
                # Get the content of the barcode
                barcode_content = barcode.data.decode('utf-8')

                # Append the content to the list
                barcode_contents.append(barcode_content)

                # Insert the barcode data into the MySQL database

                # Check if the barcode exists and get its status
                select_query = "SELECT STATUS, COUNTER FROM MACHINE WHERE BARCODE = %s"
                data = (barcode_content,)
                db_cursor.execute(select_query, data)
                result = db_cursor.fetchone()

                if result is None:
                    # Barcode doesn't exist, so insert a new instance
                    insert_query = "INSERT INTO MACHINE (BARCODE, COUNTER, STATUS) VALUES (%s, 0, 'active')"
                    data = (barcode_content,)
                    db_cursor.execute(insert_query, data)
                    db_connection.commit()
                else:
                    # Barcode exists, check and update the status
                    current_status, counter = result
                    if current_status == 'inactive':
                        # If status is 'inactive', change it to 'active'
                        update_query = "UPDATE MACHINE SET STATUS = 'active' WHERE BARCODE = %s"
                        db_cursor.execute(update_query, data)
                        db_connection.commit()

                # Set status to 'inactive' for all other instances that were previously 'active'
                update_other_instances_query = "UPDATE MACHINE SET STATUS = 'inactive' WHERE BARCODE != %s AND STATUS = 'active'"
                # Information Message of the STATUS
                message = "The Robotic arm with the Barcode << {} >> is ACTIVE".format(barcode_content)
                info_box = InformationMessageBox(message)
                info_box.open()
                db_cursor.execute(update_other_instances_query, data)
                db_connection.commit()
                # Close the database connection
                db_cursor.close()
                db_connection.close()

if __name__ == '__main__':
    CameraApp().run()

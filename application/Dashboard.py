import logging
import os
import subprocess
from dash import Dash, html, dcc, Input, Output, State
from dash_bootstrap_templates import ThemeChangerAIO, template_from_url
import dash_bootstrap_components as dbc
import dash_extensions as de
import dash_daq as daq
import RPi.GPIO as GPIO
import bluetooth
import time
from time import sleep
import Freenove_DHT as DHT
import smtplib, ssl, getpass, imaplib, email
import random
from paho.mqtt import client as mqtt_client
from datetime import datetime
import pymysql
import pymysql.cursors

#removes the post update component in the terminal
logging.getLogger('werkzeug').setLevel(logging.ERROR)

external_stylesheets = [dbc.themes.BOOTSTRAP]

app = Dash(__name__, external_stylesheets=external_stylesheets, meta_tags=[
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1.0",
        }
    ])


#---------User Information Variables-------
user_id = "Default"
temp_threshold = 25.0
light_threshold = 500
humidity = 35
path_to_picture = 'assets/cruz.jpg'
#-----------------------------------------

#MQTT connection variables
broker = '192.168.0.107' #ip in Lab class
port = 1883
topic1 = "esp/lightintensity"
topic2 = "esp/rfid"
client_id = f'python-mqtt-{random.randint(0, 100)}'
esp_message = 0
esp_rfid_message = "000000"

temp_email_sent = False
fan_status_checker = False
email_counter = 0    # just checks if email has been sent at some stage

temperature = 0

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
DHTPin = 29 # equivalent to GPIO21

Motor1 = 15 # Enable Pin
Motor2 = 13 # Input Pin
Motor3 = 11 # Input Pin
LedPin = 32

GPIO.setup(Motor1, GPIO.IN)
GPIO.setup(Motor2, GPIO.IN)
GPIO.setup(Motor3, GPIO.IN)
GPIO.setup(LedPin, GPIO.OUT)
GPIO.setup(DHTPin, GPIO.OUT)

light_bulb_off = 'assets/lightbulbOFF.png'        
light_bulb_on = 'assets/lightbulbON.png'       
url="https://assets5.lottiefiles.com/packages/lf20_UdIDHC.json" #fan lottie gif
options = dict(loop=True, autoplay=True, rendererSettings=dict(preserveAspectRatio='xMidYMid slice'))
url2 = "https://assets8.lottiefiles.com/packages/lf20_ylvmhzmx.json" #bluetooth lottie gif

daq_Gauge = daq.Gauge(
                id='my-gauge-1',
                label="",
                showCurrentValue=True,
                size=250,
                max=100,
                min=0,
                style={'margin': 'auto'}  )

html_Humidity_Label = html.H2("Humidity", style={'text-align': 'center'});


daq_Thermometer = daq.Thermometer(
                    id='my-thermometer-1',
                    min=-40,
                    max=60,
                    scale={'start': -40, 'interval': 10},
                    label="",
                    showCurrentValue=True,
                    height=150,
                    units="C",
                    color="red")

html_Temperature_Label = html.H2("Temperature Fan", style={'text-align': 'center'});


daq_Led_Light_Intensity_LEDDisplay = html.Div(
    id='light-intensity',
    children=[
        html.Label("Light Intensity Value", style={'font-weight': 'bold'}),
        html.Div(id='light-intensity-value', style={'font-size': '24px'})
    ]
)
 
html_Div_Fan_Gif = html.Div([de.Lottie(options=options, width="40%", height="25%", url=url, id='lottie-gif', isStopped=True, isClickToPauseDisabled=True)], id='fan_display')
html_Fan_Status_Message = html.H5(id='fan_status_message',style={'text-align':'center'})
html_Fan_Label = html.H2("Motor Fan", style={'text-align': 'center'});

html_Light_Intensity_Label =  html.H2('Light Intensity',style={'text-align':'center'})
html_Led_Status_Message = html.H1(id='light_h1',style={'text-align':'center'})

html_Bluetooth_Gif = html.Div([de.Lottie(options=options, width="40%", height="25%", url=url2, isClickToPauseDisabled=True)])
html_bluetooth_Label =  html.H2('Bluetooth Devices',style={'text-align':'center'})

fan_Status_Message_Interval = dcc.Interval(
            id='fan_status_message_update',
            disabled=False,
            interval=1 * 3000,
            n_intervals=0)
            
fan_Interval = dcc.Interval(
            id = 'fan-update',
            disabled=False,
            interval = 1 * 8000,  
            n_intervals = 0)
            
humidity_Interval = dcc.Interval(
            id = 'humid-update',
            disabled=False,
            interval = 1 * 3000,
            n_intervals = 0)

temperature_Interval =  dcc.Interval(
            id = 'temp-update',
            disabled=False,
            interval = 1*20000,  
            n_intervals = 0)

light_Intensity_Interval =  dcc.Interval(
            id = 'light-intensity-update',
            disabled=False,
            interval = 1*5000,   
            n_intervals = 0)

led_On_Email_Interval = dcc.Interval(
            id = 'led-email-status-update',
            disabled=False,
            interval = 1*5000,   
            n_intervals = 0)

userinfo_Interval = dcc.Interval(
            id = 'userinfo-update',
            disabled=False,
            interval = 1*2000,   
            n_intervals = 0)

bluetooth_Interval = dcc.Interval(
            id = 'bluetooth-update',
            disabled=False,
            interval = 1*2000,   
            n_intervals = 0)


sidebar = html.Div([
    html.H3('User Profile', style={'text-align': 'center', 'margin-top': '20px'}),
    dbc.CardBody([
            html.Img(src=path_to_picture, id="picture_path", style={'border-radius': '80px', 'width':'140px', 'height':'140px', 'object-fit': 'cover', 'display': 'block','margin-left':'auto','margin-right': 'auto'}),
            html.H3("Username:" + str(user_id), style={'margin-top':'30px'}, id="username_user_data"),
            html.H4("Favorites ", style={'margin-top':'40px'}),
            html.H5("Humidity: " + str(humidity), style={'margin-left':'15px'}, id="humidity_user_data"),
            html.H5("Temperature: " + str(temp_threshold), style={'margin-left':'15px'}, id="temperature_user_data"),
            html.H5("Light Intensity: " + str(light_threshold), style={'margin-left':'15px'}, id="lightintensity_user_data")
            ])
    ])

card_content1 = dbc.Container(
    [
        """ dbc.Row(
            [
                dbc.Col(
                    html.H1(
                        html.B("IOT PROJECT PHASE 4"),
                        className="text-center",
                    )
                )
            ]
        ), """
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    dbc.Col(
                        html.Div([
                            html_Humidity_Label,
                            daq_Gauge
                        ], style={'text-align': 'center'})
                    ),
                    color="secondary",
                    inverse=True,
                    style={"width": "30rem", 'height': "22rem"}
                ),
                width="auto"
            ),
            dbc.Col(
                dbc.Card(
                    dbc.Col(
                        html.Div([
                            html_Temperature_Label,
                            daq_Thermometer
                        ], style={'text-align': 'center'})
                    ),
                    color="secondary",
                    inverse=True,
                    style={"width": "30rem", 'height': "22rem"}
                ),
                width="auto"
            ),
            dbc.Col(
                dbc.Card(
                    dbc.Col(
                        html.Div([
                            html_Fan_Label,
                            html_Div_Fan_Gif,
                            html_Fan_Status_Message
                        ])
                    ),
                    color="secondary",
                    inverse=True,
                    style={"width": "30rem", 'height': "22rem"}
                ),
                width="auto"
            )
        ], justify="center")
        dbc.Row([
            dbc.Col(dbc.Card(
                     html.Div([
                         html_Light_Intensity_Label,
                         html.Img(id="light-bulb", src=light_bulb_off,
                                  style={'width':'80px', 'height': '110px',
                                  'display': 'block','margin-left':'auto','margin-right': 'auto', 'margin-top':'10px'}),
                         html.H3(id='light-intensity-label', style={'text-align': 'center'}),
                         html.H5(id='email_heading',style ={"text-align":"center"}) ]),
                     color="secondary", inverse=True, style={"width": "30rem", 'height': "22rem"}), width="auto"),
            dbc.Col(dbc.Card(
                html.Div([
                    html_bluetooth_Label,
                    html_Bluetooth_Gif,
                    html.H5("Number of Bluetooth Devices: ", id='bluetooth_heading',style ={"text-align":"center", 'margin-top':'10px'}),
                ]),
                color="secondary", inverse=True, style={"width": "30rem", 'height': "22rem"}), width="auto")],
            justify="center",
        className="mt-5"),
    ],
    fluid=True,)

content = html.Div([
           dbc.Row([
                card_content1,
                humidity_Interval, temperature_Interval, light_Intensity_Interval, led_On_Email_Interval,
                userinfo_Interval, bluetooth_Interval, fan_Status_Message_Interval, fan_Interval
             ]),
        ])

# Dashboard Layout
app.layout = dbc.Container([
                dbc.Row([
                    dbc.Col(sidebar, width=2), 
                    dbc.Col(content, width=10, className="bg-secondary") # content col
                ], style={"height": "100vh"}), # outer
            ], fluid=True) #container

# Callback for the humidity
@app.callback(Output('my-gauge-1', 'value'), Input('humid-update', 'n_intervals'))
def update_output(value):
    dht = DHT.DHT(DHTPin)  
    while(True):
        for i in range(0,15):            
            chk = dht.readDHT11()    
            if (chk is dht.DHTLIB_OK):      
                break
            time.sleep(0.1)
        time.sleep(2)
        print("Humidity : %.2f \t \n"%(dht.humidity))  
        return dht.humidity

# Callback for thermometer conversion
@app.callback(
    [Output('my-thermometer-1', 'value'),
     Output('my-thermometer-1', 'min'),
     Output('my-thermometer-1', 'max'),
     Output('my-thermometer-1', 'scale'),
     Output('my-thermometer-1', 'units')],
    [Input('my-thermometer-1', 'value'),
    Input('temp-update', 'n_intervals')])
def update_output(temp_value, interval_value):
    dht = DHT.DHT(DHTPin)   
    while(True):
        for i in range(0,15):            
            chk = dht.readDHT11()     
            if (chk is dht.DHTLIB_OK):      
                break
            time.sleep(0.1)
        time.sleep(2)
        temperature = dht.temperature
        print("Temperature : %.2f \n"%(dht.temperature))
        global temp_email_sent
        if dht.temperature >= temp_threshold and temp_email_sent == False:
            sendEmail()
            temp_email_sent = True

        return temperature, -40, 60, {'start': -40, 'interval': 10}, 'C'

# Checks if the Motor is active or not
def is_fan_on():  
    if GPIO.input(Motor1) and not GPIO.input(Motor2) and GPIO.input(Motor3):
        return True
    else:
        return False

# Callback for the Fan Lottie gif and status message
@app.callback([Output('fan_status_message', 'children'), Output('lottie-gif', 'isStopped')],
              Input('fan_status_message_update', 'n_intervals'))
def update_h1(n):
    fan_status_checker = is_fan_on()
    
    if fan_status_checker:
        return "Status: On", False
    
    else:
        return "Status: Off", True

# Callback for updating user information in the dashboard
@app.callback([Output('username_user_data', 'children'),
               Output('humidity_user_data', 'children'),
               Output('temperature_user_data', 'children'),
               Output('lightintensity_user_data', 'children'),
               Output('picture_path', 'src')],
               Input('userinfo-update', 'n_intervals'))
def update_user_information(n):
    return "Username: " + str(user_id) ,"Humidity: 40" ,"Temperature: " +  str(temp_threshold), "Light Intensity: " + str(light_threshold), path_to_picture

#Callback for light intensity
@app.callback(Output('light-intensity-label', 'children'),Input('light-intensity-update', 'n_intervals'))  
def update_output(value):
    light_intensity = esp_message
    print("Here is light intensity:", light_intensity)
    
    return f"{light_intensity}"



""" sender_email = "iotprojectemail1@gmail.com"
receiver_email = "laronichill@gmail.com"
password = "xhym qvsv srmj zfav"
smtp_server = "smtp.gmail.com" """

#Email methods
def sendEmail(): #for temperature
        port = 587  # For starttls
        smtp_server = "smtp.gmail.com"
        sender_email = "iotprojectemail1@gmail.com"
        receiver_email = "laronichill@gmail.com"
        password = "xhym qvsv srmj zfav"
        subject = "Subject: FAN CONTROL" 
        body = "Your home temperature is greater than your desired threshold. Do you wish to turn on the fan. Reply YES if so."
        message = subject + '\n\n' + body
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

def sendLedStatusEmail(): #for LED
        port = 587  # For starttls
        smtp_server = "smtp.gmail.com"
        sender_email = "iotprojectemail1@gmail.com"
        receiver_email = "laronichill@gmail.com"
        password = "xhym qvsv srmj zfav"
        subject = "Subject: LIGHT NOTIFICATION" 
        current_time = datetime.now()
        time = current_time.strftime("%H:%M")
        body = "The Light is ON at " + time
        message = subject + '\n\n' + body
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)

def sendUserEnteredEmail(user_name): #for user(rfid)
        port = 587  # For starttls
        smtp_server = "smtp.gmail.com"
        sender_email = "iotprojectemail1@gmail.com"
        receiver_email = "laronichill@gmail.com"
        password = "xhym qvsv srmj zfav"
        subject = "Subject: USER ENTERED" 
        current_time = datetime.now()
        time = current_time.strftime("%H:%M")
        body = user_name + " has entered at: " + time
        message = subject + '\n\n' + body
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message) 
        
# MQTT subscribe codes
def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
            time.sleep(10)
        else:
            print("Failed to connect, return code %d\n", rc)
    client = mqtt_client.Client(client_id)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def on_message_from_lightintensity(client, userdata, message):
   global esp_message
   esp_message = int(float(message.payload.decode()))
   

#MQTT for rfid tag
def on_message_from_rfid(client, userdata, message):
   global esp_rfid_message
   esp_rfid_message = message.payload.decode()
   print("Message Received from rfid: ")
   print(esp_rfid_message)
   get_from_database(esp_rfid_message)
   sendUserEnteredEmail(esp_rfid_message)

def on_message(client, userdata, message):
   print("Message Received from Others: "+message.payload.decode())
   
def run():
    client = connect_mqtt()
    client.subscribe(topic1, qos=1)
    client.subscribe(topic2, qos=1)
    client.message_callback_add(topic1, on_message_from_lightintensity)
    client.message_callback_add(topic2, on_message_from_rfid)
    client.loop_start()

def get_from_database(rfid):
    connection = pymysql.connect(host='localhost',
                             user='root',
                             password='root',
                             database='IOT',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
        sql = "SELECT * FROM USER WHERE id = %s"
        cursor.execute(sql, (rfid))
        user_info = cursor.fetchone()
    print("Result from database select: ")
    
    print(user_info)
    if(user_info):
        global email_counter 
        global temp_email_sent
        temp_email_sent = False
        email_counter = 0
        global user_id
        user_id = user_info['id']
        global temp_threshold
        temp_threshold = user_info['temp_threshold']
        global light_threshold
        light_threshold = user_info['light_threshold']
        global path_to_picture
        path_to_picture = user_info['picture']
        
    print(str(user_id) + " " + str(temp_threshold) + " " + str(light_threshold) + " " + path_to_picture)

def send_led_email_check(lightvalue):        
      global email_counter
      if lightvalue < light_threshold and email_counter == 0:
         print("passed here in send_led_email_check")
         sendLedStatusEmail()
         email_counter += 1
         
@app.callback([Output('email_heading', 'children'), Output('light-bulb', 'src')], Input('led-email-status-update', 'n_intervals'))      
def update_email_status(value):
    lightvalue = esp_message
    send_led_email_check(lightvalue)
    
    if email_counter > 0 and lightvalue < light_threshold:
        GPIO.output(LedPin, GPIO.HIGH)
        return "Email has been sent. Lightbulb is ON", light_bulb_on
    elif email_counter > 0 and lightvalue > light_threshold:
        GPIO.output(LedPin, GPIO.LOW)
        return "Email has been sent. Lightbulb is OFF", light_bulb_off
    else:
        GPIO.output(LedPin, GPIO.LOW)
        return "No email has been sent. Lightbulb is OFF", light_bulb_off

@app.callback(Output('bluetooth_heading', 'children'), Input('bluetooth-update', 'n_intervals'))
def update_bluetooth(value):
    return "Number of Bluetooth devices: " + str(scanNumberOfBluetoothDevices())

def scanNumberOfBluetoothDevices():
    number_of_devices = 0
    output = subprocess.check_output(['bluetoothctl', 'devices'])
    for word in output.split():
        if word == b'Device':
            number_of_devices += 1
    
    return number_of_devices
        
run()

if __name__ == '__main__':
   #app.run_server(debug=True)
    app.run_server(debug=False,dev_tools_ui=False,dev_tools_props_check=False)


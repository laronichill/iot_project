import smtplib, ssl, getpass
from datetime import datetime

class Send: 
    #code to send the email
    def sendEmail():
        port = 587  # For starttls
        sender_email = "iotprojectemail1@gmail.com"
        receiver_email = "laronichill@gmail.com"
        password = "xhym qvsv srmj zfav"
        smtp_server = "smtp.gmail.com"
        subject = "Subject: Light" 
        current_time = datetime.now()
        time = current_time.strftime("%H:%M")
        body = "The Light is ON at " + time
        message = subject + '\n\n' + body

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, port) as server:
            server.ehlo()  
            server.starttls(context=context)
            server.ehlo()  
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message)
            

sendEmail()


import requests
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr


def sendAlert(to, subject, body):
    username = "verify@hotimportnights.com"
    password = "HINconnect2020"
    server = "smtp.gmail.com"
    port = 465

    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((str(Header('Hot Import Nights', 'utf-8')), username))
    msg['To'] = to
    msg['Subject'] = subject

    html = body
    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP_SSL(server, port)
        server.login(username, password)
        server.sendmail(username, to, msg.as_string())
    except Exception as e:
        print(e)
    finally:
        server.quit()


def main():
    try:
        out = requests.get("https://hin-connect.com/health")
    except Exception as e:
        sendAlert("cnelson7265@gmail.com", "hin-connect unhealthy", "Unhealthy")
        return
    if out.status_code != 200:
        sendAlert("cnelson7265@gmail.com", "hin-connect unhealthy", "Unhealthy")
        return

    print("Healthy")

if __name__ == "__main__":
    main()

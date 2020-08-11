from aip import AipFace
from picamera import PiCamera
import urllib.request
import RPi.GPIO as GPIO
import base64
import time
import sys
import cv2
import os
import MySQLdb
import smtplib
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# 百度人识别API信息
APP_ID = '19374140'
API_KEY = '#################'
SECRET_KEY = '######################'
client = AipFace(APP_ID, API_KEY, SECRET_KEY)  # 创建客户端访问百度云
# 图像编码方式base64
IMAGE_TYPE = 'BASE64'

# 用户组
GROUP = 'zu'
GPIO_OUT = 17  # 定义gpio输出口

# 打开数据库连接
db = MySQLdb.connect("101.200.226.141", "root", "zgh789..", "raspi", charset='utf8')

# 使用cursor()方法获取操作游标
cursor = db.cursor()

#发送邮件函数
# 功能：发送解锁记录到邮箱
# 参数：log_info：用户名，时间
# 返回值：无
def smtp_email(log_info):
    # 1.连接邮箱服务器:
    con=smtplib.SMTP_SSL('smtp.qq.com' ,465)
    # 2.登陆邮箱
    #连接对象.login(id,passwd)
    #密码-写授权码
    con.login('2986627051@qq.com' , '##################')
    # 3.准备数据
    msg=MIMEMultipart()
    #设置邮件的主题
    subject=Header('登录提醒','utf-8').encode()
    msg['Subject']=subject

    #设置邮件发送人
    msg['From']='2986627051@qq.com '
    #设置邮件的收件人
    msg['To']='1987698934@qq.com'
    #设置邮件内容
    
    #html文本创建
    content="""
    <h1>登陆记录</h1>
    <h3>人脸识别门禁系统</h3>
    <p>'{}'</p>
    <img src='cid:dsaf'>
    """
    content1=content.format(log_info)
    html =MIMEText(content1,'html','utf-8')

    #4.发送邮件
    #读取图片
    fp=open('faceimage.jpg','rb').read()
    image1=MIMEImage(fp)
    image1["Content-Disposition"]='attachment; filename="faceimage.jpg"'
    image1.add_header('Content-ID','<dsaf>')
    msg.attach(image1)
    msg.attach(html)
    con.sendmail('2986627051@qq.com','15004780816@163.com',msg.as_string())
    con.quit()
#上传数据库函数
# 功能：把登录信息上传到mysql
# 参数：name：用户名 time：解锁时间
# 返回值：无
def save_datebase(name, time):
    #sql语句
    sql1 = """INSERT INTO log(name,time)  
             VALUES ('{}','{}')"""
    sql = sql1.format(name, time)
    try:
        # 执行sql语句
        cursor.execute(sql)
        # 提交到数据库执行
        db.commit()
    except:
        # Rollback in case there is any error
        db.rollback()

        # 关闭数据库连接
        db.close()


# 拍照函数
# 功能：使用opencv的级联分类器检测人脸，当检测到人脸保存图片
# 参数：无
# 返回值：无
def face_detection():
    cam = cv2.VideoCapture(0)
    cam.set(3, 640)  # set video width
    cam.set(4, 480)  # set video height
    face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    print("\n [INFO] Initializing face capture. Look the camera and wait ...")
    # Initialize individual sampling face count
    count = 0
    while (True):
        ret, img = cam.read()
        img = cv2.flip(img, 1)  # flip video image vertically
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_detector.detectMultiScale(gray, 1.3, 5)
        falg = 0
        for (x, y, w, h) in faces:
            # cv2.rectangle(img, (x,y), (x+w,y+h), (255,0,0), 2)    
            # Save the captured image into the datasets folder
            time.sleep(1)
            cv2.imwrite('faceimage.jpg' , img)
            falg = 1
            time.sleep(1)
            cam.release()
            break
        if falg == 1:
            break


# 初始化舵机函数
# 功能：无
# 参数：无
# 返回值：无
def init_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(GPIO_OUT, GPIO.OUT)


# 计算pwm占空比函数
# 功能：计算角度用来控制舵机旋转
# 参数：GPIO_OUT：pwm波输出引脚
# angle：旋转角度
# 返回值：无
def setGPIO_OUTAngle(GPIO_OUT, angle):  # 参数1：输出GPIO口  参数2：角度
    pwm = GPIO.PWM(GPIO_OUT, 50)  # pwm波产生周期
    pwm.start(8)
    dutyCycle = float(angle) / 18 + 2.5  # pwm占空比计算
    pwm.ChangeDutyCycle(dutyCycle)
    time.sleep(0.3)
    pwm.stop()  # pwm波停止函数，不加会导致电机只能运行一次

# 图片格式转换函数
# 功能：转换图片格式为base64
# 参数：无
# 返回值：img转换好的图片
def transimage():
    f = open('faceimage.jpg', 'rb')
    img = base64.b64encode(f.read())
    return img


# 上传到百度api函数
# 功能：上转到百度智能云进行人脸库搜索
# 参数：base64格式的图片
# 返回值：用户id，相似度，人脸名字
def go_api(image):
    result = client.search(str(image, 'utf-8'), IMAGE_TYPE, GROUP);  # 在百度云人脸库中寻找是否存在匹配人脸
    if result['error_msg'] == 'SUCCESS':
        name = result['result']['user_list'][0]['user_id']  # 获取id
        score = result['result']['user_list'][0]['score']  # 获取相似度
        curren_time = time.asctime(time.localtime(time.time()))  # 获取当前时间
        print(result)
        print(score)
        if score > 80:  # 相似度>80
            print('欢迎%s!' % name)
            time.sleep(3)
        else:
            print('人脸信息不存在')
            name = '陌生人'
            save_datebase(name, str(curren_time))
            log_info =name + "在" + str(curren_time) + "进行了解锁"
            smtp_email(log_info)
            f = open('log.txt', 'a')
            f.write("person:" + name + "   " + "time:" + str(curren_time) + '\n')
            f.close()
            return 0

        # 记录日志
        save_datebase(name, str(curren_time))
        f = open('log.txt', 'a')
        f.write("person:" + name + "   " + "time:" + str(curren_time) + '\n')
        log_info = name + "在" + str(curren_time) + "进行了解锁"
        smtp_email(log_info)
        f.close()
        return 1

    if result['error_msg'] == 'pic not has face':
        print('未检测到人脸')
        time.sleep(2)
        return 0
    else:
        print(result['error_code'] + ' ' + result['error_code'])
        return 0


# main
if __name__ == "__main__":
    while True:
        init_gpio()  # 初始化舵机
        if True:
            face_detection()
            img = transimage()  # 转换照片格式
            res = go_api(img)  # 将转换好的照片上传到百度云
            if (res == 1):  # 比对成功，是人脸库中的人
                print("开门")
                setGPIO_OUTAngle(GPIO_OUT, 100)  # 调用舵机函数
                GPIO.cleanup()  # 释放脚本中的使用的引脚，
            elif (res == -1):
                print("未识别到人脸，门即将关闭")
            else:
                print("关门")
            time.sleep(6)
            print("ok，关门")
            init_gpio()  # 初始化舵机
            setGPIO_OUTAngle(GPIO_OUT,10)
            GPIO.cleanup()
            time.sleep(5)

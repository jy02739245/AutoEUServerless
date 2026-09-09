# AutoEUServerless

AutoEUServerless 是一个基于腾讯云函数 Serverless 架构的自动化工具，用于自动续期 EUserv 免费 IPv6 VPS。项目目的是简化续期过程，避免因遗忘续期而导致服务中断。

## 功能
- **自动续期**：自动获取账号内所有的 VPS 项目，并检测是否需要续期。
- **多账户支持**：支持配置多个 EUserv 账户。
- **自动获取PIN码**：支持通过转发规则解析获取邮箱PIN码。
- **验证码识别**：自动识别登录过程中的验证码。
- **Telegram 通知**：通过 Telegram Bot 发送续期状态通知。

## 使用说明
大家都应该有一只德鸡,即乌龟壳之后唯一的一个永久免费VPS。  
但是头疼的是必须每个月要续订,而且本身就是白嫖鸡,难道要再开一个鸡跑脚本来给它续订?  
于是本项目诞生了,支持使用腾讯云函数或AWS工作流,自动续订你的德鸡并且对接Telegram推送!  

[Dooo.ng个人站点](https://dooo.ng)  
[Nodeseek主页:@WizisCool](https://www.nodeseek.com/space/8902#/general)  

**⭐️开发不易,如果觉得项目不错,请施舍一个Star!⭐️**  
**☕喝个咖啡吧!☕**
```
TRC20: TBY7e7YUQCG7wEH3PA8pk6fQPwpshb8Z55
```

## 使用说明
已添加Github Action模板,更加方便的使用,无需腾讯云函数(**已不在免费**),自行修改Action Secrets 即可,推荐有基础的用户使用,暂时没精力写教程

## 各家大厂云函数Serverless对比一览表

| 厂商 | 请求次数  | 运行时间          | 流量 | 免费数据库 | 区域              | 备注          |
|-------------|---------|-----------------|---------|------------|-----------------------|-------------|
| [AWS](https://aws.amazon.com/cn/serverless/)         | 100万   | 400,000 GB-秒   | 1GB     | 有         | 香港,新加坡,东京     |             |
| [Azure](https://azure.microsoft.com/en-us/products/functions/)       | 100万   | 400,000 GB-秒   | 5GB     | 有         | 香港,新加坡,日本, | **[存储空间需要收费](https://azure.microsoft.com/zh-cn/pricing/details/functions/)** |
| [Google Cloud](https://cloud.google.com/functions?hl=zh_cn)| 200万   | 400,000 GB-秒+200,000GHz | 5GB     | 有         | 香港,台湾            |  |
| [IBM Cloud](https://www.ibm.com/cloud/learn/serverless)   | 无限     | 400,000 GB-秒   | 不明     | 有         | 东京                  |             |
| ~~[阿里云](https://cn.aliyun.com/product/fc?from_alibabacloud=)~~      | ~~100万~~   | ~~400,000 CU-秒~~   | 无      | 无         | ~~大陆,香港,东京,新加坡~~ |    **[不再免费](https://help.aliyun.com/document_detail/2512929.html)**          |
| ~~[腾讯云](https://cloud.tencent.com/product/scf)~~       | ~~10万~~    | ~~20,000 GB-秒~~    | ~~0.5GB~~   | ~~无~~         | ~~中国、香港、新加坡~~     | **[不再免费](https://cloud.tencent.com/document/product/583/12282)**      |
| ~~[百度云](https://cloud.baidu.com/product/cfc.html)~~       | ~~100万~~   | ~~400,000 GB-秒~~   | ~~1GB~~     | 无         | ~~仅大陆~~                  | **[不再免费](https://cloud.baidu.com/doc/CFC/s/Tl0sz7k6j#%E5%85%8D%E8%B4%B9%E9%A2%9D%E5%BA%A6)**            |
| [华为云](https://www.huaweicloud.com/product/functiongraph.html)       | 100万   | 400,000 GB-秒   | 不明     | 无         | 大陆,泰国,香港       |             |
| [**Github Action**](https://docs.github.com/actions)       | 不明   | 不明   | 不明     | 无         | 不明       |    ***推荐使用***         |

**目前国内厂家只剩华为一家,估计也要很快收费了
就EUserV自动续费项目而言,推荐使用Github Action来完成,100%稳定,目前已经更新了Workflow代码
Fork一个到自己的仓库然后点个Star⭐️ 改一下仓库的Action Secrets 即可**

## 截图  
![Alt text](image/screenshot1.png)


## 致谢
特别感谢以下项目和文章对本项目的启发和帮助：
- [eu_ex](https://github.com/lw9726/eu_ex)
- [EUserv_extend](https://github.com/o0oo0ooo0/EUserv_extend)

## 许可
本项目基于 GPL-3.0 许可协议。


## 如何使用
1. 新建一个BeautifulSoup层  
    进入[腾讯云函数服务](https://console.cloud.tencent.com/scf/)  
    新建一个层
    ![Alt text](image/step1.jpg)
    - [**BeautifulSoup.zip**](BeautifulSoup.zip)  <-- 此处下载BeautifulSoup
    - 运行环境选择**Python3.6**
    - 注意层要选择非大陆地区且和第二部的层地区一致

2.  选择函数服务,新建一个函数 
    ![Step1](image/step2.png)
    - 由于免费的德鸡在德国,腾讯云函数只有一个欧洲机房,所以我们选择法兰克福
    - 其实选择HK或者SG也是差不多的  

3.  新建一个函数,和图片操作保持一致
    ![Step3](image/step3.png)
  
4.  复制本库的 [**main.py**](/main.py) 中的全部代码  
    粘贴到在线编辑框内  
    
5.  填写这一部分  *
    ![Step4](image/step4.png)  
    - TelegramBOT相关如何获取请搜索Youtube
    - **此时如果你还不知道如何填写Mailparser部分,暂时留空,下面有教学*

6.  **在EUserV中关闭登录二次验证!**  
    ![Step6](image/step6.png)  
    - 进入EuserV的管理面板,点击[**Settings**] -> 勾选 [**Deactivated (insecure)**] -> 点击[**Save**]

7.  配置函数的运行函数
    ![Step7](image/step7.png)
    - [函数服务] -> [函数管理]
    - 内存64MB就足够,执行事件考虑网络延迟给到[300]秒
    - 下面有个日志投递,建议开启方便debug

8.  绑定BeautifulSoup层
    ![Step8](image/step8.png)

9.  测试函数
    ![Step9](image/step9.png)
    - 此时可以点击部署并测试函数,检查日志是否有错误
    - 检查Telegram机器人是否正常发送日志
    - 没填写Mailparser也可以先测试以下看下TG Bot和登录是否正常

10. 创建定时触发器
    ![Step10](image/step10.png)
    ```
    0 0 12 */7 * * *
    ```
    - 代表每七天的中午12点触发一次,你也可以自定义

#### 11. 现在你可以毫无顾虑的让你的🐥小鸡吃灰了


## 如何配置 Mailparser
- 此功能的原理是让你绑定邮箱的PIN码邮件转发到 [Mailparser]("https://mailparser.io/")
- 之后通过规则功能筛选出PIN码,填表续订的目的
- [PIN码模板](#pin码邮件模板) 在文档的最后面

1. 首先去注册一个[Mailparser]("https://mailparser.io/")然后创建一个邮箱,不多解释
2. 然后将你绑定邮箱添加一个转发规则,这里以Gmail作为例子
    ![Step11](image/step11.png)
3. 按照图片填写转发规则
    ![Step12](image/step12.png)
    ![Step13](image/step13.png)
    - 你的登录PIN码和续订PIN码不是一样的!所以不要擅作主张修改
    - 只要一字不差的按照图片填写是没有错的!
4.  添加邮箱规则
    ![Step14](image/step14.png)
    - 此步骤需要注意, 你需要至少有一封邮件才可以创建规则
    - 你可以使用你自己的邮箱向收件箱发送一个[模板](#pin码邮件模板)

#### 此步骤开始严格按照教程走,禁止开动小脑筋

5.  #### 添加取PIN码的规则
    ![Alt text](<image/mailparser_data_parsing_rules_pin .png>)
6.  #### 添加取邮件标题的规则
    ![Alt text](image/mailparser_data_parsing_rules_subject.png)
7.  #### 添加筛选发件人邮箱地址的规则
    ![Alt text](image/mailparser_data_parsing_rules_sender.png)
8.  #### 筛选出收件人邮箱地址的规则  
    ![Alt text](image/mailparser_data_parsing_rules_receiver.png)
9.  #### 现在你的规则列表看起来应该是这样子的  
    ![Alt text](image/role.png)
10. #### 接下来我们添加一个下载URL
    ![Alt text](image/downloads.png)
11. #### 下载URL设置  
    ![Alt text](image/downloadurlsetting.png)
12. #### 收件设置
    ![Alt text](image/setting.png)
    ```
    邮件标题:
    EUserv - PIN for the Confirmation of a Security Check
    ```

13. ### 终于我们可以拿到Mailparser的URL_ID了
    ![Alt text](image/geturlid.png)
    ### 填写到python代码中
## PIN码邮件模板
```
From：	     EUserv Support <support@euserv.de>
To：	         你的绑定@邮箱.康姆
Subject：	 EUserv - PIN for the Confirmation of a Security Check
Content-Type: text/plain; charset = utf-8
Dear 你的名字,

you have just requested a PIN for confirmation of a security check at EUserv. If you have not requested the PIN then ignore this email.

PIN:
123456

PLEASE NOTE: If you already have requested a new PIN for the same process this PIN is invalid. Also this PIN is only valid within the session in which it has been requested. This means the PIN is invalid if you for example change the browser or if you logout and perform a new login.


Sincerely,
Your customer support EUserv

--
Web ................: http://www.euserv.com
Login control panel.: https://support.euserv.com
FAQ ................: http://faq.euserv.com
Help & Guides.......: http://wiki.euserv.com
Community / Forum...: http://forum.euserv.com
Mailing-Liste ......: http://www.euserv.com/en/?show_contact=mailinglist
Twitter ............: http://twitter.com/euservhosting
Facebook ...........: http://www.facebook.com/euservhosting
--

EUserv Internet
is a division of
ISPpro Internet KG

Postal address:
ISPpro Internet KG
Division EUserv Internet
P.O. Box 2224
07622 Hermsdorf
GERMANY

Support-Phone: +49 (0) 3641 3101011 (English speaking)

Administration:
ISPpro Internet KG
Neue Str. 4
D-07639 Bad Klosterlausnitz
GERMANY

Management...............: Dirk Seidel
Register.................: AG Jena, HRA 202638
VAT Number...............: 162/156/36600
Tax office ..............: Jena
International VAT Number.: DE813856317
```

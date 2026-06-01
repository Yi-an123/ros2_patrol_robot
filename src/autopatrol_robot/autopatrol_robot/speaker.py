import rclpy
from rclpy.node import Node
from autopatrol_interfaces.srv import SpeechText
import espeakng

class Speaker(Node):
    def __init__(self,node_name):
        super().__init__(node_name)
        self.speech_service_ = self.create_service(SpeechText,'speech_text',
                                                   self.speech_text_callback)
        #SpeechText — 服务类型（srv 类型定义）
        # 'speech_text' — 服务名称，其他节点通过这个名字来调用这个服务
        # self.speech_text_callback — 收到请求时的回调函数
        self.speaker_ = espeakng.Speaker() #创建一个说话者
        # 创建一个 espeakng 语音合成引擎的实例，并保存到 self.speaker_ 属性上
        self.speaker_.voice = 'zh' #中文
        
    def speech_text_callback(self,request,response):
        self.get_logger().info(f'正在准备朗读{request.text}')
        self.speaker_.say(request.text)
        self.speaker_.wait()
        response.result = True
        return response
    
def main():
    rclpy.init()
    node = Speaker('speaker')
    rclpy.spin(node)
    rclpy.shutdown()


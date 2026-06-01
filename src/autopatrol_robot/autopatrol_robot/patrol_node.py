import rclpy
from geometry_msgs.msg import PoseStamped,Pose 
#导入 ROS 2 标准消息类型，PoseStamped用于表示"带时间戳的三维位姿"（位置 + 朝向）
from nav2_simple_commander.robot_navigator import BasicNavigator,TaskResult
#导入 Nav2 的 Python 简化 API。BasicNavigator 封装了导航栈的底层调用，可以用几行代码就完成设置初始位姿、发送目标点等操作
#TaskResult
from rclpy.node import Node
from tf2_ros import TransformListener, Buffer
from tf_transformations import euler_from_quaternion,quaternion_from_euler
from autopatrol_interfaces.srv import SpeechText
from sensor_msgs.msg import Image # 消息接口
from cv_bridge import CvBridge # 转换图像格式
import cv2 # 保存图像


class PatrolNode(BasicNavigator):
    #BasicNavigator是继承于Node的，这里新建类继承于BasicNavigator也就相当于继承于Node了
    def __init__(self, node_name='patrol_node'):
        super().__init__(node_name)
        #声明相关参数
        self.declare_parameter('initial_point',[0.0,0.0,0.0]) #x,y,yaw（旋转角度）
        self.declare_parameter('target_points',[0.0,0.0,0.0,1.0,1.0,1.57]) #每三个数一个点
        self.declare_parameter('img_save_path','') # 默认值为空，表示保存到当前目录
        self.initial_point_ = self.get_parameter('initial_point').value #返回的是一个 Python 列表 [x, y, yaw]
        self.target_points_ = self.get_parameter('target_points').value
        self.img_save_path_ = self.get_parameter('img_save_path').value
        self.buffer = Buffer() #储存监听者监听到的机器人坐标
        self.listener = TransformListener(self.buffer, self)
        self.speech_client_ = self.create_client(SpeechText,'speech_text') # 创建客户端
        self.cv_bridge_ = CvBridge()
        self.latest_img_ = None
        self.img_sub_ = self.create_subscription(Image,'/camera_sensor/image_raw',self.img_callback,1)

    def img_callback(self,msg):
        self.latest_img_ = msg

    def record_img(self):
        if self.latest_img_ is not None:
            pose = self.get_current_pose()
            cv_image = self.cv_bridge_.imgmsg_to_cv2(self.latest_img_)
            cv2.imwrite(
                f'{self.img_save_path_}img_{pose.translation.x:3.2f}_{pose.translation.y:3.2f}.png',
                cv_image,
            )

    def get_pose_by_xyyaw(self,x,y,yaw):
        """
        return PoseStamped对象
        """
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.pose.position.x = x
        pose.pose.position.y = y
        #返回顺序是xyzw
        quat = quaternion_from_euler(0,0,yaw)
        pose.pose.orientation.x = quat[0]
        pose.pose.orientation.y = quat[1]
        pose.pose.orientation.z = quat[2]
        pose.pose.orientation.w = quat[3]
        return pose

    def init_robot_pose(self):
        """
        初始化机器人的位姿
        """
        self.initial_point_ = self.get_parameter('initial_point').value #返回的是一个 Python 列表 [x, y, yaw]
        init_pose = self.get_pose_by_xyyaw(self.initial_point_[0], self.initial_point_[1], self.initial_point_[2])
        #不需要传 self。 这是 Python 的基础机制：
        # 定义时：第一个参数必须写 self，用于接收实例引用。调用时：Python 会自动把 . 前面的对象作为 self 传入
        self.setInitialPose(init_pose) #不用 nav. 是因为self本身继承于BasicNavigator，他自带setInitialPose了
        #把初始位姿发给 AMCL。AMCL 收到后，会在 (0, 0) 位置初始化粒子群，定位就从这里开始
        self.waitUntilNav2Active() # 等待导航键激活可用

    def get_target_points(self):
        """
        通过参数值获取目标点的集合
        """
        points = []
        self.target_points_ = self.get_parameter('target_points').value
        for index in range(int(len(self.target_points_)/3)): #target_points_ 6个参数两个点，循环两次
            x = self.target_points_[index*3]
            y = self.target_points_[index*3+1]
            yaw = self.target_points_[index*3+2]
            points.append([x,y,yaw])
            self.get_logger().info(f'获取到目标点{index}->{x},{y},{yaw}')
        return points

    def nav_to_pose(self,target_point):
        """
        导航到目标点
        """
        self.goToPose(target_point)
        # 向 Nav2 发送导航目标 (2.0, 1.0)。BasicNavigator 内部会调用 planner_server 规划全局路径，
        # 再交给 controller_server 驱动小车沿路径走到目标点。这行是异步的——发完就程序继续往下走，不等待完成
        while not self.isTaskComplete():
            #轮询检查导航任务是否结束。isTaskComplete() 返回 True 的情况有：到达目标、任务失败、任务被取消。这是个非阻塞的方法，调用立即返回，不会卡住
            feedback = self.getFeedback()
            #获取导航过程的实时反馈。
            # BasicNavigator 内部订阅了 /follow_path 或 controller_server 发布的反馈话题，这里面包含当前剩余的直线距离、预计到达时间等数据
            self.get_logger().info(f'剩余距离：{feedback.distance_remaining}')
            #distance_remaining 是 planner 规划的剩余路径长度（米），不是直线距离——机器人需要绕过障碍物的话，这个值比直线大
            #nav.cancelTask() 超时取消
        result = self.getResult()
        self.get_logger().info(f'导航结果：{result}')

    def get_current_pose(self):
        """
        获取机器人当前的位置
        """
        while rclpy.ok():
            try:
                tf = self.buffer.lookup_transform(
                    'map', 'base_footprint', rclpy.time.Time(seconds=0), rclpy.time.Duration(seconds=1))
                transform = tf.transform
                self.get_logger().info(f'平移：{transform.translation}')
                return transform
            except Exception as e:
                self.get_logger().warn(f'不能够获取坐标变换，原因: {str(e)}')

    def speech_text(self,text):
        """
        调用服务合成语音
        """
        while not self.speech_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('语音合成未上线，等待中...')
        request = SpeechText.Request()
        request.text = text
        futrue = self.speech_client_.call_async(request)
        rclpy.spin_until_future_complete(self,futrue)
        if futrue.result() is not None:
            response = futrue.result()
            if response.result == True:
                self.get_logger().info(f'语音合成成功{text}')
            else:
                self.get_logger().warn(f'语音合成失败{text}')
        else:
                self.get_logger().warn('语音合成服务响应失败')



def main():
    rclpy.init()
    patrol = PatrolNode() #节点
    patrol.speech_text('正在准备初始化位置')
    patrol.init_robot_pose()
    patrol.speech_text('位置初始化完成')

    while rclpy.ok():
        points = patrol.get_target_points()
        for point in points:
            x,y,yaw = point[0],point[1],point[2]
            target_pose = patrol.get_pose_by_xyyaw(x,y,yaw)
            patrol.speech_text(f'正在准备前往{x},{y}目标点')
            patrol.nav_to_pose(target_pose)
            patrol.speech_text(f'已经到达目标点{x},{y}，正在准备记录图像')
            patrol.record_img()
            patrol.speech_text(f'图像记录完成')

    # BasicNavigator内部包含了spin了，所以这里就不需要了
    rclpy.shutdown()
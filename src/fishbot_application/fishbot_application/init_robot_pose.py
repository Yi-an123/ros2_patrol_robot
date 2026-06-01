from geometry_msgs.msg import PoseStamped #导入 ROS 2 标准消息类型，用于表示"带时间戳的三维位姿"（位置 + 朝向）
from nav2_simple_commander.robot_navigator import BasicNavigator
#导入 Nav2 的 Python 简化 API。BasicNavigator 封装了导航栈的底层调用，可以用几行代码就完成设置初始位姿、发送目标点等操作
import rclpy

def main():
    rclpy.init()
    nav = BasicNavigator() #节点
    #创建一个 BasicNavigator 对象。这个对象内部会启动一个 ROS 2 节点，并自动与 AMCL、planner_server、controller_server 等导航模块建立通信
    init_pose = PoseStamped() #创建一个空的位姿消息对象
    init_pose.header.frame_id = "map"
    #指定这个位姿是相对于 map 坐标系（世界坐标系）的。告诉 AMCL："我说的 (0, 0) 是地图原点"
    init_pose.header.stamp = nav.get_clock().now().to_msg()
    #打上当前时间戳。get_clock() 获取节点使用的时钟（仿真时间是 sim time，真机是 wall time），.now().to_msg() 转成 ROS 消息格式
    init_pose.pose.position.x = 0.0
    init_pose.pose.position.y = 0.0
    #设置初始位置为地图坐标 (0, 0)
    init_pose.pose.orientation.w = 1.0 # 表示朝向为0
    nav.setInitialPose(init_pose) #把初始位姿发给 AMCL。AMCL 收到后，会在 (0, 0) 位置初始化粒子群，定位就从这里开始
    nav.waitUntilNav2Active() # 等待导航键激活可用
    rclpy.spin(nav) #节点保活，纯属让程序别退出，维持节点运行
    rclpy.shutdown()
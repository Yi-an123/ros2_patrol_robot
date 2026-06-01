from geometry_msgs.msg import PoseStamped #导入 ROS 2 标准消息类型，用于表示"带时间戳的三维位姿"（位置 + 朝向）
from nav2_simple_commander.robot_navigator import BasicNavigator
#导入 Nav2 的 Python 简化 API。BasicNavigator 封装了导航栈的底层调用，可以用几行代码就完成设置初始位姿、发送目标点等操作
import rclpy

def main():
    rclpy.init()
    nav = BasicNavigator() #节点
    #创建一个 BasicNavigator 对象。这个对象内部会启动一个 ROS 2 节点，并自动与 AMCL、planner_server、controller_server 等导航模块建立通信
    nav.waitUntilNav2Active() # 等待导航键激活可用
    goal_pose = PoseStamped() #创建一个空的位姿消息对象
    goal_pose.header.frame_id = "map"
    #指定这个位姿是相对于 map 坐标系（世界坐标系）的。告诉 AMCL："我说的 (0, 0) 是地图原点"
    goal_pose.header.stamp = nav.get_clock().now().to_msg()
    #打上当前时间戳。get_clock() 获取节点使用的时钟（仿真时间是 sim time，真机是 wall time），.now().to_msg() 转成 ROS 消息格式
    goal_pose.pose.position.x = 2.0
    goal_pose.pose.position.y = 1.0
    #设置初始位置为地图坐标 (0, 0)
    goal_pose.pose.orientation.w = 1.0 # 表示朝向为0

    nav.goToPose(goal_pose)
    # 向 Nav2 发送导航目标 (2.0, 1.0)。BasicNavigator 内部会调用 planner_server 规划全局路径，
    # 再交给 controller_server 驱动小车沿路径走到目标点。这行是异步的——发完就程序继续往下走，不等待完成
    while not nav.isTaskComplete():
        #轮询检查导航任务是否结束。isTaskComplete() 返回 True 的情况有：到达目标、任务失败、任务被取消。这是个非阻塞的方法，调用立即返回，不会卡住
        feedback = nav.getFeedback()
        #获取导航过程的实时反馈。
        # BasicNavigator 内部订阅了 /follow_path 或 controller_server 发布的反馈话题，这里面包含当前剩余的直线距离、预计到达时间等数据
        nav.get_logger().info(f'剩余距离：{feedback.distance_remaining}')
        #distance_remaining 是 planner 规划的剩余路径长度（米），不是直线距离——机器人需要绕过障碍物的话，这个值比直线大
        #nav.cancelTask() 超时取消

    result = nav.getResult()
    nav.get_logger().info(f'导航结果：{result}')

    # rclpy.spin(nav) #goToPose内部包含了spin了，所以这里就不需要了
    # rclpy.shutdown()
import launch
import launch_ros # launch 在 ROS2 上的扩展，提供了 ROS2 特有的动作（如 Node）和参数描述（如 ParameterValue）
from ament_index_python.packages import get_package_share_directory
#返回某个 ROS2 包的 share/ 目录的安装路径，用来定位模型文件、配置文件等资源
import os #Python 标准库，用于路径拼接 (os.path.join)

def generate_launch_description():
    #每个 ROS2 Python launch 文件必须定义这个函数。它返回一个 LaunchDescription 对象，
    #描述了要启动的所有节点、参数和动作。ROS2 的 ros2 launch 命令会调用这个函数来获取启动配置
    #获取默认路径
    autopatrol_robot_path = get_package_share_directory('autopatrol_robot') 
    #获取 autopatrol_robot 包的 share 目录路径
    default_patrol_config_path = os.path.join(autopatrol_robot_path,'config','patrol_config.yaml')
    #拼接得到完整路径
    action_patrol_node = launch_ros.actions.Node(
        package='autopatrol_robot',
        executable='patrol_node',
        output='screen',
        parameters=[default_patrol_config_path],
    )
    
    action_speaker_node = launch_ros.actions.Node(
        #启动 rviz2 可视化工具节点
        package='autopatrol_robot',
        executable='speaker',
        output='screen',
    )

    return launch.LaunchDescription([
        action_patrol_node,
        action_speaker_node,
    ])
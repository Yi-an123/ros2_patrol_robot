import launch
import launch_ros # launch 在 ROS2 上的扩展，提供了 ROS2 特有的动作（如 Node）和参数描述（如 ParameterValue）
from ament_index_python.packages import get_package_share_directory
#返回某个 ROS2 包的 share/ 目录的安装路径，用来定位模型文件、配置文件等资源
import os #Python 标准库，用于路径拼接 (os.path.join)

def generate_launch_description():
    #每个 ROS2 Python launch 文件必须定义这个函数。它返回一个 LaunchDescription 对象，
    #描述了要启动的所有节点、参数和动作。ROS2 的 ros2 launch 命令会调用这个函数来获取启动配置
    #获取默认的share路径
    urdf_package_path = get_package_share_directory('fishbot_description') 
    #获取 fishbot_description 包的 share 目录路径
    default_xacro_path = os.path.join(urdf_package_path,'urdf','fishbot/fishbot.urdf.xacro')
    #拼接得到完整路径，.../share/fishbot_description/urdf/first_robot.urdf
    default_gazebo_world_path = os.path.join(urdf_package_path,'world','custom_room.world')
    action_declare_arg_mode_path = launch.actions.DeclareLaunchArgument(
        name = 'model',default_value=str(default_xacro_path),description='加载的模型文件路径'
    )
    #ros2 launch fishbot_description display_robot.launch.py model:=/其他路径/xxx.urdf 可以加载另一个模型

    #通过文件路径，获取内容，并转换成参数值对象，以供传入 robot_state_publisher
    substitutions_command_result = launch.substitutions.Command(['xacro ',
                                    launch.substitutions.LaunchConfiguration('model')])
    #相当于终端命令cat /xacro model的实际值（即urdf路径），会读取urdf文件内容
    #Command 是一个延迟求值的占位符。URDF 文件的内容要到 launch 启动（ros2 launch 命令执行后）才会被 cat /xacro 读出来
    robot_description_value = launch_ros.parameter_descriptions.ParameterValue(
        substitutions_command_result,value_type=str)
    # ParameterValue：告诉系统参数substitutions_command_result的值你现在还不知道，
    # 启动时候去执行Command拿，拿到后它就是 str字符串类型，直接传
    #robot_state_publisher需要一个名为 robot_description 的参数，其值就是整个 URDF 文件的文本内容

    action_robot_state_publisher = launch_ros.actions.Node(
        #启动一个 ROS2 节点
        #robot_state_publisher：发布整个 TF 树和模型数据，用于显示模型
        package = 'robot_state_publisher', #节点所在的包名
        executable = 'robot_state_publisher', #可执行文件名
        parameters = [{'robot_description':robot_description_value}]
    )#等同于终端命令效果:ros2 run rviz2 rviz2 --ros-args -p xx:=xxxvalue
    
    action_launch_gazebo = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            [get_package_share_directory('gazebo_ros'),'/launch','/gazebo.launch.py']
        ),
        launch_arguments=[('world',default_gazebo_world_path),('verbose','true')]
    )
    # 等同于使用终端命令：ros2 launch gazebo_ros gazebo.launch.py world:=xxx.world

    action_spawn_entity = launch_ros.actions.Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic','/robot_description','-entity','fishbot']

    )

    action_load_joint_state_controller = launch.actions.ExecuteProcess(
        cmd='ros2 control load_controller fishbot_joint_state_broadcaster --set-state active'.split(' '),
        output='screen'
    )

    action_load_effort_controller = launch.actions.ExecuteProcess(
        cmd='ros2 control load_controller fishbot_effort_controller --set-state active'.split(' '),
        output='screen'
    )

    action_load_diff_drive_controller = launch.actions.ExecuteProcess(
        cmd='ros2 control load_controller fishbot_diff_drive_controller --set-state active'.split(' '),
        output='screen'
    )

    return launch.LaunchDescription([
        action_declare_arg_mode_path,
        action_robot_state_publisher,
        action_launch_gazebo,
        action_spawn_entity,
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=action_spawn_entity,
                on_exit=[action_load_joint_state_controller],
            )
        ),
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=action_load_joint_state_controller,
                on_exit=[action_load_diff_drive_controller],
            )
        )
    ])
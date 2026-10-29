import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'bouncing_ball_catcher'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@todo.todo',
    description='Proyek Bouncing Ball Catcher ROS2 dan OpenCV',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'camera_node = bouncing_ball_catcher.camera_node:main',
            'game_node = bouncing_ball_catcher.game_node:main',
        ],
    },
)

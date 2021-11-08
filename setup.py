from setuptools import setup, find_packages
from glob import glob

setup(
    name='droneblocks-python-utils',
    version='0.1.1',
    packages=['droneblocks', 'droneblocksutils'],
    include_package_data=True,
    package_data={
        'media': glob('media/*'),
        'data': glob('data/*')
    },
    url='https://github.com/dbaldwin/DroneBlocks-Python-Utils',
    license='MIT',
    author='patrick ryan',
    author_email='theyoungsoul@gmail.com',
    description='DroneBlocks Python Utilities',
    install_requires=[
        'opencv-python==4.5.3.56',
        'opencv-contrib-python==4.5.3.56',
        'imutils==0.5.4',
        'djitellopy2==2.3',
    ],
    entry_points={
        'console_scripts':[
            'telloscriptrunner=droneblocks.tello_script_runner:main',
            'tt-matrix-generator=droneblocks.tt_matrix_generator:main'
        ]
    }
)

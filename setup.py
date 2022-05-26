from setuptools import setup, find_packages
from glob import glob

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='droneblocks-python-utils',
    version='0.1.9',
    packages=['droneblocks', 'droneblocksutils'],
    include_package_data=True,
    package_data={
        'media': glob('media/*'),
        'data': glob('data/*'),
        'web': glob('web/*')
    },
    url='https://github.com/dbaldwin/DroneBlocks-Python-Utils',
    license='MIT',
    author='Patrick Ryan, Dennis Baldwin',
    author_email='db@droneblocks.io',
    description='DroneBlocks Python Utilities',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        'opencv-python==4.5.5.62',
        'opencv-contrib-python==4.5.5.62',
        'imutils==0.5.4',
        'djitellopy==2.4',
        'bottle==0.12.19'
    ],
    entry_points={
        'console_scripts':[
            'telloscriptrunner=droneblocks.tello_script_runner:main',
            'tt-matrix-generator=droneblocks.tt_matrix_generator:main'
        ]
    }
)
